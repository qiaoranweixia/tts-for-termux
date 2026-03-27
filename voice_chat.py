#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音聊天助手 - Whisper STT + TTS 播放
支持本地语音识别 + TTS 语音合成
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import subprocess
import json
import os
import tempfile
import wave
import pyaudio
import threading
import time

app = Flask(__name__)

# TTS API 配置
TTS_API = "http://192.168.0.104:9880/"

# Whisper 配置
WHISPER_MODEL = "tiny"  # tiny, base, small, medium, large
whisper_model = None

# 音频配置
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024

# 全局状态
is_recording = False
current_audio = None


def load_whisper():
    """加载 Whisper 模型"""
    global whisper_model
    try:
        import whisper
        print(f"🎯 加载 Whisper 模型：{WHISPER_MODEL}...")
        whisper_model = whisper.load_model(WHISPER_MODEL)
        print("✅ Whisper 模型加载完成")
        return True
    except Exception as e:
        print(f"❌ Whisper 加载失败：{e}")
        return False


def record_audio(duration=5):
    """录音函数"""
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )
    
    print(f"🎤 录音中... ({duration}秒)")
    frames = []
    
    for _ in range(0, int(SAMPLE_RATE / CHUNK_SIZE * duration)):
        data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    return b''.join(frames)


def save_wav(audio_data, filepath):
    """保存为 WAV 文件"""
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data)


def speech_to_text(audio_data):
    """语音转文字"""
    if whisper_model is None:
        return None, "Whisper 模型未加载"
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
        save_wav(audio_data, temp_wav)
    
    try:
        result = whisper_model.transcribe(
            temp_wav,
            language="zh",
            task="transcribe"
        )
        text = result["text"].strip()
        return text, None
    except Exception as e:
        return None, str(e)
    finally:
        os.unlink(temp_wav)


def tts_to_audio(text, speaker="Keira", speed=1.0):
    """TTS 文字转音频"""
    try:
        url = f"{TTS_API}?text={requests.utils.quote(text)}&speaker={speaker}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_mp3 = f.name
                f.write(response.content)
            return temp_mp3, None
        else:
            return None, f"TTS API 错误：{response.status_code}"
    except Exception as e:
        return None, str(e)


def play_audio(filepath, speed=1.0):
    """播放音频文件"""
    try:
        cmd = ["mpv", "--no-video", f"--speed={speed}", filepath]
        subprocess.run(cmd, check=True)
        return True, None
    except Exception as e:
        return False, str(e)


# HTML 模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎙️ 语音聊天助手</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        
        .chat-box {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            min-height: 300px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .user-msg {
            background: rgba(233, 69, 96, 0.3);
            border: 1px solid #e94560;
            margin-left: auto;
            text-align: right;
        }
        
        .assistant-msg {
            background: rgba(74, 144, 217, 0.3);
            border: 1px solid #4a90d9;
            margin-right: auto;
        }
        
        .system-msg {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid #ffc107;
            text-align: center;
            margin: 10px auto;
            font-size: 14px;
        }
        
        .controls {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
        }
        
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; }
        
        .btn {
            flex: 1;
            min-width: 120px;
            padding: 15px 20px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-record {
            background: linear-gradient(135deg, #e94560, #ff6b6b);
            color: #fff;
        }
        
        .btn-record:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(233,69,96,0.4); }
        .btn-record:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        .btn-clear {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        
        .input-group { margin-bottom: 15px; }
        
        textarea {
            width: 100%;
            min-height: 80px;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 16px;
            resize: vertical;
        }
        
        .settings {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        select, input[type="range"] {
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .slider-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 14px;
            color: #888;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 10px 15px;
            text-align: center;
            font-size: 14px;
            color: #888;
        }
        
        .recording {
            animation: pulse 1s infinite;
            background: rgba(233, 69, 96, 0.3);
            color: #fff;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .loading { color: #ffc107; }
        .success { color: #4caf50; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ 语音聊天助手</h1>
        <p class="subtitle">Whisper 语音识别 + TTS 语音合成</p>
        
        <div class="chat-box" id="chatBox">
            <div class="message system-msg">👋 点击"🎤 录音"开始说话，或直接输入文字</div>
        </div>
        
        <div class="controls">
            <div class="settings">
                <div>
                    <div class="slider-label"><span>🎭 说话人</span></div>
                    <select id="speaker">
                        <option value="Keira">Keira</option>
                        <option value="老男人">老男人</option>
                        <option value="青年女">青年女</option>
                        <option value="少女">少女</option>
                    </select>
                </div>
                <div>
                    <div class="slider-label"><span>⚡ 语速：<span id="speedVal">1.0</span></span></div>
                    <input type="range" id="speed" min="0.5" max="2.0" step="0.1" value="1.0">
                </div>
            </div>
            
            <div class="input-group">
                <textarea id="textInput" placeholder="输入文字，或点击录音按钮说话..."></textarea>
            </div>
            
            <div class="btn-group">
                <button class="btn btn-record" id="recordBtn" onclick="toggleRecord()">🎤 录音</button>
                <button class="btn" onclick="sendText()" style="background: #4a90d9;">📤 发送</button>
                <button class="btn btn-clear" onclick="clearChat()">🗑️ 清空</button>
            </div>
            
            <div class="status-bar" id="statusBar">就绪</div>
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let chatHistory = [];
        
        document.getElementById('speed').addEventListener('input', function() {
            document.getElementById('speedVal').textContent = this.value;
        });
        
        function addMessage(text, type) {
            const chatBox = document.getElementById('chatBox');
            const msg = document.createElement('div');
            msg.className = `message ${type}-msg`;
            msg.textContent = text;
            chatBox.appendChild(msg);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function clearChat() {
            document.getElementById('chatBox').innerHTML = '<div class="message system-msg">👋 对话已清空</div>';
            chatHistory = [];
        }
        
        function setStatus(text, className) {
            const bar = document.getElementById('statusBar');
            bar.textContent = text;
            bar.className = 'status-bar ' + className;
        }
        
        async function toggleRecord() {
            if (isRecording) {
                // 停止录音
                isRecording = false;
                document.getElementById('recordBtn').disabled = true;
                document.getElementById('recordBtn').textContent = '⏳ 处理中...';
                setStatus('🔄 识别中...', 'loading');
                
                const r = await fetch('/api/recognize', { method: 'POST' });
                const d = await r.json();
                
                if (d.success) {
                    addMessage(d.text, 'user');
                    document.getElementById('textInput').value = d.text;
                    setStatus('✅ 识别完成', 'success');
                } else {
                    setStatus('❌ ' + d.error, 'error');
                }
                
                document.getElementById('recordBtn').disabled = false;
                document.getElementById('recordBtn').textContent = '🎤 录音';
            } else {
                // 开始录音
                isRecording = true;
                document.getElementById('recordBtn').classList.add('recording');
                document.getElementById('recordBtn').textContent = '⏹️ 停止';
                setStatus('🎤 录音中... 请说话（5 秒）', 'loading');
                
                await fetch('/api/start_record', { method: 'POST' });
            }
        }
        
        async function sendText() {
            const text = document.getElementById('textInput').value.trim();
            if (!text) return;
            
            const speaker = document.getElementById('speaker').value;
            const speed = document.getElementById('speed').value;
            
            addMessage(text, 'user');
            document.getElementById('textInput').value = '';
            setStatus('🤖 思考中...', 'loading');
            
            const r = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, speaker, speed })
            });
            const d = await r.json();
            
            if (d.success) {
                addMessage(d.reply, 'assistant');
                setStatus('✅ 播放完成', 'success');
            } else {
                setStatus('❌ ' + d.error, 'error');
            }
        }
        
        // 按 Enter 发送（Shift+Enter 换行）
        document.getElementById('textInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendText();
            }
        });
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/start_record', methods=['POST'])
def start_record():
    """开始录音"""
    global is_recording, current_audio
    
    def record_thread():
        global current_audio
        current_audio = record_audio(duration=5)
    
    thread = threading.Thread(target=record_thread)
    thread.start()
    
    return jsonify({'success': True, 'msg': '录音已开始'})


@app.route('/api/recognize', methods=['POST'])
def recognize():
    """语音识别"""
    global current_audio
    
    if current_audio is None:
        return jsonify({'success': False, 'error': '没有录音数据'})
    
    if whisper_model is None:
        return jsonify({'success': False, 'error': 'Whisper 模型未加载'})
    
    text, error = speech_to_text(current_audio)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    return jsonify({'success': True, 'text': text})


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天：TTS 回复"""
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    speed = data.get('speed', '1.0')
    
    if not text:
        return jsonify({'success': False, 'error': '文字不能为空'})
    
    # 简单的回复逻辑（可以扩展为调用 LLM）
    reply = generate_reply(text)
    
    # TTS 播放
    audio_file, error = tts_to_audio(reply, speaker, speed)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    success, error = play_audio(audio_file, speed)
    os.unlink(audio_file)
    
    if not success:
        return jsonify({'success': False, 'error': error})
    
    return jsonify({'success': True, 'reply': reply})


def generate_reply(user_text):
    """生成简单回复（可扩展为 LLM）"""
    responses = {
        "你好": "你好！有什么我可以帮你的吗？",
        "hello": "Hello! How can I help you today?",
        "再见": "再见！祝你有美好的一天！",
        "谢谢": "不客气！随时为你服务。",
        "叫什么名字": "我是你的语音助手，很高兴为你服务！",
        "你是谁": "我是一个智能语音助手，可以陪你聊天。",
    }
    
    for key, value in responses.items():
        if key in user_text.lower():
            return value
    
    return f"我听到了：{user_text}。这是一个简单的回复，可以集成 LLM 来获得更智能的回答。"


if __name__ == '__main__':
    print("=" * 50)
    print("🎙️ 语音聊天助手")
    print("=" * 50)
    
    # 加载 Whisper
    load_whisper()
    
    print("\n🌐 访问 http://localhost:5013")
    print("💡 按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5013, debug=False)
