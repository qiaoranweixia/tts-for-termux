#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 流式下载版本 - 正确读取流式响应
"""

import requests
import tempfile
import os
import subprocess
import time
import sys

TTS_API = "http://192.168.0.104:9880/"

def stream_download(text, speaker="Keira"):
    """
    流式下载 TTS 音频
    持续读取 stream 直到连接关闭
    """
    
    print(f"\n{'='*60}")
    print(f"📝 文字：{text[:50]}{'...' if len(text)>50 else ''}")
    print(f"🎭 说话人：{speaker}")
    print(f"📡 接口：{TTS_API}?text={text}&speaker={speaker}")
    print(f"{'='*60}\n")
    
    try:
        # 发送请求（流式）
        print("📡 发送请求...")
        start = time.time()
        
        r = requests.get(TTS_API,
                         params={'text': text, 'speaker': speaker},
                         timeout=300,
                         stream=True)
        
        print(f"响应状态：{r.status_code}")
        
        if r.status_code != 200:
            print(f"❌ API 错误：{r.status_code}")
            return False, 0
        
        # 流式下载
        print(f"\n📥 流式下载中...")
        print(f"   (持续读取直到连接关闭)")
        
        audio = b''
        total = 0
        chunk_count = 0
        last_update = time.time()
        
        # iter_content 会持续读取直到连接关闭
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                total += len(chunk)
                chunk_count += 1
                
                # 每秒显示进度
                now = time.time()
                if now - last_update >= 1.0:
                    elapsed = now - start
                    speed = total / 1024 / elapsed if elapsed > 0 else 0
                    print(f"   {total/1024:.1f} KB | {elapsed:.1f}秒 | {speed:.1f} KB/s | {chunk_count}块")
                    sys.stdout.flush()
        
        # 下载完成
        elapsed = time.time() - start
        size_kb = total / 1024
        size_mb = total / 1024 / 1024
        
        print(f"\n✅ 下载完成！")
        print(f"   总大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        print(f"   总时间：{elapsed:.2f}秒")
        print(f"   分块数：{chunk_count}")
        print(f"   平均速度：{size_kb/elapsed:.1f} KB/s")
        
        # 验证
        if size_mb < 0.1:
            print(f"\n❌ 文件太小 ({size_mb:.2f} MB)")
            return False, 0
        
        # 保存
        print(f"\n💾 保存文件...")
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        saved = os.path.getsize(temp.name)
        print(f"   路径：{temp.name}")
        print(f"   大小：{saved/1024:.1f} KB ({saved/1024/1024:.2f} MB)")
        
        # 播放
        print(f"\n🔊 播放...")
        duration = saved / 44100 / 2
        print(f"   预计时长：{duration:.1f}秒")
        
        result = subprocess.run(['termux-tts-speak', temp.name])
        
        os.unlink(temp.name)
        
        if result.returncode == 0:
            print(f"\n✅ 播放成功！")
            print(f"   实际时长：约 {duration:.1f}秒")
            return True, saved
        else:
            print(f"\n❌ 播放失败")
            return False, saved
            
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False, 0

# ===== 主程序 =====
if __name__ == '__main__':
    print("="*60)
    print("🔊 TTS 流式下载版本")
    print("持续读取 stream 直到连接关闭")
    print("="*60)
    
    # 测试
    tests = [
        ("你好", "极短"),
        ("你好，能听到完整的声音吗？", "短"),
        ("你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望听到完整清晰的声音。", "中"),
    ]
    
    results = []
    
    for text, name in tests:
        print(f"\n\n{'#'*60}")
        print(f"# 测试：{name}文字 ({len(text)}字)")
        print(f"{'#'*60}")
        
        success, size = stream_download(text, "Keira")
        
        results.append({
            'name': name,
            'chars': len(text),
            'success': success,
            'size': size
        })
        
        time.sleep(2)
    
    # 总结
    print(f"\n\n{'='*60}")
    print("📊 测试总结")
    print(f"{'='*60}")
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        size_mb = r['size'] / 1024 / 1024 if r['size'] > 0 else 0
        print(f"{status} {r['name']:6s} ({r['chars']:2d}字): {size_mb:.2f} MB")
    
    print(f"\n{'='*60}")
    print("✅ 所有测试完成！")
    print(f"{'='*60}\n")
