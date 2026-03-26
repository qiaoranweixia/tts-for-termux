#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TTS 语音合成 - Termux API 调用
让手机说话！🔊
"""

from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
import uuid

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'audio'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# TTS 接口配置
TTS_API_URL = "http://192.168.0.104:9880/"

# 可用说话人
SPEAKERS = [
    {"id": "老男人", "name": "成熟大叔"},
    {"id": "青年女", "name": "青年女性"},
    {"id": "少女", "name": "可爱少女"},
    {"id": "正太", "name": "正太"},
    {"id": "老女人", "name": "老年女性"},
]

@app.route('/')
def index():
    """主页"""
    return render_template('index.html', speakers=SPEAKERS)

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    文字转语音 API
    
    参数:
    - text: 要合成的文字
    - speaker: 说话人 (默认：老男人)
    - speed: 语速 (默认：1)
    - lang: 语言 (默认：Chinese)
    - novasr: 是否使用新模型 (默认：0)
    - instruct: 情感指令 (JSON 格式)
    """
    data = request.json
    
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '请输入文字'}), 400
    
    speaker = data.get('speaker', '老男人')
    speed = data.get('speed', 1)
    lang = data.get('lang', 'Chinese')
    novasr = data.get('novasr', 0)
    instruct = data.get('instruct', {})
    
    try:
        # 构建请求参数
        params = {
            'text': text,
            'speaker': speaker,
            'speed': speed,
            'lang': lang,
            'novasr': novasr
        }
        
        # 如果有情感指令，添加到参数
        if instruct:
            import json
            params['instruct'] = json.dumps(instruct, ensure_ascii=False)
        
        # 调用 TTS API
        response = requests.get(TTS_API_URL, params=params, timeout=60)
        
        if response.status_code == 200:
            # 生成唯一文件名
            filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # 保存音频文件
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'url': f'/audio/{filename}',
                'text': text,
                'speaker': speaker,
                'duration': len(response.content) / 44100 / 2  # 估算时长
            })
        else:
            return jsonify({
                'success': False,
                'error': f'TTS API 错误：{response.status_code}'
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': '请求超时'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f'网络错误：{str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'未知错误：{str(e)}'}), 500

@app.route('/audio/<filename>')
def serve_audio(filename):
    """提供音频文件下载"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/wav')
    return jsonify({'error': '文件不存在'}), 404

@app.route('/api/speakers')
def get_speakers():
    """获取可用说话人列表"""
    return jsonify({'success': True, 'speakers': SPEAKERS})

@app.route('/api/test')
def test_api():
    """测试 TTS API 连接"""
    try:
        params = {
            'text': '你好，测试',
            'speaker': '老男人'
        }
        response = requests.get(TTS_API_URL, params=params, timeout=10)
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'TTS API 连接正常',
                'api_url': TTS_API_URL
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API 返回错误：{response.status_code}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接失败：{str(e)}'
        })

if __name__ == '__main__':
    print("")
    print("🔊 TTS 语音合成服务")
    print("")
    print("📱 TTS API:", TTS_API_URL)
    print("🌐 访问地址：http://localhost:5002")
    print("")
    
    app.run(host='0.0.0.0', port=5002, debug=True)
