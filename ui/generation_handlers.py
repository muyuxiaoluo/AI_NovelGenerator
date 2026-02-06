# ui/generation_handlers.py
# -*- coding: utf-8 -*-
import os
import re
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import traceback
import glob
from utils import read_file, save_string_to_txt, clear_file_content
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    enrich_chapter_text,
    build_chapter_prompt,
    analyze_chapter_logic,
    rewrite_chapter_with_feedback,
    refine_chapter_detail,
    answer_novel_question
)
from consistency_checker import check_consistency

def generate_novel_architecture_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    def task():
        confirm = messagebox.askyesno("确认", "确定要生成小说架构吗？")
        if not confirm:
            self.enable_button_safe(self.btn_generate_architecture)
            return

        self.disable_button_safe(self.btn_generate_architecture)
        try:


            interface_format = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["timeout"]



            topic = self.topic_text.get("0.0", "end").strip()
            genre = self.genre_var.get().strip()
            num_chapters = self.safe_get_int(self.num_chapters_var, 10)
            word_number = self.safe_get_int(self.word_number_var, 3000)
            # 获取内容指导
            user_guidance = self.user_guide_text.get("0.0", "end").strip()

            self.safe_log("开始生成小说架构...")
            Novel_architecture_generate(
                interface_format=interface_format,
                api_key=api_key,
                base_url=base_url,
                llm_model=model_name,
                topic=topic,
                genre=genre,
                number_of_chapters=num_chapters,
                word_number=word_number,
                filepath=filepath,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_val,
                user_guidance=user_guidance  # 添加内容指导参数
            )
            self.safe_log("✅ 小说架构生成完成。请在 'Novel Architecture' 标签页查看或编辑。")
        except Exception:
            self.handle_exception("生成小说架构时出错")
        finally:
            self.enable_button_safe(self.btn_generate_architecture)
    threading.Thread(target=task, daemon=True).start()

def generate_chapter_blueprint_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    def task():
        if not messagebox.askyesno("确认", "确定要生成章节目录吗？"):
            self.enable_button_safe(self.btn_generate_chapter)
            return
        self.disable_button_safe(self.btn_generate_directory)
        try:

            number_of_chapters = self.safe_get_int(self.num_chapters_var, 10)

            interface_format = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["timeout"]


            user_guidance = self.user_guide_text.get("0.0", "end").strip()  # 新增获取用户指导

            self.safe_log("开始生成章节蓝图...")
            Chapter_blueprint_generate(
                interface_format=interface_format,
                api_key=api_key,
                base_url=base_url,
                llm_model=model_name,
                number_of_chapters=number_of_chapters,
                filepath=filepath,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_val,
                user_guidance=user_guidance  # 新增参数
            )
            self.safe_log("✅ 章节蓝图生成完成。请在 'Chapter Blueprint' 标签页查看或编辑。")
        except Exception:
            self.handle_exception("生成章节蓝图时出错")
        finally:
            self.enable_button_safe(self.btn_generate_directory)
    threading.Thread(target=task, daemon=True).start()

def generate_chapter_draft_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_generate_chapter)
        try:
            # === 1. 准备大模型参数 ===
            # 生成用的 LLM 配置
            draft_config_key = self.prompt_draft_llm_var.get()
            draft_config = self.loaded_config["llm_configs"][draft_config_key]
            
            draft_interface = draft_config["interface_format"]
            draft_key = draft_config["api_key"]
            draft_url = draft_config["base_url"]
            draft_model = draft_config["model_name"]
            draft_temp = draft_config["temperature"]
            draft_tokens = draft_config["max_tokens"]
            draft_timeout = draft_config["timeout"]

            # 自检用的 LLM 配置 (建议使用一致性审校的模型，通常逻辑更强)
            review_config_key = self.refine_logic_llm_var.get() 
            review_config = self.loaded_config["llm_configs"][review_config_key]
            
            review_interface = review_config["interface_format"]
            review_key = review_config["api_key"]
            review_url = review_config["base_url"]
            review_model = review_config["model_name"]
            # 补充审校模型的可选参数
            review_temp = review_config.get("temperature", 0.3)
            review_tokens = review_config.get("max_tokens", draft_tokens)
            
            # Embedding 参数
            emb_key = self.embedding_api_key_var.get().strip()
            emb_url = self.embedding_url_var.get().strip()
            emb_fmt = self.embedding_interface_format_var.get().strip()
            emb_model = self.embedding_model_name_var.get().strip()
            emb_k = self.safe_get_int(self.embedding_retrieval_k_var, 4)

            # 章节参数
            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            word_num = self.safe_get_int(self.word_number_var, 3000)
            user_guide = self.user_guide_text.get("0.0", "end").strip()
            char_inv = self.characters_involved_var.get().strip()
            key_items = self.key_items_var.get().strip()
            scene_loc = self.scene_location_var.get().strip()
            time_constr = self.time_constraint_var.get().strip()

            self.safe_log(f"模型：{draft_model}，正在生成第{chap_num}章草稿提示词...")

            # === 2. 构造提示词并让用户确认 ===
            prompt_text = build_chapter_prompt(
                api_key=draft_key,
                base_url=draft_url,
                model_name=draft_model,
                filepath=filepath,
                novel_number=chap_num,
                word_number=word_num,
                temperature=draft_temp,
                user_guidance=user_guide,
                characters_involved=char_inv,
                key_items=key_items,
                scene_location=scene_loc,
                time_constraint=time_constr,
                embedding_api_key=emb_key,
                embedding_url=emb_url,
                embedding_interface_format=emb_fmt,
                embedding_model_name=emb_model,
                embedding_retrieval_k=emb_k,
                interface_format=draft_interface,
                max_tokens=draft_tokens,
                timeout=draft_timeout,
                opening_mode=self.opening_mode_var.get(),  # 新增参数
                # 选角/逻辑模型用于人物卡和主动验证
                cast_api_key=review_key,
                cast_base_url=review_url,
                cast_model_name=review_model,
                cast_interface_format=review_interface,
                cast_temperature=review_temp,
                cast_max_tokens=review_tokens,
                cast_timeout=draft_timeout,
            )

            # 弹出确认框逻辑 (含字数统计)
            result: dict[str, str | None] = {"prompt": None}
            event = threading.Event()

            def create_prompt_dialog():
                dialog = ctk.CTkToplevel(self.master)
                dialog.title("确认提示词")
                dialog.geometry("800x600")
                
                # 顶部栏：标题 + 字数统计
                header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                header_frame.pack(fill="x", padx=10, pady=(10,0))
                ctk.CTkLabel(header_frame, text="生成提示词内容", font=("Microsoft YaHei", 12, "bold")).pack(side="left")
                prompt_wc_label = ctk.CTkLabel(header_frame, text="字数：0", font=("Microsoft YaHei", 12))
                prompt_wc_label.pack(side="right")

                text_box = ctk.CTkTextbox(dialog, wrap="word", font=("Microsoft YaHei", 12))
                text_box.pack(fill="both", expand=True, padx=10, pady=5)
                
                # 处理角色内容插入 (保持原有逻辑)
                final_prompt = prompt_text
                role_names = [name.strip() for name in self.char_inv_text.get("0.0", "end").strip().split(',') if name.strip()]
                role_lib_path = os.path.join(filepath, "角色库")
                role_contents = []
                
                if os.path.exists(role_lib_path):
                    for root, dirs, files in os.walk(role_lib_path):
                        for file in files:
                            if file.endswith(".txt") and os.path.splitext(file)[0] in role_names:
                                try:
                                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                        role_contents.append(f.read().strip())
                                except Exception: pass
                
                if role_contents:
                    role_content_str = "\n".join(role_contents)
                    placeholder_variations = [
                        "核心人物(可能未指定)：{characters_involved}",
                        "核心人物：{characters_involved}",
                        "核心人物:{characters_involved}"
                    ]
                    for ph in placeholder_variations:
                        if ph in final_prompt:
                            final_prompt = final_prompt.replace(ph, f"核心人物：\n{role_content_str}")
                            break
                    else:
                        lines = final_prompt.split('\n')
                        for i, line in enumerate(lines):
                            if "核心人物" in line and "：" in line:
                                lines[i] = f"核心人物：\n{role_content_str}"
                                break
                        final_prompt = '\n'.join(lines)

                text_box.insert("0.0", final_prompt)
                
                # 提示词字数更新逻辑
                def update_prompt_wc(e=None):
                    t = text_box.get("0.0", "end-1c")
                    prompt_wc_label.configure(text=f"字数：{len(t)}")
                text_box.bind("<KeyRelease>", update_prompt_wc)
                update_prompt_wc() # 初始化

                btn_frame = ctk.CTkFrame(dialog)
                btn_frame.pack(pady=10)
                
                def on_confirm():
                    result["prompt"] = text_box.get("1.0", "end").strip()
                    dialog.destroy()
                    event.set()
                
                def on_cancel():
                    dialog.destroy()
                    event.set()

                ctk.CTkButton(btn_frame, text="生成草稿", command=on_confirm).pack(side="left", padx=10)
                ctk.CTkButton(btn_frame, text="取消", command=on_cancel, fg_color="gray").pack(side="left", padx=10)
                dialog.protocol("WM_DELETE_WINDOW", on_cancel)

            self.master.after(0, create_prompt_dialog)
            event.wait()
            
            final_prompt = result["prompt"]
            if not final_prompt:
                self.safe_log("已取消生成。")
                return

            # === 3. 生成初稿 ===
            self.safe_log("正在生成草稿正文，请稍候...")
            draft_text = generate_chapter_draft(
                api_key=draft_key, base_url=draft_url, model_name=draft_model,
                filepath=filepath, novel_number=chap_num, word_number=word_num,
                temperature=draft_temp, user_guidance=user_guide,
                characters_involved=char_inv, key_items=key_items,
                scene_location=scene_loc, time_constraint=time_constr,
                embedding_api_key=emb_key, embedding_url=emb_url,
                embedding_interface_format=emb_fmt, embedding_model_name=emb_model,
                embedding_retrieval_k=emb_k, interface_format=draft_interface,
                max_tokens=draft_tokens, timeout=draft_timeout,
                custom_prompt_text=final_prompt
            )

            if not draft_text:
                self.safe_log("生成失败：返回内容为空。")
                return

            self.safe_log(f"✅模型：{draft_model}, 初稿生成完毕，正在进行逻辑自检...")

            # === 4. 自动逻辑自检 ===
            logic_report = analyze_chapter_logic(
                interface_format=review_interface,
                api_key=review_key,
                base_url=review_url,
                model_name=review_model,
                chapter_content=draft_text,
                filepath=filepath,
                novel_number=chap_num,
                timeout=draft_timeout
            )

            # === 5. 弹出“逻辑自检与修订”窗口 (含正文字数统计) ===
            def show_logic_check_window():
                check_win = ctk.CTkToplevel(self.master)
                check_win.title(f"逻辑自检与修订 - 第{chap_num}章")
                check_win.geometry("1200x800")
                
                # 布局配置
                check_win.grid_columnconfigure(0, weight=3) # 正文区域更宽
                check_win.grid_columnconfigure(1, weight=2)
                check_win.grid_rowconfigure(0, weight=1)
                
                # --- 左侧：正文编辑区 ---
                left_frame = ctk.CTkFrame(check_win)
                left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
                
                # 左侧顶部栏（标题 + 字数统计）
                left_header = ctk.CTkFrame(left_frame, fg_color="transparent")
                left_header.pack(fill="x", pady=5, padx=5)
                ctk.CTkLabel(left_header, text="章节正文 (可手动修改)", font=("Microsoft YaHei", 14, "bold")).pack(side="left")
                content_wc_label = ctk.CTkLabel(left_header, text="字数：0", font=("Microsoft YaHei", 12))
                content_wc_label.pack(side="right")

                content_box = ctk.CTkTextbox(left_frame, wrap="word", font=("Microsoft YaHei", 12))
                content_box.pack(fill="both", expand=True, padx=5, pady=5)
                content_box.insert("0.0", draft_text)
                
                # 正文字数更新逻辑
                def update_content_wc(event=None):
                    text = content_box.get("0.0", "end-1c")
                    content_wc_label.configure(text=f"字数：{len(text)}")
                
                content_box.bind("<KeyRelease>", update_content_wc)
                content_box.bind("<ButtonRelease>", update_content_wc)
                update_content_wc() # 初始化统计

                # --- 右侧：逻辑反馈区 ---
                right_frame = ctk.CTkFrame(check_win)
                right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
                ctk.CTkLabel(right_frame, text="逻辑漏洞报告 (可编辑反馈意见)", font=("Microsoft YaHei", 14, "bold")).pack(pady=5)

                # 解析报告中的特定段落，便于单独查看与复制
                def _parse_report_sections(text: str) -> dict:
                    sections = {
                        "knowledge_pov": "",
                        "future_conflict": "",
                        "full": text
                    }
                    try:
                        k_marker = "【知识不一致 & POV 异常】"
                        f_marker = "【后文目录冲突】"
                        k_idx = text.find(k_marker)
                        f_idx = text.find(f_marker)
                        if k_idx != -1:
                            # 从 k_marker 到 f_marker 或 文本末尾
                            start = k_idx + len(k_marker)
                            end = f_idx if (f_idx != -1 and f_idx > k_idx) else len(text)
                            sections["knowledge_pov"] = text[start:end].strip()
                        if f_idx != -1:
                            start = f_idx + len(f_marker)
                            sections["future_conflict"] = text[start:].strip()
                    except Exception:
                        pass
                    return sections

                parsed_sections = _parse_report_sections(logic_report if logic_report else "")

                # 快速查看按钮
                btns_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
                btns_frame.pack(fill="x", padx=5, pady=(0, 4))

                def _open_section_popup(title: str, content: str):
                    popup = ctk.CTkToplevel(self.master)
                    popup.title(title)
                    popup.geometry("700x400")
                    txt = ctk.CTkTextbox(popup, wrap="word")
                    txt.pack(fill="both", expand=True, padx=8, pady=8)
                    txt.insert("0.0", content if content else "(无内容)")

                    def _copy_to_feedback():
                        feedback_box.delete("0.0", "end")
                        feedback_box.insert("0.0", txt.get("0.0", "end").strip())
                        popup.destroy()

                    footer = ctk.CTkFrame(popup)
                    footer.pack(fill="x", padx=8, pady=6)
                    ctk.CTkButton(footer, text="复制到反馈框", command=_copy_to_feedback, fg_color="#3498DB").pack(side="right", padx=6)
                    ctk.CTkButton(footer, text="关闭", command=popup.destroy, fg_color="#95A5A6").pack(side="right")

                kb_btn = ctk.CTkButton(btns_frame, text="查看 知识不一致 & POV", width=200, command=lambda: _open_section_popup("知识不一致 & POV 异常", parsed_sections.get("knowledge_pov", "")))
                kb_btn.pack(side="right", padx=6)
                fc_btn = ctk.CTkButton(btns_frame, text="查看 后文目录冲突", width=200, command=lambda: _open_section_popup("后文目录冲突", parsed_sections.get("future_conflict", "")))
                fc_btn.pack(side="right", padx=6)

                feedback_box = ctk.CTkTextbox(right_frame, wrap="word", font=("Microsoft YaHei", 12))
                feedback_box.pack(fill="both", expand=True, padx=5, pady=5)
                feedback_box.insert("0.0", logic_report)
                
                # --- 底部：按钮区 ---
                btn_frame = ctk.CTkFrame(check_win)
                btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
                
                status_lbl = ctk.CTkLabel(btn_frame, text="等待操作...", text_color="gray")
                status_lbl.pack(side="left", padx=10)

                def _run_rewrite_with_model(use_interface, use_key, use_url, use_model, use_temp, use_tokens, use_timeout):
                    current_content = content_box.get("0.0", "end").strip()
                    current_feedback = feedback_box.get("0.0", "end").strip()
                    if not current_content:
                        return

                    status_lbl.configure(text=f"{use_model}⏳ 正在根据反馈重写，请稍候...", text_color="blue")
                    logic_fix_btn.configure(state="disabled")
                    plot_refine_btn.configure(state="disabled")
                    confirm_btn.configure(state="disabled")

                    def run_rewrite():
                        try:
                            new_text = rewrite_chapter_with_feedback(
                                interface_format=use_interface,
                                api_key=use_key,
                                base_url=use_url,
                                model_name=use_model,
                                original_content=current_content,
                                feedback=current_feedback,
                                temperature=use_temp,
                                max_tokens=use_tokens,
                                timeout=use_timeout,
                                filepath=filepath,
                                chapter_num=chap_num
                            )
                            if new_text:
                                self.master.after(0, lambda: content_box.delete("0.0", "end"))
                                self.master.after(0, lambda: content_box.insert("0.0", new_text))
                                self.master.after(0, lambda: feedback_box.delete("0.0", "end"))
                                self.master.after(0, lambda: feedback_box.insert("0.0", "（已根据意见重写。请检查左侧内容，如有新问题可继续输入反馈。）"))
                                # 重写完成后更新字数
                                self.master.after(0, update_content_wc)
                                self.master.after(0, lambda: status_lbl.configure(text="✅ 重写完成", text_color="green"))
                            else:
                                self.master.after(0, lambda: status_lbl.configure(text="❌ 重写失败", text_color="red"))
                        except Exception as e:
                            self.master.after(0, lambda: status_lbl.configure(text=f"❌ 出错: {str(e)}", text_color="red"))
                        finally:
                            self.master.after(0, lambda: logic_fix_btn.configure(state="normal"))
                            self.master.after(0, lambda: plot_refine_btn.configure(state="normal"))
                            self.master.after(0, lambda: confirm_btn.configure(state="normal"))

                    threading.Thread(target=run_rewrite, daemon=True).start()

                def on_rewrite_logic():
                    # 使用逻辑/审校模型进行修正（侧重逻辑一致性）
                    _run_rewrite_with_model(
                        use_interface=review_interface,
                        use_key=review_key,
                        use_url=review_url,
                        use_model=review_model,
                        use_temp=review_temp if 'review_temp' in locals() else 0.3,
                        use_tokens=review_tokens if 'review_tokens' in locals() else draft_tokens,
                        use_timeout=draft_timeout
                    )

                def on_rewrite_plot():
                    # 使用初稿生成模型进行剧情微调（保持文风与拓展）
                    _run_rewrite_with_model(
                        use_interface=draft_interface,
                        use_key=draft_key,
                        use_url=draft_url,
                        use_model=draft_model,
                        use_temp=draft_temp,
                        use_tokens=draft_tokens,
                        use_timeout=draft_timeout
                    )

                def on_confirm():
                    final_content = content_box.get("0.0", "end").strip()
                    
                    # 保存到文件
                    chapters_dir = os.path.join(filepath, "chapters")
                    os.makedirs(chapters_dir, exist_ok=True)
                    chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")
                    
                    clear_file_content(chapter_file)
                    save_string_to_txt(final_content, chapter_file)
                    
                    # 更新主界面显示
                    self.show_chapter_in_textbox(final_content)
                    self.safe_log(f"✅ 第{chap_num}章已确认并保存。")
                    check_win.destroy()

                logic_fix_btn = ctk.CTkButton(btn_frame, text="逻辑纠正 (Logic Fix)", command=on_rewrite_logic, fg_color="#E67E22", width=180)
                logic_fix_btn.pack(side="right", padx=6)

                plot_refine_btn = ctk.CTkButton(btn_frame, text="剧情微调 (Plot Refine)", command=on_rewrite_plot, fg_color="#8E44AD", width=180)
                plot_refine_btn.pack(side="right", padx=6)
                
                confirm_btn = ctk.CTkButton(btn_frame, text="确认无误，使用此版本 (Confirm)", command=on_confirm, fg_color="#27AE60", width=200)
                confirm_btn.pack(side="right", padx=10)
                
                check_win.protocol("WM_DELETE_WINDOW", on_confirm)

            self.master.after(0, show_logic_check_window)

        except Exception as e:
            self.handle_exception("生成草稿流程出错")
        finally:
            self.enable_button_safe(self.btn_generate_chapter)

    threading.Thread(target=task, daemon=True).start()

def finalize_chapter_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        if not messagebox.askyesno("确认", "确定要定稿当前章节吗？"):
            self.enable_button_safe(self.btn_finalize_chapter)
            return

        self.disable_button_safe(self.btn_finalize_chapter)
        try:

            interface_format = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["timeout"]


            embedding_api_key = self.embedding_api_key_var.get().strip()
            embedding_url = self.embedding_url_var.get().strip()
            embedding_interface_format = self.embedding_interface_format_var.get().strip()
            embedding_model_name = self.embedding_model_name_var.get().strip()

            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            word_number = self.safe_get_int(self.word_number_var, 3000)

            self.safe_log(f"开始定稿第{chap_num}章...")

            chapters_dir = os.path.join(filepath, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")

            edited_text = self.chapter_result.get("0.0", "end").strip()

            if len(edited_text) < 0.7 * word_number:
                ask = messagebox.askyesno("字数不足", f"当前章节字数 ({len(edited_text)}) 低于目标字数({word_number})的70%，是否要尝试扩写？")
                if ask:
                    self.safe_log("正在扩写章节内容...")
                    enriched = enrich_chapter_text(
                        chapter_text=edited_text,
                        word_number=word_number,
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                        temperature=temperature,
                        interface_format=interface_format,
                        max_tokens=max_tokens,
                        timeout=timeout_val
                    )
                    edited_text = enriched
                    self.master.after(0, lambda: self.chapter_result.delete("0.0", "end"))
                    self.master.after(0, lambda: self.chapter_result.insert("0.0", edited_text))
            clear_file_content(chapter_file)
            save_string_to_txt(edited_text, chapter_file)

            finalize_chapter(
                novel_number=chap_num,
                word_number=word_number,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                filepath=filepath,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val
            )
            self.safe_log(f"✅ 第{chap_num}章定稿完成（已更新前文摘要、角色状态、向量库）。")

            final_text = read_file(chapter_file)
            self.master.after(0, lambda: self.show_chapter_in_textbox(final_text))
        except Exception:
            self.handle_exception("定稿章节时出错")
        finally:
            self.enable_button_safe(self.btn_finalize_chapter)
    threading.Thread(target=task, daemon=True).start()

def do_consistency_check(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_check_consistency)
        try:
            interface_format = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["max_tokens"]
            timeout = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["timeout"]


            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            chap_file = os.path.join(filepath, "chapters", f"chapter_{chap_num}.txt")
            chapter_text = read_file(chap_file)

            if not chapter_text.strip():
                self.safe_log("⚠️ 当前章节文件为空或不存在，无法审校。")
                return

            self.safe_log("开始一致性审校...")
            result = check_consistency(
                novel_setting="",
                character_state=read_file(os.path.join(filepath, "character_state.txt")),
                global_summary=read_file(os.path.join(filepath, "global_summary.txt")),
                chapter_text=chapter_text,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout,
                plot_arcs=""
            )
            self.safe_log("审校结果：")
            self.safe_log(result)
        except Exception:
            self.handle_exception("审校时出错")
        finally:
            self.enable_button_safe(self.btn_check_consistency)
    threading.Thread(target=task, daemon=True).start()
def generate_batch_ui(self):

    # PenBo 优化界面，使用customtkinter进行批量生成章节界面
    def open_batch_dialog():
        dialog = ctk.CTkToplevel()
        dialog.title("批量生成章节")
        
        chapter_file = os.path.join(self.filepath_var.get().strip(), "chapters")
        files = glob.glob(os.path.join(chapter_file, "chapter_*.txt"))
        if not files:
            num = 1
        else:
            num = max(int(os.path.basename(f).split('_')[1].split('.')[0]) for f in files) + 1
            
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # 创建网格布局
        dialog.grid_columnconfigure(0, weight=0)
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_columnconfigure(2, weight=0)
        dialog.grid_columnconfigure(3, weight=1)
        
        # 起始章节
        ctk.CTkLabel(dialog, text="起始章节:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_start = ctk.CTkEntry(dialog)
        entry_start.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry_start.insert(0, str(num))
        
        # 结束章节
        ctk.CTkLabel(dialog, text="结束章节:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        entry_end = ctk.CTkEntry(dialog)
        entry_end.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        # 期望字数
        ctk.CTkLabel(dialog, text="期望字数:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_word = ctk.CTkEntry(dialog)
        entry_word.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        entry_word.insert(0, self.word_number_var.get())
        
        # 最低字数
        ctk.CTkLabel(dialog, text="最低字数:").grid(row=1, column=2, padx=10, pady=10, sticky="w")
        entry_min = ctk.CTkEntry(dialog)
        entry_min.grid(row=1, column=3, padx=10, pady=10, sticky="ew")
        entry_min.insert(0, self.word_number_var.get())

        # 自动扩写选项
        auto_enrich_bool = ctk.BooleanVar()
        auto_enrich_bool_ck = ctk.CTkCheckBox(dialog, text="低于最低字数时自动扩写", variable=auto_enrich_bool)
        auto_enrich_bool_ck.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        result = {"start": None, "end": None, "word": None, "min": None, "auto_enrich": None, "close": False}

        def on_confirm():
            nonlocal result
            if not entry_start.get() or not entry_end.get() or not entry_word.get() or not entry_min.get():
                messagebox.showwarning("警告", "请填写完整信息。")
                return

            result = {
                "start": entry_start.get(),
                "end": entry_end.get(),
                "word": entry_word.get(),
                "min": entry_min.get(),
                "auto_enrich": auto_enrich_bool.get(),
                "close": False
            }
            dialog.destroy()

        def on_cancel():
            nonlocal result
            result["close"] = True
            dialog.destroy()
            
        # 按钮框架
        button_frame = ctk.CTkFrame(dialog)
        button_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(button_frame, text="确认", command=on_confirm).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        ctk.CTkButton(button_frame, text="取消", command=on_cancel).grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.transient(self.master)
        dialog.wait_window(dialog)
        return result
    
    def generate_chapter_batch(self ,i ,word, min, auto_enrich):
        draft_interface_format = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["interface_format"]
        draft_api_key = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["api_key"]
        draft_base_url = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["base_url"]
        draft_model_name = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["model_name"]
        draft_temperature = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["temperature"]
        draft_max_tokens = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["max_tokens"]
        draft_timeout = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["timeout"]
        user_guidance = self.user_guide_text.get("0.0", "end").strip()  

        char_inv = self.characters_involved_var.get().strip()
        key_items = self.key_items_var.get().strip()
        scene_loc = self.scene_location_var.get().strip()
        time_constr = self.time_constraint_var.get().strip()

        embedding_api_key = self.embedding_api_key_var.get().strip()
        embedding_url = self.embedding_url_var.get().strip()
        embedding_interface_format = self.embedding_interface_format_var.get().strip()
        embedding_model_name = self.embedding_model_name_var.get().strip()
        embedding_k = self.safe_get_int(self.embedding_retrieval_k_var, 4)

        # 逻辑/选角模型配置（用于人物卡/主动验证）
        logic_cfg = self.loaded_config["llm_configs"][self.refine_logic_llm_var.get()]

        prompt_text = build_chapter_prompt(
            api_key=draft_api_key,
            base_url=draft_base_url,
            model_name=draft_model_name,
            filepath=self.filepath_var.get().strip(),
            novel_number=i,
            word_number=word,
            temperature=draft_temperature,
            user_guidance=user_guidance,
            characters_involved=char_inv,
            key_items=key_items,
            scene_location=scene_loc,
            time_constraint=time_constr,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_k,
            interface_format=draft_interface_format,
            max_tokens=draft_max_tokens,
            timeout=draft_timeout,
            opening_mode=self.opening_mode_var.get(),  # 新增参数
            cast_api_key=logic_cfg.get("api_key", ""),
            cast_base_url=logic_cfg.get("base_url", ""),
            cast_model_name=logic_cfg.get("model_name", ""),
            cast_interface_format=logic_cfg.get("interface_format", draft_interface_format),
            cast_temperature=logic_cfg.get("temperature", draft_temperature),
            cast_max_tokens=logic_cfg.get("max_tokens", draft_max_tokens),
            cast_timeout=logic_cfg.get("timeout", draft_timeout),
        )
        final_prompt = prompt_text
        role_names = [name.strip() for name in self.char_inv_text.get("0.0", "end").split("\n")]
        role_lib_path = os.path.join(self.filepath_var.get().strip(), "角色库")
        role_contents = []
        if os.path.exists(role_lib_path):
            for root, dirs, files in os.walk(role_lib_path):
                for file in files:
                    if file.endswith(".txt") and os.path.splitext(file)[0] in role_names:
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                role_contents.append(f.read().strip())  # 直接使用文件内容，不添加重复名字
                        except Exception as e:
                            self.safe_log(f"读取角色文件 {file} 失败: {str(e)}")
        if role_contents:
            role_content_str = "\n".join(role_contents)
            # 更精确的替换逻辑，处理不同情况下的占位符
            placeholder_variations = [
                "核心人物(可能未指定)：{characters_involved}",
                "核心人物：{characters_involved}",
                "核心人物(可能未指定):{characters_involved}",
                "核心人物:{characters_involved}"
            ]
            
            for placeholder in placeholder_variations:
                if placeholder in final_prompt:
                    final_prompt = final_prompt.replace(
                        placeholder,
                        f"核心人物：\n{role_content_str}"
                    )
                    break
            else:  # 如果没有找到任何已知占位符变体
                lines = final_prompt.split('\n')
                for i, line in enumerate(lines):
                    if "核心人物" in line and "：" in line:
                        lines[i] = f"核心人物：\n{role_content_str}"
                        break
                final_prompt = '\n'.join(lines)
        draft_text = generate_chapter_draft(
            api_key=draft_api_key,
            base_url=draft_base_url,
            model_name=draft_model_name,
            filepath=self.filepath_var.get().strip(),
            novel_number=i,
            word_number=word,
            temperature=draft_temperature,
            user_guidance=user_guidance,
            characters_involved=char_inv,
            key_items=key_items,
            scene_location=scene_loc,
            time_constraint=time_constr,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_k,
            interface_format=draft_interface_format,
            max_tokens=draft_max_tokens,
            timeout=draft_timeout,
            custom_prompt_text=final_prompt  
        )

        finalize_interface_format = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["interface_format"]
        finalize_api_key = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["api_key"]
        finalize_base_url = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["base_url"]
        finalize_model_name = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["model_name"]
        finalize_temperature = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["temperature"]
        finalize_max_tokens = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["max_tokens"]
        finalize_timeout = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["timeout"]

        chapters_dir = os.path.join(self.filepath_var.get().strip(), "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        chapter_path = os.path.join(chapters_dir, f"chapter_{i}.txt")
        if len(draft_text) < 0.7 * min and auto_enrich:
            self.safe_log(f"第{i}章草稿字数 ({len(draft_text)}) 低于目标字数({min})的70%，正在扩写...")
            enriched = enrich_chapter_text(
                chapter_text=draft_text,
                word_number=word,
                api_key=draft_api_key,
                base_url=draft_base_url,
                model_name=draft_model_name,
                temperature=draft_temperature,
                interface_format=draft_interface_format,
                max_tokens=draft_max_tokens,
                timeout=draft_timeout
            )
            draft_text = enriched
        clear_file_content(chapter_path)
        save_string_to_txt(draft_text, chapter_path)
        finalize_chapter(
            novel_number=i,
            word_number=word,
            api_key=finalize_api_key,
            base_url=finalize_base_url,
            model_name=finalize_model_name,
            temperature=finalize_temperature,
            filepath=self.filepath_var.get().strip(),
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            interface_format=finalize_interface_format,
            max_tokens=finalize_max_tokens,
            timeout=finalize_timeout
        )


    result = open_batch_dialog()
    if result["close"]:
        return

    for i in range(int(result["start"]), int(result["end"]) + 1):
        generate_chapter_batch(self, i, int(result["word"]), int(result["min"]), result["auto_enrich"])


def import_knowledge_handler(self):
    selected_file = filedialog.askopenfilename(
        title="选择要导入的知识库文件",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if selected_file:
        def task():
            self.disable_button_safe(self.btn_import_knowledge)
            try:
                emb_api_key = self.embedding_api_key_var.get().strip()
                emb_url = self.embedding_url_var.get().strip()
                emb_format = self.embedding_interface_format_var.get().strip()
                emb_model = self.embedding_model_name_var.get().strip()

                # 尝试不同编码读取文件
                content = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'ansi']
                for encoding in encodings:
                    try:
                        with open(selected_file, 'r', encoding=encoding) as f:
                            content = f.read()
                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        self.safe_log(f"读取文件时发生错误: {str(e)}")
                        raise

                if content is None:
                    raise Exception("无法以任何已知编码格式读取文件")

                # 创建临时UTF-8文件
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as temp:
                    temp.write(content)
                    temp_path = temp.name

                try:
                    self.safe_log(f"开始导入知识库文件: {selected_file}")
                    import_knowledge_file(
                        embedding_api_key=emb_api_key,
                        embedding_url=emb_url,
                        embedding_interface_format=emb_format,
                        embedding_model_name=emb_model,
                        file_path=temp_path,
                        filepath=self.filepath_var.get().strip()
                    )
                    self.safe_log("✅ 知识库文件导入完成。")
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except Exception:
                self.handle_exception("导入知识库时出错")
            finally:
                self.enable_button_safe(self.btn_import_knowledge)

        try:
            thread = threading.Thread(target=task, daemon=True)
            thread.start()
        except Exception as e:
            self.enable_button_safe(self.btn_import_knowledge)
            messagebox.showerror("错误", f"线程启动失败: {str(e)}")

def clear_vectorstore_handler(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    first_confirm = messagebox.askyesno("警告", "确定要清空本地向量库吗？此操作不可恢复！")
    if first_confirm:
        second_confirm = messagebox.askyesno("二次确认", "你确定真的要删除所有向量数据吗？此操作不可恢复！")
        if second_confirm:
            if clear_vector_store(filepath):
                self.log("已清空向量库。")
            else:
                self.log(f"未能清空向量库，请关闭程序后手动删除 {filepath} 下的 vectorstore 文件夹。")

def show_plot_arcs_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先在主Tab中设置保存文件路径")
        return

    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    if not os.path.exists(plot_arcs_file):
        messagebox.showinfo("剧情要点", "当前还未生成任何剧情要点或冲突记录。")
        return

    arcs_text = read_file(plot_arcs_file).strip()
    if not arcs_text:
        arcs_text = "当前没有记录的剧情要点或冲突。"

    top = ctk.CTkToplevel(self.master)
    top.title("剧情要点/未解决冲突")
    top.geometry("600x400")
    text_area = ctk.CTkTextbox(top, wrap="word", font=("Microsoft YaHei", 12))
    text_area.pack(fill="both", expand=True, padx=10, pady=10)
    text_area.insert("0.0", arcs_text)
    text_area.configure(state="disabled")


def refine_directory_card_ui(self):
    """
    微调章节目录的交互界面 (支持多章节范围修改)
    """
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return
        
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(directory_file):
        messagebox.showwarning("警告", "尚未生成目录文件 (Novel_directory.txt)。")
        return

    # 创建弹窗
    dialog = ctk.CTkToplevel(self.master)
    dialog.title("微调章节大纲 (支持多章节)")
    dialog.geometry("1000x750")
    
    # 布局配置
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    # --- 顶部控制区 ---
    top_frame = ctk.CTkFrame(dialog)
    top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
    ctk.CTkLabel(top_frame, text="起始章节:").pack(side="left", padx=(10, 5))
    start_chap_entry = ctk.CTkEntry(top_frame, width=60)
    start_chap_entry.pack(side="left", padx=5)
    
    ctk.CTkLabel(top_frame, text="结束章节:").pack(side="left", padx=(15, 5))
    end_chap_entry = ctk.CTkEntry(top_frame, width=60)
    end_chap_entry.pack(side="left", padx=5)
    
    # 辅助函数：构造正则
    def get_range_pattern(start_num, end_num):
        # 匹配从 "第{start}章" 开始，一直到 "第{end+1}章" 之前（或文件末尾）的所有内容
        # 兼容 "章节编号：第X章" 和 "第X章" 两种格式
        # 这里的逻辑是：找到 Start 的开头，然后向后找，直到找到 (End+1) 的开头
        next_num = end_num + 1
        pattern_str = (
            f"(?:(?:章节编号：\\s*)?第\\s*{start_num}\\s*章)"  # 起始标记
            f".*?"                                          # 中间内容 (非贪婪)
            f"(?=(?:\\n\\s*(?:章节编号：\\s*)?第\\s*{next_num}\\s*章)|\\Z)" # 结束标记 (前瞻断言：是下一章开头 或 文件末尾)
        )
        return re.compile(pattern_str, re.DOTALL)

    def load_chapter_info():
        s_val = start_chap_entry.get().strip()
        e_val = end_chap_entry.get().strip()
        
        if not s_val:
            messagebox.showwarning("提示", "请输入起始章节号")
            return
        
        try:
            start_num = int(s_val)
            # 如果没填结束章节，默认等于起始章节（单章模式）
            end_num = int(e_val) if e_val else start_num
            
            if end_num < start_num:
                messagebox.showerror("错误", "结束章节不能小于起始章节")
                return

            content = read_file(directory_file)
            pattern = get_range_pattern(start_num, end_num)
            
            match = pattern.search(content)
            if match:
                extracted = match.group(0).strip()
                outline_text.delete("0.0", "end")
                outline_text.insert("0.0", extracted)
                status_label.configure(text=f"已加载: 第 {start_num} - {end_num} 章", text_color="green")
                return True
            else:
                status_label.configure(text=f"未找到章节范围 {start_num}-{end_num}，请检查目录文件。", text_color="red")
                return False
                
        except ValueError:
            messagebox.showerror("错误", "章节号必须是数字")
        except Exception as e:
            messagebox.showerror("错误", f"读取失败: {str(e)}")
            return False

    ctk.CTkButton(top_frame, text="读取范围大纲", command=load_chapter_info, width=120).pack(side="left", padx=15)
    status_label = ctk.CTkLabel(top_frame, text="准备就绪", text_color="gray")
    status_label.pack(side="left", padx=10)

    # --- 中间内容区 ---
    content_frame = ctk.CTkFrame(dialog)
    content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_rowconfigure(1, weight=1)
    
    ctk.CTkLabel(content_frame, text="大纲内容 (可编辑/AI生成)", font=("Microsoft YaHei", 12, "bold")).grid(row=0, column=0, sticky="w", pady=5)
    outline_text = ctk.CTkTextbox(content_frame, wrap="word", font=("Microsoft YaHei", 12))
    outline_text.grid(row=1, column=0, sticky="nsew", padx=5)
    
    # --- 底部指令区 ---
    bottom_frame = ctk.CTkFrame(dialog)
    bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
    
    ctk.CTkLabel(bottom_frame, text="修改意见 (例如：'让第5章的战斗更惨烈，并在第6章开头增加主角的感悟'):", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=5)
    instruction_text = ctk.CTkTextbox(bottom_frame, height=80, wrap="word")
    instruction_text.pack(fill="x", padx=5, pady=5)
    
    btn_area = ctk.CTkFrame(bottom_frame, fg_color="transparent")
    btn_area.pack(fill="x", pady=5)

    def on_ai_refine():
        current_content = outline_text.get("0.0", "end").strip()
        instruction = instruction_text.get("0.0", "end").strip()
        s_val = start_chap_entry.get().strip()
        e_val = end_chap_entry.get().strip() or s_val
        
        if not s_val:
            messagebox.showwarning("提示", "请确保已填写章节号。")
            return
        if not current_content:
            messagebox.showwarning("提示", "请先读取章节大纲内容。")
            return
        if not instruction:
            messagebox.showwarning("提示", "请输入修改意见。")
            return
            
        # 读取背景
        arch_file = os.path.join(filepath, "Novel_architecture.txt")
        summary_file = os.path.join(filepath, "global_summary.txt")
        novel_arch_content = read_file(arch_file) if os.path.exists(arch_file) else ""
        global_sum_content = read_file(summary_file) if os.path.exists(summary_file) else ""

        # 获取配置 - 使用专门的目录微调配置
        try:
            llm_var = self.directory_refinement_llm_var.get()  # 使用新的配置变量
            config = self.loaded_config["llm_configs"][llm_var]
        except:
            messagebox.showerror("错误", "无法获取目录微调模型配置。")
            return

        status_label.configure(text="AI 正在思考并微调剧情...", text_color="blue")
        refine_btn.configure(state="disabled")
        
        def run_task():
            try:
                chapter_range_str = f"第{s_val}章" if s_val == e_val else f"第{s_val}章 到 第{e_val}章"
                
                new_outline = refine_chapter_detail(
                    interface_format=config["interface_format"],
                    api_key=config["api_key"],
                    base_url=config["base_url"],
                    model_name=config["model_name"],
                    chapter_range=chapter_range_str, # 传入范围描述
                    novel_architecture=novel_arch_content,
                    global_summary=global_sum_content,
                    current_outline=current_content,
                    user_instruction=instruction,
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"],
                    timeout=config["timeout"]
                )
                
                if new_outline:
                    self.master.after(0, lambda: outline_text.delete("0.0", "end"))
                    self.master.after(0, lambda: outline_text.insert("0.0", new_outline))
                    self.master.after(0, lambda: status_label.configure(text="✅ 微调完成，请检查", text_color="green"))
                else:
                    self.master.after(0, lambda: status_label.configure(text="❌ 微调失败 (返回空)", text_color="red"))
            except Exception as e:
                self.master.after(0, lambda: status_label.configure(text=f"❌ 出错: {str(e)}", text_color="red"))

            finally:
                self.master.after(0, lambda: refine_btn.configure(state="normal"))

        threading.Thread(target=run_task, daemon=True).start()

    refine_btn = ctk.CTkButton(btn_area, text="AI 微调大纲", command=on_ai_refine, width=120, fg_color="#E67E22")
    refine_btn.pack(side="left", padx=5)

    def on_save_changes():
        content = outline_text.get("0.0", "end").strip()
        if not content:
            messagebox.showwarning("提示", "大纲内容为空。")
            return
            
        s_val = start_chap_entry.get().strip()
        e_val = end_chap_entry.get().strip() or s_val
        
        if not s_val:
            messagebox.showwarning("提示", "请输入起始章节号。")
            return

        try:
            start_num = int(s_val)
            end_num = int(e_val)
            
            if end_num < start_num:
                messagebox.showerror("错误", "结束章节不能小于起始章节")
                return

            # 读取现有目录
            directory_content = read_file(directory_file)
            
            # 使用正则表达式替换指定范围内的章节
            pattern = get_range_pattern(start_num, end_num)
            updated_content = pattern.sub(content, directory_content, count=1)
            
            # 保存修改后的目录
            clear_file_content(directory_file)
            save_string_to_txt(updated_content.strip(), directory_file)
            
            status_label.configure(text="✅ 保存成功", text_color="green")
            
        except ValueError:
            messagebox.showerror("错误", "章节号必须是数字")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    save_btn = ctk.CTkButton(btn_area, text="保存修改", command=on_save_changes, width=120)
    save_btn.pack(side="left", padx=5)

    def on_cancel():
        dialog.destroy()

    cancel_btn = ctk.CTkButton(btn_area, text="取消", command=on_cancel, width=120)
    cancel_btn.pack(side="right", padx=5)

def show_foreshadowing_records_ui(self):
    """
    [新增] 显示伏笔记录库的弹窗
    """
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先在主Tab中设置保存文件路径")
        return

    record_file = os.path.join(filepath, "foreshadowing_records.txt")
    if not os.path.exists(record_file):
        messagebox.showinfo("提示", "当前还未生成任何伏笔记录。\n请先进行章节定稿(Finalize)以自动生成。")
        return

    content = read_file(record_file).strip()
    if not content:
        content = "伏笔记录为空。"

    top = ctk.CTkToplevel(self.master)
    top.title("全书伏笔线索库 (Foreshadowing Records)")
    top.geometry("700x600")

    # === 【修改】 设置为从属窗口 (Transient) ===
    # 这样它永远会在 self.master (主窗口) 之上，但不会挡住其他软件
    top.transient(self.master)  
    top.lift() # 首次打开时提升一下层级
    
    # 顶部说明
    ctk.CTkLabel(top, text="这里记录了每一章定稿时AI提取的伏笔线索", text_color="gray").pack(pady=5)

    # 文本区域
    text_area = ctk.CTkTextbox(top, wrap="word", font=("Microsoft YaHei", 12))
    text_area.pack(fill="both", expand=True, padx=10, pady=5)
    text_area.insert("0.0", content)
    
    # 允许用户手动编辑和保存整理
    def on_save_edit():
        new_text = text_area.get("0.0", "end").strip()
        save_string_to_txt(new_text, record_file)
        messagebox.showinfo("成功", "伏笔记录已保存更新。")

    btn_frame = ctk.CTkFrame(top)
    btn_frame.pack(fill="x", padx=10, pady=10)
    
    ctk.CTkButton(btn_frame, text="保存修改", command=on_save_edit, fg_color="green").pack(side="right")


def show_novel_qa_ui(self):
    """
    [新增] 全书问答 UI (类似聊天窗口)
    """
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先在主Tab中设置保存文件路径")
        return
        
    # 创建弹窗
    top = ctk.CTkToplevel(self.master)
    top.title("全书知识库问答 (Novel Q&A)")
    top.geometry("600x700")

    # === 【修改】 设置为从属窗口 ===
    top.transient(self.master)
    top.lift()
    
    # 1. 聊天记录显示区
    history_frame = ctk.CTkFrame(top)
    history_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    chat_box = ctk.CTkTextbox(history_frame, font=("Microsoft YaHei", 12), state="disabled")
    chat_box.pack(fill="both", expand=True, padx=5, pady=5)
    
    # 2. 输入区
    input_frame = ctk.CTkFrame(top)
    input_frame.pack(fill="x", padx=10, pady=(0, 10))
    
    input_entry = ctk.CTkEntry(input_frame, placeholder_text="输入关于小说的问题，例如：叶落现在的等级是多少？", font=("Microsoft YaHei", 12))
    input_entry.pack(side="left", fill="x", expand=True, padx=(5, 5), pady=5)
    
    # 3. 发送逻辑
    def send_question(event=None):
        question = input_entry.get().strip()
        if not question: return
        
        # 显示用户问题
        chat_box.configure(state="normal")
        chat_box.insert("end", f"You: {question}\n\n", "user")
        chat_box.insert("end", "AI: 正在翻阅全书...\n", "system")
        chat_box.see("end")
        chat_box.configure(state="disabled")
        input_entry.delete(0, "end")
        
        def run_qa():
            try:
                # === 获取配置 ===
                # 使用【逻辑/微调模型】来回答问题，因为它通常更便宜且逻辑够用
                # 如果没配置，回退到 draft 模型
                try:
                    llm_key = self.refine_logic_llm_var.get()
                    llm_conf = self.loaded_config["llm_configs"][llm_key]
                except:
                    llm_key = self.prompt_draft_llm_var.get()
                    llm_conf = self.loaded_config["llm_configs"][llm_key]
                
                # === 2. 获取 Embedding 配置 (用于检索) ===
                # 【关键修改】：直接读取主界面当前绑定的变量，而不是读配置文件里的第一个
                # 这样可以确保和你“定稿”时用的是同一个配置，且 API Key 不会为空（只要你界面上填了）
                emb_api_key = self.embedding_api_key_var.get().strip()
                emb_base_url = self.embedding_url_var.get().strip()
                emb_model_name = self.embedding_model_name_var.get().strip()
                emb_interface_format = self.embedding_interface_format_var.get().strip()

                # 简单校验
                if not emb_api_key and "ollama" not in emb_interface_format.lower():
                    update_chat("错误：Embedding API Key 为空，请在配置页检查。", is_error=True)
                    return

                # === 3. 调用后端 ===
                answer = answer_novel_question(
                    filepath=filepath,
                    question=question,
                    # LLM 参数
                    llm_api_key=llm_conf["api_key"],
                    llm_base_url=llm_conf["base_url"],
                    llm_model_name=llm_conf["model_name"],
                    interface_format=llm_conf["interface_format"],
                    # Embedding 参数 (使用直接获取的值)
                    emb_api_key=emb_api_key,
                    emb_base_url=emb_base_url,
                    emb_model_name=emb_model_name,
                    emb_interface_format=emb_interface_format
                )
                
                update_chat(answer)
                
            except Exception as e:
                # 打印完整堆栈以便调试
                traceback.print_exc() 
                update_chat(f"发生错误: {str(e)}", is_error=True)

        threading.Thread(target=run_qa, daemon=True).start()

    def update_chat(text, is_error=False):
        """线程安全更新 UI"""
        def _update():
            chat_box.configure(state="normal")
            # 删除“正在翻阅...”
            # 简单起见，直接追加新内容。为了体验更好，可以把上一行删掉，但追加也没问题。
            prefix = "❌ Error: " if is_error else "AI: "
            chat_box.insert("end", f"\n{prefix}{text}\n" + "-"*30 + "\n\n")
            chat_box.see("end")
            chat_box.configure(state="disabled")
        top.after(0, _update)

    # 按钮
    send_btn = ctk.CTkButton(input_frame, text="发送", width=80, command=send_question)
    send_btn.pack(side="right", padx=5, pady=5)
    
    # 绑定回车发送
    input_entry.bind("<Return>", send_question)

def continue_directory_ui(self):
    """
    续写章节目录的交互界面
    """
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return
        
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        messagebox.showwarning("警告", "尚未生成架构文件 (Novel_architecture.txt)。")
        return

    directory_file = os.path.join(filepath, "Novel_directory.txt")
    existing_chapters_count = 0
    if os.path.exists(directory_file):
        content = read_file(directory_file)
        # 使用正则表达式找出所有章节编号
        pattern = r"第\s*(\d+)\s*章"
        chapter_numbers = re.findall(pattern, content)
        if chapter_numbers:
            chapter_numbers = [int(num) for num in chapter_numbers if num.isdigit()]
            if chapter_numbers:
                existing_chapters_count = max(chapter_numbers)

    # 创建弹窗
    dialog = ctk.CTkToplevel(self.master)
    dialog.title("续写章节大纲")
    dialog.geometry("1000x700")
    
    # 布局配置
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    # --- 顶部控制区 ---
    top_frame = ctk.CTkFrame(dialog)
    top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
    
    ctk.CTkLabel(top_frame, text="起始章节:").pack(side="left", padx=(10, 5))
    start_chap_entry = ctk.CTkEntry(top_frame, width=60)
    start_chap_entry.pack(side="left", padx=5)
    
    # 设置默认起始章节为现有最大章节+1
    if existing_chapters_count > 0:
        start_chap_entry.insert(0, str(existing_chapters_count + 1))
    
    ctk.CTkLabel(top_frame, text="结束章节:").pack(side="left", padx=(15, 5))
    end_chap_entry = ctk.CTkEntry(top_frame, width=60)
    end_chap_entry.pack(side="left", padx=5)

    # --- 信息提示 ---
    info_frame = ctk.CTkFrame(dialog)
    info_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    info_frame.grid_columnconfigure(0, weight=1)
    info_frame.grid_rowconfigure(0, weight=1)
    
    info_text = ctk.CTkTextbox(info_frame, wrap="word", font=("Microsoft YaHei", 12))
    info_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
    # 插入提示信息
    info_text.insert("0.0", f"当前已有章节: {existing_chapters_count} 章\n\n")
    info_text.insert("end", "此功能将根据现有架构和目录信息，生成后续章节的目录。\n\n")
    info_text.insert("end", "提示：\n")
    info_text.insert("end", "- 起始章节建议设置为当前最大章节号+1\n")
    info_text.insert("end", "- 结束章节设置为你希望生成到的章节号\n")
    info_text.insert("end", "- 生成的内容将追加到现有目录文件末尾")
    info_text.configure(state="disabled")  # 设为只读

    # --- 底部控制区 ---
    bottom_frame = ctk.CTkFrame(dialog)
    bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
    
    status_label = ctk.CTkLabel(bottom_frame, text=f"当前已有 {existing_chapters_count} 章", text_color="green")
    status_label.pack(side="left", padx=10)
    
    continue_btn = ctk.CTkButton(bottom_frame, text="续写目录 (AI)", command=lambda: on_continue_directory(), fg_color="#3498DB")
    continue_btn.pack(side="right", padx=10)

    def on_continue_directory():
        s_val = start_chap_entry.get().strip()
        e_val = end_chap_entry.get().strip()
        
        if not s_val or not e_val:
            messagebox.showwarning("提示", "请填写起始和结束章节号。")
            return
            
        try:
            start_num = int(s_val)
            end_num = int(e_val)
            
            if end_num < start_num:
                messagebox.showerror("错误", "结束章节不能小于起始章节")
                return
                
            if start_num <= 0 or end_num <= 0:
                messagebox.showerror("错误", "章节号必须是正整数")
                return
                
            if existing_chapters_count > 0 and start_num <= existing_chapters_count:
                messagebox.showwarning("提示", f"起始章节 ({start_num}) 应该大于现有最大章节 ({existing_chapters_count})，否则可能导致章节重复。")
                
        except ValueError:
            messagebox.showerror("错误", "章节号必须是数字")
            return

        # 获取配置 - 使用专门的目录续写配置
        try:
            llm_var = self.directory_continuation_llm_var.get()  # 使用新的配置变量
            config = self.loaded_config["llm_configs"][llm_var]
        except:
            messagebox.showerror("错误", "无法获取目录续写模型配置。")
            return

        status_label.configure(text="AI 正在分析现有目录并续写...", text_color="blue")
        continue_btn.configure(state="disabled")
        
        def run_task():
            try:
                from novel_generator.blueprint import continue_chapter_blueprint
                
                result = continue_chapter_blueprint(
                    interface_format=config["interface_format"],
                    api_key=config["api_key"],
                    base_url=config["base_url"],
                    llm_model=config["model_name"],
                    filepath=filepath,
                    start_chapter=start_num,
                    end_chapter=end_num,
                    user_guidance="",  # 可以扩展以支持用户指导
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"],
                    timeout=config["timeout"]
                )
                
                if result:
                    self.master.after(0, lambda: status_label.configure(text="✅ 续写完成，请检查", text_color="green"))
                    # 更新主界面的目录显示
                    self.master.after(0, lambda: self.load_chapter_blueprint())
                else:
                    self.master.after(0, lambda: status_label.configure(text="❌ 续写失败 (返回空)", text_color="red"))
            except Exception as e:
                self.master.after(0, lambda: status_label.configure(text=f"❌ 出错: {str(e)}", text_color="red"))
            finally:
                self.master.after(0, lambda: continue_btn.configure(state="normal"))

        threading.Thread(target=run_task, daemon=True).start()

