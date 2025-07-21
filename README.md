# Bilibili View Count Booster

一个用于提升B站视频播放量的工具，使用[代理池](https://checkerproxy.net/getAllProxy)对目标视频进行轮询点击，模拟游客观看。

## 特性

- 🚀 **高效稳定**: 多线程代理过滤，速度约为8播放量/分钟
- 🔧 **配置灵活**: 支持配置文件和命令行参数
- 📊 **详细统计**: 实时显示进度和最终统计信息
- 🛡️ **错误处理**: 完善的异常处理和日志记录
- 🧪 **测试覆盖**: 包含单元测试确保代码质量

## 工作原理

B站目前限制同一IP对视频点击间隔大于5分钟，本工具通过代理轮询来绕过这个限制：

1. 从代理池获取大量代理服务器
2. 多线程过滤出可用的代理
3. 使用代理轮询发送点击请求
4. 实时监控播放量变化

## 安装使用

### 方法一：Python环境
```bash
# 克隆仓库
git clone https://github.com/TwTsimon/bilibili-viewcount-booster.git
cd bilibili-viewcount-booster

# 安装依赖
pip install -r requirements.txt

# 基本使用
python booster.py <BV号> <目标播放数>

# 高级使用
python booster.py BV1fz421o8J7 1000 --config config.json --threads 50 --verbose
```

### 方法二：预编译二进制文件
1. 在[Release界面](https://github.com/TwTsimon/bilibili-viewcount-booster/releases/latest)下载对应系统的文件
2. 重命名为`booster`(Windows为`booster.exe`)
3. 在终端中运行：
```bash
# macOS/Linux需要添加执行权限
chmod +x booster

# 运行
./booster <BV号> <目标播放数>
```

> [!NOTE]
> macOS可能会遇到安全警告，请参考[Apple官方解决方案](https://support.apple.com/zh-cn/guide/mac-help/mchleab3a043/mac)

## 命令行参数

```bash
python booster.py [-h] [--config CONFIG] [--threads THREADS] [--timeout TIMEOUT] [--verbose] bvid target

positional arguments:
  bvid                  Bilibili video BV ID (e.g., BV1fz421o8J7)
  target                Target view count

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Configuration file path
  --threads THREADS, -t THREADS
                        Number of threads for proxy filtering
  --timeout TIMEOUT     Timeout for proxy requests (seconds)
  --verbose, -v         Enable verbose logging
```

## 配置文件

创建 `config.json` 文件来自定义设置：

```json
{
  "timeout": 3,
  "thread_num": 75,
  "round_time": 305,
  "update_pbar_count": 10,
  "max_proxies": 10000,
  "min_proxies_threshold": 100
}
```

### 配置说明

- `timeout`: 代理连接超时时间（秒）
- `thread_num`: 代理过滤线程数
- `round_time`: 每轮播放量提升的时间间隔（秒）
- `update_pbar_count`: 每处理多少个代理更新一次进度
- `max_proxies`: 最大使用代理数量
- `min_proxies_threshold`: 最少需要的可用代理数

## 运行效果

```bash
$ python booster.py BV1fz421o8J7 1000

2024-07-21 20:27:30 - bilibili_booster - INFO - Starting proxy collection...
2024-07-21 20:27:31 - bilibili_booster - INFO - Getting proxies from https://api.checkerproxy.net/v1/landing/archive/2024-07-20...
2024-07-21 20:27:32 - bilibili_booster - INFO - Successfully got 2,624 proxies
2024-07-21 20:27:32 - bilibili_booster - INFO - Filtering 2,624 proxies using 75 threads...

2624/2624 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100.0%
2024-07-21 20:32:08 - bilibili_booster - INFO - Successfully filtered 165 active proxies in 4min 36s

2024-07-21 20:32:08 - bilibili_booster - INFO - Starting view count boosting for BV1fz421o8J7 at 20:32:08
2024-07-21 20:32:09 - bilibili_booster - INFO - Initial view count: 298

361/1000 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ [Hits: 697, Views+: 63] done

Finished at 20:58:00
==================================================
FINAL STATISTICS
==================================================
- Initial views: 298
- Final views: 361
- Total increase: 63
- Successful hits: 697
- Success rate: 43.80%
- Total duration: 25min 52s
- Active proxies used: 165
==================================================
```

## 测试

运行单元测试：

```bash
python -m pytest test_booster.py -v
# 或者
python test_booster.py
```

## 注意事项

⚠️ **免责声明**: 本工具仅供学习和研究使用，请遵守相关法律法规和平台规则。

- 请合理使用，避免对B站服务器造成过大压力
- 建议在测试环境中先验证功能
- 代理质量会影响成功率，建议选择稳定的代理源

## 开发

### 项目结构

```
bilibili-viewcount-booster/
├── booster.py          # 主程序
├── config.json         # 配置文件示例
├── test_booster.py     # 单元测试
├── requirements.txt    # Python依赖
├── README.md          # 说明文档
└── .github/
    └── workflows/
        └── release.yml # GitHub Actions自动构建
```

### 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 参考

- [原始项目](https://github.com/xu0329/bilibili_proxy)
- [代理池API](https://checkerproxy.net/getAllProxy)
  
