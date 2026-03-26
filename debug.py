#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 调试版本 - 详细日志
"""

from flask import Flask, request, jsonify, Response
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
    <head><meta charset="UTF-8"><title>TTS 调试版</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
        .btn { padding: 15px 30px; font-size: 18px; background: #e94560; color: #fff; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        .status { margin-top: 20px; padding: 20px; border-radius: 10px; white-space: pre-wrap; font-family: monospace; }
        .loading { background: rgba(255,193,7,0.2); border: 2px solid #ffc107; }
        .success { background: rgba(76,175,80,0.2); border: 2px solid #4caf50; }
        .error { background: rgba(244,67,54,0.2); border: 2px solid #f44336; }
    </style>
    </head>
    <body>
        <h1>🔊 TTS 调试版</h1>
        <p>详细日志显示每个步骤</p>
        <textarea id="t" placeholder="输入文字..." style="width:100%;height:80px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.1);color:#fff;border:1px solid #fff;font-size:16px">你好，能听到完整的声音吗？这是一个完整的测试。</textarea>
        <br>
        <button class="btn" onclick="speak()">🔊 播放</button>
        <button class="btn" onclick="test()">🧪 测试 API</button>
        <div id="s" class="status" style="display:none"></div>
        <script>
        async function speak(){
            const t=document.getElementById('t').value;
            const s=document.getElementById('s');
            s.style.display='block';
            s.className='status loading';
            s.textContent='📡 步骤 1: 请求 TTS API...\\n';
            
            const r=await fetch('/api/tts',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({text:t,speaker:'老男人',speed:1})
            });
            const d=await r.json();
            
            if(d.success){
                s.className='status success';
                s.textContent+='\\n✅ '+d.msg+'\\n\\n📊 大小：'+d.size+' KB\\n⏱️ 时长：'+d.duration+'秒';
            }else{
                s.className='status error';
                s.textContent+='\\n❌ '+d.error;
            }
        }
        
        async function test(){
            const s=document.getElementById('s');
            s.style.display='block';
            s.className='status loading';
            s.textContent='🧪 测试 API 连接...\\n';
            
            const r=await fetch('/api/test');
            const d=await r.json();
            
            if(d.success){
                s.className='status success';
                s.textContent+='✅ '+d.msg;
            }else{
                s.className='status error';
                s.textContent+='❌ '+d.error;
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
    
    log = []
    log.append(f"📝 文字：{text[:50]}...")
    log.append(f"🎭 说话人：{speaker}")
    
    if not text:
        return jsonify({'success': False, 'error': '\n'.join(log + ['❌ 请输入文字'])})
    
    try:
        # 1. 请求 TTS API 并等待生成
        log.append("")
        log.append("📡 步骤 1: 请求 TTS API...")
        
        # 先发送请求获取响应头
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        log.append(f"   状态码：{r.status_code}")
        log.append(f"   Content-Type: {r.headers.get('Content-Type')}")
        
        # 等待音频生成（最多 60 秒）
        log.append("")
        log.append("⏳ 步骤 1.5: 等待 TTS API 生成音频...")
        log.append("   (这可能需要 40-60 秒，请耐心等待)")
        
        import time
        wait_start = time.time()
        max_wait = 60  # 最多等 60 秒
        
        # 等待 Content-Length 稳定
        last_size = 0
        stable_count = 0
        
        for i in range(max_wait):
            # 尝试读取一些数据看看是否还在生成
            try:
                chunk = next(r.iter_content(chunk_size=1024))
                if chunk:
                    last_size = len(chunk)
                    # 如果连续 3 次都有数据，说明还在生成
                    stable_count += 1
                    if stable_count >= 3:
                        log.append(f"   等待了 {i+1} 秒，音频还在生成...")
                        stable_count = 0
            except StopIteration:
                # 没有更多数据，生成完成
                log.append(f"   ✅ 生成完成！等待了 {i+1} 秒")
                break
            
            time.sleep(1)
        
        wait_time = time.time() - wait_start
        log.append(f"   总等待时间：{wait_time:.1f}秒")
        
        # 2. 重新下载完整音频
        log.append("")
        log.append("📥 步骤 2: 下载完整音频...")
        
        # 重新请求以下载完整音频
        r = requests.get(TTS_API, params={'text': text, 'speaker': speaker, 'speed': speed}, 
                         timeout=300, stream=True)
        
        audio = b''
        total = 0
        chunks = 0
        start_time = time.time()
        
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                total += len(chunk)
                chunks += 1
                
                # 每 50KB 记录一次
                if total % (50 * 1024) < 8192:
                    log.append(f"   已下载：{total / 1024:.1f} KB ({chunks} chunks)")
        
        download_time = time.time() - start_time
        size_kb = total / 1024
        
        log.append("")
        log.append(f"✅ 下载完成：{size_kb:.1f} KB ({total} bytes)")
        log.append(f"   分块数：{chunks}")
        log.append(f"   下载时间：{download_time:.2f}秒")
        log.append(f"   平均速度：{size_kb / download_time:.1f} KB/s")
        
        # 3. 验证
        log.append("")
        log.append("🔍 步骤 3: 验证文件...")
        
        if size_kb < 50:
            log.append(f"❌ 文件太小 ({size_kb:.1f} KB)")
            return jsonify({'success': False, 'error': '\n'.join(log)})
        
        log.append(f"✅ 文件大小正常")
        
        # 4. 保存
        log.append("")
        log.append("💾 步骤 4: 保存文件...")
        
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        saved = os.path.getsize(temp.name)
        log.append(f"   路径：{temp.name}")
        log.append(f"   大小：{saved / 1024:.1f} KB")
        
        if saved < 51200:
            log.append(f"❌ 保存失败")
            os.unlink(temp.name)
            return jsonify({'success': False, 'error': '\n'.join(log)})
        
        log.append(f"✅ 保存成功")
        
        # 5. 播放
        log.append("")
        log.append("🔊 步骤 5: 播放音频...")
        log.append(f"   命令：termux-tts-speak {temp.name}")
        
        result = subprocess.run(['termux-tts-speak', temp.name], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                timeout=300)
        
        # 6. 清理
        os.unlink(temp.name)
        log.append("")
        log.append("🗑️ 步骤 6: 清理临时文件")
        
        if result.returncode == 0:
            duration = saved / 44100 / 2
            log.append("")
            log.append(f"✅ 播放成功！")
            log.append(f"   时长：约 {duration:.1f} 秒")
            
            print('\n'.join(log))
            
            return jsonify({
                'success': True,
                'msg': '播放完成',
                'size': f"{size_kb:.1f}",
                'duration': f"{duration:.1f}",
                'log': '\n'.join(log)
            })
        else:
            log.append(f"❌ 播放失败：{result.stderr.decode()[:200]}")
            return jsonify({'success': False, 'error': '\n'.join(log)})
            
    except Exception as e:
        import traceback
        error_log = f"❌ 错误：{e}\n\n{traceback.format_exc()}"
        log.append(error_log)
        print('\n'.join(log))
        return jsonify({'success': False, 'error': '\n'.join(log)})

@app.route('/api/test')
def test():
    try:
        r = requests.get(TTS_API, params={'text': '测试', 'speaker': '老男人'}, timeout=30)
        if r.status_code == 200 and len(r.content) > 1000:
            return jsonify({
                'success': True,
                'msg': f'TTS API 正常，音频大小：{len(r.content) / 1024:.1f} KB'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API 返回异常：{r.status_code}, {len(r.content)} bytes'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("\n🔊 TTS 调试版")
    print("🌐 http://localhost:5006")
    print("")
    app.run(host='0.0.0.0', port=5006, debug=False)
