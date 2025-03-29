# 使用Python的腾讯云SDK进行TTS合成
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tts.v20190823 import tts_client, models
import base64
import json
import os
import re
import argparse
from datetime import datetime
import csv
import tempfile
import subprocess
import pathlib

# 设置基础目录（项目根目录）
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./"))

# FFmpeg路径
ffmpeg_path = os.path.abspath(os.path.join(base_dir, "Softwares", "ffmpeg", "bin", "ffmpeg.exe"))
ffprobe_path = os.path.abspath(os.path.join(base_dir, "Softwares", "ffmpeg", "bin", "ffprobe.exe"))

def load_credentials_from_csv(csv_path):
    """从CSV文件中加载腾讯云凭证"""
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            # 跳过标题行
            next(reader, None)
            # 读取第一行数据
            for row in reader:
                if len(row) >= 2:
                    return row[0], row[1]  # SecretId, SecretKey
                break
        print(f"错误：无法从CSV文件中读取有效的凭证")
        return None, None
    except Exception as e:
        print(f"读取凭证文件失败: {str(e)}")
        return None, None

def process_text_by_lines(text):
    """将文本按行分割，并组合成不超过150字的片段"""
    segments = []
    current_segment = ""
    max_length = 150
    
    # 按行分割文本
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:  # 跳过空行
            continue
            
        # 如果添加当前行会超出长度限制
        if len(current_segment) + len(line) + 1 > max_length:  # +1 是为了可能添加的换行符
            if current_segment:
                segments.append(current_segment)
            current_segment = line
        else:
            # 如果不是第一行，添加换行符
            if current_segment:
                current_segment += "\n" + line
            else:
                current_segment = line
    
    # 添加最后一个段落
    if current_segment:
        segments.append(current_segment)
        
    return segments

def get_voice_name(voice_id):
    """根据音色ID获取音色名称"""
    voice_id_str = str(voice_id)
    csv_path = os.path.join('Config', 'tencent_cloud_voice_type.csv')
    
    # 如果音色文件不存在，直接返回ID作为前缀
    if not os.path.exists(csv_path):
        print(f"音色文件 {csv_path} 不存在，使用音色ID作为前缀")
        return voice_id_str
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 跳过标题行
            next(reader, None)
            # 查找匹配的音色ID
            for row in reader:
                if len(row) >= 2 and row[0].strip() == voice_id_str:
                    return row[1].strip()  # 返回音色名称
                    
        # 如果没有找到匹配的音色ID
        print(f"未找到音色ID {voice_id} 的名称，使用ID作为前缀")
        return voice_id_str
    except Exception as e:
        print(f"读取音色文件失败: {str(e)}")
        return voice_id_str

def text_to_speech(text, output_file="output.wav", voice_type=101011, speed=0, volume=5):
    temp_dir = None
    temp_files = []
    concat_list_path = None
    
    try:
        # 从CSV文件加载凭证
        csv_path = os.path.join('Config', 'tencent_cloud_secret_key.csv')
        secret_id, secret_key = load_credentials_from_csv(csv_path)
        
        if not secret_id or not secret_key:
            print("错误：无法获取腾讯云凭证，请检查CSV文件")
            return False
        
        # 实例化一个认证对象
        cred = credential.Credential(secret_id, secret_key)
        
        # 实例化client
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tts.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = tts_client.TtsClient(cred, "ap-guangzhou", clientProfile)
        
        # 将文本分段，每段不超过150字，并保持句子完整性
        segments = process_text_by_lines(text)
        print(f"文本已分割为{len(segments)}个片段")
        
        # 创建临时目录存放临时音频片段
        temp_dir = tempfile.mkdtemp()
        
        # 处理每个文本片段
        for i, segment in enumerate(segments):
            temp_file = os.path.join(temp_dir, f"segment_{i}.wav")
            temp_files.append(temp_file)
            
            print(f"处理片段 {i+1}/{len(segments)}: {segment[:30]}...({len(segment)}字)")
            
            # 实例化请求对象
            req = models.TextToVoiceRequest()
            params = {
                "Text": segment,
                "SessionId": f"session-{i}-{hash(segment)}",
                "VoiceType": voice_type,  # 使用传入的音色ID
                "Volume": volume,        # 音量
                "Speed": speed,         # 语速
                "Codec": "wav",     # 编码格式
                "PrimaryLanguage": 1,  # 语言
            }
            req.from_json_string(json.dumps(params))
            
            try:
                # 发送请求并获取响应
                resp = client.TextToVoice(req)
                
                # 解析Base64编码的音频数据并保存为临时文件
                audio_data = base64.b64decode(resp.Audio)
                with open(temp_file, 'wb') as f:
                    f.write(audio_data)
                    
                print(f"片段 {i+1}/{len(segments)} 合成成功")
                
            except Exception as e:
                print(f"片段 {i+1}/{len(segments)} 合成失败: {e}")
                return False
        
        # 使用FFmpeg合并所有音频片段
        if len(temp_files) > 0:
            # 创建concat文件列表
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, "w") as f:
                for temp_file in temp_files:
                    f.write(f"file '{temp_file}'\n")
            
            # 获取输出文件的格式
            output_ext = os.path.splitext(output_file)[1].lower()
            
            # 使用FFmpeg合并音频文件
            cmd = [
                ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path
            ]
            
            # 根据输出格式添加相应的编码选项
            if output_ext == ".mp3":
                cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
            elif output_ext == ".aac" or output_ext == ".m4a":
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            elif output_ext == ".ogg":
                cmd.extend(["-c:a", "libvorbis", "-q:a", "4"])
            elif output_ext == ".flac":
                cmd.extend(["-c:a", "flac"])
            else:
                # WAV或其他未指定格式，直接复制
                cmd.extend(["-c", "copy"])
            
            # 添加输出文件
            cmd.append(output_file)
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"所有片段已合并，最终文件保存为 {output_file}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"合并音频失败: {e.stderr}")
                return False
        else:
            print("没有生成任何音频片段")
            return False
            
    except Exception as e:
        print(f"语音合成失败: {e}")
        return False
    finally:
        # 确保在任何情况下都清理临时文件
        try:
            if concat_list_path and os.path.exists(concat_list_path):
                os.remove(concat_list_path)
                
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
            if temp_dir and os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                
            print("临时文件已清理")
        except Exception as e:
            print(f"清理临时文件时出错: {e}")

# 主函数
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='文本转语音工具')
    parser.add_argument('-f', '--file', required=True, help='指定文本文件路径（必需）')
    parser.add_argument('-o', '--output', help='指定输出文件路径，包含完整路径和文件后缀（例如：path/to/output.mp3）')
    parser.add_argument('-v', '--voice', type=int, default=101012, help='指定音色ID')
    args = parser.parse_args()
    
    text_file = args.file
    output_path = args.output
    voice_type = args.voice
    
    # 获取音色名称
    voice_name = get_voice_name(voice_type)
    
    # 检查指定的文件是否存在
    if not os.path.exists(text_file):
        print(f"错误：指定的文件 {text_file} 不存在")
        exit(1)
    
    # 设置输出文件路径和名称
    if output_path:
        # 如果指定了输出路径，则直接使用
        output_file = output_path
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    else:
        # 未指定输出路径，则使用输入文件的路径和名称，但后缀改为.wav
        input_path_without_ext = os.path.splitext(text_file)[0]  # 获取不含扩展名的输入文件路径
        output_file = f"{input_path_without_ext}.wav"  # 添加.wav后缀
    
    # 读取文本内容
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text_content = f.read().strip()
            
        if not text_content:
            print(f"错误：文件 {text_file} 内容为空")
            exit(1)
        
        # 合成语音
        text_to_speech(text_content, output_file, voice_type)
    except Exception as e:
        print(f"处理文件时出错: {str(e)}")