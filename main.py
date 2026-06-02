import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont

from translator_engine import GalTranslatorThread

class FloatingSubtitleWindow(QWidget):
    def __init__(self, api_key, base_url, model_name):
        super().__init__()
        
        # UI 配置
        self.init_ui()
        
        # 拖拽相关
        self.old_pos = None

        # 初始化后台翻译线程
        self.translator_thread = GalTranslatorThread(api_key, base_url, model_name)
        self.translator_thread.translation_done.connect(self.update_translation)
        self.translator_thread.error_occurred.connect(self.show_error)
        self.translator_thread.start()

    def init_ui(self):
        # 设置窗口标志：无边框、置顶、不抢占焦点
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.ToolTip  # 加上 ToolTip 级别，强行突破普通全屏置顶限制
        )
        # 背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 初始窗口大小和位置
        self.resize(1000, 200)
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 翻译文本显示标签
        self.label = QLabel("🚀 翻译模块已启动，等待游戏文本复制...", self)
        self.label.setWordWrap(True)
        # 文字居中对齐，偏下
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
        
        # 字体设置：大字号，粗体，适合阅读
        font = QFont("Microsoft YaHei", 24, QFont.Weight.Bold)
        self.label.setFont(font)
        
        # 文本颜色设为白色
        self.label.setStyleSheet("color: white;")
        
        # 添加黑色文字阴影（实现类似描边的效果以保证在复杂画面背景下的可读性）
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)          # 阴影模糊半径
        shadow.setColor(QColor(0, 0, 0, 255)) # 纯黑且不透明
        shadow.setOffset(2, 2)           # 阴影偏移
        self.label.setGraphicsEffect(shadow)
        
        layout.addWidget(self.label)
        
    def update_translation(self, original_text, translated_text):
        """收到翻译结果时更新 UI"""
        self.label.setText(f"{translated_text}")
        self.raise_() # 每次刷新翻译时，强行把自己提升到最前
        
    def show_error(self, error_msg):
        """显示错误信息，使用红色或带颜色的 HTML 标记"""
        self.label.setText(f"<font color='#ff6b6b'>{error_msg}</font>")

    # --- 以下实现无边框窗口的鼠标拖拽功能 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        """双击窗口任意位置退出程序"""
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        """窗口关闭时安全停止线程"""
        if self.translator_thread.isRunning():
            self.translator_thread.stop()
        event.accept()

if __name__ == "__main__":
    # 加载 .env 环境变量
    load_dotenv()
    
    API_KEY = os.getenv("API_KEY")
    BASE_URL = os.getenv("BASE_URL")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
    
    app = QApplication(sys.argv)
    
    if not API_KEY or not BASE_URL:
        # 如果没有配置好环境变量，则提示用户
        print("【启动失败】: 找不到 API_KEY 或 BASE_URL。")
        print("请将 .env.example 复制为 .env，并在里面填入你的 API Key。")
        sys.exit(1)
        
    window = FloatingSubtitleWindow(API_KEY, BASE_URL, MODEL_NAME)
    window.show()
    
    sys.exit(app.exec())
