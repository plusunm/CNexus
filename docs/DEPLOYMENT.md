# CNexus 部署指南

## 1. 环境要求
- Python 3.11+
- Ollama（推荐本地运行）
- LanceDB + Kuzu（自动创建）
- 推荐硬件：16GB+ RAM（长期运行建议 32GB+）

## 2. 安装步骤
```bash
cd D:\类脑记忆\cursor
pip install -r requirements.txt

# 配置 Ollama
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.2
```

## 3. 配置
复制 `config/default.json` 并修改：
- `ollama_host`
- `importance_threshold`
- `write_gate_threshold`

## 4. 启动
```python
from brain_memory import BrainMemoryRuntime

runtime = BrainMemoryRuntime(project_root=".")
runtime.run_background_governance()  # 启动周期性稳定性检查
```

## 5. 生产建议
- 使用 systemd / supervisor 守护进程
- 定期运行 `StabilityValidationOrchestrator`
- 监控 `logs/governance.log`
- 备份 `memory/` 目录（snapshot 支持）

## 6. 常见问题
- Ollama 未启动 → 回退到零向量（警告）
- 内存过大 → 触发 Entropy Regulation 自动清理
