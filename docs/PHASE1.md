# Phase 1 — Memory Infrastructure

Phase 1 构建了稳定、可扩展、可观测的长期记忆底座。

## 已实现模块

- `config/default.json` — 配置中心
- `core/config_loader.py` — 配置加载 + 环境变量覆盖
- `memory/schema.py` — Memory 数据模型
- `memory/filter.py` — CaptureFilter 丘脑过滤
- `storage/vector.py` — LanceDB 向量存储
- `storage/graph.py` — Kuzu 认知图谱
- `storage/manager.py` — UnifiedStorageManager 统一入口
- `storage/provenance.py` — 全链路溯源

## 测试

```bash
python -m unittest tests.test_memory
```
