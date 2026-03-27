#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音聊天助手 - 简化版（无需 Whisper）
使用系统录音 + TTS 播放
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import subprocess
import json
import os
import tempfile
import threading

app = Flask(__name__)

# TTS API 配置
TTS_API = "http://192.168.0.104:9880/"


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
    <title>🎙️ 语音聊天</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 10px; }
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
        
        .controls {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 20px;
        }
        
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; }
        
        .btn {
            flex: 1;
            min-width: 100px;
            padding: 12px 16px;
            font-size: 16px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
        }
        
        .btn-send { background: #4a90d9; color: #fff; }
        .btn-tts { background: #e94560; color: #fff; }
        .btn-clear { background: rgba(255,255,255,0.1); color: #fff; }
        
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
        
        select {
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .status-bar {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 10px 15px;
            text-align: center;
            font-size: 14px;
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ 语音聊天</h1>
        <p class="subtitle">输入文字 → TTS 朗读</p>
        
        <div class="chat-box" id="chatBox">
            <div class="message assistant-msg">👋 输入文字，我来朗读！</div>
        </div>
        
        <div class="controls">
            <div class="settings">
                <div>
                    <label>🎭 说话人</label>
                    <select id="speaker">
                        <option value="Keira">Keira</option>
                        <option value="老男人">老男人</option>
                        <option value="青年女">青年女</option>
                        <option value="少女">少女</option>
                    </select>
                </div>
                <div>
                    <label>⚡ 语速</label>
                    <select id="speed">
                        <option value="0.8">0.8x</option>
                        <option value="1.0" selected>1.0x</option>
                        <option value="1.2">1.2x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2.0">2.0x</option>
                    </select>
                </div>
            </div>
            
            <textarea id="textInput" placeholder="输入要朗读的文字..."></textarea>
            
            <div class="btn-group">
                <button class="btn btn-tts" onclick="speak()">🔊 朗读</button>
                <button class="btn btn-send" onclick="chat()">💬 聊天</button>
                <button class="btn btn-clear" onclick="clearChat()">🗑️ 清空</button>
            </div>
            
            <div class="status-bar" id="statusBar">就绪</div>
        </div>
    </div>
    
    <script>
        function addMessage(text, type) {
            const chatBox = document.getElementById('chatBox');
            const msg = document.createElement('div');
            msg.className = `message ${type}-msg`;
            msg.textContent = text;
            chatBox.appendChild(msg);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function clearChat() {
            document.getElementById('chatBox').innerHTML = '<div class="message assistant-msg">👋 对话已清空</div>';
        }
        
        function setStatus(text) {
            document.getElementById('statusBar').textContent = text;
        }
        
        async function speak() {
            const text = document.getElementById('textInput').value.trim();
            if (!text) {
                setStatus('❌ 请输入文字');
                return;
            }
            
            const speaker = document.getElementById('speaker').value;
            const speed = document.getElementById('speed').value;
            
            addMessage(text, 'user');
            setStatus('🔊 朗读中...');
            
            const r = await fetch('/api/speak', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, speaker, speed })
            });
            const d = await r.json();
            
            if (d.success) {
                setStatus('✅ 朗读完成');
            } else {
                setStatus('❌ ' + d.error);
            }
        }
        
        async function chat() {
            const text = document.getElementById('textInput').value.trim();
            if (!text) return;
            
            const speaker = document.getElementById('speaker').value;
            const speed = document.getElementById('speed').value;
            
            addMessage(text, 'user');
            setStatus('🤖 回复中...');
            
            const r = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ text, speaker, speed })
            });
            const d = await r.json();
            
            if (d.success) {
                addMessage(d.reply, 'assistant');
                setStatus('✅ 完成');
            } else {
                setStatus('❌ ' + d.error);
            }
            
            document.getElementById('textInput').value = '';
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/speak', methods=['POST'])
def speak():
    """朗读文字"""
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    speed = data.get('speed', '1.0')
    
    if not text:
        return jsonify({'success': False, 'error': '文字不能为空'})
    
    audio_file, error = tts_to_audio(text, speaker, speed)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    # 后台播放
    def play_thread():
        play_audio(audio_file, speed)
        os.unlink(audio_file)
    
    threading.Thread(target=play_thread, daemon=True).start()
    
    return jsonify({'success': True, 'msg': '开始播放'})


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天回复"""
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    speed = data.get('speed', '1.0')
    
    if not text:
        return jsonify({'success': False, 'error': '文字不能为空'})
    
    # 简单回复逻辑
    reply = generate_reply(text)
    
    audio_file, error = tts_to_audio(reply, speaker, speed)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    def play_thread():
        play_audio(audio_file, speed)
        os.unlink(audio_file)
    
    threading.Thread(target=play_thread, daemon=True).start()
    
    return jsonify({'success': True, 'reply': reply})


def generate_reply(user_text):
    """生成简单回复"""
    responses = {
        "你好": "你好！有什么我可以帮你的吗？",
        "hello": "Hello! How can I help you?",
        "再见": "再见！祝你有美好的一天！",
        "谢谢": "不客气！随时为你服务。",
        "叫什么": "我是你的语音助手！",
        "名字": "我没有名字，但你可以叫我助手。",
    }
    
    for key, value in responses.items():
        if key in user_text.lower():
            return value
    
    return f"我听到了：{user_text}。"


if __name__ == '__main__':
    print("=" * 50)
    print("🎙️ 语音聊天助手（简化版）")
    print("=" * 50)
    print("\n🌐 访问 http://localhost:5013")
    print("💡 按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5013, debug=False)
