import sys
import os
import csv
import tempfile
import subprocess
import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QScrollArea, QGridLayout,
                            QTabWidget, QFrame, QStackedWidget, QComboBox, QPlainTextEdit,
                            QFileDialog)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QTextCursor, QCursor
from PyQt5.QtSvg import QSvgRenderer
from qfluentwidgets import (PushButton, TabBar, SearchLineEdit, Slider, 
                           ToggleButton, CardWidget, ToolButton, InfoBar,
                           FluentIcon, ComboBox)

# 导入audio_generator模块
import audio_generator

# 音色信息类
class VoiceInfo:
    def __init__(self, voice_id, name, scene, voice_type, language, sample_rate, emotion):
        self.voice_id = voice_id
        self.name = name
        self.scene = scene
        self.voice_type = voice_type
        self.language = language
        self.sample_rate = sample_rate
        self.emotion = emotion
        # 判断性别
        self.gender = "女声" if ("女声" in scene or not ("男声" in scene)) else "男声"
        self.is_female = self.gender == "女声"

# 修改VoiceCard类以支持悬停播放功能
class VoiceCard(CardWidget):
    def __init__(self, voice_info, parent=None):
        super().__init__(parent)
        self.voice_info = voice_info
        self.setFixedSize(180, 80)
        
        # 设置鼠标跟踪，以便接收鼠标悬停事件
        self.setMouseTracking(True)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 头像容器，用于放置头像和播放按钮
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(40, 40)
        self.avatar_container_layout = QVBoxLayout(self.avatar_container)
        self.avatar_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 头像
        self.avatar_label = QLabel()
        
        # 获取当前项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 根据性别选择头像
        if voice_info.is_female:
            avatar_path = os.path.join(current_dir, "Resources", "icon-women.svg")
        else:
            avatar_path = os.path.join(current_dir, "Resources", "icon-man.svg")
            
        if os.path.exists(avatar_path):
            # 加载SVG文件
            renderer = QSvgRenderer(avatar_path)
            pixmap = QPixmap(40, 40)
            pixmap.fill(Qt.transparent)  # 确保背景透明
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
        else:
            # 默认头像
            pixmap = QPixmap(40, 40)
            if voice_info.is_female:
                pixmap.fill(Qt.red)  # 默认红色头像-女声
            else:
                pixmap.fill(Qt.blue)  # 默认蓝色头像-男声
        
        self.avatar_label.setPixmap(pixmap)
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_container_layout.addWidget(self.avatar_label)
        
        # 创建播放按钮（初始隐藏）
        self.play_button = ToolButton(self.avatar_container)
        play_icon_path = os.path.join(current_dir, "Resources", "image_icon_listen_play.svg")
        
        if os.path.exists(play_icon_path):
            # 加载播放图标
            play_renderer = QSvgRenderer(play_icon_path)
            play_pixmap = QPixmap(30, 30)
            play_pixmap.fill(Qt.transparent)
            play_painter = QPainter(play_pixmap)
            play_renderer.render(play_painter)
            play_painter.end()
            
            self.play_button.setIcon(QIcon(play_pixmap))
        else:
            # 如果找不到SVG，使用内置图标
            self.play_button.setIcon(FluentIcon.PLAY)
        
        self.play_button.setFixedSize(30, 30)
        self.play_button.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); border-radius: 15px;")
        self.play_button.setCursor(QCursor(Qt.PointingHandCursor))  # 设置鼠标悬停样式为手型
        self.play_button.clicked.connect(self.play_audio_sample)
        
        # 设置播放按钮在头像中央
        self.play_button.setGeometry(5, 5, 30, 30)  # 居中放置
        self.play_button.hide()  # 初始时隐藏
        
        # 文本信息
        self.info_layout = QVBoxLayout()
        self.name_label = QLabel(voice_info.name)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.description_label = QLabel(voice_info.scene)
        self.description_label.setStyleSheet("color: gray;")
        
        self.info_layout.addWidget(self.name_label)
        self.info_layout.addWidget(self.description_label)
        
        self.layout.addWidget(self.avatar_container)
        self.layout.addLayout(self.info_layout)
        
        # 热门标签 (大模型音色和精品音色添加热门标签)
        if "大模型音色" in voice_info.voice_type or "精品音色" in voice_info.voice_type:
            self.hot_button = PushButton("热门")
            self.hot_button.setFixedSize(40, 20)
            self.hot_button.setStyleSheet("background-color: orange; color: white; border-radius: 5px;")
            self.layout.addWidget(self.hot_button, 0, Qt.AlignTop | Qt.AlignRight)
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.play_button.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.play_button.hide()
        super().leaveEvent(event)
    
    def play_audio_sample(self):
        """播放音色示例"""
        # 通过找到父窗口来调用播放函数
        app = self.window()
        if app and hasattr(app, 'find_audio_sample') and hasattr(app, 'play_audio_file'):
            voice_id = self.voice_info.voice_id
            audio_file = app.find_audio_sample(voice_id)
            if audio_file:
                app.play_audio_file(audio_file)
                # 添加日志
                if hasattr(app, 'log'):
                    app.log(f"播放音色 {self.voice_info.name} (ID: {voice_id}) 的示例音频")
            else:
                # 未找到音频文件时通知用户
                if hasattr(app, 'log'):
                    app.log(f"未找到音色 {self.voice_info.name} 的示例音频")
                
                InfoBar.warning(
                    title="警告",
                    content=f"未找到音色 {self.voice_info.name} 的示例音频",
                    parent=app
                )
        
    def mousePressEvent(self, event):
        # 选中效果
        self.setStyleSheet("background-color: #e0e0e0; border: 2px solid #1890ff; border-radius: 5px;")
        super().mousePressEvent(event)

# 日志输出重定向类
class LogRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        
    def write(self, text):
        self.buffer += text
        if text.endswith('\n'):
            self.text_widget.appendPlainText(self.buffer.rstrip())
            self.buffer = ""
            # 自动滚动到底部
            self.text_widget.moveCursor(QTextCursor.End)
    
    def flush(self):
        if self.buffer:
            self.text_widget.appendPlainText(self.buffer)
            self.buffer = ""

# 创建一个线程类来运行语音合成任务
class SynthesisThread(QThread):
    synthesis_complete = pyqtSignal(bool, str)  # 信号：合成完成(成功/失败, 输出文件路径)
    progress_update = pyqtSignal(str)  # 信号：进度更新

    def __init__(self, voice_id, text, speed, volume, output_path):
        super().__init__()
        self.voice_id = voice_id
        self.text = text
        self.speed = speed
        self.volume = volume
        self.output_path = output_path

    def run(self):
        try:
            # 添加日志输出，检查文本内容
            self.progress_update.emit(f"准备合成文本: '{self.text}'")
            
            # 确保文本不为空且为字符串类型
            if not self.text or not isinstance(self.text, str):
                self.progress_update.emit("错误: 文本为空或类型错误")
                self.synthesis_complete.emit(False, "")
                return
                
            # 尝试去除可能导致问题的特殊字符
            cleaned_text = self.text.strip()
            
            # 重定向stdout来捕获audio_generator的输出
            original_stdout = sys.stdout
            sys.stdout = self

            # 调用audio_generator的text_to_speech函数
            self.progress_update.emit("调用text_to_speech函数...")
            success = audio_generator.text_to_speech(
                text=cleaned_text,  # 使用清理后的文本
                output_file=self.output_path,
                voice_type=int(self.voice_id)
            )

            # 恢复原始stdout
            sys.stdout = original_stdout

            # 发送完成信号
            self.synthesis_complete.emit(success, self.output_path if success else "")
            
        except Exception as e:
            self.progress_update.emit(f"合成过程出错: {str(e)}")
            self.synthesis_complete.emit(False, "")

    def write(self, text):
        # 捕获print输出并发送为进度更新
        if text.strip():
            self.progress_update.emit(text.strip())
            
    def flush(self):
        # 必须有的方法，用于io操作
        pass

class TTSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.voice_list = []
        self.voice_by_scene = {}
        self.all_scenes = []
        self.all_genders = ["女声", "男声"]
        self.current_scene = None
        self.current_gender = None
        self.current_type = None
        self.load_voice_types()
        self.initUI()

    def load_voice_types(self):
        """从CSV文件加载音色类型"""
        try:
            with open('config/tencent_cloud_voice_type.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过标题行
                
                scenes_set = set()  # 用于收集不重复的场景类型
                types_set = set()   # 用于收集不重复的音色类型
                
                for row in reader:
                    if len(row) >= 7:
                        voice_id = row[0]
                        name = row[1]
                        scene = row[2]
                        voice_type = row[3]
                        language = row[4]
                        sample_rate = row[5]
                        emotion = row[6]
                        
                        voice_info = VoiceInfo(voice_id, name, scene, voice_type, language, sample_rate, emotion)
                        self.voice_list.append(voice_info)
                        
                        # 提取场景，去掉"男声"、"女声"字样
                        cleaned_scene = scene
                        for gender in ["男声", "女声"]:
                            cleaned_scene = cleaned_scene.replace(gender, "")
                        cleaned_scene = cleaned_scene.strip()
                        
                        # 收集唯一场景和类型
                        scenes_set.add(cleaned_scene)
                        types_set.add(voice_type)
                        
                        # 按推荐场景分组
                        if cleaned_scene not in self.voice_by_scene:
                            self.voice_by_scene[cleaned_scene] = []
                            
                        self.voice_by_scene[cleaned_scene].append(voice_info)
                
                # 将场景集合转换为列表并排序
                self.all_scenes = sorted(list(scenes_set))
                self.all_types = sorted(list(types_set))
                        
            print(f"已加载 {len(self.voice_list)} 种音色，{len(self.all_scenes)} 种场景")
            
        except Exception as e:
            print(f"加载音色文件失败: {e}")
            
    def find_audio_sample(self, voice_id):
        """查找音色对应的示例音频"""
        voice_id_str = str(voice_id)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        audio_dirs = [
            os.path.join(current_dir, "AudioResources", "samples_8k"),
            os.path.join(current_dir, "AudioResources", "samples_16k"),
            os.path.join(current_dir, "AudioResources", "samples_24k")
        ]
        
        for dir_path in audio_dirs:
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.startswith(voice_id_str) and (file.endswith('.mp3') or file.endswith('.wav')):
                        return os.path.join(dir_path, file)
        
        return None

    def initUI(self):
        # 设置窗口标题
        self.setWindowTitle('语音合成工具')
        self.resize(1800, 1200)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabBar::tab { height: 30px; min-width: 100px; }")
        
        # 合成音频标签页
        self.synthesis_tab = QWidget()
        self.synthesis_layout = QVBoxLayout(self.synthesis_tab)
        
        # 合成记录标签页
        self.history_tab = QWidget()
        self.history_layout = QVBoxLayout(self.history_tab)
        self.history_layout.addWidget(QLabel("合成记录将在这里显示"))
        
        # 添加标签页
        self.tab_widget.addTab(self.synthesis_tab, "合成音频")
        self.tab_widget.addTab(self.history_tab, "合成记录")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建搜索框和过滤器区域
        search_filter_layout = QHBoxLayout()
        
        # 搜索框
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("请输入音色名称搜索")
        self.search_box.setFixedWidth(200)
        search_filter_layout.addWidget(self.search_box)
        
        # 场景下拉框
        self.scene_combo = ComboBox(self)
        self.scene_combo.addItem("全部场景")
        for scene in self.all_scenes:
            self.scene_combo.addItem(scene)
        search_filter_layout.addWidget(self.scene_combo)
        
        # 性别下拉框
        self.gender_combo = ComboBox(self)
        self.gender_combo.addItem("全部性别")
        for gender in self.all_genders:
            self.gender_combo.addItem(gender)
        search_filter_layout.addWidget(self.gender_combo)
        
        # 类型下拉框
        self.type_combo = ComboBox(self)
        self.type_combo.addItem("全部类型")
        for voice_type in self.all_types:
            self.type_combo.addItem(voice_type)
        search_filter_layout.addWidget(self.type_combo)
        
        # 添加伸展因子使右侧文本靠右
        search_filter_layout.addStretch(1)
        
        # 右侧提示文本
        hint_label = QLabel("请输入需要合成的文字，支持直接解析SSML标签，最多可支持600个字符")
        hint_label.setStyleSheet("color: gray;")
        search_filter_layout.addWidget(hint_label)
        
        self.synthesis_layout.addLayout(search_filter_layout)
        
        # 添加分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.synthesis_layout.addWidget(line)
        
        # 创建左右分栏布局
        split_layout = QHBoxLayout()
        
        # 左侧音色选择区域 - 创建一个可以刷新的容器
        self.left_container = QWidget()
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setWidget(self.left_container)
        
        # 右侧文本输入和控制区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 选中的音色显示(默认选择WeRose)
        selected_voice_layout = QHBoxLayout()
        
        # 查找WeRose音色
        default_voice = None
        for voice in self.voice_list:
            if voice.name == "WeRose":
                default_voice = voice
                break
        
        if not default_voice and self.voice_list:
            default_voice = self.voice_list[0]
            
        # 默认选中的音色
        if default_voice:
            self.selected_voice = VoiceCard(default_voice)
            self.selected_voice.setFixedSize(180, 60)
            selected_voice_layout.addWidget(self.selected_voice)
        else:
            # 如果没有找到任何音色，添加一个占位符
            temp_label = QLabel("未找到音色数据")
            selected_voice_layout.addWidget(temp_label)
            
        selected_voice_layout.addStretch(1)
        
        right_layout.addLayout(selected_voice_layout)
        
        # 文本输入区域
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入需要合成的文字...")
        self.text_input.setMinimumHeight(200)
        right_layout.addWidget(self.text_input)
        
        # 语速和音量控制
        controls_layout = QHBoxLayout()
        
        # 语速控制
        speed_layout = QVBoxLayout()
        speed_label = QLabel("语速")
        self.speed_slider = Slider(Qt.Horizontal)
        self.speed_slider.setRange(-20, 20)  # -2.0到2.0
        self.speed_slider.setSingleStep(1)   # 步长0.1
        self.speed_slider.setValue(0)
        self.speed_value = QLabel("0.0")
        
        speed_slider_layout = QHBoxLayout()
        speed_slider_layout.addWidget(self.speed_slider)
        speed_slider_layout.addWidget(self.speed_value)
        
        speed_layout.addWidget(speed_label)
        speed_layout.addLayout(speed_slider_layout)
        
        controls_layout.addLayout(speed_layout)
        controls_layout.addSpacing(20)
        
        # 音量控制
        volume_layout = QVBoxLayout()
        volume_label = QLabel("音量")
        self.volume_slider = Slider(Qt.Horizontal)
        self.volume_slider.setRange(0, 10)
        self.volume_slider.setValue(5)
        self.volume_value = QLabel("5")
        
        volume_slider_layout = QHBoxLayout()
        volume_slider_layout.addWidget(self.volume_slider)
        volume_slider_layout.addWidget(self.volume_value)
        
        volume_layout.addWidget(volume_label)
        volume_layout.addLayout(volume_slider_layout)
        
        controls_layout.addLayout(volume_layout)
        
        right_layout.addLayout(controls_layout)
        
        # 底部控制区域
        bottom_controls = QHBoxLayout()
        
        # 合成按钮
        self.synthesize_button = PushButton("合成语音")
        self.synthesize_button.setIcon(FluentIcon.MICROPHONE)
        self.synthesize_button.setFixedSize(100, 36)
        self.synthesize_button.setEnabled(False)  # 初始时禁用按钮
        bottom_controls.addWidget(self.synthesize_button)
        
        # 下载按钮
        self.download_button = ToolButton()
        self.download_button.setIcon(FluentIcon.DOWNLOAD)
        self.download_button.setFixedSize(36, 36)
        bottom_controls.addWidget(self.download_button)
        
        # 播放按钮
        self.play_button = ToolButton()
        self.play_button.setIcon(FluentIcon.PLAY)
        self.play_button.setFixedSize(36, 36)
        bottom_controls.addWidget(self.play_button)
        
        # 播放进度条
        self.progress_slider = Slider(Qt.Horizontal)
        self.progress_slider.setEnabled(False)
        bottom_controls.addWidget(self.progress_slider)
        
        # 时间显示
        self.time_label = QLabel("00:00 / 00:00")
        bottom_controls.addWidget(self.time_label)
        
        right_layout.addLayout(bottom_controls)
        
        # 添加日志输出区域
        log_layout = QVBoxLayout()
        
        # 日志标题和清除按钮
        log_header_layout = QHBoxLayout()
        log_header_layout.addWidget(QLabel("输出信息"))
        
        self.clear_log_button = ToolButton()
        self.clear_log_button.setIcon(FluentIcon.DELETE)
        self.clear_log_button.setToolTip("清除日志")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_header_layout.addWidget(self.clear_log_button)
        
        log_layout.addLayout(log_header_layout)
        
        # 日志文本框
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("background-color: #f5f5f5; font-family: Consolas, Monaco, monospace;")
        log_layout.addWidget(self.log_output)
        
        # 重定向标准输出到日志框
        self.log_redirector = LogRedirector(self.log_output)
        
        right_layout.addLayout(log_layout)
        
        # 添加左右面板到分栏布局
        split_layout.addWidget(self.left_scroll, 1)  # 1是伸展因子，左侧占比更小
        split_layout.addWidget(right_panel, 2)  # 2是伸展因子，右侧占比更大
        
        self.synthesis_layout.addLayout(split_layout)
        
        # 初始显示所有音色
        self.update_voice_list()
        
        # 连接信号和槽
        self.speed_slider.valueChanged.connect(self.update_speed_value)
        self.volume_slider.valueChanged.connect(self.update_volume_value)
        self.synthesize_button.clicked.connect(self.on_synthesize)
        self.play_button.clicked.connect(self.on_play_audio)
        self.search_box.textChanged.connect(self.filter_voices)
        self.scene_combo.currentTextChanged.connect(self.on_scene_changed)
        self.gender_combo.currentTextChanged.connect(self.on_gender_changed)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        self.text_input.textChanged.connect(self.check_text_length)  # 添加文本变化监听
        
        # 输出初始化信息
        self.log("语音合成工具初始化完成")
        self.log(f"已加载 {len(self.voice_list)} 种音色")
    
    def check_text_length(self):
        """检查文本长度，并启用或禁用合成按钮"""
        text = self.text_input.toPlainText()
        has_text = len(text.strip()) > 0
        self.synthesize_button.setEnabled(has_text)
    
    def log(self, message):
        """添加日志到输出框"""
        self.log_output.appendPlainText(message)
        # 自动滚动到底部
        self.log_output.moveCursor(QTextCursor.End)
    
    def clear_log(self):
        """清除日志"""
        self.log_output.clear()
        self.log("日志已清除")
    
    def update_voice_list(self):
        """更新左侧音色列表显示"""
        # 清理旧的布局
        if self.left_container.layout():
            QWidget().setLayout(self.left_container.layout())
        
        left_layout = QVBoxLayout(self.left_container)
        
        # 确定显示哪些音色，通过应用所有筛选条件
        voices_to_display = self.voice_list.copy()
        
        # 筛选场景
        if self.current_scene and self.current_scene != "全部场景":
            filtered_voices = []
            for voice in voices_to_display:
                # 清理场景名称进行比较
                cleaned_scene = voice.scene
                for gender in ["男声", "女声"]:
                    cleaned_scene = cleaned_scene.replace(gender, "")
                cleaned_scene = cleaned_scene.strip()
                
                if cleaned_scene == self.current_scene:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 筛选性别
        if self.current_gender and self.current_gender != "全部性别":
            filtered_voices = []
            for voice in voices_to_display:
                if voice.gender == self.current_gender:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 筛选类型
        if self.current_type and self.current_type != "全部类型":
            filtered_voices = []
            for voice in voices_to_display:
                if voice.voice_type == self.current_type:
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 搜索过滤
        search_text = self.search_box.text().strip().lower()
        if search_text:
            filtered_voices = []
            for voice in voices_to_display:
                if (search_text in voice.name.lower() or 
                    search_text in voice.scene.lower()):
                    filtered_voices.append(voice)
            voices_to_display = filtered_voices
        
        # 按推荐场景对音色进行分组显示
        # 整理场景分组
        scene_groups = {}
        
        # 将音色按场景分组
        for voice in voices_to_display:
            cleaned_scene = voice.scene
            for gender in ["男声", "女声"]:
                cleaned_scene = cleaned_scene.replace(gender, "")
            cleaned_scene = cleaned_scene.strip()
            
            if cleaned_scene not in scene_groups:
                scene_groups[cleaned_scene] = []
                
            scene_groups[cleaned_scene].append(voice)
        
        # 添加各场景分组
        for scene, voices in scene_groups.items():
            if voices:  # 如果该分组有音色
                scene_label = QLabel(scene)
                scene_label.setStyleSheet("font-weight: bold; font-size: 14px;")
                left_layout.addWidget(scene_label)
                
                scene_grid = QGridLayout()
                
                for i, voice in enumerate(voices):
                    card = VoiceCard(voice)
                    card.mousePressEvent = lambda event, v=voice: self.on_voice_selected(event, v)
                    scene_grid.addWidget(card, i // 3, i % 3)
                
                left_layout.addLayout(scene_grid)
        
        # 添加伸展因子确保内容可滚动
        left_layout.addStretch(1)
        
        # 如果没有音色显示，添加提示
        if not voices_to_display:
            no_voice_label = QLabel("没有找到匹配的音色")
            no_voice_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(no_voice_label)
        
        # 记录筛选结果
        if hasattr(self, 'log_output'):
            self.log(f"显示 {len(voices_to_display)} 种音色")
    
    def on_scene_changed(self, scene_text):
        """处理场景下拉框选择变化"""
        self.current_scene = scene_text
        self.log(f"选择场景: {scene_text}")
        self.update_voice_list()
    
    def on_gender_changed(self, gender_text):
        """处理性别下拉框选择变化"""
        self.current_gender = gender_text
        self.log(f"选择性别: {gender_text}")
        self.update_voice_list()
    
    def on_type_changed(self, type_text):
        """处理类型下拉框选择变化"""
        self.current_type = type_text
        self.log(f"选择类型: {type_text}")
        self.update_voice_list()
    
    def on_voice_selected(self, event, voice_info):
        """处理音色选择"""
        # 更新选中的音色
        if hasattr(self, 'selected_voice'):
            # 移除旧的选中音色
            self.selected_voice.setParent(None)
        
        # 创建新的音色卡片
        self.selected_voice = VoiceCard(voice_info)
        self.selected_voice.setFixedSize(180, 60)
        
        # 查找右侧面板的选中音色布局
        for i in range(self.synthesis_layout.count()):
            item = self.synthesis_layout.itemAt(i)
            if isinstance(item, QHBoxLayout) and item.indexOf(self.left_scroll) >= 0:
                # 找到分栏布局
                split_layout = item
                # 找到右侧面板
                right_panel = split_layout.itemAt(1).widget()
                # 找到右侧面板的布局
                right_layout = right_panel.layout()
                # 找到选中音色布局
                selected_voice_layout = right_layout.itemAt(0).layout()
                
                # 清空现有内容
                while selected_voice_layout.count():
                    item = selected_voice_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # 添加新的选中音色
                selected_voice_layout.addWidget(self.selected_voice)
                selected_voice_layout.addStretch(1)
                break
        
        # 调用原始的点击事件处理
        QWidget.mousePressEvent(self.selected_voice, event)
        
        # 记录选择的音色
        self.log(f"已选择音色: {voice_info.name} (ID: {voice_info.voice_id})")
    
    def update_speed_value(self, value):
        """更新语速值显示"""
        real_value = value / 10.0
        self.speed_value.setText(f"{real_value:.1f}")
    
    def update_volume_value(self, value):
        """更新音量值显示"""
        self.volume_value.setText(str(value))
    
    def on_synthesize(self):
        """合成按钮点击事件"""
        text = self.text_input.toPlainText()
        if not text:
            InfoBar.error(
                title="错误",
                content="请输入需要合成的文字！",
                parent=self
            )
            self.log("错误: 请输入需要合成的文字")
            return
        
        # 获取选中的音色ID
        voice_id = None
        if hasattr(self, 'selected_voice') and hasattr(self.selected_voice, 'voice_info'):
            voice_id = self.selected_voice.voice_info.voice_id
        else:
            InfoBar.error(
                title="错误",
                content="请先选择一个音色！",
                parent=self
            )
            self.log("错误: 未选择音色")
            return
        
        # 获取语速和音量
        speed = self.speed_slider.value() / 10.0  # 转换为实际值(-2.0到2.0)
        volume = self.volume_slider.value()
        
        # 记录合成参数
        self.log("开始语音合成:")
        self.log(f"- 音色ID: {voice_id}")
        self.log(f"- 语速: {speed:.1f}")
        self.log(f"- 音量: {volume}")
        self.log(f"- 文本长度: {len(text)}字符")
        
        # 禁用UI控件，防止重复操作
        self.synthesize_button.setEnabled(False)
        self.text_input.setReadOnly(True)
        
        # 显示正在处理消息 - 不保存对象引用，避免线程安全问题
        InfoBar.info(
            title="处理中",
            content="正在合成语音，请稍候...",
            duration=3000,  # 3秒后自动消失
            parent=self
        )
        
        # 创建Audios目录（如果不存在）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        audio_dir = os.path.join(current_dir, "Audios")
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        
        # 创建带时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{voice_id}_{timestamp}.wav"
        output_path = os.path.join(audio_dir, filename)
        
        self.log(f"音频将保存至: {output_path}")
        
        # 创建并启动合成线程
        self.synthesis_thread = SynthesisThread(voice_id, text, speed, volume, output_path)
        self.synthesis_thread.progress_update.connect(self.log)
        self.synthesis_thread.synthesis_complete.connect(self.on_synthesis_complete)
        self.synthesis_thread.start()

    def on_synthesis_complete(self, success, output_path):
        """语音合成完成后的处理"""
        if success:
            self.log("语音合成成功！")
            InfoBar.info(
                title="成功",
                content="语音合成成功！",
                parent=self
            )
        else:
            self.log("语音合成失败。")
            InfoBar.error(
                title="失败",
                content="语音合成失败。",
                parent=self
            )
        
        # 启用UI控件，允许重复操作
        self.synthesize_button.setEnabled(True)
        self.text_input.setReadOnly(False)
    
    def play_audio_file(self, file_path):
        """播放音频文件"""
        if not os.path.exists(file_path):
            self.log(f"错误: 音频文件 {file_path} 不存在")
            return False
        
        try:
            # 使用系统默认播放器播放音频
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
            
            self.log(f"正在播放音频: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            self.log(f"播放音频失败: {str(e)}")
            return False
    
    def on_play_audio(self):
        """播放按钮点击事件"""
        if hasattr(self, 'selected_voice') and hasattr(self.selected_voice, 'voice_info'):
            voice_id = self.selected_voice.voice_info.voice_id
            voice_name = self.selected_voice.voice_info.name
            
            self.log(f"查找音色 {voice_name} (ID: {voice_id}) 的示例音频...")
            audio_file = self.find_audio_sample(voice_id)
            
            if audio_file and os.path.exists(audio_file):
                # 播放示例音频
                self.log(f"播放音频文件: {os.path.basename(audio_file)}")
                self.play_audio_file(audio_file)
                InfoBar.info(
                    title="播放音频",
                    content=f"正在播放音色 {voice_name} 的示例音频",
                    parent=self
                )
                
            else:
                self.log(f"未找到音色 {voice_name} 的示例音频")
                InfoBar.warning(
                    title="警告",
                    content=f"未找到音色 {voice_name} 的示例音频",
                    parent=self
                )
    
    def filter_voices(self, text):
        """根据搜索框筛选音色"""
        if text:
            self.log(f"搜索音色: {text}")
        self.update_voice_list()  # 根据当前的搜索文本和各种筛选条件重新加载音色列表

# 启动应用
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = TTSApp()
    ex.show()
    sys.exit(app.exec_())
