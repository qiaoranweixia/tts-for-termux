#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 稳健版本 - 带进度显示和自动重试
"""

import requests
import tempfile
import os
import subprocess
import time
import sys

TTS_API = "http://192.168.0.104:9880/"

def download_with_progress(text, speaker="老男人", max_retries=3):
    """带进度的下载，支持重试"""
    
    for attempt in range(max_retries):
        print(f"\n{'='*60}")
        print(f"尝试 {attempt+1}/{max_retries}")
        print(f"文字：{text[:50]}{'...' if len(text)>50 else ''}")
        print(f"说话人：{speaker}")
        print(f"{'='*60}\n")
        
        try:
            # 计算预估时间（约 20KB/字，下载速度约 100KB/s）
            estimated_time = len(text) * 20 / 100 + 5  # 秒
            timeout = max(60, estimated_time * 3)  # 至少 60 秒，最多 3 倍预估时间
            
            print(f"⏱️  预估时间：{estimated_time:.0f}秒")
            print(f"⏱️  超时设置：{timeout}秒")
            print(f"\n📡 开始请求...")
            
            start = time.time()
            
            # 使用 Session 保持连接
            session = requests.Session()
            
            # 发送请求，使用流式但持续读取
            r = session.get(TTS_API, 
                           params={'text': text, 'speaker': speaker},
                           timeout=timeout,
                           stream=True)
            
            print(f"响应状态：{r.status_code}")
            
            # 下载
            print(f"\n📥 下载中...")
            audio = b''
            total = 0
            last_update = 0
            
            for i, chunk in enumerate(r.iter_content(chunk_size=8192)):
                if chunk:
                    audio += chunk
                    total += len(chunk)
                    
                    # 每秒更新一次进度
                    now = time.time()
                    if now - last_update > 1.0:
                        elapsed = now - start
                        speed = total / 1024 / elapsed if elapsed > 0 else 0
                        print(f"   {total/1024:.1f} KB ({elapsed:.1f}秒, {speed:.1f} KB/s)")
                        last_update = now
                        sys.stdout.flush()
            
            elapsed = time.time() - start
            size_kb = total / 1024
            size_mb = total / 1024 / 1024
            
            print(f"\n✅ 下载完成！")
            print(f"   大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
            print(f"   时间：{elapsed:.2f}秒")
            print(f"   速度：{size_kb/elapsed:.1f} KB/s")
            
            # 验证
            if size_mb < 0.3:
                print(f"\n⚠️  文件小于 0.3MB，可能不完整")
                if attempt < max_retries - 1:
                    print("   等待 5 秒后重试...")
                    time.sleep(5)
                    continue
            else:
                print(f"\n✅ 文件大小正常")
            
            # 保存
            temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp.write(audio)
            temp.flush()
            os.fsync(temp.fileno())
            temp.close()
            
            saved = os.path.getsize(temp.name)
            print(f"\n💾 保存：{saved/1024:.1f} KB ({saved/1024/1024:.2f} MB)")
            
            # 播放
            duration = saved / 44100 / 2
            print(f"\n🔊 播放...（预计{duration:.1f}秒）")
            result = subprocess.run(['termux-tts-speak', temp.name], timeout=300)
            
            os.unlink(temp.name)
            
            if result.returncode == 0:
                print(f"\n✅ 播放成功！")
                return True, saved
            else:
                print(f"\n❌ 播放失败")
                return False, saved
                
        except requests.exceptions.Timeout:
            print(f"\n❌ 超时（{timeout}秒）")
            if attempt < max_retries - 1:
                print("   重试...")
                time.sleep(5)
            continue
        except Exception as e:
            print(f"\n❌ 错误：{e}")
            if attempt < max_retries - 1:
                print("   重试...")
                time.sleep(5)
            continue
    
    print(f"\n❌ {max_retries}次尝试后失败")
    return False, 0

# ===== 主程序 =====
if __name__ == '__main__':
    print("="*60)
    print("🔊 TTS 稳健版本")
    print("="*60)
    
    # 测试不同长度
    tests = [
        ("你好", "短文字"),
        ("你好，能听到完整的声音吗？这是测试。", "中等文字"),
        ("你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望听到完整清晰的声音，而不是被截断的音频。请生成高质量的语音输出。", "长文字"),
    ]
    
    for text, name in tests:
        print(f"\n\n{'#'*60}")
        print(f"# 测试：{name} ({len(text)}字)")
        print(f"{'#'*60}")
        
        success, size = download_with_progress(text, "老男人", max_retries=3)
        
        if success:
            print(f"\n✅ {name} 测试成功！({size/1024/1024:.2f} MB)")
        else:
            print(f"\n❌ {name} 测试失败")
        
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print("✅ 所有测试完成！")
    print(f"{'='*60}")
