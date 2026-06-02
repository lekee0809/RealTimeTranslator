init -999 python:
    import os
    os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

init 999 python:
    config.gl_resize = True
    
    store.auto_translate_mode = True

    def toggle_translate_mode():
        store.auto_translate_mode = not store.auto_translate_mode
        if store.auto_translate_mode:
            renpy.notify("【翻译系统】: 已切换为 -> 持续自动翻译模式")
        else:
            renpy.notify("【翻译系统】: 已切换为 -> 节约 Token 模式 (按 T 键手动翻译)")

    def force_read_screen_text():
        import re
        text = ""
        
        # 第一层：绝对的物理抓取！直接去抓取 UI 界面上的 "what" 组件的实际内容。
        # 很多魔改游戏底层变量不更新，全靠这个组件在变。按 T 键时调用这个，绝对能抓到屏幕上的字！
        try:
            for screen_name in ["say", "nvl", "centered", "dialogue"]:
                w = renpy.get_widget(screen_name, "what")
                if w and hasattr(w, "text"):
                    text_data = w.text
                    if isinstance(text_data, list):
                        text = "".join([str(item) for item in text_data if type(item).__name__ in ('str', 'unicode')])
                    elif type(text_data).__name__ in ('str', 'unicode'):
                        text = text_data
                    if text:
                        break
        except Exception:
            pass

        # 第二层：如果 UI 组件没名字，抓取屏幕的底层内存池
        if not text:
            try:
                for screen_name in ["say", "nvl", "centered", "dialogue"]:
                    s = renpy.get_screen(screen_name)
                    if s and hasattr(s, "scope"):
                        if "what" in s.scope:
                            text_data = s.scope["what"]
                            if isinstance(text_data, list):
                                text = "".join([str(item) for item in text_data if type(item).__name__ in ('str', 'unicode')])
                            elif type(text_data).__name__ in ('str', 'unicode'):
                                text = text_data
                            if text:
                                break
                        elif "dialogue" in s.scope and s.scope["dialogue"]:
                            text = s.scope["dialogue"][-1].what
                            break
            except Exception:
                pass
                
        # 第三层：净化标签
        try:
            if text:
                text = re.sub(r'\{.*?\}', '', str(text))
        except Exception:
            pass
            
        return text

    store.last_polled_text = ""

    def poll_and_copy():
        if getattr(store, "auto_translate_mode", True):
            try:
                text = force_read_screen_text()
                if text and text != getattr(store, "last_polled_text", ""):
                    store.last_polled_text = text
                    import pygame.scrap
                    pygame.scrap.put(pygame.scrap.SCRAP_TEXT, text.encode('utf-8'))
            except Exception:
                pass

    def manual_copy_text():
        try:
            text = force_read_screen_text()
            if text:
                import pygame.scrap
                pygame.scrap.put(pygame.scrap.SCRAP_TEXT, text.encode('utf-8'))
                renpy.notify("【强制刷新】已抓取屏幕最新文本！")
        except Exception:
            pass

screen translation_hotkeys():
    # 轮询器：每 0.2 秒强制扫描一次屏幕像素/组件层，雷达式抓取！
    timer 0.2 action Function(poll_and_copy) repeat True

    # 兼容两种按键命名方式，确保万无一失
    key "y" action Function(toggle_translate_mode)
    key "K_y" action Function(toggle_translate_mode)
    key "t" action Function(manual_copy_text)
    key "K_t" action Function(manual_copy_text)

init 999 python:
    # 确保不管是刚进游戏，还是读取存档，这个热键界面都绝对会生效
    def ensure_hotkeys_active():
        renpy.show_screen("translation_hotkeys")
        
    config.start_callbacks.append(ensure_hotkeys_active)
    config.after_load_callbacks.append(ensure_hotkeys_active)

    def apply_borderless_2k():
        import sys
        try:
            preferences.fullscreen = False
        except Exception:
            pass
            
        if sys.platform == "win32":
            try:
                import ctypes
                
                # 【终极武器】：宣告进程为 DPI 感知模式。彻底无视 Windows 125% 的缩放坑！
                ctypes.windll.user32.SetProcessDPIAware()
                
                title = getattr(config, "window_title", "Z.A.T.O.")
                hwnd = ctypes.windll.user32.FindWindowW(None, title)
                if not hwnd:
                    hwnd = ctypes.windll.user32.GetForegroundWindow()

                if hwnd:
                    GWL_STYLE = -16
                    WS_POPUP = 0x80000000
                    WS_VISIBLE = 0x10000000
                    WS_MINIMIZEBOX = 0x00020000
                    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, WS_POPUP | WS_VISIBLE | WS_MINIMIZEBOX)
                    # -2 确保不抢占顶层，2560x1440 精准坐标
                    ctypes.windll.user32.SetWindowPos(hwnd, -2, 0, 0, 2560, 1440, 0x0024)
            except Exception:
                pass

screen manual_translate_overlay():
    timer 1.5 action [Function(apply_borderless_2k)]

init 999 python:
    config.always_shown_screens.append("manual_translate_overlay")
