# Brain-Memory 发布指南

## 打包（ClawHub / GitHub Releases）

```powershell
cd extensions\brain-memory
python scripts\pack_release.py --skip-memory
```

产出：`dist/brain-memory-4.0.0.zip`

### 打包策略

| 模式 | 说明 |
|------|------|
| **完整包** | 含 `memory/lancedb/`（保留已有记忆） |
| **干净包** | `--skip-memory`（新用户首次运行自动建库） |

## ClawHub 提交清单

- [ ] `plugin.json` version 与 README 一致
- [ ] `requirements.txt` 完整
- [ ] `brain_skill/SKILL.md` 工具文档
- [ ] 截图：recall / consolidate / stats
- [ ] 标签：memory, local, hyde, hebbian, openclaw

## GitHub 开源

建议 `.gitignore` 排除运行时 `memory/lancedb/`、`memory/kuzu_db/`（见仓库 `.gitignore`）。

README 徽章示例：

```markdown
![version](https://img.shields.io/badge/version-4.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
```

## OpenClaw 配置示例

```json
{
  "plugins": {
    "slots": {
      "memory": "brain-memory"
    },
    "brain-memory": {
      "use_hyde": true,
      "recall_top_k": 12,
      "consolidate_cron": "0 3 * * *"
    }
  }
}
```

## 版本历史

- **4.0.0** — HyDE, 多层记忆, Provenance, APScheduler, 实体 Hebbian
- **3.0.0** — OpenClaw 钩子, 混合 recall, 主动遗忘
- **1.0.0** — 初始 LanceDB + Kuzu
