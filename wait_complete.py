#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 等待完成版本 - 确保音频完全生成后再下载
"""

import requests
import tempfile
import os
import subprocess
import time
import sys

TTS_API = "http://192.168.0.104:9880/"

def wait_and_download(text, speaker="老男人", max_wait=120):
    """
    等待 TTS API 生成完成后再下载
    
    策略：
    1. 先发送请求获取响应
    2. 持续读取数据直到没有新数据（生成完成）
    3. 验证文件大小
    4. 保存并播放
    """
    
    print(f"\n{'='*60}")
    print(f"📝 文字：{text[:50]}{'...' if len(text)>50 else ''} ({len(text)}字)")
    print(f"🎭 说话人：{speaker}")
    print(f"⏱️  最大等待：{max_wait}秒")
    print(f"{'='*60}\n")
    
    try:
        # 1. 发送请求
        print("📡 步骤 1: 发送请求...")
        start = time.time()
        
        session = requests.Session()
        r = session.get(TTS_API,
                       params={'text': text, 'speaker': speaker},
                       timeout=max_wait,
                       stream=True)
        
        print(f"   响应状态：{r.status_code}")
        print(f"   Content-Type: {r.headers.get('Content-Type')}")
        
        if r.status_code != 200:
            print(f"❌ API 错误：{r.status_code}")
            return False, 0
        
        # 2. 等待并下载（持续读取直到完成）
        print(f"\n📥 步骤 2: 等待生成并下载...")
        print(f"   (这会等待 TTS API 完全生成音频)")
        
        audio = b''
        total = 0
        chunk_count = 0
        last_size = 0
        stable_count = 0
        last_update = time.time()
        
        # 持续读取数据
        for chunk in r.iter_content(chunk_size=1024):
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
                    last_update = now
                
                # 检查是否稳定（没有新数据）
                if total == last_size:
                    stable_count += 1
                else:
                    stable_count = 0
                    last_size = total
                
                # 如果连续 5 秒没有新数据，说明生成完成
                if stable_count >= 5:
                    print(f"\n✅ 数据稳定，生成完成！")
                    break
        
        elapsed = time.time() - start
        size_kb = total / 1024
        size_mb = total / 1024 / 1024
        
        print(f"\n📊 下载统计:")
        print(f"   总大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        print(f"   总时间：{elapsed:.2f}秒")
        print(f"   分块数：{chunk_count}")
        print(f"   平均速度：{size_kb/elapsed:.1f} KB/s")
        
        # 3. 验证文件大小
        print(f"\n🔍 步骤 3: 验证文件...")
        
        # 根据文字长度估算合理大小（约 20-30 KB/字）
        min_expected = len(text) * 15  # KB
        max_expected = len(text) * 40  # KB
        
        print(f"   预期大小：{min_expected/1000:.1f} - {max_expected/1000:.1f} MB")
        
        if size_mb < 0.1:
            print(f"   ❌ 文件太小 ({size_mb:.2f} MB)，可能生成失败")
            return False, 0
        elif size_mb < min_expected / 1000:
            print(f"   ⚠️  文件偏小，但可能可用")
        else:
            print(f"   ✅ 文件大小正常")
        
        # 4. 保存文件
        print(f"\n💾 步骤 4: 保存文件...")
        
        temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp.write(audio)
        temp.flush()
        os.fsync(temp.fileno())  # 确保写入磁盘
        temp.close()
        
        saved = os.path.getsize(temp.name)
        print(f"   路径：{temp.name}")
        print(f"   大小：{saved/1024:.1f} KB ({saved/1024/1024:.2f} MB)")
        
        # 5. 播放
        print(f"\n🔊 步骤 5: 播放音频...")
        duration = saved / 44100 / 2
        print(f"   预计时长：{duration:.1f}秒")
        print(f"   (请仔细听是否完整)")
        
        # 不设置超时，让它自然播放完
        result = subprocess.run(['termux-tts-speak', temp.name])
        
        # 6. 清理
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
        print(f"\n❌ 超时（{max_wait}秒）")
        return False, 0
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False, 0

# ===== 主程序 =====
if __name__ == '__main__':
    print("="*60)
    print("🔊 TTS 等待完成版本")
    print("确保音频完全生成后再下载")
    print("="*60)
    
    # 测试不同长度
    tests = [
        ("你好", "极短"),
        ("你好，能听到吗？", "短"),
        ("你好，能听到完整的声音吗？这是测试。", "中"),
        ("你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望听到完整清晰的声音。", "长"),
    ]
    
    results = []
    
    for text, name in tests:
        print(f"\n\n{'#'*60}")
        print(f"# 测试：{name}文字 ({len(text)}字)")
        print(f"{'#'*60}")
        
        success, size = wait_and_download(text, "老男人", max_wait=120)
        
        results.append({
            'name': name,
            'chars': len(text),
            'success': success,
            'size': size
        })
        
        # 间隔 2 秒
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
