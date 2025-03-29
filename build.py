#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
腾讯云语音合成工具打包脚本
用于自动构建可执行文件，同时优化文件大小
"""

import os
import sys
import shutil
import subprocess
import argparse

def run_command(command):
    """执行系统命令并打印输出"""
    print(f"执行: {command}")
    process = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        shell=True, 
        universal_newlines=True
    )
    
    for line in process.stdout:
        print(line.strip())
    
    process.wait()
    return process.returncode

def create_spec_file():
    """创建并配置spec文件"""
    # 检查是否有图标文件
    icon_path = ""
    if os.path.exists("Resources/app_icon.ico"):
        icon_path = "--icon=Resources/app_icon.ico"
    
    # 创建基础spec文件
    cmd = f"pyi-makespec --onefile --windowed {icon_path} tts_gui.py"
    run_command(cmd)
    
    # 读取spec文件内容
    with open("tts_gui.spec", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 修改spec文件:
    # 1. 添加额外的导入模块
    # 2. 排除不必要的模块
    # 3. 添加资源文件
    
    # 找到Analysis部分并修改
    analysis_start = content.find("a = Analysis(")
    analysis_end = content.find(")", analysis_start)
    
    modified_analysis = content[analysis_start:analysis_end]
    
    # 添加隐藏导入
    if "hiddenimports" in modified_analysis:
        modified_analysis = modified_analysis.replace(
            "hiddenimports=[]", 
            "hiddenimports=['PyQt5.QtSvg', 'PyQt5.QtMultimedia', 'qfluentwidgets']"
        )
    else:
        modified_analysis += ",\n    hiddenimports=['PyQt5.QtSvg', 'PyQt5.QtMultimedia', 'qfluentwidgets']"
    
    # 添加排除模块
    if "excludes" in modified_analysis:
        modified_analysis = modified_analysis.replace(
            "excludes=[]", 
            "excludes=['matplotlib', 'pandas', 'scipy', 'numpy', 'PIL', 'tkinter', 'PySide2', 'IPython', 'notebook', 'jedi']"
        )
    else:
        modified_analysis += ",\n    excludes=['matplotlib', 'pandas', 'scipy', 'numpy', 'PIL', 'tkinter', 'PySide2', 'IPython', 'notebook', 'jedi']"
    
    # 替换修改后的Analysis部分
    content = content[:analysis_start] + modified_analysis + content[analysis_end:]
    
    # 添加资源文件收集函数
    resources_function = """

# 添加资源文件和配置文件
def extra_datas(folder_path):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob(f"{d}/*", files)
        return files
    
    files = []
    extra_datas = rec_glob(f"{folder_path}/*", files)
    return [(f, f, 'DATA') for f in extra_datas]

# 添加配置文件
a.datas += [('config/tencent_cloud_voice_type.csv', 'config/tencent_cloud_voice_type.csv', 'DATA')]

# 添加Resources文件夹中的资源
if os.path.exists('Resources'):
    a.datas += extra_datas('Resources')
"""
    
    # 在pyz定义之前插入资源收集代码
    pyz_pos = content.find("pyz = PYZ(")
    if pyz_pos != -1:
        content = content[:pyz_pos] + resources_function + content[pyz_pos:]
    
    # 写回修改后的spec文件
    with open("tts_gui.spec", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("spec文件创建和配置完成")

def build_exe(use_upx=False, one_file=True):
    """执行打包操作"""
    # 清理旧的构建文件
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # 打包命令
    cmd = "pyinstaller --clean --noconfirm"
    
    # 添加UPX支持
    if use_upx:
        # 查找UPX
        upx_paths = [
            "upx",  # 如果在PATH中
            "C:\\Tools\\upx\\upx.exe",
            "C:\\Program Files\\upx\\upx.exe",
            "C:\\Program Files (x86)\\upx\\upx.exe",
        ]
        
        upx_path = None
        for path in upx_paths:
            try:
                subprocess.run([path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                upx_path = path
                break
            except (FileNotFoundError, PermissionError):
                continue
        
        if upx_path:
            cmd += f" --upx-dir=\"{os.path.dirname(upx_path)}\""
            print(f"使用UPX: {upx_path}")
        else:
            print("未找到UPX，将不使用压缩")
    
    # 添加spec文件
    cmd += " tts_gui.spec"
    
    # 执行打包
    returncode = run_command(cmd)
    
    if returncode == 0:
        print("\n打包成功！")
        # 显示可执行文件位置和大小
        exe_path = "dist/tts_gui.exe" if one_file else "dist/tts_gui/tts_gui.exe"
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"可执行文件位置: {os.path.abspath(exe_path)}")
            print(f"文件大小: {size_mb:.2f} MB")
            
            # 新增：复制资源目录到exe所在目录
            target_dir = os.path.dirname(os.path.abspath(exe_path))
            for folder in ['AudioResources', 'config']:
                if os.path.exists(folder):
                    dest = os.path.join(target_dir, folder)
                    shutil.copytree(folder, dest, dirs_exist_ok=True)
                    print(f"已复制 {folder} 到 {dest}")
                else:
                    print(f"警告：未找到资源目录 {folder}")
            
            # 新增：复制ffmpeg.exe（保持目录结构）
            source_ffmpeg = os.path.abspath("softwares/ffmpeg/ffmpeg.exe")
            if os.path.exists(source_ffmpeg):
                target_ffmpeg_dir = os.path.join(target_dir, "softwares/ffmpeg")
                os.makedirs(target_ffmpeg_dir, exist_ok=True)
                shutil.copy2(source_ffmpeg, target_ffmpeg_dir)
                print(f"已复制 ffmpeg.exe 到 {target_ffmpeg_dir}")
            else:
                print(f"警告：未找到ffmpeg.exe文件：{source_ffmpeg}")

        else:
            print(f"警告: 未找到生成的可执行文件: {exe_path}")
    else:
        print("\n打包失败，请检查上述错误信息")

def main():
    parser = argparse.ArgumentParser(description="腾讯云语音合成工具打包脚本")
    parser.add_argument("--no-upx", action="store_true", help="不使用UPX压缩")
    parser.add_argument("--multi-file", action="store_true", help="使用多文件模式而不是单文件")
    args = parser.parse_args()
    
    print("=== 腾讯云语音合成工具打包脚本 ===")
    
    # 检查PyInstaller是否已安装
    try:
        subprocess.run(["pyinstaller", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("错误: 未安装PyInstaller。请运行 pip install pyinstaller")
        return 1
    
    # 创建和配置spec文件
    create_spec_file()
    
    # 执行打包
    build_exe(use_upx=not args.no_upx, one_file=not args.multi_file)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())