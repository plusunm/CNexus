from typing import List


METHOD_ACTIONS = {
    "事实核查三步法": "列出已知事实、假设、待验证项各 3 条",
    "延迟判断 24 小时": "记录初步判断，24 小时后再做最终决定",
    "主动寻求反证": "找一位持不同意见者讨论此问题",
    "情绪命名与暂停": "说出当前情绪名称，暂停 5 分钟再回复",
    "每日复盘 10 分钟": "睡前记录今日一个可改进的行为模式",
    "每日自省": "早晨设定一个今日修养焦点",
    "正念观察": "观察一次自动化反应而不立即行动",
}


class ActionGenerator:
    """将修养方法转化为可执行行动"""

    def generate(self, methods: List[str]) -> List[str]:
        actions = []
        for method in methods:
            action = METHOD_ACTIONS.get(method, f"实践「{method}」至少一次")
            if action not in actions:
                actions.append(action)
        if not actions:
            actions.append("每日记录一次自我反思")
        return actions
