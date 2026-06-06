from typing import List


TRAIT_KEYWORDS = {
    "主观臆断": ["主观", "臆断", "感觉当作事实", "以为"],
    "情绪化": ["情绪", "冲动", "生气", "焦虑", "烦躁"],
    "急躁": ["急躁", "不耐烦", "赶时间", "仓促"],
    "过度自信": ["一定", "肯定", "绝对", "不可能错"],
    "回避冲突": ["回避", "不说", "沉默", "避免争论"],
    "完美主义": ["完美", "必须最好", "不能出错"],
    "注意力分散": ["分心", "走神", "无法专注", "注意力"],
}


class TraitDetector:
    """规则驱动的特质检测（可扩展为 LLM）"""

    def detect(self, content: str) -> List[str]:
        traits = []
        for trait, keywords in TRAIT_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                traits.append(trait)
        if not traits:
            traits.append("自我觉察不足")
        return traits[:5]
