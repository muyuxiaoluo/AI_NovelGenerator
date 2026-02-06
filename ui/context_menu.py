# ui/context_menu.py
# -*- coding: utf-8 -*-
import tkinter as tk
import customtkinter as ctk
from tkinter import simpledialog, messagebox

class FindDialog:
    """
    自定义查找对话框，提供更大的输入框和更好的用户体验
    """
    def __init__(self, parent, search_callback):
        self.parent = parent
        self.search_callback = search_callback
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("查找")
        self.dialog.geometry("500x150")
        self.dialog.resizable(False, False)
        
        # 居中显示
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self._create_widgets()
        
        # 居中窗口
        self._center_window()
        
        # 绑定回车键
        self.search_entry.bind("<Return>", lambda e: self.on_search())
        
        # 等待窗口关闭
        self.dialog.wait_window()
    
    def _create_widgets(self):
        """创建对话框组件"""
        # 标签
        label = tk.Label(
            self.dialog, 
            text="请输入要查找的文本：",
            font=("Microsoft YaHei", 12)
        )
        label.pack(pady=(15, 5))
        
        # 输入框
        self.search_entry = tk.Entry(
            self.dialog, 
            font=("Microsoft YaHei", 12),
            width=50
        )
        self.search_entry.pack(pady=5, padx=20)
        self.search_entry.focus_set()
        
        # 按钮框架
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        # 查找按钮
        search_btn = tk.Button(
            button_frame,
            text="查找",
            command=self.on_search,
            font=("Microsoft YaHei", 10),
            width=10
        )
        search_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        cancel_btn = tk.Button(
            button_frame,
            text="取消",
            command=self.dialog.destroy,
            font=("Microsoft YaHei", 10),
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def _center_window(self):
        """将窗口居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def on_search(self):
        """执行查找"""
        search_text = self.search_entry.get()
        if search_text:
            self.result = search_text
            self.dialog.destroy()
        else:
            messagebox.showwarning("提示", "请输入要查找的文本", parent=self.dialog)

class TextWidgetContextMenu:
    """
    为 customtkinter.TextBox 或 tkinter.Text 提供右键复制/剪切/粘贴/全选的功能。
    同时支持 Ctrl+Z 撤回和 Ctrl+F 查找功能。
    """
    def __init__(self, widget):
        self.widget = widget
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_stack = 50
        
        self.menu = tk.Menu(widget, tearoff=0)
        self.menu.add_command(label="复制", command=self.copy)
        self.menu.add_command(label="粘贴", command=self.paste)
        self.menu.add_command(label="剪切", command=self.cut)
        self.menu.add_separator()
        self.menu.add_command(label="全选", command=self.select_all)
        
        # 绑定右键事件
        self.widget.bind("<Button-3>", self.show_menu)
        
        # 绑定 Ctrl+Z 撤回
        self.widget.bind("<Control-z>", self.undo)
        self.widget.bind("<Control-Z>", self.undo)
        
        # 绑定 Ctrl+Y 重做
        self.widget.bind("<Control-y>", self.redo)
        self.widget.bind("<Control-Y>", self.redo)
        
        # 绑定 Ctrl+F 查找
        self.widget.bind("<Control-f>", self.find_text)
        self.widget.bind("<Control-F>", self.find_text)
        
        # 监听文本变化，记录撤回历史
        self.widget.bind("<KeyRelease>", self.on_text_change)
        self.widget.bind("<ButtonRelease>", self.on_text_change)
        
        self._last_content = ""
        self._is_undoing = False
        
    def show_menu(self, event):
        if isinstance(self.widget, ctk.CTkTextbox):
            try:
                self.menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.menu.grab_release()
            
    def copy(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except tk.TclError:
            pass  # 没有选中文本时忽略错误

    def paste(self):
        try:
            text = self.widget.clipboard_get()
            self.widget.insert("insert", text)
        except tk.TclError:
            pass  # 剪贴板为空时忽略错误

    def cut(self):
        try:
            text = self.widget.get("sel.first", "sel.last")
            self.widget.delete("sel.first", "sel.last")
            self.widget.clipboard_clear()
            self.widget.clipboard_append(text)
        except tk.TclError:
            pass  # 没有选中文本时忽略错误

    def select_all(self):
        self.widget.tag_add("sel", "1.0", "end")
    
    def on_text_change(self, event=None):
        """
        监听文本变化，记录撤回历史
        """
        if self._is_undoing:
            return
            
        try:
            current_content = self.widget.get("1.0", "end")
            if current_content != self._last_content:
                self.undo_stack.append(self._last_content)
                if len(self.undo_stack) > self.max_undo_stack:
                    self.undo_stack.pop(0)
                self.redo_stack.clear()
                self._last_content = current_content
        except Exception:
            pass
    
    def undo(self, event=None):
        """
        Ctrl+Z 撤回操作
        """
        if not self.undo_stack:
            return
            
        try:
            current_content = self.widget.get("1.0", "end")
            self.redo_stack.append(current_content)
            
            previous_content = self.undo_stack.pop()
            self._is_undoing = True
            self.widget.delete("1.0", "end")
            self.widget.insert("1.0", previous_content)
            self._last_content = previous_content
            self._is_undoing = False
        except Exception as e:
            print(f"Undo error: {e}")
            self._is_undoing = False
        
        return "break"
    
    def redo(self, event=None):
        """
        Ctrl+Y 重做操作
        """
        if not self.redo_stack:
            return
            
        try:
            current_content = self.widget.get("1.0", "end")
            self.undo_stack.append(current_content)
            
            next_content = self.redo_stack.pop()
            self._is_undoing = True
            self.widget.delete("1.0", "end")
            self.widget.insert("1.0", next_content)
            self._last_content = next_content
            self._is_undoing = False
        except Exception as e:
            print(f"Redo error: {e}")
            self._is_undoing = False
        
        return "break"
    
    def find_text(self, event=None):
        """
        Ctrl+F 查找功能
        """
        try:
            dialog = FindDialog(self.widget, None)
            search_text = dialog.result
            
            if search_text:
                self._find_next(search_text, start="1.0")
            
        except Exception as e:
            print(f"Find error: {e}")
        
        return "break"
    
    def _find_next(self, search_text, start="1.0"):
        """
        查找下一个匹配项
        """
        try:
            pos = self.widget.search(search_text, start, nocase=1)
            
            if pos:
                self.widget.tag_remove("sel", "1.0", "end")
                
                end_pos = f"{pos}+{len(search_text)}c"
                self.widget.tag_add("sel", pos, end_pos)
                self.widget.see(pos)
                self.widget.focus_set()
                
                return pos
            else:
                from tkinter import messagebox
                messagebox.showinfo("查找", f"未找到 '{search_text}'")
                return None
                
        except Exception as e:
            print(f"Find next error: {e}")
            return None
