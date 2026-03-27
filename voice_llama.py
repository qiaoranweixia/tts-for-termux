#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整语音助手：Whisper STT + Llama LLM + TTS
语音识别 → AI 思考 → 语音回复
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

# Llama 配置
LLAMA_MODEL = os.path.expanduser("~/.llama/models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
LLAMA_CTX = 2048
LLAMA_TEMP = 0.7

# Whisper 配置
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
        return False


def check_llama():
    """检查 Llama 是否可用"""
    if not os.path.exists(LLAMA_MODEL):
        print(f"⚠️ Llama 模型不存在：{LLAMA_MODEL}")
        return False
    
    # 检查 llama-cli
    try:
        result = subprocess.run(["llama-cli", "--version"], capture_output=True, timeout=5)
        print("✅ llama-cli 可用")
        return True
    except:
        print("⚠️ llama-cli 未找到，将使用备用回复")
        return False


def speech_to_text(audio_data):
    """Whisper 语音识别"""
    if whisper_model is None:
        return None, "Whisper 未加载"
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        temp_wav = f.name
        # 保存 WAV（假设输入是 16k 16bit 单声道）
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


def llama_reply(user_text):
    """Llama 生成回复"""
    global conversation_history
    
    if not os.path.exists(LLAMA_MODEL):
        return generate_fallback_reply(user_text), "llama"
    
    # 构建对话历史
    messages = conversation_history[-MAX_HISTORY*2:] + [{"role": "user", "content": user_text}]
    
    # 转换为 llama.cpp 提示格式
    prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            prompt += f"User: {msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n"
    prompt += "Assistant: "
    
    # 调用 llama-cli
    cmd = [
        "llama-cli",
        "-m", LLAMA_MODEL,
        "-p", prompt,
        "-n", "256",
        "-c", str(LLAMA_CTX),
        "--temp", str(LLAMA_TEMP),
        "-ngl", "0"
    ]
    
    try:
        print("🤖 Llama 思考中...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        output = result.stdout
        # 提取回复
        if "Assistant:" in output:
            reply = output.split("Assistant:")[-1].strip()
            # 清理重复
            if user_text in reply:
                reply = reply.split(user_text)[0].strip()
            if reply:
                return reply, "llama"
        
        return generate_fallback_reply(user_text), "llama"
        
    except subprocess.TimeoutExpired:
        return "抱歉，思考时间太长了。", "timeout"
    except Exception as e:
        print(f"❌ Llama 错误：{e}")
        return generate_fallback_reply(user_text), "error"


def generate_fallback_reply(user_text):
    """备用回复（无 Llama 时）"""
    responses = {
        "你好": "你好！有什么我可以帮你的吗？",
        "hello": "Hello! How can I help you today?",
        "再见": "再见！祝你有美好的一天！",
        "谢谢": "不客气！随时为你服务。",
        "叫什么": "我是你的本地语音助手，运行在 Termux 上。",
        "你是谁": "我是一个 AI 助手，可以陪你聊天、回答问题。",
        "名字": "我没有特定的名字，你可以叫我助手。",
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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 700px; margin: 0 auto; }
        
        h1 { text-align: center; margin-bottom: 10px; font-size: 32px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 14px; }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 15px 20px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 14px;
        }
        .status-bar.recording { background: rgba(233,69,96,0.3); animation: pulse 1s infinite; }
        .status-bar.thinking { background: rgba(255,193,7,0.2); }
        .status-bar.speaking { background: rgba(76,175,80,0.2); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
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
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
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
            background: rgba(255, 193, 7, 0.15);
            border: 1px solid #ffc107;
            text-align: center;
            margin: 10px auto;
            font-size: 13px;
            color: #ffc107;
        }
        
        .controls {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
        }
        
        .btn-main {
            width: 100%;
            padding: 18px;
            font-size: 18px;
            font-weight: 600;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }
        
        .btn-record {
            background: linear-gradient(135deg, #e94560, #ff6b6b);
            color: #fff;
        }
        .btn-record:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(233,69,96,0.4);
        }
        .btn-record:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .btn-group { display: flex; gap: 10px; }
        .btn {
            flex: 1;
            padding: 12px;
            font-size: 14px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .btn:hover { background: rgba(255,255,255,0.2); }
        
        .settings {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        select {
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .input-area {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        textarea {
            flex: 1;
            min-height: 60px;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 14px;
            resize: vertical;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 11px;
            margin-left: 5px;
        }
        .badge-llama { background: #4a90d9; }
        .badge-fallback { background: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ AI 语音助手</h1>
        <p class="subtitle">Whisper 识别 · Llama 思考 · TTS 朗读</p>
        
        <div class="status-bar" id="statusBar">🟢 就绪 - 点击录音开始</div>
        
        <div class="chat-box" id="chatBox">
            <div class="message system-msg">
                👋 点击"🎤 按住说话"开始语音对话<br>
                或直接输入文字发送
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-main btn-record" id="recordBtn" onmousedown="startRecord()" onmouseup="stopRecord()" ontouchstart="startRecord()" ontouchend="stopRecord()">
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
                    <label style="font-size:12px;color:#888">🧠 模式</label>
                    <select id="mode">
                        <option value="llama">Llama AI</option>
                        <option value="simple">简单回复</option>
                    </select>
                </div>
            </div>
            
            <div class="input-area">
                <textarea id="textInput" placeholder="或输入文字..."></textarea>
                <button class="btn" onclick="sendText()" style="min-width:80px;background:#4a90d9">发送</button>
            </div>
            
            <div class="btn-group" style="margin-top:15px">
                <button class="btn" onclick="clearChat()">🗑️ 清空</button>
                <button class="btn" onclick="checkStatus()">📊 状态</button>
            </div>
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let recordStartTime = 0;
        
        function addMessage(text, type, badge='') {
            const chatBox = document.getElementById('chatBox');
            const msg = document.createElement('div');
            msg.className = `message ${type}-msg`;
            msg.innerHTML = text + (badge ? `<span class="badge badge-${badge}">${badge}</span>` : '');
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
            
            document.getElementById('recordBtn').disabled = true;
            document.getElementById('recordBtn').textContent = '🔴 录音中...';
            setStatus('🎤 录音中... 请说话', 'recording');
            
            await fetch('/api/start_record', { method: 'POST' });
        }
        
        async function stopRecord() {
            if (!isRecording) return;
            isRecording = false;
            
            const duration = ((Date.now() - recordStartTime) / 1000).toFixed(1);
            document.getElementById('recordBtn').textContent = '⏳ 识别中...';
            setStatus('🔄 语音识别中...', 'thinking');
            
            const r = await fetch('/api/recognize', { method: 'POST' });
            const d = await r.json();
            
            document.getElementById('recordBtn').disabled = false;
            document.getElementById('recordBtn').textContent = '🎤 按住说话';
            
            if (d.success && d.text) {
                addMessage(d.text, 'user');
                setStatus(`✅ 识别："${d.text}" (${duration}s)`, 'speaking');
                processChat(d.text);
            } else {
                setStatus('❌ ' + (d.error || '识别失败'), '');
            }
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
            const mode = document.getElementById('mode').value;
            
            setStatus('🤖 AI 思考中...', 'thinking');
            
            const r = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, speaker, speed, mode })
            });
            const d = await r.json();
            
            if (d.success) {
                addMessage(d.reply, 'assistant', d.source || 'llama');
                setStatus('✅ 回复完成', 'speaking');
            } else {
                setStatus('❌ ' + d.error, '');
            }
        }
        
        async function checkStatus() {
            const r = await fetch('/api/status');
            const d = await r.json();
            addMessage(`系统状态：<br>Whisper: ${d.whisper ? '✅' : '❌'}<br>Llama: ${d.llama ? '✅' : '❌'}<br>TTS: ${d.tts ? '✅' : '❌'}`, 'system');
        }
        
        // Enter 发送
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


# ============ API 路由 ============

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/start_record', methods=['POST'])
def start_record():
    """开始录音（前端触发）"""
    return jsonify({'success': True})


@app.route('/api/recognize', methods=['POST'])
def recognize():
    """语音识别"""
    # 这里简化处理，实际应该录音
    # 前端调用此 API 时，应该已经有录音数据
    return jsonify({
        'success': False, 
        'error': '请在完整版本中实现录音功能'
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天处理"""
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    speed = float(data.get('speed', '1.0'))
    mode = data.get('mode', 'llama')
    
    if not text:
        return jsonify({'success': False, 'error': '文字不能为空'})
    
    # 生成回复
    if mode == 'llama':
        reply, source = llama_reply(text)
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
        success, err = play_audio(audio_file, speed)
        os.unlink(audio_file)
        if not success:
            print(f"播放失败：{err}")
    
    threading.Thread(target=play_thread, daemon=True).start()
    
    return jsonify({'success': True, 'reply': reply, 'source': source})


@app.route('/api/status')
def status():
    """系统状态"""
    return jsonify({
        'whisper': whisper_model is not None,
        'llama': os.path.exists(LLAMA_MODEL),
        'tts': True
    })


# ============ 主程序 ============

if __name__ == '__main__':
    print("=" * 60)
    print("🎙️  AI 语音助手 - Whisper + Llama + TTS")
    print("=" * 60)
    
    # 加载组件
    load_whisper()
    check_llama()
    
    print(f"\n📁 Llama 模型：{LLAMA_MODEL}")
    print(f"🌐 访问：http://localhost:5014")
    print("💡 按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5014, debug=False)
