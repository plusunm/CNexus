"""Policy engine — map ComputeProfile → scheduler / runtime / CSE policies."""

from __future__ import annotations

import copy
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal

from core.compute_profile import ComputeProfile, SAFE_BASELINE_RAM_GB, resolve_compute_profile

ComputeEnvelope = Literal["safe_baseline", "balanced", "performance", "accelerated"]
EmbedStrategy = Literal["serial", "parallel_limited", "parallel"]
CseMode = Literal["batch", "idle", "realtime"]
ModelTier = Literal["small", "medium", "large"]
RuntimeMode = Literal["auto", "unrestricted", "cloud"]


@dataclass
class SchedulerPolicy:
    enabled: bool
    max_concurrency: int
    embed_strategy: EmbedStrategy
    cache_aggressive: bool
    chat_priority: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComputePolicy:
    envelope: ComputeEnvelope
    scheduler: SchedulerPolicy
    cse_mode: CseMode
    model_tier: ModelTier
    runtime_overrides: Dict[str, Any]
    runtime_mode: RuntimeMode

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["scheduler"] = self.scheduler.to_dict()
        return payload


def resolve_runtime_mode(cfg: Dict[str, Any]) -> RuntimeMode:
    env = os.environ.get("CNEXUS_RUNTIME_MODE", "").strip().lower()
    if env in ("auto", "unrestricted", "cloud"):
        return env  # type: ignore[return-value]

    legacy = os.environ.get("CNEXUS_RUNTIME_PROFILE", "").strip().lower()
    if legacy in ("dev", "unrestricted"):
        return "unrestricted"
    if legacy == "cloud":
        return "cloud"
    if legacy in ("local_16gb", "safe_baseline", "safe"):
        return "auto"

    mode = str(cfg.get("runtime_mode") or cfg.get("compute", {}).get("runtime_mode") or "auto").lower()
    if mode in ("auto", "unrestricted", "cloud"):
        return mode  # type: ignore[return-value]
    return "auto"


def classify_envelope(profile: ComputeProfile, *, safe_baseline_ram_gb: float) -> ComputeEnvelope:
    if profile.locality == "cloud":
        return "balanced"

    if profile.gpu and (profile.gpu_vram_gb or 0) >= 8:
        return "accelerated"
    if profile.ram_gb >= 64 or profile.compute_score() >= 80:
        return "performance"
    if profile.ram_gb >= 32 or profile.compute_score() >= 40:
        return "balanced"
    if profile.ram_gb <= safe_baseline_ram_gb * 1.25 and not profile.gpu:
        return "safe_baseline"
    return "balanced"


def _scheduler_policy(profile: ComputeProfile, envelope: ComputeEnvelope, mode: RuntimeMode) -> SchedulerPolicy:
    if mode == "cloud" or profile.locality == "cloud":
        return SchedulerPolicy(
            enabled=False,
            max_concurrency=0,
            embed_strategy="parallel",
            cache_aggressive=False,
        )

    if envelope == "accelerated":
        return SchedulerPolicy(
            enabled=True,
            max_concurrency=4,
            embed_strategy="parallel",
            cache_aggressive=False,
        )
    if envelope == "performance":
        return SchedulerPolicy(
            enabled=True,
            max_concurrency=4,
            embed_strategy="parallel_limited",
            cache_aggressive=False,
        )
    if envelope == "balanced":
        return SchedulerPolicy(
            enabled=True,
            max_concurrency=2,
            embed_strategy="parallel_limited",
            cache_aggressive=True,
        )
    # safe_baseline — default envelope assumption (~16GB class), not a hard ceiling
    return SchedulerPolicy(
        enabled=True,
        max_concurrency=1,
        embed_strategy="serial",
        cache_aggressive=True,
    )


def _cse_mode(envelope: ComputeEnvelope, mode: RuntimeMode) -> CseMode:
    if mode == "unrestricted":
        return "realtime"
    if mode == "cloud":
        return "realtime"
    if envelope == "accelerated":
        return "realtime"
    if envelope == "performance":
        return "idle"
    if envelope == "balanced":
        return "idle"
    return "batch"


def _model_tier(envelope: ComputeEnvelope) -> ModelTier:
    if envelope == "accelerated":
        return "large"
    if envelope == "performance":
        return "large"
    if envelope == "balanced":
        return "medium"
    return "small"


def _runtime_overlays(
    envelope: ComputeEnvelope,
    mode: RuntimeMode,
    scheduler: SchedulerPolicy,
) -> Dict[str, Any]:
    if mode == "unrestricted":
        return {
            "chat_default_full_cognitive_loop": True,
            "chat_defer_cognition": True,
            "capture_cognize_default": True,
            "governance_background_enabled": True,
            "governance_interval_seconds": 3600,
            "inference_scheduler_enabled": scheduler.enabled,
            "inference_max_concurrent": scheduler.max_concurrency,
            "embedding_cache_enabled": True,
        }

    if mode == "cloud" or scheduler.enabled is False:
        return {
            "chat_default_full_cognitive_loop": True,
            "chat_defer_cognition": False,
            "capture_cognize_default": True,
            "governance_background_enabled": True,
            "governance_interval_seconds": 3600,
            "inference_scheduler_enabled": False,
            "embedding_cache_enabled": True,
        }

    if envelope == "safe_baseline":
        return {
            "chat_default_full_cognitive_loop": False,
            "chat_defer_cognition": True,
            "capture_cognize_default": False,
            "governance_background_enabled": True,
            "governance_interval_seconds": 7200,
            "inference_scheduler_enabled": True,
            "inference_max_concurrent": scheduler.max_concurrency,
            "embedding_cache_enabled": True,
        }

    if envelope == "balanced":
        return {
            "chat_default_full_cognitive_loop": True,
            "chat_defer_cognition": True,
            "capture_cognize_default": True,
            "governance_background_enabled": True,
            "governance_interval_seconds": 5400,
            "inference_scheduler_enabled": True,
            "inference_max_concurrent": scheduler.max_concurrency,
            "embedding_cache_enabled": True,
        }

    return {
        "chat_default_full_cognitive_loop": True,
        "chat_defer_cognition": False,
        "capture_cognize_default": True,
        "governance_background_enabled": True,
        "governance_interval_seconds": 3600,
        "inference_scheduler_enabled": True,
        "inference_max_concurrent": scheduler.max_concurrency,
        "embedding_cache_enabled": not scheduler.cache_aggressive,
    }


def generate_compute_policy(profile: ComputeProfile, cfg: Dict[str, Any]) -> ComputePolicy:
    compute_cfg = cfg.get("compute") or {}
    safe_ram = float(compute_cfg.get("safe_baseline_ram_gb", SAFE_BASELINE_RAM_GB))
    mode = resolve_runtime_mode(cfg)
    envelope = classify_envelope(profile, safe_baseline_ram_gb=safe_ram)
    scheduler = _scheduler_policy(profile, envelope, mode)
    cse_mode = _cse_mode(envelope, mode)
    overlays = _runtime_overlays(envelope, mode, scheduler)
    overlays["cse_mode"] = cse_mode
    overlays["model_tier"] = _model_tier(envelope)
    return ComputePolicy(
        envelope=envelope,
        scheduler=scheduler,
        cse_mode=cse_mode,
        model_tier=_model_tier(envelope),
        runtime_overrides=overlays,
        runtime_mode=mode,
    )


def apply_compute_aware_config(
    cfg: Dict[str, Any],
) -> tuple[Dict[str, Any], ComputeProfile, ComputePolicy]:
    """Merge compute-derived policy into runtime config."""
    merged = copy.copy(cfg)
    profile = resolve_compute_profile(cfg)
    policy = generate_compute_policy(profile, cfg)

    explicit_keys = set((cfg.get("compute") or {}).get("preserve_keys") or [])
    for key, value in policy.runtime_overrides.items():
        if key in explicit_keys and key in cfg:
            continue
        merged[key] = value

    if os.environ.get("CNEXUS_INFERENCE_SCHEDULER", "").lower() in ("0", "false", "no"):
        merged["inference_scheduler_enabled"] = False

    merged["compute_profile"] = profile.to_dict()
    merged["compute_policy"] = policy.to_dict()
    merged["runtime_envelope"] = policy.envelope
    merged["runtime_mode"] = policy.runtime_mode
    merged["cse_mode"] = policy.cse_mode
    return merged, profile, policy
