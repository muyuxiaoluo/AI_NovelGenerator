# ui/directory_tab.py
# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu

def build_directory_tab(self):
    self.directory_tab = self.tabview.add("Chapter Blueprint")
    self.directory_tab.rowconfigure(0, weight=0)
    self.directory_tab.rowconfigure(1, weight=1)
    self.directory_tab.columnconfigure(0, weight=1)

    # 创建顶部按钮容器框架，方便管理
    top_frame = ctk.CTkFrame(self.directory_tab, fg_color="transparent")
    top_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    
    # 加载按钮
    load_btn = ctk.CTkButton(top_frame, text="加载 Novel_directory.txt", command=self.load_chapter_blueprint, font=("Microsoft YaHei", 12))
    load_btn.pack(side="left", padx=5)

    # 字数统计
    self.directory_word_count_label = ctk.CTkLabel(top_frame, text="字数：0", font=("Microsoft YaHei", 12))
    self.directory_word_count_label.pack(side="left", padx=10)

    # 保存按钮
    save_btn = ctk.CTkButton(top_frame, text="保存修改", command=self.save_chapter_blueprint, font=("Microsoft YaHei", 12))
    save_btn.pack(side="right", padx=5)

    # === 新增：生成后续目录按钮 ===
    continue_btn = ctk.CTkButton(top_frame, text="📚 续写目录 (AI)", command=self.continue_directory_ui, font=("Microsoft YaHei", 12), fg_color="#3498DB")
    continue_btn.pack(side="right", padx=5)
    # ========================

    # === 新增：微调目录按钮 ===
    refine_btn = ctk.CTkButton(top_frame, text="✨ 微调目录 (AI)", command=self.refine_directory_card_ui, font=("Microsoft YaHei", 12), fg_color="#E67E22")
    refine_btn.pack(side="right", padx=5)
    # ========================

    self.directory_text = ctk.CTkTextbox(self.directory_tab, wrap="word", font=("Microsoft YaHei", 12))
    
    def update_word_count(event=None):
        text = self.directory_text.get("0.0", "end")
        count = len(text) - 1
        self.directory_word_count_label.configure(text=f"字数：{count}")
    
    self.directory_text.bind("<KeyRelease>", update_word_count)
    self.directory_text.bind("<ButtonRelease>", update_word_count)
    TextWidgetContextMenu(self.directory_text)
    self.directory_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

def load_chapter_blueprint(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    filename = os.path.join(filepath, "Novel_directory.txt")
    content = read_file(filename)
    self.directory_text.delete("0.0", "end")
    self.directory_text.insert("0.0", content)
    self.log("已加载 Novel_directory.txt 内容到编辑区。")

def save_chapter_blueprint(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    
    try:
        content = self.directory_text.get("0.0", "end").strip()
        if not content:
            messagebox.showwarning("警告", "目录内容为空，无法保存")
            return
        
        filename = os.path.join(filepath, "Novel_directory.txt")
        
        # 确保目录存在
        os.makedirs(filepath, exist_ok=True)
        
        # 直接保存（不需要先清空）
        save_string_to_txt(content, filename)
        
        # 验证保存是否成功
        if os.path.exists(filename):
            saved_content = read_file(filename)
            if saved_content.strip() == content:
                self.log("✅ 已成功保存对 Novel_directory.txt 的修改。")
                messagebox.showinfo("成功", "目录修改已保存！")
            else:
                self.log("❌ 保存验证失败：文件内容不匹配")
                messagebox.showerror("错误", "保存验证失败，请重试")
        else:
            self.log(f"❌ 保存失败：文件 {filename} 不存在")
            messagebox.showerror("错误", f"保存失败：文件 {filename} 未创建")
            
    except Exception as e:
        self.log(f"❌ 保存目录时出错: {str(e)}")
        messagebox.showerror("错误", f"保存目录时出错：{str(e)}")
