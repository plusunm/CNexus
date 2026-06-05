# Changelog

## 5.0.0 (2026-05-28)

### Cognitive Stability Architecture

- **DeterministicRouter**：关键词 → 嵌入原型 → LLM 兜底，减少路由漂移
- **Dynamic Attention Field**：Working Memory 半衰期衰减（`attention_half_life`）
- **Belief System**：`beliefs.json` 持久化 + 写入兼容检测 + 代谢调和
- **Reflection Engine**：`run_reflection()` Meta-Memory + `meta` 层
- **Goal Lifecycle Graph**：`goal_lifecycle.json` + 状态机（active/completed/…）
- **Identity Stability**：`self_model.json` + stability_score 治理
- **Cognitive Governance**：Write Gate + Belief Conflict Gate 扩展

## 4.2.0 (2026-06-05)

### Cognitive OS 升级

- **QueryRouter**：short_term / episodic / semantic / graph_reasoning / goal / archive 分层路由
- **Attention Working Memory**：recency + importance + emotional + goal_relevance 加权驱逐
- **Write Gate**：低价值记忆拒绝落盘（`write_gate_threshold`）
- **Graph Pruning**：`edge_meta.json` 追踪 confidence/last_verified，定期剪枝
- **Semantic Compression**：`compress_similar_episodics()` 冗余 episodic → semantic
- **Goal Memory**：goal / intent / plan 层 + `update_goal_memory()` 等接口
- **Recall Metrics**：`get_stats()` 返回 `recall_routes`、压缩/剪枝计数

## 4.1.0 (2026-06-05)

### 最优合并版（Desktop ind + 旧版 .bak）

- **旧版保留**：HyDE、Working Memory、Reconsolidation、Consolidation、Ebbinghaus 遗忘
- **v4 并入**：Multi-hop 图遍历、Cognitive Graph（RELATED/FOLLOWS）、Schema 层注入、SUPPORTED_BY 溯源
- **焊死 pipeline**：CaptureFilter 入口过滤、embedding 去重合并、代谢循环 `_neuro_forgetting`
- **桥接同步**：`index.js` / `openclaw.plugin.json` 新配置项、`brain_link_provenance` 工具
- **Skill 同步**：`brain_skill/tools.py` + `SKILL.md` v4.1

## 4.0.0 (2026-05-30)

### 正式发布 (2026-06-05)

- **OpenClaw 原生插件桥接**：`openclaw.plugin.json` + `index.js` + `rpc_server.py`
- 安装路径：`%OPENCLAW_STATE_DIR%/extensions/brain-memory`
- 工具：`brain_recall` / `brain_store` / `brain_consolidate` / `brain_stats`
- 自动钩子：`before_agent_start` recall、`agent_end` capture
- Python 路径：`env.BRAIN_MEMORY_PYTHON` 或内置 `C:\Python311\python.exe` fallback
- Host E2E 验证通过（`config validate` + gateway loaded）

### 审计与发布准备 (2026-06-05)

- 全量审计评分 **7.6/10** — 代码完成度高，Host E2E 与语料信噪比为主要缺口
- Ollama 验证：`verify.py` HyDE / 实体 / 钩子 / forget dry_run
- 记忆治理：清理 toolResult / JSON 噪声；注入 Semantic（审计结论、架构决策、发布 checklist）
- 首次 `brain_consolidate()` 生成 Semantic 摘要
- 修复 `update_hebbian_edges` 非 dict 关系项 / null strength 崩溃
- Ollama 调用优先直连 HTTP API（规避 langchain 502）
- `config_loader` 支持 `LLM_MODEL` 环境变量
- 干净发布包：`scripts/pack_release.py --skip-memory`
- 演示脚本：`scripts/demo_text.py`（本地录屏用）

- HyDE 召回（可配置 `use_hyde`）
- 三层记忆 layer：episodic / semantic / procedural
- Prefrontal 短期 LRU 缓存
- LLM 实体抽取 + Hebbian 图边强化
- Reconsolidation + Provenance 溯源
- LanceDB schema 迁移（last_access, access_count, layer）— 兼容 145+ 旧记忆
- APScheduler 内置每日 consolidate
- 发布包：PUBLISH.md、pack_release.py、LICENSE、.gitignore

## 3.0.0

- OpenClaw on_message / before_llm_call
- 混合 recall + 主动遗忘
- access_meta.json sidecar

## 1.0.0

- 初始 LanceDB + Kuzu + Ollama
