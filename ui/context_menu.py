# ui/context_menu.py
# -*- coding: utf-8 -*-
import tkinter as tk
import customtkinter as ctk
from tkinter import simpledialog

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
            search_text = simpledialog.askstring(
                "查找",
                "请输入要查找的文本：",
                parent=self.widget
            )
            
            if not search_text:
                return
            
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
