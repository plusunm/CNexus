from typing import Dict, List, Optional

TRAIT_SCENES: Dict[str, str] = {
    "主观臆断": "在信息不完整时过早下结论",
    "情绪化": "在压力或冲突情境中反应过激",
    "急躁": "面对复杂任务时追求快速结果",
    "过度自信": "在不确定领域仍坚持己见",
    "回避冲突": "需要表达立场时选择退让",
    "完美主义": "因细节标准过高而拖延行动",
    "注意力分散": "多任务并行时丢失核心目标",
    "自我觉察不足": "未意识到行为模式的重复出现",
    "default": "日常交互中的惯性反应",
}

TRAIT_METHODS: Dict[str, List[str]] = {
    "主观臆断": ["事实核查三步法", "延迟判断 24 小时", "主动寻求反证"],
    "情绪化": ["情绪命名与暂停", "深呼吸 6 次后再回应", "写情绪日志"],
    "急躁": ["番茄工作法", "设定最小可行步骤", "优先级矩阵"],
    "过度自信": ["红队思维", "邀请他人挑战观点", "记录预测与结果"],
    "回避冲突": ["非暴力沟通框架", "预先准备边界陈述", "小步表达练习"],
    "完美主义": ["完成优于完美", "设定 80% 交付标准", "时间盒限制"],
    "注意力分散": ["单任务专注块", "关闭通知", "每日三件要事"],
    "自我觉察不足": ["每日复盘 10 分钟", "行为-结果对照表", "第三方反馈"],
}


class CultivationEngine:
    """匹配典型场景与修养方法"""

    def get_scene(self, trait: str) -> Optional[str]:
        return TRAIT_SCENES.get(trait, TRAIT_SCENES["default"])

    def match_methods(self, traits: List[str]) -> List[str]:
        methods: List[str] = []
        for trait in traits:
            for m in TRAIT_METHODS.get(trait, ["每日自省", "正念观察"]):
                if m not in methods:
                    methods.append(m)
        return methods[:5]
