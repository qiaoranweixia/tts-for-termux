#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Termux TTS - 让手机说话！🔊
调用 192.168.0.104:9880 的 TTS API 合成音频，然后用 termux-tts-speak 播放
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import json
import requests
import tempfile
import os

app = Flask(__name__)

# TTS API 配置
TTS_API_URL = "http://192.168.0.104:9880/"

@app.route('/')
def index():
    """主页"""
    return render_template('termux.html')

@app.route('/api/speak', methods=['POST'])
def speak():
    """
    直接用 termux-tts-speak 播放文字
    
    参数:
    - text: 要播放的文字
    - engine: TTS 引擎
    - pitch: 音调
    - rate: 语速
    """
    data = request.json
    
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'}), 400
    
    engine = data.get('engine', '')
    pitch = data.get('pitch', 1.0)
    rate = data.get('rate', 1.0)
    
    try:
        cmd = ['termux-tts-speak']
        
        if engine:
            cmd.extend(['-e', engine])
        
        cmd.extend(['-p', str(pitch)])
        cmd.extend(['-r', str(rate)])
        cmd.append(text)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '🔊 正在播放...',
                'text': text
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Termux API 错误：{result.stderr}'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tts-play', methods=['POST'])
def tts_play():
    """
    从 TTS API 获取音频并播放
    
    1. 调用 192.168.0.104:9880 的 TTS API 合成音频
    2. 用 termux-tts-speak 播放音频文件
    """
    data = request.json
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'}), 400
    
    # TTS API 参数
    speaker = data.get('speaker', '老男人')
    speed = data.get('speed', 1)
    lang = data.get('lang', 'Chinese')
    novasr = data.get('novasr', 0)
    instruct = data.get('instruct', {})
    
    print(f"\n🔊 收到 TTS 播放请求:")
    print(f"   文字：{text}")
    print(f"   说话人：{speaker}")
    print(f"   语速：{speed}")
    
    try:
        # 1. 调用 TTS API 获取音频
        params = {
            'text': text,
            'speaker': speaker,
            'speed': speed,
            'lang': lang,
            'novasr': novasr
        }
        
        if instruct:
            params['instruct'] = json.dumps(instruct, ensure_ascii=False)
        
        print(f"\n📡 请求 TTS API: {TTS_API_URL}")
        print(f"   参数：text={text}, speaker={speaker}, speed={speed}, lang={lang}, novasr={novasr}")
        
        # 增加超时时间到 300 秒（5 分钟）
        response = requests.get(TTS_API_URL, params=params, timeout=300, stream=True)
        
        if response.status_code != 200:
            print(f"❌ TTS API 错误：{response.status_code}")
            return jsonify({
                'success': False,
                'error': f'TTS API 错误：{response.status_code}'
            }), 500
        
        # 流式下载，确保完整
        print(f"📥 开始下载音频...")
        audio_content = b''
        total_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                audio_content += chunk
                total_size += len(chunk)
                if total_size % (1024 * 1024) < 8192:  # 每 1MB 显示一次
                    print(f"   已下载：{total_size / 1024:.1f} KB")
        
        print(f"✅ TTS API 返回音频：{total_size / 1024:.1f} KB ({total_size} bytes)")
        
        # 2. 保存音频到临时文件（确保完整写入）
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.write(audio_content)
        temp_file.flush()  # 确保写入磁盘
        temp_file_path = temp_file.name
        temp_file.close()
        
        # 验证文件是否正确保存
        saved_size = os.path.getsize(temp_file_path)
        print(f"💾 临时文件：{temp_file_path}")
        print(f"   文件大小：{saved_size / 1024:.1f} KB")
        
        if saved_size == 0:
            print(f"❌ 文件保存失败！")
            os.unlink(temp_file_path)
            return jsonify({'success': False, 'error': '音频文件保存失败'}), 500
        
        # 3. 用 termux-tts-speak 播放文件（不设置超时，让它播放完）
        print(f"🔊 开始播放...")
        print(f"   命令：termux-tts-speak {temp_file_path}")
        cmd = ['termux-tts-speak', temp_file_path]
        
        # 不捕获输出，让声音直接播放
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        
        # 4. 清理临时文件
        try:
            os.unlink(temp_file_path)
            print(f"🗑️ 已清理临时文件")
        except Exception as e:
            print(f"⚠️ 清理文件失败：{e}")
        
        if result.returncode == 0:
            print(f"✅ 播放成功")
            return jsonify({
                'success': True,
                'message': '🔊 正在播放...',
                'text': text,
                'speaker': speaker,
                'audio_size': len(response.content)
            })
        else:
            print(f"❌ 播放失败：{result.stderr}")
            return jsonify({
                'success': False,
                'error': f'播放失败：{result.stderr}'
            }), 500
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络错误：{e}")
        return jsonify({'success': False, 'error': f'网络错误：{str(e)}'}), 500
    except Exception as e:
        print(f"❌ 未知错误：{e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/engines')
def get_engines():
    """获取可用的 TTS 引擎"""
    try:
        cmd = ['termux-tts-engines']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            engines = [e.strip() for e in result.stdout.strip().split('\n') if e.strip()]
            return jsonify({
                'success': True,
                'engines': engines,
                'default': engines[0] if engines else '系统默认'
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法获取引擎列表'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'engines': ['系统默认']
        })

@app.route('/api/test')
def test():
    """测试 Termux TTS"""
    try:
        cmd = ['termux-tts-speak', '测试']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': '✅ Termux TTS 可用',
                'test_text': '测试'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr.strip() if result.stderr else '测试失败'
            })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': '未安装 termux-api',
            'install': 'pkg install termux-api'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("")
    print("=" * 50)
    print("🔊 Termux TTS - 让手机说话！")
    print("=" * 50)
    print("")
    print("📱 TTS API: " + TTS_API_URL)
    print("📱 播放工具：termux-tts-speak")
    print("🌐 访问地址：http://localhost:5003")
    print("")
    print("⚠️  确保已安装 termux-api:")
    print("    pkg install termux-api")
    print("")
    print("🎯 工作流程:")
    print("  1. 调用 TTS API 合成音频")
    print("  2. 用 termux-tts-speak 播放")
    print("  3. 手机发出声音！")
    print("")
    
    app.run(host='0.0.0.0', port=5003, debug=True)

@app.route('/test')
def test_page():
    """测试页面"""
    return render_template('test.html')
