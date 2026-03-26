#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 完善版本 - 支持播放控制、音量、语速等
"""

from flask import Flask, request, jsonify
import requests
import subprocess
import time
import json
import os

app = Flask(__name__)

TTS_API = "http://192.168.0.104:9880/"

# 全局播放控制
now_playing = None

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS 完善版本</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-control { padding: 10px 20px; font-size: 16px; background: #4a90d9; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        input, select { padding: 10px; margin: 5px; border-radius: 5px; background: rgba(255,255,255,0.1); color: #fff; border: 1px solid #fff; font-size: 16px; }
        .slider { width: 100%; margin: 10px 0; }
        label { display: block; margin: 10px 0 5px; font-weight: bold; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS 完善版本</h1>
        <p>✅ 支持播放控制、音量、语速</p>
        
        <textarea id="text" placeholder="输入文字..." style="width:100%;height:100px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？这是一个完整的测试语音。</textarea>
        
        <label>🎭 说话人：</label>
        <select id="speaker">
            <option value="Keira">Keira</option>
            <option value="老男人">老男人</option>
            <option value="青年女">青年女</option>
            <option value="少女">少女</option>
        </select>
        
        <label>🔊 音量：<span id="volVal">1.0</span></label>
        <input type="range" id="volume" class="slider" min="0.1" max="2.0" step="0.1" value="1.0" oninput="document.getElementById('volVal').textContent=this.value">
        
        <label>⚡ 语速：<span id="spdVal">1.0</span></label>
        <input type="range" id="speed" class="slider" min="0.5" max="2.0" step="0.1" value="1.0" oninput="document.getElementById('spdVal').textContent=this.value">
        
        <br><br>
        
        <button class="btn" id="playBtn" onclick="speak()">▶️ 播放</button>
        <button class="btn btn-control" onclick="pause()">⏸️ 暂停</button>
        <button class="btn btn-control" onclick="resume()">▶️ 继续</button>
        <button class="btn btn-control" onclick="stop()">⏹️ 停止</button>
        
        <div id="status" class="status" style="display:none"></div>
        
        <script>
        let isPlaying = false;
        
        async function speak(){
            const text = document.getElementById('text').value;
            const speaker = document.getElementById('speaker').value;
            const volume = document.getElementById('volume').value;
            const speed = document.getElementById('speed').value;
            const status = document.getElementById('status');
            const playBtn = document.getElementById('playBtn');
            
            status.style.display = 'block';
            status.className = 'status loading';
            status.textContent = '📡 播放中...';
            playBtn.disabled = true;
            isPlaying = true;
            
            const r = await fetch('/api/tts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, speaker, volume, speed})
            });
            const d = await r.json();
            
            if(d.success){
                status.className = 'status success';
                status.textContent = '✅ '+d.msg+'\\n📊 '+d.size+' KB\\n⏱️ 约'+d.duration+'秒';
                playBtn.disabled = false;
                isPlaying = false;
            }else{
                status.className = 'status error';
                status.textContent = '❌ '+d.error;
                playBtn.disabled = false;
                isPlaying = false;
            }
        }
        
        async function pause(){
            const r = await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'pause'})
            });
            const d = await r.json();
            alert(d.msg);
        }
        
        async function resume(){
            const r = await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'resume'})
            });
            const d = await r.json();
            alert(d.msg);
        }
        
        async function stop(){
            const r = await fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'stop'})
            });
            const d = await r.json();
            alert(d.msg);
        }
        </script>
    </body>
    </html>
    '''

@app.route('/api/tts', methods=['POST'])
def tts():
    global now_playing
    
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    volume = float(data.get('volume', 1.0))
    speed = float(data.get('speed', 1.0))
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'})
    
    log = []
    log.append(f"📝 文字：{text[:50]}...")
    log.append(f"🎭 说话人：{speaker}")
    log.append(f"🔊 音量：{volume}")
    log.append(f"⚡ 语速：{speed}")
    
    try:
        log.append("")
        log.append("📡 使用 mpv 播放...")
        
        start = time.time()
        
        # 构建 mpv 命令
        cmd = [
            'mpv',
            f'{TTS_API}?text={text}&speaker={speaker}',
            '--no-video',
            '--no-terminal',
            f'--volume={int(volume * 100)}',
            f'--speed={speed}'
        ]
        
        # 后台播放
        now_playing = subprocess.Popen(cmd)
        
        elapsed = time.time() - start
        
        log.append(f"✅ 播放开始")
        log.append(f"   时间：{elapsed:.2f}秒")
        
        print('\n'.join(log))
        
        return jsonify({
            'success': True,
            'msg': '播放中',
            'size': '流式',
            'duration': f"{len(text) * 0.1 / speed:.1f}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/control', methods=['POST'])
def control():
    global now_playing
    
    data = request.json
    action = data.get('action', '')
    
    if action == 'pause':
        if now_playing and now_playing.poll() is None:
            now_playing.send_signal(19)  # SIGSTOP
            return jsonify({'success': True, 'msg': '已暂停'})
        else:
            return jsonify({'success': False, 'error': '没有在播放'})
    
    elif action == 'resume':
        if now_playing and now_playing.poll() is None:
            now_playing.send_signal(18)  # SIGCONT
            return jsonify({'success': True, 'msg': '已继续'})
        else:
            return jsonify({'success': False, 'error': '没有在播放'})
    
    elif action == 'stop':
        if now_playing and now_playing.poll() is None:
            now_playing.terminate()
            return jsonify({'success': True, 'msg': '已停止'})
        else:
            return jsonify({'success': False, 'error': '没有在播放'})
    
    else:
        return jsonify({'success': False, 'error': '未知操作'})

if __name__ == '__main__':
    print("\n🔊 TTS 完善版本")
    print("接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}")
    print("🌐 http://localhost:5012")
    print("✅ 支持播放控制、音量、语速")
    print("")
    app.run(host='0.0.0.0', port=5012, debug=False)
