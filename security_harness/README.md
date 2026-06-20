# CNexus 防护验证套件

用于 **自有产品** 的授权、FeatureGate、心跳降级与环境完整性验证。  
不生成可用于绕过第三方软件的破解组件。

## 模块对照（旧名 → 合法用途）

| 旧模块（攻击向） | 本套件替代 | 用途 |
|------------------|------------|------|
| `fake_auth_server.py` | `staging_auth_server.py` | 仅签发测试 license，需 `CNEXUS_LICENSE_SECRET` |
| `cfg_forger.py` | `security_bootstrap.py --cfg-only` | 调用官方 `issue_license()` 生成测试 token |
| `hosts_modifier.py` | `integrity_checker.py` | **只读**检测 hosts 污染 |
| `cache_cleaner.py` | pytest fixture | 测试前后清理环境变量 |
| `bootloader.py` | `security_bootstrap.py` | 编排验证流程，无攻击步骤 |
| `patcher.py` | 暂不实现 | 若需要，只做 **检测** 不注入 |
| `version.dll` | 暂不实现 | 若需要，改为签名过的 `wetool_security.dll` 自检 |

## 快速开始

```bash
# 1. FeatureGate 单测
python -m pytest tests/security -q

# 2. 启动 staging 授权（另开终端）
set CNEXUS_LICENSE_SECRET=staging-secret-change-me
python -m security_harness.staging_auth_server --port 18711

# 3. dry-run（不连网）
python -m security_harness.security_bootstrap --dry-run

# 4. 全流程（需 staging 在跑）
set CNEXUS_LICENSE_SECRET=staging-secret-change-me
python -m security_harness.security_bootstrap --edition enterprise

# 5. 仅生成测试 license
python -m security_harness.security_bootstrap --cfg-only
```

## config.json

见 `security_harness/config.json`：staging 地址、心跳阈值、完整性检查项。

## 与 Runtime 集成

生产环境继续使用 `brain-memory-ui/api/license_guard.py`。  
本套件只用于 CI / 手工防护回归，不要把 `staging-secret-change-me` 打进发行包。
