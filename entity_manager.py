# entity_manager.py
# -*- coding: utf-8 -*-
"""
实体管理辅助脚本
用于初始化、更新和管理小说中的实体属性
"""
import os
import sys
import json
import argparse
from entity_tracker import (
    create_tracker,
    analyze_and_update_entities,
    extract_entities_from_text
)
from utils import read_file


def init_entity_tracker(filepath: str):
    """初始化实体追踪器"""
    print(f"初始化实体追踪器: {filepath}")
    tracker = create_tracker(filepath)
    print("实体追踪器初始化完成")
    return tracker


def analyze_chapter_file(filepath: str, chapter_num: int, use_llm: bool = False):
    """分析章节文件并更新实体属性"""
    tracker = create_tracker(filepath)
    
    chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_num}.txt")
    if not os.path.exists(chapter_file):
        print(f"章节文件不存在: {chapter_file}")
        return
    
    print(f"分析第{chapter_num}章...")
    text = read_file(chapter_file)
    
    if use_llm:
        # 使用LLM提取实体
        from llm_adapters import create_llm_adapter
        # 这里需要从配置中读取API信息
        # 暂时使用默认值
        llm_adapter = create_llm_adapter(
            interface_format="openai",
            base_url="http://localhost:11434/v1",
            model_name="qwen2.5",
            api_key="sk-test",
            temperature=0.1
        )
        conflicts = analyze_and_update_entities(tracker, text, chapter_num, use_llm=True, llm_adapter=llm_adapter)
    else:
        # 使用规则提取实体
        conflicts = analyze_and_update_entities(tracker, text, chapter_num, use_llm=False)
    
    if conflicts:
        print(f"\n发现 {len(conflicts)} 个属性冲突:")
        for conflict in conflicts:
            print(f"  - {conflict['类别']}.{conflict['名称']}.{conflict['属性']}: "
                  f"'{conflict['旧值']}' -> '{conflict['新值']}' (第{conflict['章节']}章)")
    else:
        print("未发现属性冲突")
    
    print(f"第{chapter_num}章分析完成")


def analyze_all_chapters(filepath: str, use_llm: bool = False):
    """分析所有章节并更新实体属性"""
    tracker = create_tracker(filepath)
    chapters_dir = os.path.join(filepath, "chapters")
    
    if not os.path.exists(chapters_dir):
        print(f"章节目录不存在: {chapters_dir}")
        return
    
    # 获取所有章节文件
    chapter_files = sorted([f for f in os.listdir(chapters_dir) if f.startswith("chapter_") and f.endswith(".txt")])
    
    print(f"发现 {len(chapter_files)} 个章节文件")
    
    all_conflicts = []
    
    for chapter_file in chapter_files:
        chapter_num = int(chapter_file.replace("chapter_", "").replace(".txt", ""))
        print(f"\n分析第{chapter_num}章...")
        
        text = read_file(os.path.join(chapters_dir, chapter_file))
        
        if use_llm:
            from llm_adapters import create_llm_adapter
            llm_adapter = create_llm_adapter(
                interface_format="openai",
                base_url="http://localhost:11434/v1",
                model_name="qwen2.5",
                api_key="sk-test",
                temperature=0.1
            )
            conflicts = analyze_and_update_entities(tracker, text, chapter_num, use_llm=True, llm_adapter=llm_adapter)
        else:
            conflicts = analyze_and_update_entities(tracker, text, chapter_num, use_llm=False)
        
        all_conflicts.extend(conflicts)
    
    if all_conflicts:
        print(f"\n\n总共发现 {len(all_conflicts)} 个属性冲突:")
        for conflict in all_conflicts:
            print(f"  - {conflict['类别']}.{conflict['名称']}.{conflict['属性']}: "
                  f"'{conflict['旧值']}' -> '{conflict['新值']}' (第{conflict['章节']}章)")
    else:
        print("\n\n未发现属性冲突")
    
    print(f"\n所有章节分析完成")


def show_entities(filepath: str, category: str = None):
    """显示实体属性"""
    tracker = create_tracker(filepath)
    entities = tracker.get_all_entities()
    
    if category:
        if category in entities:
            print(f"\n【{category}】")
            for name, entity_data in entities[category].items():
                attrs = entity_data.get("属性", {})
                if attrs:
                    attr_str = ", ".join([f"{k}={v}" for k, v in attrs.items()])
                    print(f"  • {name}: {attr_str}")
                else:
                    print(f"  • {name}")
        else:
            print(f"未找到类别: {category}")
    else:
        for cat_name, cat_entities in entities.items():
            if not cat_entities:
                continue
            print(f"\n【{cat_name}】")
            for name, entity_data in cat_entities.items():
                attrs = entity_data.get("属性", {})
                if attrs:
                    attr_str = ", ".join([f"{k}={v}" for k, v in attrs.items()])
                    print(f"  • {name}: {attr_str}")
                else:
                    print(f"  • {name}")


def add_entity_manual(filepath: str, category: str, name: str, attributes: str):
    """手动添加实体属性"""
    tracker = create_tracker(filepath)
    
    # 解析属性字符串
    attrs = {}
    for attr_pair in attributes.split(','):
        if '=' in attr_pair:
            key, value = attr_pair.split('=', 1)
            attrs[key.strip()] = value.strip()
    
    tracker.add_entity(category, name, attrs, chapter=0)
    print(f"已添加实体: {category}.{name} - {attrs}")


def export_entities(filepath: str, output_file: str):
    """导出实体属性到文件"""
    tracker = create_tracker(filepath)
    entities = tracker.get_all_entities()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    
    print(f"实体属性已导出到: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='实体管理工具')
    parser.add_argument('--filepath', type=str, required=True, help='项目路径')
    parser.add_argument('--action', type=str, required=True, 
                       choices=['init', 'analyze', 'analyze-all', 'show', 'add', 'export'],
                       help='操作类型')
    parser.add_argument('--chapter', type=int, help='章节号（用于analyze操作）')
    parser.add_argument('--category', type=str, help='实体类别（用于show/add操作）')
    parser.add_argument('--name', type=str, help='实体名称（用于add操作）')
    parser.add_argument('--attributes', type=str, help='实体属性（用于add操作），格式：key1=value1,key2=value2')
    parser.add_argument('--output', type=str, help='输出文件（用于export操作）')
    parser.add_argument('--use-llm', action='store_true', help='使用LLM提取实体')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_entity_tracker(args.filepath)
    elif args.action == 'analyze':
        if not args.chapter:
            print("错误: analyze操作需要指定--chapter参数")
            sys.exit(1)
        analyze_chapter_file(args.filepath, args.chapter, args.use_llm)
    elif args.action == 'analyze-all':
        analyze_all_chapters(args.filepath, args.use_llm)
    elif args.action == 'show':
        show_entities(args.filepath, args.category)
    elif args.action == 'add':
        if not args.category or not args.name or not args.attributes:
            print("错误: add操作需要指定--category, --name和--attributes参数")
            sys.exit(1)
        add_entity_manual(args.filepath, args.category, args.name, args.attributes)
    elif args.action == 'export':
        if not args.output:
            print("错误: export操作需要指定--output参数")
            sys.exit(1)
        export_entities(args.filepath, args.output)


if __name__ == '__main__':
    main()
