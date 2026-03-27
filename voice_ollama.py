#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音助手：Whisper/其他 STT + Ollama LLM + TTS
配置灵活，支持多种语音识别方案
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import subprocess
import json
import os
import tempfile
import threading
import time

app = Flask(__name__)

# ============ 配置 ============

# TTS API
TTS_API = "http://192.168.0.104:9880/"

# Ollama API 配置（请根据实际情况修改）
OLLAMA_API = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:0.5b"  # 或 llama2, mistral 等

# 语音识别配置
STT_TYPE = "whisper"  # whisper, faster-whisper, 或 ollama（如果支持）
WHISPER_MODEL = "tiny"
whisper_model = None

# 对话历史
conversation_history = []
MAX_HISTORY = 10


# ============ 功能函数 ============

def load_whisper():
    """加载 Whisper 模型"""
    global whisper_model
    try:
        import whisper
        print(f"🎯 加载 Whisper 模型：{WHISPER_MODEL}...")
        whisper_model = whisper.load_model(WHISPER_MODEL)
        print("✅ Whisper 加载完成")
        return True
    except Exception as e:
        print(f"❌ Whisper 加载失败：{e}")
        print("💡 将使用 Ollama 或其他备用方案")
        return False


def check_ollama():
    """检查 Ollama 是否可用"""
    try:
        response = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✅ Ollama 可用，已安装模型：{[m['name'] for m in models]}")
            return True
        return False
    except Exception as e:
        print(f"❌ Ollama 不可用：{e}")
        return False


def speech_to_text_whisper(audio_data):
    """Whisper 语音识别"""
    if whisper_model is None:
        return None, "Whisper 未加载"
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
        import wave
        with wave.open(f.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_data)
    
    try:
        result = whisper_model.transcribe(f.name, language="zh", task="transcribe")
        return result["text"].strip(), None
    except Exception as e:
        return None, str(e)
    finally:
        os.unlink(f.name)


def ollama_chat(user_text):
    """Ollama LLM 对话"""
    global conversation_history
    
    messages = conversation_history[-MAX_HISTORY*2:] + [{"role": "user", "content": user_text}]
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    try:
        print(f"🤖 Ollama 思考中 ({OLLAMA_MODEL})...")
        response = requests.post(
            f"{OLLAMA_API}/api/chat",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result.get('message', {}).get('content', '')
            
            if reply:
                return reply, "ollama"
        
        return generate_fallback_reply(user_text), "fallback"
        
    except requests.exceptions.Timeout:
        return "抱歉，思考时间太长了。", "timeout"
    except Exception as e:
        print(f"❌ Ollama 错误：{e}")
        return generate_fallback_reply(user_text), "error"


def generate_fallback_reply(user_text):
    """备用回复"""
    responses = {
        "你好": "你好！有什么我可以帮你的吗？",
        "hello": "Hello! How can I help you today?",
        "再见": "再见！祝你有美好的一天！",
        "谢谢": "不客气！随时为你服务。",
        "叫什么": "我是你的本地语音助手。",
        "你是谁": "我是一个 AI 助手，可以陪你聊天、回答问题。",
    }
    
    for key, value in responses.items():
        if key in user_text.lower():
            return value
    
    return f"我听到了：{user_text}。"


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
    """播放音频"""
    try:
        cmd = ["mpv", "--no-video", f"--speed={speed}", filepath]
        subprocess.run(cmd, check=True, capture_output=True)
        return True, None
    except Exception as e:
        return False, str(e)


# ============ HTML 界面 ============

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎙️ AI 语音助手</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 15px 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        .status-bar.recording { background: rgba(233,69,96,0.3); animation: pulse 1s infinite; }
        .status-bar.thinking { background: rgba(255,193,7,0.2); }
        .status-bar.speaking { background: rgba(76,175,80,0.2); }
        
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
        
        .chat-box {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            min-height: 350px;
            max-height: 450px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 85%;
            word-wrap: break-word;
        }
        .user-msg { background: rgba(233,69,96,0.3); border:1px solid #e94560; margin-left:auto; text-align:right; }
        .assistant-msg { background: rgba(74,144,217,0.3); border:1px solid #4a90d9; margin-right:auto; }
        .system-msg { background: rgba(255,193,7,0.15); border:1px solid #ffc107; text-align:center; margin:10px auto; font-size:13px; }
        
        .controls { background: rgba(255,255,255,0.05); border-radius:20px; padding:20px; }
        
        .btn-main {
            width:100%; padding:18px; font-size:18px; font-weight:600;
            border:none; border-radius:15px; cursor:pointer; margin-bottom:15px;
            background: linear-gradient(135deg, #e94560, #ff6b6b); color:#fff;
        }
        .btn-main:disabled { opacity:0.6; cursor:not-allowed; }
        
        .settings { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:15px; }
        select { width:100%; padding:10px; border-radius:8px; background:rgba(255,255,255,0.1); color:#fff; border:1px solid rgba(255,255,255,0.2); }
        
        .input-area { display:flex; gap:10px; margin-top:15px; }
        textarea { flex:1; min-height:60px; padding:12px; border-radius:12px; border:1px solid rgba(255,255,255,0.2); background:rgba(255,255,255,0.05); color:#fff; }
        
        .btn { padding:12px; border:none; border-radius:12px; cursor:pointer; background:rgba(255,255,255,0.1); color:#fff; }
        .btn-blue { background:#4a90d9; }
        
        .badge { display:inline-block; padding:3px 8px; border-radius:5px; font-size:11px; margin-left:5px; background:#4a90d9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ AI 语音助手</h1>
        <p class="subtitle">语音识别 · Ollama AI · TTS 朗读</p>
        
        <div class="status-bar" id="statusBar">🟢 就绪</div>
        
        <div class="chat-box" id="chatBox">
            <div class="message system-msg">👋 点击"🎤 按住说话"开始语音对话</div>
        </div>
        
        <div class="controls">
            <button class="btn-main" id="recordBtn" onmousedown="startRecord()" onmouseup="stopRecord()" ontouchstart="startRecord()" ontouchend="stopRecord()">
                🎤 按住说话
            </button>
            
            <div class="settings">
                <div>
                    <label style="font-size:12px;color:#888">🎭 说话人</label>
                    <select id="speaker">
                        <option value="Keira">Keira</option>
                        <option value="老男人">老男人</option>
                        <option value="青年女">青年女</option>
                        <option value="少女">少女</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:12px;color:#888">⚡ 语速</label>
                    <select id="speed">
                        <option value="0.8">0.8x</option>
                        <option value="1.0" selected>1.0x</option>
                        <option value="1.2">1.2x</option>
                        <option value="1.5">1.5x</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:12px;color:#888">🧠 AI</label>
                    <select id="model">
                        <option value="ollama">Ollama</option>
                        <option value="simple">简单回复</option>
                    </select>
                </div>
            </div>
            
            <div class="input-area">
                <textarea id="textInput" placeholder="或输入文字..."></textarea>
                <button class="btn btn-blue" onclick="sendText()" style="min-width:80px">发送</button>
            </div>
            
            <div style="display:flex;gap:10px;margin-top:15px">
                <button class="btn" onclick="clearChat()">🗑️ 清空</button>
                <button class="btn" onclick="checkStatus()">📊 状态</button>
            </div>
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let recordStartTime = 0;
        let mediaRecorder = null;
        let audioChunks = [];
        
        function addMessage(text, type, badge='') {
            const chatBox = document.getElementById('chatBox');
            const msg = document.createElement('div');
            msg.className = `message ${type}-msg`;
            msg.innerHTML = text + (badge ? `<span class="badge">${badge}</span>` : '');
            chatBox.appendChild(msg);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function setStatus(text, className='') {
            const bar = document.getElementById('statusBar');
            bar.textContent = text;
            bar.className = 'status-bar ' + className;
        }
        
        function clearChat() {
            document.getElementById('chatBox').innerHTML = '<div class="message system-msg">👋 对话已清空</div>';
        }
        
        async function startRecord() {
            if (isRecording) return;
            isRecording = true;
            recordStartTime = Date.now();
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = sendAudio;
                
                mediaRecorder.start();
                document.getElementById('recordBtn').disabled = true;
                document.getElementById('recordBtn').textContent = '🔴 录音中...';
                setStatus('🎤 录音中... 请说话', 'recording');
            } catch(e) {
                setStatus('❌ 无法访问麦克风：' + e.message, '');
                isRecording = false;
            }
        }
        
        async function stopRecord() {
            if (!isRecording || !mediaRecorder) return;
            isRecording = false;
            mediaRecorder.stop();
            document.getElementById('recordBtn').textContent = '⏳ 识别中...';
            setStatus('🔄 语音识别中...', 'thinking');
        }
        
        async function sendAudio() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            try {
                const r = await fetch('/api/recognize', { method: 'POST', body: formData });
                const d = await r.json();
                
                if (d.success && d.text) {
                    addMessage(d.text, 'user');
                    setStatus(`✅ 识别："${d.text}"`, 'speaking');
                    processChat(d.text);
                } else {
                    setStatus('❌ ' + (d.error || '识别失败'), '');
                }
            } catch(e) {
                setStatus('❌ ' + e.message, '');
            }
            
            document.getElementById('recordBtn').disabled = false;
            document.getElementById('recordBtn').textContent = '🎤 按住说话';
        }
        
        async function sendText() {
            const text = document.getElementById('textInput').value.trim();
            if (!text) return;
            addMessage(text, 'user');
            document.getElementById('textInput').value = '';
            await processChat(text);
        }
        
        async function processChat(text) {
            const speaker = document.getElementById('speaker').value;
            const speed = document.getElementById('speed').value;
            const model = document.getElementById('model').value;
            
            setStatus('🤖 AI 思考中...', 'thinking');
            
            const r = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, speaker, speed, model })
            });
            const d = await r.json();
            
            if (d.success) {
                addMessage(d.reply, 'assistant', d.source);
                setStatus('✅ 完成', 'speaking');
            } else {
                setStatus('❌ ' + d.error, '');
            }
        }
        
        async function checkStatus() {
            const r = await fetch('/api/status');
            const d = await r.json();
            addMessage(`系统状态：<br>Whisper: ${d.whisper?'✅':'❌'}<br>Ollama: ${d.ollama?'✅':'❌'}<br>TTS: ${d.tts?'✅':'❌'}`, 'system');
        }
        
        document.getElementById('textInput').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
        });
    </script>
</body>
</html>
'''


# ============ API 路由 ============

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/recognize', methods=['POST'])
def recognize():
    """语音识别"""
    audio_file = request.files.get('audio')
    
    if not audio_file:
        return jsonify({'success': False, 'error': '没有音频数据'})
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
        audio_file.save(f.name)
    
    try:
        # 使用 Whisper 识别
        if whisper_model:
            text, error = speech_to_text_whisper(None)  # 需要重新实现
            # 简化：读取文件
            import wave
            with wave.open(temp_wav, 'rb') as wf:
                audio_data = wf.readframes(wf.getnframes())
            text, error = speech_to_text_whisper(audio_data)
            
            if error:
                return jsonify({'success': False, 'error': error})
            return jsonify({'success': True, 'text': text})
        else:
            return jsonify({'success': False, 'error': 'Whisper 未加载'})
    finally:
        os.unlink(temp_wav)


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天处理"""
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    speed = float(data.get('speed', '1.0'))
    model = data.get('model', 'ollama')
    
    if not text:
        return jsonify({'success': False, 'error': '文字不能为空'})
    
    # 生成回复
    if model == 'ollama':
        reply, source = ollama_chat(text)
    else:
        reply = generate_fallback_reply(text)
        source = 'simple'
    
    # 更新历史
    conversation_history.append({"role": "user", "content": text})
    conversation_history.append({"role": "assistant", "content": reply})
    
    # TTS 播放
    audio_file, error = tts_to_audio(reply, speaker, speed)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    # 后台播放
    def play_thread():
        play_audio(audio_file, speed)
        os.unlink(audio_file)
    
    threading.Thread(target=play_thread, daemon=True).start()
    
    return jsonify({'success': True, 'reply': reply, 'source': source})


@app.route('/api/status')
def status():
    """系统状态"""
    return jsonify({
        'whisper': whisper_model is not None,
        'ollama': check_ollama(),
        'tts': True
    })


# ============ 主程序 ============

if __name__ == '__main__':
    print("=" * 60)
    print("🎙️  AI 语音助手 - Ollama + TTS")
    print("=" * 60)
    
    # 加载组件
    load_whisper()
    ollama_available = check_ollama()
    
    print(f"\n📁 Ollama API: {OLLAMA_API}")
    print(f"🤖 Ollama 模型：{OLLAMA_MODEL}")
    print(f"🌐 访问：http://localhost:5015")
    print("💡 按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5015, debug=False)
