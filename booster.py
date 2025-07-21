#!/usr/bin/env python3
"""
Bilibili View Count Booster

A tool to boost view counts for Bilibili videos using proxy rotation.
"""

import sys
import threading
import random
import argparse
import logging
import json
from time import sleep
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from fake_useragent import UserAgent


class Config:
    """Configuration class for the booster."""

    def __init__(self):
        self.timeout = 3  # seconds for proxy connection timeout
        self.thread_num = 75  # thread count for filtering active proxies
        self.round_time = 305  # seconds for each round of view count boosting
        self.update_pbar_count = 10  # update view count progress bar for every xx proxies
        self.max_proxies = 10000  # maximum number of proxies to use
        self.min_proxies_threshold = 100  # minimum proxies needed to proceed

    def load_from_file(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except FileNotFoundError:
            logging.warning(f"Config file {config_path} not found, using default settings")
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in config file: {e}")


class Statistics:
    """Statistics tracking for the booster."""

    def __init__(self):
        self.successful_hits = 0
        self.initial_view_count = 0
        self.start_time = None
        self.end_time = None

    def calculate_success_rate(self, total_proxies: int) -> float:
        """Calculate success rate percentage."""
        return (self.successful_hits / total_proxies * 100) if total_proxies > 0 else 0.0

    def get_duration(self) -> timedelta:
        """Get total duration of the boosting process."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return timedelta(0)

class BilibiliBooster:
    """Main class for Bilibili view count boosting."""

    def __init__(self, config: Config):
        self.config = config
        self.stats = Statistics()
        self.active_proxies: List[str] = []
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('bilibili_booster')
        logger.setLevel(logging.INFO)

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add handler to logger
        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    @staticmethod
    def format_time(seconds: int) -> str:
        """Format seconds into human readable time string."""
        if seconds < 60:
            return f'{seconds}s'
        else:
            return f'{int(seconds / 60)}min {seconds % 60}s'

    @staticmethod
    def format_progress_bar(n: int, total: int, hits: Optional[int] = None,
                           view_increase: Optional[int] = None) -> str:
        """Format progress bar string."""
        progress = '━' * int(n / total * 50) if total > 0 else ''
        blank = ' ' * (50 - len(progress))
        if hits is None or view_increase is None:
            return f'\r{n}/{total} {progress}{blank}'
        else:
            return f'\r{n}/{total} {progress}{blank} [Hits: {hits}, Views+: {view_increase}]'

    def get_proxies(self) -> List[str]:
        """Get proxy list from checkerproxy.net API."""
        self.logger.info("Starting proxy collection...")

        day = date.today()
        max_attempts = 7  # Try up to 7 days back

        for attempt in range(max_attempts):
            day = day - timedelta(days=1)
            proxy_url = f'https://api.checkerproxy.net/v1/landing/archive/{day.strftime("%Y-%m-%d")}'
            self.logger.info(f'Getting proxies from {proxy_url}...')

            try:
                response = requests.get(proxy_url, timeout=10)
                if response.status_code == requests.codes.ok:
                    data = response.json()
                    proxies_obj = data['data']['proxyList']

                    # Extract proxies based on data structure
                    if isinstance(proxies_obj, list):
                        total_proxies = proxies_obj
                    elif isinstance(proxies_obj, dict):
                        total_proxies = [proxy for proxy in proxies_obj.values() if proxy]
                    else:
                        raise TypeError(f'Unexpected type of $.data.proxyList: {type(proxies_obj)}')

                    # Check if we have enough proxies
                    if len(total_proxies) >= self.config.min_proxies_threshold:
                        self.logger.info(f'Successfully got {len(total_proxies)} proxies')

                        # Limit proxy count if too many
                        if len(total_proxies) > self.config.max_proxies:
                            self.logger.info(f'More than {self.config.max_proxies} proxies, randomly selecting {self.config.max_proxies}')
                            random.shuffle(total_proxies)
                            total_proxies = total_proxies[:self.config.max_proxies]

                        return total_proxies
                    else:
                        self.logger.warning(f'Only found {len(total_proxies)} proxies, need at least {self.config.min_proxies_threshold}')
                else:
                    self.logger.warning(f'Failed to get proxies: HTTP {response.status_code}')

            except requests.RequestException as e:
                self.logger.error(f'Request failed: {e}')
            except (KeyError, TypeError, json.JSONDecodeError) as e:
                self.logger.error(f'Failed to parse proxy data: {e}')

        raise RuntimeError(f"Could not find sufficient proxies after {max_attempts} attempts")

    def filter_proxies(self, total_proxies: List[str]) -> List[str]:
        """Filter active proxies using multi-threading."""
        self.logger.info(f"Filtering {len(total_proxies)} proxies using {self.config.thread_num} threads...")

        active_proxies = []
        count = 0
        lock = threading.Lock()

        def filter_proxy_batch(proxies: List[str]) -> None:
            nonlocal count
            for proxy in proxies:
                with lock:
                    count += 1
                    progress = self.format_progress_bar(count, len(total_proxies))
                    print(f'{progress} {100*count/len(total_proxies):.1f}%   ', end='')

                try:
                    response = requests.post(
                        'http://httpbin.org/post',
                        proxies={'http': f'http://{proxy}'},
                        timeout=self.config.timeout
                    )
                    if response.status_code == 200:
                        with lock:
                            active_proxies.append(proxy)
                except requests.RequestException:
                    # Proxy connection failed, skip it
                    pass

        start_filter_time = datetime.now()

        # Calculate proxies per thread
        thread_proxy_num = len(total_proxies) // self.config.thread_num
        threads = []

        for i in range(self.config.thread_num):
            start_idx = i * thread_proxy_num
            end_idx = start_idx + thread_proxy_num if i < (self.config.thread_num - 1) else len(total_proxies)

            thread = threading.Thread(
                target=filter_proxy_batch,
                args=(total_proxies[start_idx:end_idx],)
            )
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        filter_duration = int((datetime.now() - start_filter_time).total_seconds())
        self.logger.info(f'\nSuccessfully filtered {len(active_proxies)} active proxies in {self.format_time(filter_duration)}')

        if len(active_proxies) == 0:
            raise RuntimeError("No active proxies found")

        return active_proxies

    def get_video_info(self, bvid: str) -> Dict[str, Any]:
        """Get video information from Bilibili API."""
        try:
            response = requests.get(
                f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}',
                headers={'User-Agent': UserAgent().random},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data['code'] != 0:
                raise RuntimeError(f"Bilibili API error: {data.get('message', 'Unknown error')}")

            return data['data']
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get video info: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to parse video info: {e}")

    def boost_view_count(self, bvid: str, target: int) -> None:
        """Main function to boost view count."""
        self.logger.info(f"Starting view count boosting for {bvid} at {datetime.now().strftime('%H:%M:%S')}")

        # Get initial video info
        try:
            info = self.get_video_info(bvid)
            self.stats.initial_view_count = info['stat']['view']
            current_views = self.stats.initial_view_count
            self.logger.info(f'Initial view count: {self.stats.initial_view_count}')
        except Exception as e:
            self.logger.error(f'Failed to get initial view count: {e}')
            return

        self.stats.start_time = datetime.now()

        while current_views < target:
            reach_target = False
            round_start_time = datetime.now()

            # Send click requests for each proxy
            for i, proxy in enumerate(self.active_proxies):
                try:
                    # Update view count periodically
                    if i % self.config.update_pbar_count == 0:
                        progress = self.format_progress_bar(
                            current_views, target, self.stats.successful_hits,
                            current_views - self.stats.initial_view_count
                        )
                        print(f'{progress} updating view count...', end='')

                        try:
                            updated_info = self.get_video_info(bvid)
                            current_views = updated_info['stat']['view']
                            info = updated_info  # Update info for click requests

                            if current_views >= target:
                                reach_target = True
                                progress = self.format_progress_bar(
                                    current_views, target, self.stats.successful_hits,
                                    current_views - self.stats.initial_view_count
                                )
                                print(f'{progress} done                 ', end='')
                                break
                        except Exception as e:
                            self.logger.warning(f"Failed to update view count: {e}")

                    # Send click request
                    click_data = {
                        'aid': info['aid'],
                        'cid': info['cid'],
                        'bvid': bvid,
                        'part': '1',
                        'mid': info['owner']['mid'],
                        'jsonp': 'jsonp',
                        'type': info['desc_v2'][0]['type'] if info.get('desc_v2') else '1',
                        'sub_type': '0'
                    }

                    response = requests.post(
                        'http://api.bilibili.com/x/click-interface/click/web/h5',
                        proxies={'http': f'http://{proxy}'},
                        headers={'User-Agent': UserAgent().random},
                        timeout=self.config.timeout,
                        data=click_data
                    )

                    if response.status_code == 200:
                        self.stats.successful_hits += 1
                        progress = self.format_progress_bar(
                            current_views, target, self.stats.successful_hits,
                            current_views - self.stats.initial_view_count
                        )
                        print(f'{progress} proxy({i+1}/{len(self.active_proxies)}) success   ', end='')
                    else:
                        progress = self.format_progress_bar(
                            current_views, target, self.stats.successful_hits,
                            current_views - self.stats.initial_view_count
                        )
                        print(f'{progress} proxy({i+1}/{len(self.active_proxies)}) fail      ', end='')

                except requests.RequestException:
                    progress = self.format_progress_bar(
                        current_views, target, self.stats.successful_hits,
                        current_views - self.stats.initial_view_count
                    )
                    print(f'{progress} proxy({i+1}/{len(self.active_proxies)}) fail      ', end='')

            if reach_target:
                break

            # Wait for next round if needed
            elapsed_time = (datetime.now() - round_start_time).total_seconds()
            remain_seconds = int(self.config.round_time - elapsed_time)

            if remain_seconds > 0:
                for second in reversed(range(remain_seconds)):
                    progress = self.format_progress_bar(
                        current_views, target, self.stats.successful_hits,
                        current_views - self.stats.initial_view_count
                    )
                    print(f'{progress} next round: {self.format_time(second)}          ', end='')
                    sleep(1)

        self.stats.end_time = datetime.now()

        # Final view count check
        try:
            final_info = self.get_video_info(bvid)
            final_views = final_info['stat']['view']
        except Exception:
            final_views = current_views

        self.print_final_statistics(final_views)

    def print_final_statistics(self, final_views: int) -> None:
        """Print final statistics."""
        success_rate = self.stats.calculate_success_rate(len(self.active_proxies))
        duration = self.stats.get_duration()

        print(f'\nFinished at {datetime.now().strftime("%H:%M:%S")}')
        print('=' * 50)
        print('FINAL STATISTICS')
        print('=' * 50)
        print(f'- Initial views: {self.stats.initial_view_count:,}')
        print(f'- Final views: {final_views:,}')
        print(f'- Total increase: {final_views - self.stats.initial_view_count:,}')
        print(f'- Successful hits: {self.stats.successful_hits:,}')
        print(f'- Success rate: {success_rate:.2f}%')
        print(f'- Total duration: {self.format_time(int(duration.total_seconds()))}')
        print(f'- Active proxies used: {len(self.active_proxies):,}')
        print('=' * 50)

    def run(self, bvid: str, target: int) -> None:
        """Main execution function."""
        try:
            # Step 1: Get proxies
            total_proxies = self.get_proxies()

            # Step 2: Filter active proxies
            self.active_proxies = self.filter_proxies(total_proxies)

            # Step 3: Boost view count
            self.boost_view_count(bvid, target)

        except Exception as e:
            self.logger.error(f"Boosting failed: {e}")
            raise


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Bilibili View Count Booster',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python booster.py BV1fz421o8J7 1000
  python booster.py BV1fz421o8J7 1000 --config config.json
  python booster.py BV1fz421o8J7 1000 --threads 50 --timeout 5
        """
    )

    parser.add_argument('bvid', help='Bilibili video BV ID (e.g., BV1fz421o8J7)')
    parser.add_argument('target', type=int, help='Target view count')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--threads', '-t', type=int, help='Number of threads for proxy filtering')
    parser.add_argument('--timeout', type=int, help='Timeout for proxy requests (seconds)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config = Config()
    if args.config:
        config.load_from_file(args.config)

    # Override config with command line arguments
    if args.threads:
        config.thread_num = args.threads
    if args.timeout:
        config.timeout = args.timeout

    # Validate arguments
    if args.target <= 0:
        print("Error: Target view count must be positive")
        sys.exit(1)

    if not args.bvid.startswith('BV'):
        print("Error: Invalid BV ID format")
        sys.exit(1)

    # Run the booster
    booster = BilibiliBooster(config)
    try:
        booster.run(args.bvid, args.target)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
