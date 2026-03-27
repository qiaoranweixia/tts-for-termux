# TTS for Termux 🔊

在 Termux 中使用 TTS（文字转语音）+ Whisper STT（语音识别）的语音交互系统。

## 功能特性

- ✅ **Whisper 本地语音识别**（STT）
- ✅ **流式下载 TTS 音频**
- ✅ **mpv 播放器支持**
- ✅ **音量调节** (0.1-2.0)
- ✅ **语速调节** (0.5-2.0)
- ✅ **播放控制**（播放/暂停/继续/停止）
- ✅ **多说话人选择**（Keira、老男人、青年女、少女）
- ✅ **Web 界面**
- ✅ **语音聊天模式**（录音→识别→回复→朗读）

## 安装依赖

### 1. 系统依赖

```bash
# 基础依赖
pkg install mpv sox termux-api ffmpeg -y

# 语音识别依赖（可选）
pip install pyaudio webrtcvad
```

### 2. Python 依赖

```bash
pip install flask requests

# Whisper 语音识别（可选，约 39MB+ 模型）
pip install openai-whisper
```

### 3. 下载 Whisper 模型（首次运行自动下载）

Whisper 模型大小：
- `tiny` - 39 MB（推荐，速度快）
- `base` - 74 MB
- `small` - 244 MB
- `medium` - 769 MB
- `large` - 1.5 GB

### 4. 下载 Llama 模型（用于 AI 回复）

```bash
mkdir -p ~/.llama/models
cd ~/.llama/models

# Qwen2.5 0.5B 量化版（推荐，约 400MB）
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
```

### 5. 安装 llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j4
cp llama-cli ~/.local/bin/
```

## 使用方法

### 🤖 完整语音助手（Whisper + Llama + TTS）- 推荐

```bash
# 启动完整语音助手
python3 voice_llama.py

# 访问 http://localhost:5014
```

**完整流程：**
1. 🎤 **按住说话** → 录音
2. 🧠 **Whisper 识别** → 文字
3. 💭 **Llama 思考** → AI 回复
4. 🔊 **TTS 朗读** → 语音播放

**功能：**
- 🎙️ 语音识别（Whisper）
- 🤖 AI 对话（Llama）
- 🔊 语音合成（TTS）
- ⚙️ 多说话人、语速调节
- 💬 文字输入备用

### 🎙️ 语音聊天助手（简化版 - 推荐）

```bash
# 启动语音聊天（无需 Whisper）
python3 voice_chat_simple.py

# 访问 http://localhost:5013
```

功能：
- 💬 文字输入 → AI 回复 → 语音播放
- ⚙️ 可调节说话人、语速
- ✅ 无需复杂依赖

### 🎙️ 语音聊天助手（完整版 - 需 Whisper）

```bash
# 安装 Whisper（可选）
pip install openai-whisper

# 启动完整版（支持语音识别）
python3 voice_chat.py

# 访问 http://localhost:5013
```

功能：
- 🎤 点击录音 → 说话 → 自动识别（Whisper）
- 💬 文字输入 → AI 回复 → 语音播放
- ⚙️ 可调节说话人、语速

### Web 界面（TTS 播放）

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

| 文件 | 说明 | 端口 |
|------|------|------|
| `voice_llama.py` | 🆕 **完整语音助手** (Whisper+Llama+TTS) | 5014 |
| `voice_chat_simple.py` | 语音聊天（简化版） | 5013 |
| `voice_chat.py` | 语音聊天（完整版+Whisper） | 5013 |
| `advanced_tts.py` | 完整 TTS Web | 5012 |
| `mpv_web.py` | mpv TTS Web | 5011 |
| `tts_web.py` | TTS Web 界面 | - |
| `app_termux.py` | Termux 专用版本 | - |
| `robust_tts.py` | 稳定版本 | - |
| `stream_tts.py` | 流式下载测试 | - |
| `simple_speak.py` | 简单命令行播放 | - |

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
