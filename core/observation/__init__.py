"""
CNexus Observation Runtime Layer v1 + P2 nervous system.

Runtime emits events → Gateway normalizes → append-only JSONL → CNexus L2–L8 reads.
No reverse edge. See docs/architecture/CNexus_Runtime_Observation_Boundary_Contract_v0.1.md
"""

from core.observation.adapters.chat_adapter import record_chat_observation
from core.observation.adapters.file_tail_adapter import FileTailAdapter
from core.observation.adapters.jsonl_push_adapter import JsonlPushAdapter
from core.observation.adapters.metrics_scrape_adapter import MetricsScrapeAdapter
from core.observation.demotion import DEMOTION_MAP, OUTPUT_FIELD_DEMOTION, demote_payload
from core.observation.density import DensityPolicy, ObservationDensityManager
from core.observation.event_normalizer import EventNormalizer
from core.observation.gateway import ObservationGateway, get_observation_writer
from core.observation.l2_streaming import StreamingL2Window, build_streaming_l2_report
from core.observation.schema import (
    CONTRACT_META,
    CONTROL_STRIP_KEYS,
    OBSERVATION_CONTRACT_VERSION,
    OBSERVATION_NORTH_STAR,
    ObservationEvent,
)
from core.observation.streaming import ObservationStreamTailer
from core.observation.writer import ObservationWriter

__all__ = [
    "CONTRACT_META",
    "CONTROL_STRIP_KEYS",
    "DEMOTION_MAP",
    "DensityPolicy",
    "EventNormalizer",
    "FileTailAdapter",
    "JsonlPushAdapter",
    "MetricsScrapeAdapter",
    "OBSERVATION_CONTRACT_VERSION",
    "OBSERVATION_NORTH_STAR",
    "ObservationDensityManager",
    "ObservationEvent",
    "ObservationGateway",
    "ObservationStreamTailer",
    "ObservationWriter",
    "OUTPUT_FIELD_DEMOTION",
    "StreamingL2Window",
    "build_streaming_l2_report",
    "demote_payload",
    "get_observation_writer",
    "record_chat_observation",
]
