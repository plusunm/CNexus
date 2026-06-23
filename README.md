# CNexus — Network Edition（网络版）

> **分布式认知节点：本地记忆 + P2P 互联 + 自组织网络栈**

CNexus **网络版** 是面向多节点协作的轻量认知运行时：单文件网关 `app_v2.py`、静态 UI、零重型框架依赖。每个节点在本地维护认知状态与审计日志，并通过 **DHT 发现、连通性管理、Gossip 同步、资产推送** 与其他节点组成去中心化认知网络。

> 本仓库为 **Network Edition（纯净网络版）** — 已移除旧版 Observational Cognition Platform 全栈（`brain-memory-ui/`、Docker 企业运行时、Tauri 安装包等）。完整平台版历史请见 Git 历史；日常开发请使用本网络版目录结构。

**相关仓库：** [plusunm/CNexus2.0](https://github.com/plusunm/CNexus2.0)（个人版演进分支）

---

## 网络版能做什么？

### ① 自组织网络栈（L1 / L2 / L3）

| 层级 | 模块 | 能力 |
|------|------|------|
| **L1** | `ConnectivityManager` + STUN | ICE 式路径选择、中继回退、跨 NAT 候选发现 |
| **L2** | `DHTService` | Kademlia k-buckets、HTTP RPC（FIND_NODE / STORE） |
| **L3** | `NetworkFirewall` + `GossipSync` | 信誉封禁、心跳自愈、审计增量同步 |
| **资产层** | `AssetPeerSync` + 推送重试队列 | 签名资产跨节点传播、失败指数退避重试 |

### ② 认知连续性与元认知

| 能力 | 说明 |
|------|------|
| **StateReconstructor** | 快照 + 增量回放，节点重启后「唤醒」认知状态 |
| **SelfReflectionEngine** | 审计日志模式分析 + 可选 LLM 元反思 |
| **六步认知闭环** | OBSERVE → COGNIZE → DECIDE → SPEAK → STORE → REFLECT |
| **REM 深度睡眠** | 空闲时剪枝噪声、压缩碎片记忆 |
| **真多模态 CLIP** | 图像直接向量化（ONNX），非视觉描述中转 |

### ③ 前端 · 网络拓扑工作台

侧栏 **「网络拓扑」** 分区提供：

- **Mission Control** — 节点状态、唤醒进度、拓扑总览
- **连接管理** — DHT / 连通性状态、按 PeerID 建连、封禁恶意节点
- **网络运维** — 日志回放、重索引、推送队列、元反思、REM 触发
- **网络资产** — 资产摄入、语义检索（文本 / 图像）

---

## 快速启动

**Windows**

```bat
start_cnexus.bat
```

**手动**

```bash
pip install -r requirements.txt
python app_v2.py
# 浏览器 http://127.0.0.1:7864
```

### 跨网 P2P 必备环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `CNEXUS_BIND_HOST` | 监听地址（跨网设为 `0.0.0.0`） | `127.0.0.1` |
| `CNEXUS_PUBLIC_URL` | 对外可达 URL（供其他节点回调） | — |
| `CNEXUS_DHT_ENABLE` | 启用 DHT | `0` |
| `CNEXUS_DHT_BOOTSTRAP` | 引导节点 URL（逗号分隔） | — |
| `CNEXUS_CONNECTIVITY_ENABLE` | 启用连通性管理器 | `0` |
| `CNEXUS_STUN_SERVERS` | STUN 服务器列表 | 公共 STUN |
| `CNEXUS_RELAY_URL` | 中继回退 URL | — |
| `CNEXUS_ASSET_PEER_PUSH` | 索引后自动推送资产 | `0` |
| `CNEXUS_ASSET_PUSH_RETRY_ENABLE` | 推送失败重试队列 | `1` |
| `CNEXUS_SNAPSHOT_INTERVAL` | 认知快照间隔（条） | `1000` |
| `CNEXUS_CLIP_ENABLE` | 启用 CLIP 向量 | `0` |
| `CNEXUS_CLIP_IMAGE_ONNX` | 图像 ONNX 模型路径 | — |
| `CNEXUS_CLIP_TEXT_ONNX` | 文本 ONNX 模型路径 | — |

---

## 主要网络 API

| 端点 | 说明 |
|------|------|
| `GET /api/connectivity/status` | 连通性状态与活跃路径 |
| `POST /api/connectivity/connect` | 向 PeerID 发起建连 |
| `GET /api/dht/status` | DHT 路由表与节点信息 |
| `POST /api/dht/rpc` | Kademlia RPC |
| `POST /api/network/firewall/ban` | 封禁恶意 Peer |
| `GET /api/awakening/status` | 唤醒 / 快照回放状态 |
| `POST /api/replay/run` | 审计日志增量回放 |
| `POST /api/reflect/meta` | 元认知反思 |
| `POST /api/asset/push` | 向可信节点推送资产 |
| `GET /api/asset/push/queue` | 推送重试队列状态 |
| `POST /api/asset/search/semantic` | 文本或 `image_base64` 语义检索 |

完整对话与记忆 API 见 `app_v2.py` 启动日志。

---

## 项目结构（网络版）

```
CNexus/
├── app_v2.py              # 统一 HTTP 网关（7864）
├── start_cnexus.bat       # Windows 一键启动
├── requirements.txt       # 可选依赖（pynacl、CLIP 等）
├── src/
│   ├── kernel/            # 六步认知 reducer
│   ├── core/              # 审计、向量、身份、状态重建、元反思
│   ├── network/           # DHT、连通性、防火墙、Gossip、资产同步
│   └── api/               # 指标与 P2P 中间件
├── ui/                    # 静态前端（含网络拓扑工作台）
└── tests/                 # 网络栈与核心模块测试
```

---

## 双节点联调示例

**节点 A（引导）**

```bash
set CNEXUS_BIND_HOST=0.0.0.0
set CNEXUS_PUBLIC_URL=http://192.168.1.10:7864
set CNEXUS_DHT_ENABLE=1
python app_v2.py
```

**节点 B（加入）**

```bash
set CNEXUS_BIND_HOST=0.0.0.0
set CNEXUS_PUBLIC_URL=http://192.168.1.11:7864
set CNEXUS_DHT_ENABLE=1
set CNEXUS_DHT_BOOTSTRAP=http://192.168.1.10:7864
set CNEXUS_CONNECTIVITY_ENABLE=1
python app_v2.py
```

在 B 的 UI **网络拓扑 → 连接管理** 中查看 DHT 状态，或通过 `POST /api/connectivity/connect` 连接 A 的 PeerID。

---

## License

MIT — free to use, modify, and extend.
