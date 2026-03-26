#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 最终可用版本
"""

from flask import Flask, request, jsonify
import requests
import tempfile
import os
import subprocess
import time
import json

app = Flask(__name__)

TTS_API = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS 最终可用版</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; font-size: 12px; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        .error { background: rgba(244,67,54,0.2); border: 2px solid #f44336; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS 最终可用版</h1>
        <textarea id="t" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？</textarea>
        <br>
        <button class="btn" onclick="speak()">🔊 播放</button>
        <div id="s" class="status" style="display:none"></div>
        <script>
        async function speak(){
            const t=document.getElementById('t').value;
            const s=document.getElementById('s');
            s.style.display='block';
            s.className='status loading';
            s.textContent='📡 请求中...\\n';
            
            const r=await fetch('/api/tts',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({text:t,speaker:'老男人'})
            });
            const d=await r.json();
            
            if(d.success){
                s.className='status success';
                s.textContent+='\\n✅ '+d.msg+'\\n📊 '+d.size+' KB\\n⏱️ '+d.duration+'秒';
            }else{
                s.className='status error';
                s.textContent+='\\n❌ '+d.error;
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
    speaker = data.get('speaker', '老男人')
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'})
    
    print(f"\n📝 文字：{text}")
    print(f"🎭 说话人：{speaker}")
    
    try:
        print("📡 请求 TTS API...")
        start = time.time()
        
        # 直接请求，不流式
        r = requests.get(TTS_API, 
                         params={'text': text, 'speaker': speaker},
                         timeout=300)
        
        elapsed = time.time() - start
        print(f"✅ 响应：{r.status_code}, {len(r.content)/1024:.1f} KB, {elapsed:.2f}秒")
        
        if r.status_code != 200 or len(r.content) < 50000:
            return jsonify({
                'success': False, 
                'error': f'API 错误：{r.status_code}, {len(r.content)} bytes'
            })
        
        # 保存
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(r.content)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        size = os.path.getsize(temp.name)
        print(f"💾 保存：{size/1024:.1f} KB")
        
        # 播放
        print("🔊 播放...")
        result = subprocess.run(['termux-tts-speak', temp.name], timeout=300)
        os.unlink(temp.name)
        
        if result.returncode == 0:
            duration = size / 44100 / 2
            print(f"✅ 成功！{duration:.1f}秒")
            return jsonify({
                'success': True,
                'msg': '播放完成',
                'size': f"{size/1024:.1f}",
                'duration': f"{duration:.1f}"
            })
        else:
            return jsonify({'success': False, 'error': '播放失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 最终可用版")
    print("🌐 http://localhost:5008")
    app.run(host='0.0.0.0', port=5008, debug=False)
