#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 最终版本 - 确保下载完整音频
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
    <head><meta charset="UTF-8"><title>TTS 最终测试</title></head>
    <body style="font-family:sans-serif;padding:20px;background:#1a1a2e;color:#fff">
        <h1>🔊 TTS 最终测试</h1>
        <p>这次会等待音频完全生成再播放</p>
        <textarea id="t" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff">你好，这是一个完整的测试语音，希望能听到完整清晰的声音。</textarea>
        <br><br>
        <button onclick="speak()" style="padding:15px 30px;font-size:18px;background:#e94560;color:#fff;border:none;border-radius:10px;cursor:pointer">🔊 播放</button>
        <div id="s" style="margin-top:20px;padding:15px;border-radius:10px;display:none"></div>
        <script>
        async function speak(){
            const t=document.getElementById('t').value;
            const s=document.getElementById('s');
            s.style.display='block';
            s.style.background='rgba(255,193,7,0.2)';
            s.style.border='2px solid #ffc107';
            s.textContent='📡 正在请求 TTS API...';
            
            const r=await fetch('/api/tts',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({text:t,speaker:'老男人',speed:1})
            });
            const d=await r.json();
            
            if(d.success){
                s.style.background='rgba(76,175,80,0.2)';
                s.style.border='2px solid #4caf50';
                s.textContent='✅ '+d.msg+'\\n\\n📊 大小：'+d.size+' KB\\n⏱️ 时长：'+d.duration+'秒';
            }else{
                s.style.background='rgba(244,67,54,0.2)';
                s.style.border='2px solid #f44336';
                s.textContent='❌ '+d.error;
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
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'})
    
    print(f"\n🔊 请求：text={text}, speaker={speaker}")
    
    try:
        # 1. 先获取音频 URL（有些 TTS API 返回的是 URL）
        print("📡 请求 TTS API...")
        
        # 尝试直接下载
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        if r.status_code != 200:
            return jsonify({'success': False, 'error': f'TTS API 错误：{r.status_code}'})
        
        # 2. 下载完整音频
        print("📥 下载音频...")
        audio = b''
        total = 0
        last_update = 0
        
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                audio += chunk
                total += len(chunk)
                
                # 每 0.5 秒更新一次进度
                now = time.time()
                if now - last_update > 0.5:
                    print(f"   已下载：{total / 1024:.1f} KB")
                    last_update = now
        
        size_kb = total / 1024
        print(f"✅ 下载完成：{size_kb:.1f} KB")
        
        # 3. 验证文件完整性
        if size_kb < 50:
            print(f"⚠️  文件太小 ({size_kb:.1f} KB)，可能生成失败")
            return jsonify({'success': False, 'error': f'音频文件太小 ({size_kb:.1f} KB)，可能 TTS API 生成失败'})
        
        # 4. 保存到临时文件
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())  # 确保写入磁盘
        temp.close()
        
        saved = os.path.getsize(temp.name)
        print(f"💾 保存：{temp.name} ({saved/1024:.1f} KB)")
        
        # 5. 再次验证
        if saved < 51200:  # 50KB
            print(f"❌ 保存的文件太小")
            os.unlink(temp.name)
            return jsonify({'success': False, 'error': '文件保存失败'})
        
        # 6. 播放
        print("🔊 开始播放...")
        print(f"   命令：termux-tts-speak {temp.name}")
        
        # 不捕获输出，让声音直接播放
        result = subprocess.run(['termux-tts-speak', temp.name], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                timeout=300)
        
        # 7. 清理
        os.unlink(temp.name)
        print("🗑️ 清理完成")
        
        if result.returncode == 0:
            duration = saved / 44100 / 2
            print(f"✅ 播放成功！时长：{duration:.1f}秒")
            return jsonify({
                'success': True,
                'msg': '播放完成',
                'size': f"{size_kb:.1f}",
                'duration': f"{duration:.1f}"
            })
        else:
            print(f"❌ 播放失败：{result.stderr}")
            return jsonify({'success': False, 'error': f'播放失败：{result.stderr}'})
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 最终测试")
    print("🌐 http://localhost:5005")
    print("")
    app.run(host='0.0.0.0', port=5005, debug=False)
