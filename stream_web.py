#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 流式 Web 版本
"""

from flask import Flask, request, jsonify
import requests
import tempfile
import os
import subprocess
import time

app = Flask(__name__)

TTS_API = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS 流式版本</title>
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
        <h1>🔊 TTS 流式版本</h1>
        <p>接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}</p>
        <p>✅ 流式下载，自动等待生成完成</p>
        
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
            status.textContent = '📡 请求中...\\n(流式下载，请等待)';
            
            const r = await fetch('/api/tts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text, speaker})
            });
            const d = await r.json();
            
            if(d.success){
                status.className = 'status success';
                status.textContent += '\\n\\n✅ '+d.msg+'\\n📊 '+d.size+' KB\\n⏱️ '+d.duration+'秒';
            }else{
                status.className = 'status error';
                status.textContent += '\\n\\n❌ '+d.error;
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
        log.append("📡 请求 TTS API...")
        
        start = time.time()
        
        # 流式请求
        r = requests.get(TTS_API,
                         params={'text': text, 'speaker': speaker},
                         timeout=300,
                         stream=True)
        
        log.append(f"   状态：{r.status_code}")
        
        if r.status_code != 200:
            return jsonify({'success': False, 'error': '\n'.join(log + [f'❌ API 错误：{r.status_code}'])})
        
        # 流式下载
        log.append("")
        log.append("📥 流式下载中...")
        
        audio = b''
        total = 0
        chunks = 0
        last_update = time.time()
        
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                total += len(chunk)
                chunks += 1
                
                # 每秒更新
                now = time.time()
                if now - last_update >= 1.0:
                    elapsed = now - start
                    log.append(f"   {total/1024:.1f} KB ({elapsed:.1f}秒)")
                    last_update = now
        
        elapsed = time.time() - start
        size_kb = total / 1024
        size_mb = total / 1024 / 1024
        
        log.append("")
        log.append(f"✅ 下载完成！")
        log.append(f"   大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        log.append(f"   时间：{elapsed:.2f}秒")
        log.append(f"   分块：{chunks}")
        
        if size_mb < 0.1:
            log.append(f"   ❌ 文件太小")
            return jsonify({'success': False, 'error': '\n'.join(log)})
        
        # 保存
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        log.append(f"💾 保存：{os.path.getsize(temp.name)/1024:.1f} KB")
        
        # 播放（后台播放，不阻塞）
        log.append("")
        log.append("🔊 播放中...")
        
        subprocess.Popen(['termux-tts-speak', temp.name])
        # 不等待播放完成，立即返回
        
        log.append(f"✅ 已发送播放命令")
    duration = os.path.getsize(temp.name) / 44100 / 2 if os.path.exists(temp.name) else size_kb / 44
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
    print("\n🔊 TTS 流式 Web 版本")
    print("接口：http://192.168.0.104:9880/?text={text}&speaker={speaker}")
    print("🌐 http://localhost:5010")
    print("✅ 流式下载，自动等待生成完成")
    print("")
    app.run(host='0.0.0.0', port=5010, debug=False)
