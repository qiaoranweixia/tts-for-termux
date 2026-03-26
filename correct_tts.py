#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 正确版本 - 使用正确的接口格式
"""

from flask import Flask, request, jsonify
import requests
import tempfile
import os
import subprocess
import time

app = Flask(__name__)

# 正确的接口格式
TTS_API = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS 正确版本</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; font-size: 12px; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        .error { background: rgba(244,67,54,0.2); border: 2px solid #f44336; }
        input, select { padding: 10px; margin: 5px; border-radius: 5px; border: 1px solid #fff; background: rgba(255,255,255,0.1); color: #fff; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS 正确版本</h1>
        <p>接口：http://192.168.0.104:9880/?text={{ text }}&speaker=Keira</p>
        
        <textarea id="text" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？</textarea>
        <br>
        
        <label>说话人：</label>
        <select id="speaker">
            <option value="Keira">Keira</option>
            <option value="老男人">老男人</option>
            <option value="青年女">青年女</option>
            <option value="少女">少女</option>
        </select>
        <br>
        
        <button class="btn" onclick="speak()">🔊 播放</button>
        <div id="status" class="status" style="display:none"></div>
        
        <script>
        async function speak(){
            const text = document.getElementById('text').value;
            const speaker = document.getElementById('speaker').value;
            const status = document.getElementById('status');
            
            status.style.display = 'block';
            status.className = 'status loading';
            status.textContent = '📡 请求中...\\n';
            
            const r = await fetch('/api/tts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, speaker})
            });
            const d = await r.json();
            
            if(d.success){
                status.className = 'status success';
                status.textContent += '\\n✅ '+d.msg+'\\n📊 '+d.size+' KB\\n⏱️ '+d.duration+'秒';
            }else{
                status.className = 'status error';
                status.textContent += '\\n❌ '+d.error;
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
        # 正确的接口格式
        log.append("")
        log.append("📡 请求 TTS API...")
        
        start = time.time()
        
        # 使用正确的接口格式
        r = requests.get(TTS_API, 
                         params={'text': text, 'speaker': speaker},
                         timeout=300)
        
        elapsed = time.time() - start
        size = len(r.content)
        size_kb = size / 1024
        size_mb = size / 1024 / 1024
        
        log.append(f"   状态：{r.status_code}")
        log.append(f"   大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        log.append(f"   时间：{elapsed:.2f}秒")
        
        if size < 50000:
            log.append(f"   ❌ 文件太小")
            return jsonify({'success': False, 'error': '\n'.join(log)})
        
        log.append(f"   ✅ 音频正常")
        
        # 保存
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(r.content)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        saved = os.path.getsize(temp.name)
        log.append(f"💾 保存：{saved/1024:.1f} KB")
        
        # 播放
        log.append("")
        log.append("🔊 播放...")
        
        result = subprocess.run(['termux-tts-speak', temp.name])
        os.unlink(temp.name)
        
        if result.returncode == 0:
            duration = saved / 44100 / 2
            log.append(f"✅ 成功！时长：{duration:.1f}秒")
            
            print('\n'.join(log))
            
            return jsonify({
                'success': True,
                'msg': '播放完成',
                'size': f"{size_kb:.1f}",
                'duration': f"{duration:.1f}"
            })
        else:
            return jsonify({'success': False, 'error': '播放失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 正确版本")
    print("接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}")
    print("🌐 http://localhost:5009")
    print("")
    app.run(host='0.0.0.0', port=5009, debug=False)
