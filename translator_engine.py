import pyperclip
import time
import json
import requests
import os
from PyQt6.QtCore import QThread, pyqtSignal

class GalTranslatorThread(QThread):
    # 定义信号：(原文, 翻译文本)
    translation_done = pyqtSignal(str, str)
    # 定义信号：(错误信息)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, base_url, model_name="deepseek-chat", cache_file="translation_cache.json"):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.last_copied = ""
        self.is_running = True
        self.interval = 0.5

    def _load_cache(self) -> dict:
        """从本地加载翻译缓存字典"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ 缓存文件损坏，将创建新缓存。")
                return {}
        return {}

    def _save_cache(self):
        """将最新的缓存写回本地文件"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _call_api(self, text: str, context: str = "") -> str:
        """调用云端大模型 API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 优化提示词：处理标点符号，并加入上下文支持
        sys_prompt = (
            "将以下游戏文本翻译为中文。要求：\n"
            "1. 直接输出翻译结果，不要任何解释，不要带上任何额外的说明。\n"
            "2. 如果输入仅包含标点符号或无意义字符（如“...”、“？”、“！”、“～”等），请直接原样返回，绝对不要输出类似“请输入翻译内容”之类的话。\n"
        )
        
        user_content = text
        if context:
            user_content = f"[这是上一句话的翻译，供你参考上下文，不要翻译它]：{context}\n\n[请翻译以下当前文本]：\n{text}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3 
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=15)
            if response.status_code == 429:
                return "[翻译错误] API 额度已耗尽或请求太频繁 (429)"
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except requests.exceptions.Timeout:
            return "[翻译错误] 网络请求超时，请检查网络。"
        except requests.exceptions.RequestException as e:
            return f"[翻译错误] 网络请求异常: {e}"
        except Exception as e:
            return f"[翻译错误] API 调用失败: {e}"

    def get_translation(self, text: str) -> str:
        """获取翻译：优先查缓存，没有再调 API，并维护上下文"""
        text = text.strip()
        if not text:
            return ""

        if text in self.cache:
            # 命中缓存，更新上下文并返回
            trans = self.cache[text]
            self.context_history = trans
            return trans

        # 未命中，走 API（带上上一句话的翻译作为上下文）
        context = getattr(self, 'context_history', "")
        translated_text = self._call_api(text, context)
        
        if not translated_text.startswith("[翻译错误]"):
            self.cache[text] = translated_text
            self.context_history = translated_text  # 记录这句成功的翻译供下一句使用
            self._save_cache()

        return translated_text

    def run(self):
        """重写 QThread 的 run 方法，开始监听剪贴板"""
        # 尝试清空启动时的剪贴板，防止读入之前的脏数据
        try:
            pyperclip.copy("") 
        except pyperclip.PyperclipException:
            self.error_occurred.emit("⚠️ 剪贴板可能被其他程序锁定，无法清空。")
        
        while self.is_running:
            try:
                current_clipboard = pyperclip.paste().strip()
                
                # 检测到新的纯文本（排除空字符串和重复触发）
                if current_clipboard and current_clipboard != self.last_copied:
                    self.last_copied = current_clipboard
                    
                    translation = self.get_translation(current_clipboard)
                    
                    if translation.startswith("[翻译错误]"):
                        self.error_occurred.emit(translation)
                    else:
                        self.translation_done.emit(current_clipboard, translation)
                    
            except pyperclip.PyperclipException:
                # 剪贴板被其他应用锁定，忽略并在下次循环重试
                pass
            except Exception as e:
                 self.error_occurred.emit(f"[系统异常] 监听发生未知错误: {e}")
                 
            time.sleep(self.interval)

    def stop(self):
        """安全停止线程"""
        self.is_running = False
        self.wait()
