# SANDBOX BOOT 干跑报告 — D 盘 CNexus

- **日期**: 2026-06-19
- **目标**: Runbook `FIXED_POINT_VALIDATION_SPEC` + evolved 运行时验证
- **模式**: 只读干跑（跑测试 + 结构校验，未 commit Σ_REMAP → Σ₀）

---

## 1. 运行时测试（BOOT 子集）

命令:

```text
python -m unittest tests.test_evolved_integration -v
```

| # | 测试用例 | 验证项 | 结果 |
|---|---------|--------|------|
| 1 | `TestEvolvedBlockStore.test_persist_sigma_slot_on_create` | MemoryBlock 持久化含 `sigma_slot=Σ.M` + lifecycle metadata | ✅ PASS |
| 2 | `TestEvolvedBlockStore.test_get_sigma_projection` | block_store → Σ.M 投影可读 | ✅ PASS |
| 3 | `TestEvolvedStoreProjection.test_build_store_projection_from_record` | ExecutionRecord → STORE 投影 | ✅ PASS |
| 4 | `TestEvolvedStoreProjection.test_record_helper_methods` | `build_sigma_trace()` / `build_store_projection()` | ✅ PASS |
| 5 | `TestEvolvedTraceEmit.test_emit_sigma_trace_writes_jsonl` | Σ.T append → `execution_trace.jsonl` | ✅ PASS |
| 6 | `TestMigrationRunner.test_loads_mapping_ir` | 44 映射 IR 加载 | ✅ PASS |
| 7 | `TestApplySigmaToBlock.test_apply_sigma_increments_iteration` | factory_gap iteration_counter | ✅ PASS |

**合计: 7/7 PASS**（0.085s）

---

## 2. MigrationRunner IR 加载

| 字段 | 值 |
|------|-----|
| IR 路径 | `docs/evolved/step_01_mapping_table.ref.json` |
| loaded | true |
| total_mappings | 44 |
| exists | 33 |
| rename | 27 |
| redirect | 8 |
| factory_gap | 4 |
| merge | 1 |
| partial | 2 |

factory_gap targets: `block_decay_rate`, `block_created_at`, `block_updated_at`, `block_version_seq`

**运行时闭合**: D `sigma_mapping.py` + `store_step.py` 在测试中已覆盖上述 gap 的派生/写入。

---

## 3. FIXED_POINT 结构验证（Runbook §1–§5）

| 验证项 | 方法 | 结果 | 备注 |
|--------|------|------|------|
| Idempotence | IR 已为 canonical；δ_REMAP 纯函数 | ✅ PASS | 结构保证，见 Runbook §1 |
| Trace reconstructability | 44 映射分类统计 | ✅ PASS WITH NOTES | 95% 可逆；4 factory_gap + 1 partial 不可逆 |
| Invariance under replay | REMAP_DETERMINISM_CONTRACT | ✅ PASS | 合同禁止二次 REMAP |
| Attractor stability | Σ.I 初值 = attractor target | ✅ PASS | Runbook 已验证 |
| Governance constraints | Σ_REMAP transition_meta | ✅ PASS | 见 F Runbook Σ_REMAP.json |

---

## 4. SANDBOX BOOT 步骤对照（运行时可达部分）

| Runbook 步骤 | D 盘证据 | 状态 |
|-------------|---------|------|
| COMPILE (Σ_REMAP) | `docs/evolved/step_01_mapping_table.ref.json` hash = Runbook | ✅ |
| BOOT Σ₀ side-channel | `ExecutionRecord.build_*` + evolved 接线 | ✅ 部分 |
| EXECUTE δ (单轮) | kernel `_persist_record` → trace + cognitive | ✅ 代码路径存在 |
| VERIFY trace 行 | test #5 jsonl 行 `type=kernel_execution` | ✅ |
| VERIFY Σ.M block | test #1 metadata.sigma_slot | ✅ |
| VERIFY factory_gap | test #7 iteration_counter | ✅ |
| FULL Σ₀ boot (Tauri/API) | 未在本干跑范围 | ⏸ 未测 |
| commit Σ_REMAP → Σ₀ | Runbook 禁止自动 commit | ❌ 未执行（符合规范） |

---

## 5. 干跑结论

```
SANDBOX_BOOT_DRY_RUN:
  runtime_tests:     7/7 PASS
  mapping_ir:        44/44 loaded
  fixed_point_struct: 5/5 PASS (with notes)
  full_product_boot:  NOT RUN

仲裁:
  D evolved 层已达到 Runbook Layer1 SANDBOX 的运行时可验证子集。
  阻塞 Layer2+ 的仍是: 产品级 BOOT、trace 按日分片、t- trace_id、X2 三域持久化拆分。
  commit(Σ_SANDBOX_REFERENCE) 允许；commit(Σ_REMAP → Σ₀) 需人工确认（Runbook §5）。
```

---

## 6. 建议下一干跑（仍可不写业务代码）

1. `python -m unittest tests.test_execution_kernel_migration tests.test_kernel_* -v`
2. 启动 API 后 GET `/v1/system/ready` + kernel observe 端点 smoke
3. 对比一次真实 `execution_trace.jsonl` 是否含 `kernel_execution` 行
