#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 强制等待版本 - 至少等待 50 秒确保生成完成
"""

import requests
import tempfile
import os
import subprocess
import time
import sys

TTS_API = "http://192.168.0.104:9880/"

def wait_50s_then_download(text, speaker="老男人"):
    """
    强制等待 50 秒后再下载，确保 TTS API 生成完成
    """
    
    print(f"\n{'='*60}")
    print(f"📝 文字：{text[:50]}{'...' if len(text)>50 else ''} ({len(text)}字)")
    print(f"🎭 说话人：{speaker}")
    print(f"⏱️  强制等待：至少 50 秒")
    print(f"{'='*60}\n")
    
    try:
        # 1. 发送请求
        print("📡 步骤 1: 发送请求...")
        start = time.time()
        
        session = requests.Session()
        r = session.get(TTS_API,
                       params={'text': text, 'speaker': speaker},
                       timeout=300,
                       stream=True)
        
        print(f"   响应状态：{r.status_code}")
        
        if r.status_code != 200:
            print(f"❌ API 错误：{r.status_code}")
            return False, 0
        
        # 2. 强制等待 50 秒（让 TTS API 有足够时间生成）
        print(f"\n⏳ 步骤 2: 强制等待 50 秒...")
        print(f"   (这确保 TTS API 完全生成音频)")
        
        for i in range(50):
            elapsed = i + 1
            print(f"   等待了 {elapsed} 秒 / 50 秒", end='\r')
            sys.stdout.flush()
            time.sleep(1)
        
        print(f"\n   ✅ 等待完成！")
        
        # 3. 开始下载
        print(f"\n📥 步骤 3: 开始下载...")
        
        audio = b''
        total = 0
        chunk_count = 0
        last_update = time.time()
        
        # 持续读取直到完成
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                audio += chunk
                total += len(chunk)
                chunk_count += 1
                
                # 每秒显示进度
                now = time.time()
                if now - last_update >= 1.0:
                    elapsed_total = now - start
                    speed = total / 1024 / elapsed_total if elapsed_total > 0 else 0
                    print(f"   {total/1024:.1f} KB | {elapsed_total:.1f}秒 | {speed:.1f} KB/s | {chunk_count}块")
                    sys.stdout.flush()
                    last_update = now
        
        elapsed_total = time.time() - start
        size_kb = total / 1024
        size_mb = total / 1024 / 1024
        
        print(f"\n📊 下载统计:")
        print(f"   总大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        print(f"   总时间：{elapsed_total:.2f}秒")
        print(f"   分块数：{chunk_count}")
        print(f"   平均速度：{size_kb/elapsed_total:.1f} KB/s")
        
        # 4. 验证文件大小
        print(f"\n🔍 步骤 4: 验证文件...")
        
        # 根据文字长度估算（约 20-30 KB/字）
        min_expected = len(text) * 15 / 1000  # MB
        max_expected = len(text) * 40 / 1000  # MB
        
        print(f"   预期大小：{min_expected:.2f} - {max_expected:.2f} MB")
        
        if size_mb < 0.1:
            print(f"   ❌ 文件太小 ({size_mb:.2f} MB)")
            return False, 0
        elif size_mb < min_expected:
            print(f"   ⚠️  文件偏小，但可能可用")
        else:
            print(f"   ✅ 文件大小正常")
        
        # 5. 保存文件
        print(f"\n💾 步骤 5: 保存文件...")
        
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())
        temp.close()
        
        saved = os.path.getsize(temp.name)
        print(f"   路径：{temp.name}")
        print(f"   大小：{saved/1024:.1f} KB ({saved/1024/1024:.2f} MB)")
        
        # 6. 播放（不设置超时）
        print(f"\n🔊 步骤 6: 播放音频...")
        duration = saved / 44100 / 2
        print(f"   预计时长：{duration:.1f}秒")
        print(f"   (请仔细听是否完整)")
        
        print(f"   开始播放...")
        result = subprocess.run(['termux-tts-speak', temp.name])
        
        # 7. 清理
        os.unlink(temp.name)
        print(f"\n🗑️  清理临时文件")
        
        if result.returncode == 0:
            print(f"\n✅ 播放成功！")
            print(f"   实际时长：约 {duration:.1f}秒")
            return True, saved
        else:
            print(f"\n❌ 播放失败")
            return False, saved
            
    except requests.exceptions.Timeout:
        print(f"\n❌ 超时")
        return False, 0
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False, 0

# ===== 主程序 =====
if __name__ == '__main__':
    print("="*60)
    print("🔊 TTS 强制等待版本")
    print("至少等待 50 秒确保音频完全生成")
    print("="*60)
    
    # 测试不同长度
    tests = [
        ("你好", "极短"),
        ("你好，能听到吗？", "短"),
        ("你好，能听到完整的声音吗？这是测试。", "中"),
        ("你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望听到完整清晰的声音，而不是被截断的音频。请生成高质量的语音输出。这对于测试系统非常重要。", "长"),
    ]
    
    results = []
    
    for text, name in tests:
        print(f"\n\n{'#'*60}")
        print(f"# 测试：{name}文字 ({len(text)}字)")
        print(f"{'#'*60}")
        
        success, size = wait_50s_then_download(text, "老男人")
        
        results.append({
            'name': name,
            'chars': len(text),
            'success': success,
            'size': size
        })
        
        # 间隔 3 秒
        time.sleep(3)
    
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
