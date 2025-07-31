"""
Message type definitions for SN27 Validator Pub/Sub communication.

This module contains all the message schemas and constants used for
communication between validators and the SN27 backend.
"""

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
    # Validator → Backend messages (4 core messages)
    POG_RESULT = "pog_result"
    MINER_ALLOCATION = "miner_allocation"
    MINER_DEALLOCATION = "miner_deallocation"
    MINER_DISCOVERY = "miner_discovery"


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

# Validator → Backend message types


# @dataclass
# class GpuSpecs:
#     model: str
#     vram_gb: int
#     cpu_cores: int
#     ram_gb: int


# @dataclass
# class NetworkInfo:
#     ip_address: str | None = None
#     port: int | None = None
#     region: str | None = None


# @dataclass
# class MinerDiscoveryMessage(BasePubSubMessage):
#     # Required fields first
#     validator_hotkey: str = field(default_factory=str)
#     miner_hotkey: str = field(default_factory=str)
#     discovered_at: str = field(default_factory=str)
#     gpu_specs: GpuSpecs = field(default_factory=GpuSpecs)
#     network_info: NetworkInfo = field(default_factory=NetworkInfo)
#     # Optional fields last
#     registration_block: int | None = None
#     initial_benchmark_score: float | None = None

#     def __post_init__(self):
#         self.message_type = MESSAGE_TYPES.MINER_DISCOVERY
#         self.source = "validator"
#         self.data = {
#             "validator_hotkey": self.validator_hotkey,
#             "miner_hotkey": self.miner_hotkey,
#             "discovered_at": self.discovered_at,
#             "gpu_specs": {
#                 "model": self.gpu_specs.model,
#                 "vram_gb": self.gpu_specs.vram_gb,
#                 "cpu_cores": self.gpu_specs.cpu_cores,
#                 "ram_gb": self.gpu_specs.ram_gb,
#             },
#             "network_info": {
#                 "ip_address": self.network_info.ip_address,
#                 "port": self.network_info.port,
#                 "region": self.network_info.region,
#             },
#         }
#         if self.registration_block is not None:
#             self.data["registration_block"] = self.registration_block
#         if self.initial_benchmark_score is not None:
#             self.data["initial_benchmark_score"] = self.initial_benchmark_score


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
        self.source = "validator"
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
        self.source = "validator"
        self.data = {
            "validator_hotkey": self.validator_hotkey,
            "miner_hotkey": self.miner_hotkey,
        }
        if self.allocation_result:
            self.data['allocation_result'] = self.allocation_result
        if self.allocation_error:
            self.data['allocation_error'] = self.allocation_error


# Union type for all validator messages (3 core messages)
# PogResultMessage,                 # Report Proof of GPU test results
# MinerDiscoveryMessage,            # Announce new miners joining the network
# MinerDeallocationMessage,         # Announce validator deallocated miner
# MinerAllocationMessage,           # Announce validator allocated miner
ValidatorMessage = PogResultMessage | MinerDeallocationMessage | MinerAllocationMessage
