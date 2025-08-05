"""
Message type definitions for SN27 Validator Pub/Sub communication.

This module contains all the message schemas and constants used for
communication between validators and the SN27 backend.
"""

from datetime import datetime, timezone
from typing import Literal
from dataclasses import dataclass, field


# Topic constants
class TOPICS:
    ALLOCATION_EVENTS = "allocation-events"
    MINER_EVENTS = "miner-events"
    SYSTEM_EVENTS = "system-events"
    VALIDATION_EVENTS = "validation-events"


# Message type constants
class MESSAGE_TYPES:
    # Register API → Backend messages (3 core messages)
    GPU_STATUS_CHANGE = "gpu_status_change"
    GPU_DEALLOCATION = "gpu_deallocation"
    # Validator → Backend messages (3 core messages)
    MINER_ALLOCATION = "miner_allocation"
    MINER_DEALLOCATION = "miner_deallocation"
    POG_RESULT = "pog_result"


# Base message structure
@dataclass
class BasePubSubMessage:
    message_type: str = field(default_factory=str)
    timestamp: str = field(default_factory=str)
    source: Literal["validator", "backend"] = field(default="validator")
    priority: Literal["low", "normal", "high", "urgent"] | None = "normal"
    correlation_id: str | None = None
    data: dict | None = None

    def to_dict(self) -> dict:
        """Convert message to dictionary for JSON serialization."""
        result = {
            "message_type": self.message_type,
            "timestamp": self.timestamp,
            "source": self.source,
            "data": self.data or {}
        }
        if self.priority != "normal":
            result["priority"] = self.priority
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        return result


@dataclass
class BenchmarkData:
    gpu_utilization: float
    memory_usage: float
    compute_performance: float
    network_latency: float


@dataclass
class PogResultMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    miner_hotkey: str = field(default_factory=str)
    request_id: str = field(default_factory=str)
    result: Literal["success", "failure", "timeout", "error"] = field(default="error")
    validation_duration_seconds: float = field(default_factory=float)
    # Optional fields last
    score: float | None = None
    benchmark_data: BenchmarkData | None = None
    error_details: str | None = None
    health_check_result: bool | None = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.POG_RESULT
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "request_id": self.request_id,
            "result": self.result,
            "validation_duration_seconds": self.validation_duration_seconds,
        }
        if self.score is not None:
            self.data["score"] = self.score
        if self.benchmark_data:
            self.data["benchmark_data"] = {
                "gpu_utilization": self.benchmark_data.gpu_utilization,
                "memory_usage": self.benchmark_data.memory_usage,
                "compute_performance": self.benchmark_data.compute_performance,
                "network_latency": self.benchmark_data.network_latency,
            }
        if self.error_details:
            self.data["error_details"] = self.error_details
        if self.health_check_result:
            self.data['health_check_result'] = self.health_check_result


@dataclass
class MinerDeallocationMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    miner_hotkey: str = field(default_factory=str)
    retry_count: int | None = None
    deallocation_result: bool | None = None
    deallocation_error: str | None = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.MINER_DEALLOCATION
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
        }
        if self.retry_count:
            self.data["retry_count"] = self.retry_count
        if self.deallocation_result:
            self.data['deallocation_result'] = self.deallocation_result
        if self.deallocation_error:
            self.data['deallocation_error'] = self.deallocation_error


@dataclass
class MinerAllocationMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    miner_hotkey: str = field(default_factory=str)
    allocation_result: bool | None = None
    allocation_error: str | None = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.MINER_DEALLOCATION
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
        }
        if self.allocation_result:
            self.data['allocation_result'] = self.allocation_result
        if self.allocation_error:
            self.data['allocation_error'] = self.allocation_error


@dataclass
class GpuStatusChangePubSubMessage(BasePubSubMessage):
    """
    GPU status change message for pub/sub notifications.

    Used when miners change status (online/offline/testing/allocated) to notify
    external services via pub/sub topics.
    """
    # Required fields first
    validator_hotkey: str = field(default="")
    miner_hotkey: str = field(default="")
    previous_status: str = field(default="")
    current_status: str = field(default="")

    # Optional fields last
    allocation_uuid: str | None = None
    reason: str | None = None
    status_change_at: str | None = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.GPU_STATUS_CHANGE
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "previous_status": self.previous_status,
            "current_status": self.current_status,
            "status_change_at": self.status_change_at or datetime.now(timezone.utc).isoformat(),
        }
        if self.allocation_uuid:
            self.data["allocation_uuid"] = self.allocation_uuid
        if self.reason:
            self.data["reason"] = self.reason


@dataclass
class GpuDeallocationPubSubMessage(BasePubSubMessage):
    """
    GPU deallocation message for pub/sub notifications.

    Used when GPU allocations are terminated to notify external services
    via pub/sub topics about the deallocation event.
    """
    # Required fields first
    validator_hotkey: str = field(default="")
    miner_hotkey: str = field(default="")
    allocation_uuid: str = field(default="")
    deallocation_reason: str = field(default="")

    # Optional fields last
    gpu_model: str | None = None
    allocation_duration_minutes: int | None = None
    deallocated_at: str | None = None
    user_id: str | None = None
    allocation_start_time: str | None = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.GPU_DEALLOCATION
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "allocation_uuid": self.allocation_uuid,
            "deallocation_reason": self.deallocation_reason,
            "deallocated_at": self.deallocated_at or datetime.now(timezone.utc).isoformat(),
        }
        if self.gpu_model:
            self.data["gpu_model"] = self.gpu_model
        if self.allocation_duration_minutes:
            self.data["allocation_duration_minutes"] = self.allocation_duration_minutes
        if self.user_id:
            self.data["user_id"] = self.user_id
        if self.allocation_start_time:
            self.data["allocation_start_time"] = self.allocation_start_time


# Union type for all pub sub messages (5 core messages)
# GpuDeallocationPubSubMessage,     # Announce register - miner status change
# GpuStatusChangePubSubMessage,     # Announce register - miner deallocation
# MinerDeallocationMessage,         # Announce validator deallocated miner
# MinerAllocationMessage,           # Announce validator allocated miner
# PogResultMessage,                 # Report Proof of GPU test results
PubSubMessage = (
    GpuDeallocationPubSubMessage | GpuStatusChangePubSubMessage |
    MinerDeallocationMessage | MinerAllocationMessage |
    PogResultMessage
)
