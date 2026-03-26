#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS mpv 播放 Web 版本
"""

from flask import Flask, request, jsonify
import requests
import subprocess
import time

app = Flask(__name__)

TTS_API = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS mpv 播放版本</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        input, select { padding: 10px; margin: 5px; border-radius: 5px; background: rgba(255,255,255,0.1); color: #fff; border: 1px solid #fff; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS mpv 播放版本</h1>
        <p>接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}</p>
        <p>✅ 使用 mpv 播放器</p>
        
        <textarea id="text" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？</textarea>
        <br>
        
        <label>说话人：</label>
        <select id="speaker">
            <option value="Keira">Keira</option>
            <option value="老男人">老男人</option>
            <option value="青年女">青年女</option>
            <option value="少女">少女</option>
        </select>
        <br><br>
        
        <button class="btn" onclick="speak()">🔊 播放</button>
        <div id="status" class="status" style="display:none"></div>
        
        <script>
        async function speak(){
            const text = document.getElementById('text').value;
            const speaker = document.getElementById('speaker').value;
            const status = document.getElementById('status');
            
            status.style.display = 'block';
            status.className = 'status loading';
            status.textContent = '📡 下载并播放中...';
            
            const r = await fetch('/api/tts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, speaker})
            });
            const d = await r.json();
            
            if(d.success){
                status.className = 'status success';
                status.textContent = '✅ '+d.msg+'\\n📊 '+d.size+' KB\\n⏱️ 约'+d.duration+'秒';
            }else{
                status.className = 'status error';
                status.textContent = '❌ '+d.error;
            }
        }
        </script>
    </body>
    </html>
    '''

@app.route('/api/tts', methods=['POST'])
def tts():
    data = request.json
    text = data.get('text', '')
    speaker = data.get('speaker', 'Keira')
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'})
    
    log = []
    log.append(f"📝 文字：{text[:50]}...")
    log.append(f"🎭 说话人：{speaker}")
    
    try:
        log.append("")
        log.append("📡 下载并播放...")
        
        start = time.time()
        
        # 使用 mpv 直接播放流媒体
        log.append("   使用 mpv 播放...")
        
        # 后台播放
        subprocess.Popen([
            'mpv',
            f'{TTS_API}?text={text}&speaker={speaker}',
            '--no-video',
            '--no-terminal',
            '--quiet'
        ])
        
        elapsed = time.time() - start
        
        log.append(f"✅ 已发送播放命令")
        log.append(f"   时间：{elapsed:.2f}秒")
        
        print('\n'.join(log))
        
        return jsonify({
            'success': True,
            'msg': '播放中',
            'size': '流式',
            'duration': f"{len(text) * 0.1:.1f}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS mpv 播放 Web 版本")
    print("接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}")
    print("🌐 http://localhost:5011")
    print("✅ 使用 mpv 播放器")
    print("")
    app.run(host='0.0.0.0', port=5011, debug=False)
