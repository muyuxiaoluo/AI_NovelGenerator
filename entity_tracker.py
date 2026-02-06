# entity_tracker.py
# -*- coding: utf-8 -*-
"""
实体属性追踪系统
用于追踪小说中所有实体（人物、道具、场景、技能等）的属性，确保一致性
"""
import os
import re
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from utils import read_file, save_string_to_txt

logging.basicConfig(
    filename='app.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class EntityTracker:
    """实体属性追踪器"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.entity_file = os.path.join(filepath, "entity_attributes.json")
        self.entities = self._load_entities()
        
    def _load_entities(self) -> Dict:
        """加载实体属性数据"""
        try:
            if os.path.exists(self.entity_file):
                with open(self.entity_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.warning(f"加载实体属性文件失败: {e}")
        return self._get_default_structure()
    
    def _get_default_structure(self) -> Dict:
        """获取默认的实体属性结构"""
        return {
            "人物": {},
            "道具": {},
            "场景": {},
            "技能": {},
            "其他": {}
        }
    
    def _save_entities(self):
        """保存实体属性数据"""
        try:
            with open(self.entity_file, 'w', encoding='utf-8') as f:
                json.dump(self.entities, f, ensure_ascii=False, indent=2)
            logging.info("实体属性已保存")
        except Exception as e:
            logging.error(f"保存实体属性失败: {e}")
    
    def add_entity(self, category: str, name: str, attributes: Dict, chapter: int = 0):
        """
        添加或更新实体属性
        
        Args:
            category: 实体类别（人物/道具/场景/技能/其他）
            name: 实体名称
            attributes: 属性字典，如 {"颜色": "淡黄色", "状态": "完好"}
            chapter: 章节号，用于追踪属性来源
        """
        if category not in self.entities:
            self.entities[category] = {}
        
        if name not in self.entities[category]:
            self.entities[category][name] = {
                "属性": {},
                "首次出现章节": chapter,
                "最后更新章节": chapter
            }
        
        # 更新属性
        for attr_name, attr_value in attributes.items():
            # 如果属性已存在且值不同，记录冲突
            if attr_name in self.entities[category][name]["属性"]:
                old_value = self.entities[category][name]["属性"][attr_name]
                if old_value != attr_value:
                    logging.warning(
                        f"属性冲突: {category}.{name}.{attr_name} "
                        f"从 '{old_value}' 变为 '{attr_value}' (第{chapter}章)"
                    )
                    # 保留历史记录
                    if "历史记录" not in self.entities[category][name]:
                        self.entities[category][name]["历史记录"] = []
                    self.entities[category][name]["历史记录"].append({
                        "属性": attr_name,
                        "旧值": old_value,
                        "新值": attr_value,
                        "章节": chapter
                    })
            
            self.entities[category][name]["属性"][attr_name] = attr_value
        
        self.entities[category][name]["最后更新章节"] = chapter
        self._save_entities()
    
    def get_entity_attributes(self, category: str, name: str) -> Optional[Dict]:
        """获取实体的所有属性"""
        if category in self.entities and name in self.entities[category]:
            return self.entities[category][name]["属性"]
        return None
    
    def get_attribute_value(self, category: str, name: str, attr_name: str) -> Optional[str]:
        """获取实体的特定属性值"""
        attrs = self.get_entity_attributes(category, name)
        if attrs and attr_name in attrs:
            return attrs[attr_name]
        return None
    
    def get_all_entities(self) -> Dict:
        """获取所有实体"""
        return self.entities
    
    def get_entities_by_category(self, category: str) -> Dict:
        """获取指定类别的所有实体"""
        return self.entities.get(category, {})
    
    def check_attribute_conflicts(self) -> List[Dict]:
        """检查所有属性冲突"""
        conflicts = []
        for category, entities in self.entities.items():
            for name, entity_data in entities.items():
                if "历史记录" in entity_data:
                    for record in entity_data["历史记录"]:
                        conflicts.append({
                            "类别": category,
                            "名称": name,
                            "属性": record["属性"],
                            "旧值": record["旧值"],
                            "新值": record["新值"],
                            "章节": record["章节"]
                        })
        return conflicts
    
    def generate_lock_list(self) -> str:
        """
        生成实体属性锁定列表，用于提示词中
        格式化输出，确保AI在写作时不会随意更改属性
        """
        lock_list = []
        lock_list.append("=" * 60)
        lock_list.append("【实体属性锁定清单】（严禁随意更改以下属性）")
        lock_list.append("=" * 60)
        
        for category, entities in self.entities.items():
            if not entities:
                continue
                
            lock_list.append(f"\n【{category}】")
            for name, entity_data in entities.items():
                attrs = entity_data.get("属性", {})
                if not attrs:
                    continue
                    
                attr_strs = []
                for attr_name, attr_value in attrs.items():
                    attr_strs.append(f"{attr_name}={attr_value}")
                
                if attr_strs:
                    lock_list.append(f"  • {name}: {', '.join(attr_strs)}")
        
        lock_list.append("\n" + "=" * 60)
        lock_list.append("【重要约束】")
        lock_list.append("1. 上述属性为已确定的设定，严禁随意修改")
        lock_list.append("2. 如需修改属性，必须有合理的剧情推动和明确描述")
        lock_list.append("3. 禁止出现属性前后矛盾的情况（如光罩颜色变化）")
        lock_list.append("4. 人物身份、职位等关键属性必须保持一致")
        lock_list.append("=" * 60)
        
        return "\n".join(lock_list)


def extract_entities_from_text(text: str, chapter: int = 0) -> List[Tuple[str, str, Dict]]:
    """
    从文本中提取实体及其属性（简化版）
    
    Args:
        text: 要分析的文本
        chapter: 章节号
    
    Returns:
        实体列表，每个元素为 (类别, 名称, 属性字典)
    """
    entities = []
    
    # 这里使用简单的规则匹配，实际应用中可以使用更复杂的NLP方法
    # 或者调用LLM进行实体提取
    
    # 示例规则：提取颜色属性
    color_patterns = [
        r'(\w+光罩).*?(淡黄|淡蓝|红色|蓝色|绿色|白色|黑色|金色|紫色)',
        r'(\w+阵法).*?(完好|破损|激活|失效)',
        r'(\w+).*?(是|为|担任)(术研院主事|城防军队长|掌门|弟子|长老)'
    ]
    
    # 人物职位模式
    position_patterns = [
        r'(\w+).*?(是|为|担任)(术研院主事|城防军队长|掌门|长老|弟子|护法)',
    ]
    
    for pattern in position_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            name = match.group(1)
            position = match.group(2)
            entities.append(("人物", name, {"职位": position}))
    
    return entities


def analyze_and_update_entities(
    tracker: EntityTracker,
    text: str,
    chapter: int,
    use_llm: bool = False,
    llm_adapter=None
) -> List[Dict]:
    """
    分析文本并更新实体属性
    
    Args:
        tracker: 实体追踪器
        text: 要分析的文本
        chapter: 章节号
        use_llm: 是否使用LLM进行实体提取
        llm_adapter: LLM适配器
    
    Returns:
        发现的冲突列表
    """
    if use_llm and llm_adapter:
        # 使用LLM提取实体
        entities = extract_entities_with_llm(llm_adapter, text, chapter)
    else:
        # 使用规则提取实体
        entities = extract_entities_from_text(text, chapter)
    
    # 更新实体属性
    for category, name, attributes in entities:
        tracker.add_entity(category, name, attributes, chapter)
    
    # 检查冲突
    conflicts = tracker.check_attribute_conflicts()
    
    return conflicts


def extract_entities_with_llm(llm_adapter, text: str, chapter: int) -> List[Tuple[str, str, Dict]]:
    """
    使用LLM从文本中提取实体及其属性
    
    Args:
        llm_adapter: LLM适配器
        text: 要分析的文本
        chapter: 章节号
    
    Returns:
        实体列表
    """
    prompt = f"""请从以下文本中提取所有实体及其属性，严格按照JSON格式输出。

提取要求：
1. 识别实体类别：人物、道具、场景、技能、其他
2. 提取实体的关键属性：颜色、状态、职位、位置、大小、形状等
3. 属性值必须准确，不要推测

输出格式（JSON）：
{{
    "实体": [
        {{
            "类别": "人物",
            "名称": "杨尘",
            "属性": {{
                "职位": "术研院主事",
                "状态": "健康"
            }}
        }},
        {{
            "类别": "道具",
            "名称": "光罩",
            "属性": {{
                "颜色": "淡黄色",
                "状态": "完好"
            }}
        }}
    ]
}}

文本内容：
{text[:2000]}

请直接输出JSON，不要包含任何其他文字。"""
    
    try:
        response = llm_adapter.invoke(prompt)
        # 解析JSON响应
        result = json.loads(response)
        entities = []
        for entity in result.get("实体", []):
            entities.append((
                entity.get("类别", "其他"),
                entity.get("名称", ""),
                entity.get("属性", {})
            ))
        return entities
    except Exception as e:
        logging.error(f"LLM实体提取失败: {e}")
        return []


def generate_entity_constraint_prompt(tracker: EntityTracker) -> str:
    """
    生成用于提示词的实体约束文本
    
    Args:
        tracker: 实体追踪器
    
    Returns:
        约束文本
    """
    lock_list = tracker.generate_lock_list()
    
    constraint_prompt = f"""
{lock_list}

【写作时的额外要求】
1. 在描述上述实体时，必须使用锁定的属性值
2. 如果需要修改属性，必须在正文中明确说明原因（如：光罩被攻击后颜色发生变化）
3. 禁止出现属性前后矛盾的情况
4. 人物身份、职位等关键信息必须与锁定列表一致
"""
    return constraint_prompt


def merge_character_state_with_entities(
    tracker: EntityTracker,
    character_state_text: str
) -> str:
    """
    将角色状态与实体属性合并，生成更完整的状态描述
    
    Args:
        tracker: 实体追踪器
        character_state_text: 原始角色状态文本
    
    Returns:
        合并后的状态文本
    """
    # 获取所有人物实体
    person_entities = tracker.get_entities_by_category("人物")
    
    if not person_entities:
        return character_state_text
    
    # 在角色状态文本后添加实体属性信息
    entity_info = ["\n【实体属性补充】"]
    for name, entity_data in person_entities.items():
        attrs = entity_data.get("属性", {})
        if attrs:
            attr_strs = [f"{k}={v}" for k, v in attrs.items()]
            entity_info.append(f"{name}: {', '.join(attr_strs)}")
    
    return character_state_text + "\n" + "\n".join(entity_info)


def create_tracker(filepath: str) -> EntityTracker:
    """
    创建实体追踪器
    
    Args:
        filepath: 项目路径
    
    Returns:
        EntityTracker实例
    """
    return EntityTracker(filepath)
