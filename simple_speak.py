#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单 TTS 播放 - 像小说 APP 一样
"""

import requests
import subprocess
import sys

def speak(text, speaker="Keira"):
    """直接调用 TTS API 并播放"""
    
    print(f"📖 文字：{text}")
    print(f"🎭 说话人：{speaker}")
    
    # 1. 下载音频
    print("📡 下载中...")
    r = requests.get('http://192.168.0.104:9880/',
                     params={'text': text, 'speaker': speaker},
                     timeout=120,
                     stream=True)
    
    if r.status_code != 200:
        print(f"❌ API 错误：{r.status_code}")
        return False
    
    # 2. 流式下载
    audio = b''
    for chunk in r.iter_content(chunk_size=8192):
        if chunk:
            audio += chunk
    
    print(f"✅ 下载完成：{len(audio)/1024:.1f} KB")
    
    # 3. 直接播放（不保存文件）
    print("🔊 播放中...")
    
    # 使用 termux-tts-speak 从 stdin 读取
    proc = subprocess.Popen(['termux-tts-speak'], 
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    
    stdout, stderr = proc.communicate(input=audio)
    
    if proc.returncode == 0:
        print("✅ 播放完成")
        return True
    else:
        print(f"❌ 播放失败：{stderr.decode()}")
        return False

if __name__ == '__main__':
    text = sys.argv[1] if len(sys.argv) > 1 else "你好，这是一个测试。"
    speaker = sys.argv[2] if len(sys.argv) > 2 else "Keira"
    
    speak(text, speaker)
