#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 最终修复版 - 强制等待 40 秒
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
    <head><meta charset="UTF-8"><title>TTS 最终修复版</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; font-size: 12px; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        .error { background: rgba(244,67,54,0.2); border: 2px solid #f44336; }
        .progress { margin: 10px 0; }
        .progress-bar { width: 100%; height: 20px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #e94560, #ff6b6b); transition: width 0.3s; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS 最终修复版</h1>
        <p>强制等待 40 秒让 TTS API 生成完整音频</p>
        <textarea id="t" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？这是一个完整的测试。</textarea>
        <br>
        <button class="btn" onclick="speak()">🔊 播放</button>
        <div id="s" class="status" style="display:none"></div>
        <div id="p" class="progress" style="display:none">
            <div class="progress-bar"><div id="pf" class="progress-fill" style="width:0%"></div></div>
            <div id="pt" style="text-align:center;margin-top:5px">等待中... 0%</div>
        </div>
        <script>
        async function speak(){
            const t=document.getElementById('t').value;
            const s=document.getElementById('s');
            const p=document.getElementById('p');
            const pf=document.getElementById('pf');
            const pt=document.getElementById('pt');
            
            s.style.display='block';
            p.style.display='block';
            s.className='status loading';
            s.textContent='📡 步骤 1: 请求 TTS API...\\n';
            
            // 显示进度条
            for(let i=0; i<=100; i++){
                await new Promise(r=>setTimeout(r,400)); // 40 秒
                pf.style.width=i+'%';
                pt.textContent='⏳ 等待生成... '+i+'% (约'+(40-i*0.4).toFixed(0)+'秒)';
                if(i%10==0) s.textContent+='   等待了 '+i+'%...\\n';
            }
            
            s.textContent+='\\n📥 步骤 2: 下载音频...\\n';
            
            const r=await fetch('/api/tts',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({text:t,speaker:'老男人',speed:1,wait:true})
            });
            const d=await r.json();
            
            p.style.display='none';
            
            if(d.success){
                s.className='status success';
                s.textContent+='\\n✅ '+d.msg+'\\n\\n📊 大小：'+d.size+' KB\\n⏱️ 时长：'+d.duration+'秒';
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
    speed = data.get('speed', 1)
    wait = data.get('wait', False)
    
    log = []
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'})
    
    log.append(f"📝 文字：{text[:50]}...")
    log.append(f"🎭 说话人：{speaker}")
    
    try:
        # 1. 请求 TTS API
        log.append("")
        log.append("📡 步骤 1: 请求 TTS API...")
        
        # 如果前端已经等了 40 秒，直接下载
        # 否则在这里等
        if not wait:
            log.append("⏳ 等待 40 秒让音频生成...")
            for i in range(40):
                time.sleep(1)
                if i % 10 == 0:
                    log.append(f"   等待了 {i} 秒...")
        
        log.append("")
        log.append("📥 步骤 2: 下载完整音频...")
        
        # 下载音频
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        log.append(f"   状态码：{r.status_code}")
        
        if r.status_code != 200:
            return jsonify({'success': False, 'error': '\n'.join(log + [f'❌ TTS API 错误：{r.status_code}'])})
        
        # 下载
        audio = b''
        total = 0
        chunks = 0
        start = time.time()
        
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                total += len(chunk)
                chunks += 1
                if total % (100 * 1024) < 8192:
                    log.append(f"   已下载：{total / 1024:.1f} KB")
        
        download_time = time.time() - start
        size_kb = total / 1024
        
        log.append("")
        log.append(f"✅ 下载完成：{size_kb:.1f} KB")
        log.append(f"   分块数：{chunks}")
        log.append(f"   下载时间：{download_time:.2f}秒")
        
        # 验证
        if size_kb < 50:
            log.append(f"❌ 文件太小")
            return jsonify({'success': False, 'error': '\n'.join(log)})
        
        # 保存
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        saved = os.path.getsize(temp.name)
        log.append(f"💾 保存：{saved / 1024:.1f} KB")
        
        # 播放
        log.append("")
        log.append("🔊 播放...")
        
        result = subprocess.run(['termux-tts-speak', temp.name], timeout=300)
        
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
            return jsonify({'success': False, 'error': f'播放失败'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 最终修复版")
    print("🌐 http://localhost:5007")
    print("⏱️  会等待 40 秒让音频生成")
    print("")
    app.run(host='0.0.0.0', port=5007, debug=False)
