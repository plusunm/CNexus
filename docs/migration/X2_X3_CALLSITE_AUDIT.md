# X2 / X3 调用栈审计 — SelfModel 混写 & observe 直读 memory

- **日期**: 2026-06-19
- **目标项目**: `D:\类脑记忆\CNexus — Observational Cognition Platform`
- **Runbook 引用**: LAYER1_NORMALIZATION §5 — X2 (HIGH), X3 (MEDIUM)
- **模式**: 静态 grep + 人工归类，未改代码

---

## X2 — SelfModel 单文件混写 (Σ.S + Σ.I + Σ.M)

### 持久化 SSOT

| 项 | 值 |
|----|-----|
| 文件 | `{base_dir}/unified_self_model.json` |
| 回退 | `{base_dir}/subject_self_model.json` |
| 写入 API | `SelfModelStore.save()` — **一次写 10 字段** |
| Runbook 要求 | 三域分写：COGNIZE→Σ.S, DECIDE→Σ.I, STORE→Σ.M metadata |

### 写入调用栈（生产路径）

| ID | 调用链 | 触发 | 写入域 | 仍混写? |
|----|--------|------|--------|---------|
| X2-01 | `runtime._apply_post_cdg_interaction_updates` → `self_model_store.integrate()` → `save()` | chat 后 CDG | Σ.S+Σ.I+Σ.M 全量 | ✅ 是 |
| X2-02 | `runtime.trait_based_reflection` → `self_model_store.integrate()` → `save()` | reflect_review | 全量 | ✅ 是 |
| X2-03 | `kernel._emit_evolved_observability` → `dispatch_cognitive_step` → `apply_cognize/decide/store` → `save()` | 每次 kernel persist | 逻辑分 writer，**物理单文件** | ✅ 是 |
| X2-04 | `SelfModelStore.store_step_touch` → `apply_store_selfmodel_step` → `save()` | STORE 显式 | 仅 touch last_reconstruction，**仍全量 serialize** | ✅ 是 |
| X2-05 | `SelfModelStore.integrate` → `integrate_experience` (内存) → `save()` | 任意 integrate | 全量 | ✅ 是 |
| X2-06 | `SelfModel.reconstruct` → `integrate_experience` → (via store) `save()` | legacy alias | 全量 | ✅ 是 |

### evolved 逻辑 writer（未拆 storage）

| 函数 | 文件 | 意图域 | 实际持久化 |
|------|------|--------|-----------|
| `apply_cognize_step` | `core/evolved/cognitive_hooks.py:16` | Σ.S | `store.save()` 全文件 |
| `apply_decide_step` | `core/evolved/cognitive_hooks.py:36` | Σ.I | 同上 |
| `apply_store_selfmodel_step` | `core/evolved/cognitive_hooks.py:54` | Σ.M metadata | 同上 |
| `dispatch_cognitive_step` | `core/evolved/cognitive_hooks.py:63` | 路由 | `kernel.py:101` 每 persist 后 |

### 非 SelfModel 的 `.save()`（排除误报）

| 文件 | 说明 | X2? |
|------|------|-----|
| `core/model_registry.py` | 模型注册表 | ❌ 无关 |
| `core/personality/reflective/reflective_store.py` | 反思存储 | ❌ 不同域 |
| `FactorGraphCanvas.tsx` / `GraphViewCanvas.tsx` | Canvas 2D | ❌ 前端 |

### X2 结论

```
状态: OPEN
缓解: evolved cognitive_hooks 已实现 Runbook ownership_table 的「逻辑 writer」
缺口: unified_self_model.json 仍为 Single Writer 全量 JSON
影响: 无法独立回放 Σ.S / Σ.I；STORE 步无法单独审计 Σ.M metadata 写
建议迁移: 三文件或三 JSONL 分域（Σ.S.json, Σ.I.json, Σ.M.meta.json）+ adapter 读合并
```

---

## X3 — router.observe / 直读 memory & governance

### 内核路由 SSOT（Runbook 标 violation）

**文件**: `core/kernel/router.py`

```python
def _route_observe(p, runtime):
    kind = p.get("_observe_kind") or p.get("kind")
    if kind == "memory_stats":      → runtime.memory_stats()
    if kind == "governance_state":  → runtime.get_current_state()
    if kind == "cdg_trajectory":    → runtime.cdg.trajectory_report(...)
    if kind == "active_reflections":→ runtime.reflection_pipeline.get_active_reflections()
```

| kind | 直读对象 | Runbook 期望 | 严重度 |
|------|---------|-------------|--------|
| `memory_stats` | `lifecycle.collect_stats()` | Σ.T 或 Σ.M 封装读 | MEDIUM |
| `governance_state` | 聚合 cognitive/self_model/beliefs/... | 非 Σ.M 单一接口 | MEDIUM |
| `cdg_trajectory` | CDG 子系统 | 稳定守卫域 | LOW |
| `active_reflections` | reflection_pipeline | REFLECT 域 | LOW |

### 调用栈 — 经 kernel observe 意图

| ID | 调用链 | 文件:行 |
|----|--------|---------|
| X3-K1 | `Dispatcher.observe_read(kind)` → `RouteKind.OBSERVE_READ` → kernel.execute(observe) → `_route_observe` | `dispatch.py:637-640` → `router.py:72-95` |
| X3-K2 | `intent.py` OBSERVE_READ → `"observe"` + `_observe_kind` | `core/kernel/intent.py:39,98` |
| X3-K3 | registry `"observe": "kernel.observe"` | `core/kernel/registry.py:24` |

### 调用栈 — 绕过 kernel 直读 runtime（X3 扩展）

| ID | 调用链 | 读什么 | 经 kernel? |
|----|--------|--------|-----------|
| X3-B1 | `brain-memory-ui/api/routes/memory.py:memory_stats` → `get_runtime().memory_stats()` | memory 统计 | ❌ 直读 |
| X3-B2 | `brain-memory-ui/api/routes/governance.py` → `observe_read("governance_state")` | 治理快照 | ⚠️ 经 dispatcher→kernel |
| X3-B3 | `brain-memory-ui/api/routes/governance.py` → `observe_read("cdg_trajectory")` | CDG | ⚠️ 经 kernel |
| X3-B4 | `brain-memory-ui/api/routes/reflective.py` → `observe_read("active_reflections")` | 反思 | ⚠️ 经 kernel |
| X3-B5 | `api/v1_endpoints.py:454,468,516` → `get_current_state()` / `memory_stats()` | 状态+memory | ❌ 直读 |
| X3-B6 | `brain-memory-ui/api/routes/cse.py:61` → `get_current_state()` | CSE 状态 | ❌ 直读 |
| X3-B7 | `core/skill/skill_registry.py:120` → `runtime.get_current_state()` | skill 上下文 | ❌ 直读 |
| X3-B8 | `core/governance/cdg/attractor.py:53` → `memory.memory_stats()` | CDG 内部 | ❌ 直读 storage |
| X3-B9 | `scripts/phase_a_landscape_report.py:28` | 脚本 | ❌ 直读 |

### 合规读路径（Runbook 推荐方向）

| ID | API | 文件 | 说明 |
|----|-----|------|------|
| OK-1 | `ExecutionRecordView.read(trace_id, kernel)` | `core/kernel/observe/record_view.py:65` | 单 trace 观测 SSOT |
| OK-2 | `kernel.py` routes | `brain-memory-ui/api/routes/kernel.py:141+` | UI 经 record_view / learn_view |
| OK-3 | `Dispatcher` OBSERVE_READ flags | `dispatch.py:203-207` | `read_only=True`, `mutate_state=False` |
| OK-4 | `verify/protocol.py` | 静态规则禁止 `get_runtime().memory_stats` | 治理扫描 |

### `get_current_state()` 泄露面（governance_state 实质）

**文件**: `brain_memory/runtime.py:2660+`

聚合字段包括: `cognitive_state`, `working_self`, **`self_model`**, `predictive`, `beliefs`, `reflective`, `narrative`, ...

→ observe 的 `governance_state` **不是** 只读 Σ.T，而是 **runtime 全状态快照**（含 Σ.S/Σ.I 混写副本）。

### X3 结论

```
状态: OPEN（D/F 相同）
kernel observe 路由: 4 kinds，其中 memory_stats + governance_state 违反 Σ.M 封装
API 层直读: 至少 5 处不经 ExecutionRecordView
缓解已有: kernel.py UI 路由、verify/protocol 静态规则、OBSERVE_READ read_only 标记
建议迁移:
  1. memory_stats → lifecycle stats 经 Σ.T query 或 read-only adapter
  2. governance_state → 拆为 governance_trace 读路径，禁止嵌套 self_model 全量
  3. v1_endpoints / memory.py 改 dispatcher.observe_read 或 kernel record_view
```

---

## 汇总

| 项 | 生产调用点数 | evolved 缓解 | 存储/路由拆分 |
|----|-------------|-------------|--------------|
| X2 SelfModel | 6 条写链 | 逻辑 writer ✅ | 物理拆分 ❌ |
| X3 observe | 4 kernel kinds + 9 直读/绕路 | read_only 标记 ✅ | Σ 封装 ❌ |

**优先级建议**: X2 阻塞 Runbook ownership_table 完整落地；X3 阻塞 OBSERVE 步「只读 Σ.T」纯度，但不阻塞 Layer1 memory_store 迁移。
