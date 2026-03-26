# TTS for Termux 🔊

在 Termux 中使用 TTS（文字转语音）API 播放音频。

## 功能特性

- ✅ 流式下载 TTS 音频
- ✅ mpv 播放器支持
- ✅ 音量调节 (0.1-2.0)
- ✅ 语速调节 (0.5-2.0)
- ✅ 播放控制（播放/暂停/继续/停止）
- ✅ 多说话人选择（Keira、老男人、青年女、少女）
- ✅ Web 界面

## 安装依赖

```bash
# 安装系统依赖
pkg install mpv sox termux-api -y

# 安装 Python 依赖
pip install flask requests
```

## 使用方法

### Web 界面（推荐）

```bash
# 启动完整版本（支持音量、语速、播放控制）
python3 advanced_tts.py

# 访问 http://localhost:5012
```

### 命令行

```bash
# 简单播放
python3 simple_speak.py "你好，测试" "Keira"

# 使用 mpv 直接播放
mpv "http://192.168.0.104:9880/?text=你好&speaker=Keira" --no-video

# 调节语速
mpv "http://192.168.0.104:9880/?text=你好&speaker=Keira" --no-video --speed=1.5

# 调节音量
mpv "http://192.168.0.104:9880/?text=你好&speaker=Keira" --no-video --volume=150
```

## 项目文件

| 文件 | 说明 |
|------|------|
| `advanced_tts.py` | 完整功能 Web 版本（5012 端口） |
| `mpv_web.py` | mpv 基础 Web 版本（5011 端口） |
| `simple_speak.py` | 简单命令行播放脚本 |
| `stream_tts.py` | 流式下载测试脚本 |

## API 接口

```
http://192.168.0.104:9880/?text={文字}&speaker={说话人}
```

**参数：**
- `text` - 要合成的文字
- `speaker` - 说话人（Keira、老男人、青年女、少女等）

## 说话人列表

- Keira
- 老男人
- 青年女
- 少女

## 注意事项

1. 确保 TTS API 服务器（192.168.0.104:9880）可访问
2. 授予 Termux 必要的权限（存储、音频）
3. 使用 mpv 播放器获得最佳体验

## 许可证

MIT License

## 作者

qiaoranweixia
