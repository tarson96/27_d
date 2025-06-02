"""
Message type definitions for SN27 Validator Pub/Sub communication.

This module contains all the message schemas and constants used for
communication between validators and the SN27 backend.
"""

from typing import Dict, Any, Optional, Literal, Union
from dataclasses import dataclass, field
from datetime import datetime

# Topic constants
class TOPICS:
    ALLOCATION_EVENTS = "allocation-events"
    MINER_EVENTS = "miner-events"
    SYSTEM_EVENTS = "system-events"
    VALIDATION_EVENTS = "validation-events"

# Message type constants
class MESSAGE_TYPES:
    # Validator → Backend messages (4 core messages)
    VALIDATOR_STATUS_UPDATE = "validator_status_update"
    ALLOCATION_REQUEST = "allocation_request"
    POG_RESULT = "pog_result"
    MINER_DISCOVERY = "miner_discovery"

# Base message structure
@dataclass
class BasePubSubMessage:
    message_type: str = field(default_factory=str)
    timestamp: str = field(default_factory=str)
    source: Literal["validator", "backend"] = field(default="validator")
    priority: Optional[Literal["low", "normal", "high", "urgent"]] = "normal"
    correlation_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        result = {
            "messageType": self.message_type,
            "timestamp": self.timestamp,
            "source": self.source,
            "data": self.data or {}
        }
        if self.priority != "normal":
            result["priority"] = self.priority
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        return result

# Validator → Backend message types

@dataclass
class GpuSpecs:
    model: str
    vram_gb: int
    cpu_cores: int
    ram_gb: int

@dataclass
class NetworkInfo:
    ip_address: Optional[str] = None
    port: Optional[int] = None
    region: Optional[str] = None

@dataclass
class MinerDiscoveryMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    miner_hotkey: str = field(default_factory=str)
    discovered_at: str = field(default_factory=str)
    gpu_specs: GpuSpecs = field(default_factory=GpuSpecs)
    network_info: NetworkInfo = field(default_factory=NetworkInfo)
    # Optional fields last
    registration_block: Optional[int] = None
    initial_benchmark_score: Optional[float] = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.MINER_DISCOVERY
        self.source = "validator"
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "discovered_at": self.discovered_at,
            "gpu_specs": {
                "model": self.gpu_specs.model,
                "vram_gb": self.gpu_specs.vram_gb,
                "cpu_cores": self.gpu_specs.cpu_cores,
                "ram_gb": self.gpu_specs.ram_gb,
            },
            "network_info": {
                "ip_address": self.network_info.ip_address,
                "port": self.network_info.port,
                "region": self.network_info.region,
            },
        }
        if self.registration_block is not None:
            self.data["registration_block"] = self.registration_block
        if self.initial_benchmark_score is not None:
            self.data["initial_benchmark_score"] = self.initial_benchmark_score

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
    score: Optional[float] = None
    benchmark_data: Optional[BenchmarkData] = None
    error_details: Optional[str] = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.POG_RESULT
        self.source = "validator"
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

@dataclass
class PerformanceMetrics:
    avg_response_time_ms: float
    success_rate_percentage: float
    uptime_percentage: float

@dataclass
class ValidatorStatusMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    status: Literal["online", "offline", "maintenance", "syncing"] = field(default="syncing")
    version: str = field(default_factory=str)
    active_validations: int = field(default_factory=int)
    # Optional fields last
    last_sync_block: Optional[int] = None
    performance_metrics: Optional[PerformanceMetrics] = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.VALIDATOR_STATUS_UPDATE
        self.source = "validator"
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "status": self.status,
            "version": self.version,
            "active_validations": self.active_validations,
        }
        if self.last_sync_block is not None:
            self.data["last_sync_block"] = self.last_sync_block
        if self.performance_metrics:
            self.data["performance_metrics"] = {
                "avg_response_time_ms": self.performance_metrics.avg_response_time_ms,
                "success_rate_percentage": self.performance_metrics.success_rate_percentage,
                "uptime_percentage": self.performance_metrics.uptime_percentage,
            }

@dataclass
class DeviceRequirements:
    gpu_count: int = 1
    min_vram_gb: int = 4
    cpu_cores: int = 1
    ram_gb: int = 1
    storage_gb: int = 1

@dataclass
class AllocationRequestMessage(BasePubSubMessage):
    # Required fields first
    validator_hotkey: str = field(default_factory=str)
    miner_hotkey: str = field(default_factory=str)
    allocation_uuid: str = field(default_factory=str)
    # Fields with defaults
    request_type: str = "pog_test"
    expected_duration_minutes: int = 10
    device_requirements: Optional[DeviceRequirements] = None
    requested_at: Optional[str] = None

    def __post_init__(self):
        self.message_type = MESSAGE_TYPES.ALLOCATION_REQUEST
        self.source = "validator"
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
            "allocation_uuid": self.allocation_uuid,
            "request_type": self.request_type,
            "expected_duration_minutes": self.expected_duration_minutes,
            "requested_at": self.requested_at or datetime.utcnow().isoformat() + "Z",
        }
        if self.device_requirements:
            self.data["device_requirements"] = {
                "gpu_count": self.device_requirements.gpu_count,
                "min_vram_gb": self.device_requirements.min_vram_gb,
                "cpu_cores": self.device_requirements.cpu_cores,
                "ram_gb": self.device_requirements.ram_gb,
                "storage_gb": self.device_requirements.storage_gb,
            }


# Union type for all validator messages (4 core messages)
ValidatorMessage = Union[
    ValidatorStatusMessage,           # 📊 Periodic health and performance reporting
    AllocationRequestMessage,         # 🎯 Track allocation requests before they're made
    PogResultMessage,                 # ✅ Report Proof of GPU test results
    MinerDiscoveryMessage,            # 🔍 Announce new miners joining the network
]
