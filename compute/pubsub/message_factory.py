"""
Message factory for creating type-safe pub/sub messages.

This module provides a convenient factory class for creating properly
formatted messages for validator-backend communication.
"""

from datetime import datetime

from .message_types import (
    MinerAllocationMessage,
    MinerDeallocationMessage,
    # MinerDiscoveryMessage,
    PogResultMessage,
    # GpuSpecs,
    # NetworkInfo,
    BenchmarkData,
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

    # def create_miner_discovery(
    #     self,
    #     miner_hotkey: str,
    #     gpu_specs: dict,
    #     network_info: dict | None = None,
    #     registration_block: int | None = None,
    #     initial_benchmark_score: float | None = None,
    #     discovered_at: datetime | None = None,
    # ) -> MinerDiscoveryMessage:
    #     """
    #     Create a new miner discovery message.

    #     Args:
    #         miner_hotkey: The hotkey of the discovered miner
    #         gpu_specs: GPU specifications dict with keys: model, vram_gb, cpu_cores, ram_gb
    #         network_info: Optional network info dict with keys: ip_address, port, region
    #         initial_benchmark_score: Optional initial benchmark score
    #         discovered_at: Optional discovery timestamp (defaults to now)

    #     Returns:
    #         NewMinerDiscoveryMessage instance
    #     """
    #     gpu_specs_obj = GpuSpecs(
    #         model=gpu_specs["model"],
    #         vram_gb=gpu_specs["vram_gb"],
    #         cpu_cores=gpu_specs["cpu_cores"],
    #         ram_gb=gpu_specs["ram_gb"],
    #     )

    #     network_info_obj = NetworkInfo(
    #         ip_address=network_info.get("ip_address") if network_info else None,
    #         port=network_info.get("port") if network_info else None,
    #         region=network_info.get("region") if network_info else None,
    #     )

    #     discovered_timestamp = (discovered_at or datetime.utcnow()).isoformat() + "Z"

    #     return MinerDiscoveryMessage(
    #         validator_hotkey=self.validator_hotkey,
    #         miner_hotkey=miner_hotkey,
    #         discovered_at=discovered_timestamp,
    #         gpu_specs=gpu_specs_obj,
    #         network_info=network_info_obj,
    #         registration_block=registration_block,
    #         initial_benchmark_score=initial_benchmark_score,
    #         message_type="",  # Will be set in __post_init__
    #         timestamp=self._get_timestamp(),
    #         source="validator",
    #     )

    def create_pog_result(
        self,
        miner_hotkey: str,
        request_id: str,
        result: str,
        validation_duration_seconds: float,
        score: float | None = None,
        benchmark_data: dict | None = None,
        error_details: str | None = None,
        health_check_result: bool | None = None,
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
            health_check_result=health_check_result,
        )

    def create_miner_deallocation(
        self,
        miner_hotkey: str,
        retry_count: int | None = None,
        deallocation_result: bool | None = None,
        deallocation_error: str | None = None,
    ) -> MinerDeallocationMessage:
        """
        Create a Miner deallocation message.

        Args:
            miner_hotkey: The hotkey of the deallocated miner
            retry_count: Optional retry count
            deallocation_result: Optional deallocation result
            deallocation_error: Optional deallocation error

        Returns:
            MinerDeallocationMessage instance
        """
        return MinerDeallocationMessage(
            validator_hotkey=self.validator_hotkey,
            miner_hotkey=miner_hotkey,
            retry_count=retry_count,
            deallocation_result=deallocation_result,
            deallocation_error=deallocation_error,
        )

    def create_miner_allocation(
        self,
        miner_hotkey: str,
        allocation_result: bool | None = None,
        allocation_error: str | None = None,
    ) -> MinerAllocationMessage:
        """
        Create a Miner allocation message.

        Args:
            miner_hotkey: The hotkey of the deallocated miner
            allocation_result: Optional allocation result
            allocation_error: Optional allocation error

        Returns:
            MinerAllocationMessage instance
        """
        return MinerAllocationMessage(
            validator_hotkey=self.validator_hotkey,
            miner_hotkey=miner_hotkey,
            allocation_result=allocation_result,
            allocation_error=allocation_error,
        )
