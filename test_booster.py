#!/usr/bin/env python3
"""
Unit tests for Bilibili View Count Booster
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta

from booster import Config, Statistics, BilibiliBooster


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        self.assertEqual(config.timeout, 3)
        self.assertEqual(config.thread_num, 75)
        self.assertEqual(config.round_time, 305)
        self.assertEqual(config.update_pbar_count, 10)
        self.assertEqual(config.max_proxies, 10000)
        self.assertEqual(config.min_proxies_threshold, 100)
    
    def test_load_from_file(self):
        """Test loading configuration from file."""
        config = Config()
        
        # Test with non-existent file
        config.load_from_file('non_existent.json')
        self.assertEqual(config.timeout, 3)  # Should remain default
        
        # Test with valid config
        test_config = {
            'timeout': 5,
            'thread_num': 50,
            'max_proxies': 5000
        }
        
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(test_config))):
            config.load_from_file('test_config.json')
            self.assertEqual(config.timeout, 5)
            self.assertEqual(config.thread_num, 50)
            self.assertEqual(config.max_proxies, 5000)
            self.assertEqual(config.round_time, 305)  # Should remain default


class TestStatistics(unittest.TestCase):
    """Test cases for Statistics class."""
    
    def test_initial_values(self):
        """Test initial statistics values."""
        stats = Statistics()
        self.assertEqual(stats.successful_hits, 0)
        self.assertEqual(stats.initial_view_count, 0)
        self.assertIsNone(stats.start_time)
        self.assertIsNone(stats.end_time)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = Statistics()
        stats.successful_hits = 50
        
        # Test with valid total
        self.assertEqual(stats.calculate_success_rate(100), 50.0)
        
        # Test with zero total
        self.assertEqual(stats.calculate_success_rate(0), 0.0)
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        stats = Statistics()
        
        # Test with no times set
        self.assertEqual(stats.get_duration(), timedelta(0))
        
        # Test with times set
        stats.start_time = datetime(2024, 1, 1, 10, 0, 0)
        stats.end_time = datetime(2024, 1, 1, 10, 5, 30)
        expected_duration = timedelta(minutes=5, seconds=30)
        self.assertEqual(stats.get_duration(), expected_duration)


class TestBilibiliBooster(unittest.TestCase):
    """Test cases for BilibiliBooster class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        self.booster = BilibiliBooster(self.config)
    
    def test_format_time(self):
        """Test time formatting."""
        self.assertEqual(BilibiliBooster.format_time(30), '30s')
        self.assertEqual(BilibiliBooster.format_time(90), '1min 30s')
        self.assertEqual(BilibiliBooster.format_time(3661), '61min 1s')
    
    def test_format_progress_bar(self):
        """Test progress bar formatting."""
        # Test without hits and view increase
        result = BilibiliBooster.format_progress_bar(50, 100)
        self.assertIn('50/100', result)
        
        # Test with hits and view increase
        result = BilibiliBooster.format_progress_bar(50, 100, 25, 10)
        self.assertIn('50/100', result)
        self.assertIn('Hits: 25', result)
        self.assertIn('Views+: 10', result)
    
    @patch('requests.get')
    def test_get_video_info_success(self, mock_get):
        """Test successful video info retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'aid': 123456,
                'cid': 789012,
                'stat': {'view': 1000},
                'owner': {'mid': 345678}
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.booster.get_video_info('BV1234567890')
        self.assertEqual(result['aid'], 123456)
        self.assertEqual(result['stat']['view'], 1000)
    
    @patch('requests.get')
    def test_get_video_info_api_error(self, mock_get):
        """Test video info retrieval with API error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': -1,
            'message': 'Video not found'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.assertRaises(RuntimeError) as context:
            self.booster.get_video_info('BV1234567890')
        
        self.assertIn('Bilibili API error', str(context.exception))


if __name__ == '__main__':
    unittest.main()
