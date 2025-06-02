"""
Message factory for creating type-safe pub/sub messages.

This module provides a convenient factory class for creating properly
formatted messages for validator-backend communication.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from .message_types import (
    MinerDiscoveryMessage,
    PogResultMessage,
    AllocationRequestMessage,
    ValidatorStatusMessage,
    GpuSpecs,
    NetworkInfo,
    BenchmarkData,
    PerformanceMetrics,
    DeviceRequirements,
)


class MessageFactory:
    """Factory class for creating pub/sub messages with proper formatting."""

    def __init__(self, validator_hotkey: str):
        """
        Initialize the message factory.

        Args:
            validator_hotkey: The hotkey of the validator creating messages
        """
        self.validator_hotkey = validator_hotkey

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        return datetime.utcnow().isoformat() + "Z"

    def create_miner_discovery(
        self,
        miner_hotkey: str,
        gpu_specs: Dict[str, Any],
        network_info: Optional[Dict[str, Any]] = None,
        registration_block: Optional[int] = None,
        initial_benchmark_score: Optional[float] = None,
        discovered_at: Optional[datetime] = None,
    ) -> MinerDiscoveryMessage:
        """
        Create a new miner discovery message.

        Args:
            miner_hotkey: The hotkey of the discovered miner
            gpu_specs: GPU specifications dict with keys: model, vram_gb, cpu_cores, ram_gb
            network_info: Optional network info dict with keys: ip_address, port, region
            initial_benchmark_score: Optional initial benchmark score
            discovered_at: Optional discovery timestamp (defaults to now)

        Returns:
            NewMinerDiscoveryMessage instance
        """
        gpu_specs_obj = GpuSpecs(
            model=gpu_specs["model"],
            vram_gb=gpu_specs["vram_gb"],
            cpu_cores=gpu_specs["cpu_cores"],
            ram_gb=gpu_specs["ram_gb"],
        )

        network_info_obj = NetworkInfo(
            ip_address=network_info.get("ip_address") if network_info else None,
            port=network_info.get("port") if network_info else None,
            region=network_info.get("region") if network_info else None,
        )

        discovered_timestamp = (discovered_at or datetime.utcnow()).isoformat() + "Z"

        return MinerDiscoveryMessage(
            validator_hotkey=self.validator_hotkey,
            miner_hotkey=miner_hotkey,
            discovered_at=discovered_timestamp,
            gpu_specs=gpu_specs_obj,
            network_info=network_info_obj,
            registration_block=registration_block,
            initial_benchmark_score=initial_benchmark_score,
            message_type="",  # Will be set in __post_init__
            timestamp=self._get_timestamp(),
            source="validator",
        )



    def create_pog_result(
        self,
        miner_hotkey: str,
        request_id: str,
        result: str,
        validation_duration_seconds: float,
        score: Optional[float] = None,
        benchmark_data: Optional[Dict[str, float]] = None,
        error_details: Optional[str] = None,
    ) -> PogResultMessage:
        """
        Create a PoG result message.

        Args:
            miner_hotkey: The hotkey of the validated miner
            request_id: The request ID from the original PoG request
            result: Result of validation ("success", "failure", "timeout", "error")
            validation_duration_seconds: How long the validation took
            score: Optional validation score
            benchmark_data: Optional benchmark data dict
            error_details: Optional error details if result was error/failure

        Returns:
            PogResultMessage instance
        """
        benchmark_obj = None
        if benchmark_data:
            benchmark_obj = BenchmarkData(
                gpu_utilization=benchmark_data["gpu_utilization"],
                memory_usage=benchmark_data["memory_usage"],
                compute_performance=benchmark_data["compute_performance"],
                network_latency=benchmark_data["network_latency"],
            )

        return PogResultMessage(
            validator_hotkey=self.validator_hotkey,
            miner_hotkey=miner_hotkey,
            request_id=request_id,
            result=result,
            validation_duration_seconds=validation_duration_seconds,
            score=score,
            benchmark_data=benchmark_obj,
            error_details=error_details,
            message_type="",  # Will be set in __post_init__
            timestamp=self._get_timestamp(),
            source="validator",
        )



    def create_validator_status(
        self,
        status: str,
        version: str,
        active_validations: int,
        last_sync_block: Optional[int] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
    ) -> ValidatorStatusMessage:
        """
        Create a validator status message.

        Args:
            status: Validator status ("online", "offline", "maintenance", "syncing")
            version: Current validator version
            active_validations: Number of active validations
            last_sync_block: Optional last synced block number
            performance_metrics: Optional performance metrics dict

        Returns:
            ValidatorStatusMessage instance
        """
        metrics_obj = None
        if performance_metrics:
            metrics_obj = PerformanceMetrics(
                avg_response_time_ms=performance_metrics["avg_response_time_ms"],
                success_rate_percentage=performance_metrics["success_rate_percentage"],
                uptime_percentage=performance_metrics["uptime_percentage"],
            )

        return ValidatorStatusMessage(
            validator_hotkey=self.validator_hotkey,
            status=status,
            version=version,
            active_validations=active_validations,
            last_sync_block=last_sync_block,
            performance_metrics=metrics_obj,
            message_type="",  # Will be set in __post_init__
            timestamp=self._get_timestamp(),
            source="validator",
        )

    def create_allocation_request(
        self,
        miner_hotkey: str,
        allocation_uuid: str,
        request_type: str = "pog_test",
        device_requirements: Optional[Dict[str, Any]] = None,
        expected_duration_minutes: int = 10,
        priority: str = "normal",
    ) -> AllocationRequestMessage:
        """
        Create an allocation request message.

        Args:
            miner_hotkey: The hotkey of the target miner
            allocation_uuid: Unique allocation identifier
            request_type: Type of allocation request
            device_requirements: Required device specifications
            expected_duration_minutes: Expected allocation duration
            priority: Request priority

        Returns:
            AllocationRequestMessage instance
        """
        device_req_obj = None
        if device_requirements:
            device_req_obj = DeviceRequirements(
                gpu_count=device_requirements.get("gpu_count", 1),
                min_vram_gb=device_requirements.get("min_vram_gb", 4),
                cpu_cores=device_requirements.get("cpu_cores", 1),
                ram_gb=device_requirements.get("ram_gb", 1),
                storage_gb=device_requirements.get("storage_gb", 1),
            )

        return AllocationRequestMessage(
            validator_hotkey=self.validator_hotkey,
            miner_hotkey=miner_hotkey,
            allocation_uuid=allocation_uuid,
            request_type=request_type,
            device_requirements=device_req_obj,
            expected_duration_minutes=expected_duration_minutes,
            message_type="",  # Will be set in __post_init__
            timestamp=self._get_timestamp(),
            source="validator",
            priority=priority,
        )
