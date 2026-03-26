#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最简单的 TTS 测试
"""

from flask import Flask, request, jsonify
import requests
import tempfile
import os
import subprocess

app = Flask(__name__)

TTS_API = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>TTS 简单测试</title></head>
    <body style="font-family:sans-serif;padding:20px;background:#1a1a2e;color:#fff">
        <h1>🔊 TTS 简单测试</h1>
        <textarea id="t" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff">你好，这是一个测试</textarea>
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
            s.textContent='📡 正在下载音频...';
            
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
    
    # 1. 调用 TTS API - 等待生成完成
    try:
        print("📡 请求 TTS API...")
        print(f"   文字：{text}")
        print(f"   说话人：{speaker}")
        
        # 先发送请求
        print("📡 发送请求，等待 TTS API 生成...")
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        if r.status_code != 200:
            return jsonify({'success': False, 'error': f'TTS API 错误：{r.status_code}'})
        
        # 获取内容长度（如果有）
        content_length = r.headers.get('Content-Length')
        expected_size = int(content_length) if content_length else 0
        
        # 等待音频完全生成（检查 Content-Length 是否稳定）
        print("⏳ 等待 TTS API 生成完成...")
        wait_count = 0
        last_size = 0
        
        # 最多等待 60 秒，每 2 秒检查一次
        while wait_count < 30:
            # 尝试获取当前已生成的数据量
            current_size = 0
            for chunk in r.iter_content(chunk_size=8192):
                current_size += len(chunk)
                if current_size >= 8192:
                    break
            
            if current_size == 0:
                # 没有数据，继续等待
                import time
                time.sleep(2)
                wait_count += 1
                print(f"   等待中... ({wait_count * 2}秒)")
            elif current_size == last_size:
                # 数据量不再增长，生成完成
                print(f"✅ 生成完成！等待了 {wait_count * 2} 秒")
                break
            else:
                # 还在生成，继续等待
                last_size = current_size
                import time
                time.sleep(2)
                wait_count += 1
        
        # 重新下载完整音频
        print("📥 开始下载完整音频...")
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        audio = b''
        downloaded = 0
        
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                downloaded += len(chunk)
                # 每下载 100KB 显示一次
                if downloaded % (100 * 1024) < 8192:
                    print(f"   已下载：{downloaded / 1024:.1f} KB")
        
        size_kb = len(audio) / 1024
        print(f"✅ 下载完成：{size_kb:.1f} KB")
        
        # 验证文件大小
        if size_kb < 10:
            print(f"⚠️  文件太小，可能生成失败")
        
        # 2. 保存文件
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        temp.close()
        
        saved = os.path.getsize(temp.name)
        print(f"💾 保存：{temp.name} ({saved/1024:.1f} KB)")
        
        # 3. 播放
        print("🔊 播放...")
        result = subprocess.run(['termux-tts-speak', temp.name], timeout=300)
        
        # 4. 清理
        os.unlink(temp.name)
        print("🗑️ 清理完成")
        
        if result.returncode == 0:
            duration = saved / 44100 / 2
            print(f"✅ 成功！时长：{duration:.1f}秒")
            return jsonify({
                'success': True,
                'msg': '播放完成',
                'size': f"{size_kb:.1f}",
                'duration': f"{duration:.1f}"
            })
        else:
            return jsonify({'success': False, 'error': '播放失败'})
            
    except Exception as e:
        print(f"❌ 错误：{e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 简单测试")
    print("🌐 http://localhost:5004")
    print("")
    app.run(host='0.0.0.0', port=5004, debug=False)
