#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 TTS API
"""

import requests

TTS_API_URL = "http://192.168.0.104:9880/"

print("🔊 测试 TTS API...")
print(f"API 地址：{TTS_API_URL}")
print("")

# 测试参数
params = {
    'text': '你好，测试一下',
    'speaker': '老男人'
}

print(f"请求参数:")
print(f"  text: {params['text']}")
print(f"  speaker: {params['speaker']}")
print("")

try:
    print("📡 发送请求...")
    response = requests.get(TTS_API_URL, params=params, timeout=60)
    
    print(f"响应状态码：{response.status_code}")
    print(f"响应内容大小：{len(response.content)} bytes")
    
    if response.status_code == 200 and len(response.content) > 0:
        print("")
        print("✅ TTS API 正常！")
        print("")
        
        # 保存测试文件
        with open('/tmp/tts_test.wav', 'wb') as f:
            f.write(response.content)
        
        print(f"💾 音频已保存到：/tmp/tts_test.wav")
        
        import subprocess
        print("")
        print("🔊 播放测试...")
        subprocess.run(['termux-tts-speak', '/tmp/tts_test.wav'])
        
    else:
        print("")
        print("❌ TTS API 返回异常")
        print(f"响应内容：{response.content[:200]}")
        
except Exception as e:
    print(f"❌ 错误：{e}")
