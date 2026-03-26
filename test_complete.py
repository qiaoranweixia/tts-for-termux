#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 完整测试 - 直到下载几 MB 音频
"""

import requests
import tempfile
import os
import subprocess
import time
import json

TTS_API = "http://192.168.0.104:9880/"

def test_tts(text, speaker="老男人", wait_time=0, **kwargs):
    """测试 TTS API"""
    print(f"\n{'='*60}")
    print(f"📝 文字：{text[:50]}{'...' if len(text)>50 else ''}")
    print(f"🎭 说话人：{speaker}")
    print(f"⏳ 等待时间：{wait_time}秒")
    print(f"{'='*60}\n")
    
    # 构建参数
    params = {'text': text, 'speaker': speaker}
    params.update(kwargs)
    
    print("📡 请求参数:")
    for k, v in params.items():
        print(f"   {k}: {v}")
    print()
    
    # 发送请求
    print("📥 开始下载...")
    start = time.time()
    
    try:
        # 方法 1：直接请求（等待完整响应）
        print("方法 1：直接请求（不流式）")
        r = requests.get(TTS_API, params=params, timeout=300)
        
        elapsed = time.time() - start
        size = len(r.content)
        size_kb = size / 1024
        size_mb = size / 1024 / 1024
        
        print(f"✅ 响应：{r.status_code}")
        print(f"📊 大小：{size_kb:.1f} KB ({size_mb:.2f} MB)")
        print(f"⏱️  时间：{elapsed:.2f}秒")
        print(f"📈 速度：{size_kb/elapsed:.1f} KB/s")
        
        # 检查文件头
        print(f"\n🔍 文件类型检查:")
        if r.content[:4] == b'RIFF':
            print("   ✅ WAV 音频文件")
        elif r.content.startswith(b'{'):
            print(f"   ❌ JSON 数据：{r.content[:200]}")
        elif r.content.startswith(b'<!DOCTYPE'):
            print(f"   ❌ HTML 页面")
        else:
            print(f"   ❓ 未知格式：{r.content[:20].hex()}")
        
        # 如果小于 1MB，尝试等待后重新下载
        if size_mb < 1.0 and wait_time > 0:
            print(f"\n⚠️  文件小于 1MB，等待{wait_time}秒后重试...")
            time.sleep(wait_time)
            
            print("方法 2：等待后重新请求")
            start2 = time.time()
            r2 = requests.get(TTS_API, params=params, timeout=300)
            elapsed2 = time.time() - start2
            size2 = len(r2.content)
            
            print(f"✅ 第二次响应：{r2.status_code}")
            print(f"📊 大小：{size2/1024:.1f} KB ({size2/1024/1024:.2f} MB)")
            print(f"⏱️  时间：{elapsed2:.2f}秒")
            
            if size2 > size:
                r = r2
                size = size2
                size_kb = size / 1024
                size_mb = size / 1024 / 1024
        
        # 保存文件
        if size > 50000:  # 大于 50KB
            temp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp.write(r.content)
            temp.flush()
            os.fsync(temp.fileno())
            temp.close()
            
            saved = os.path.getsize(temp.name)
            print(f"\n💾 保存：{temp.name}")
            print(f"   实际大小：{saved/1024:.1f} KB ({saved/1024/1024:.2f} MB)")
            
            # 播放
            print(f"\n🔊 播放测试...")
            print(f"   预计时长：{saved/44100/2:.1f}秒")
            result = subprocess.run(['termux-tts-speak', temp.name], timeout=300)
            
            os.unlink(temp.name)
            
            if result.returncode == 0:
                print(f"\n✅ 播放成功！")
                return True
            else:
                print(f"\n❌ 播放失败")
                return False
        else:
            print(f"\n❌ 文件太小，跳过播放")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        return False

# ===== 开始测试 =====
print("="*60)
print("🔊 TTS 完整音频测试")
print("="*60)

# 测试 1：短文字
test_tts("你好", wait_time=5)

# 测试 2：中等文字
test_tts("你好，能听到完整的声音吗？这是一个测试。", wait_time=10)

# 测试 3：长文字
test_tts("你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望听到完整清晰的声音，而不是被截断的音频。请生成高质量的语音输出。", wait_time=20)

# 测试 4：超长文字
test_tts("""
股票经纪人有两个诀窍。第一是要对市场有深入的了解，包括各种经济指标、公司财报和行业动态。第二是要有良好的沟通能力，能够清晰地向客户解释复杂的投资概念。
你好，能听到完整的声音吗？这是一个完整的测试语音。我们希望测试 TTS API 能否生成完整的、高质量的音频文件。如果音频被截断或者只有几秒钟，那说明还有问题需要解决。
请生成一段完整的、清晰的语音，让我们能够听到完整的内容。这对于测试系统非常重要。
""", wait_time=40)

# 测试 5：带参数
test_tts("你好，测试新模式。", speaker="老男人", novasr=1, speed=1, wait_time=30)

# 测试 6：带情感
test_tts("太棒了！我们成功了！这是一个令人兴奋的时刻！", 
         speaker="老男人", 
         instruct=json.dumps({"情感": "高兴"}, ensure_ascii=False),
         wait_time=30)

print("\n" + "="*60)
print("✅ 测试完成！")
print("="*60)
