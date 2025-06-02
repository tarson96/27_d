"""
Validator Pub/Sub Helper Library

This module provides utilities for SN27 validators to publish messages
to the backend via Google Cloud Pub/Sub.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

import psutil
from google.cloud import pubsub_v1


class ValidatorPubSubClient:
    """Client for publishing validator messages to Google Cloud Pub/Sub."""

    def __init__(
        self,
        project_id: str,
        topic_name: str = "validator-messages",
        credentials_path: Optional[str] = None
    ):
        """
        Initialize the Pub/Sub client.

        Args:
            project_id: Google Cloud project ID
            topic_name: Pub/Sub topic name for validator messages
            credentials_path: Path to service account key file (optional)
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self.logger = logging.getLogger(__name__)

        # Set up credentials if provided
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

        # Initialize publisher client
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(project_id, topic_name)

        self.logger.info(f"Initialized Validator Pub/Sub client for topic: {self.topic_path}")

    def create_base_message(
        self,
        message_type: str,
        validator_hotkey: str,
        data: Dict[str, Any],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Create a base message structure."""
        return {
            "messageType": message_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "validator",
            "priority": priority,
            "correlationId": f"{message_type}_{validator_hotkey}_{int(time.time())}",
            "data": data
        }

    def publish_message(self, message: Dict[str, Any]) -> str:
        """
        Publish a message to Pub/Sub.

        Args:
            message: Message dictionary to publish

        Returns:
            Message ID from Pub/Sub
        """
        try:
            # Convert message to JSON
            message_json = json.dumps(message)
            message_bytes = message_json.encode('utf-8')

            # Create attributes for message routing
            attributes = {
                "messageType": message["messageType"],
                "source": message["source"],
                "validatorHotkey": message["data"].get("validator_hotkey", ""),
                "timestamp": message["timestamp"]
            }

            # Publish message
            future = self.publisher.publish(
                self.topic_path,
                message_bytes,
                **attributes
            )

            message_id = future.result()
            self.logger.info(f"Published {message['messageType']} message with ID: {message_id}")
            return message_id

        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            raise

    def publish_validator_status(
        self,
        validator_hotkey: str,
        version: str,
        current_block: int,
        active_allocations: int,
        performance_metrics: Dict[str, float],
        status: str = "online"
    ) -> str:
        """
        Publish validator status message.

        Args:
            validator_hotkey: Validator's hotkey
            version: Validator software version
            current_block: Current blockchain block number
            active_allocations: Number of active allocations
            performance_metrics: Performance metrics dictionary
            status: Validator status (online, maintenance, syncing)

        Returns:
            Message ID from Pub/Sub
        """
        # Get system resource usage
        resource_usage = self._get_resource_usage()

        data = {
            "validator_hotkey": validator_hotkey,
            "status": status,
            "version": version,
            "current_block": current_block,
            "active_allocations": active_allocations,
            "performance_metrics": performance_metrics,
            "resource_usage": resource_usage
        }

        message = self.create_base_message(
            "validator_status",
            validator_hotkey,
            data,
            priority="low"
        )

        return self.publish_message(message)

    def publish_allocation_request(
        self,
        validator_hotkey: str,
        miner_hotkey: str,
        allocation_uuid: str,
        request_type: str = "pog_test",
        device_requirements: Optional[Dict[str, Any]] = None,
        expected_duration_minutes: int = 10,
        priority: str = "normal"
    ) -> str:
        """
        Publish allocation request message.

        Args:
            validator_hotkey: Validator's hotkey
            miner_hotkey: Target miner's hotkey
            allocation_uuid: Unique allocation identifier
            request_type: Type of allocation request
            device_requirements: Required device specifications
            expected_duration_minutes: Expected allocation duration
            priority: Request priority

        Returns:
            Message ID from Pub/Sub
        """
        if device_requirements is None:
            device_requirements = {
                "gpu_count": 1,
                "min_vram_gb": 4,
                "cpu_cores": 1,
                "ram_gb": 1,
                "storage_gb": 1
            }

        data = {
            "validator_hotkey": validator_hotkey,
            "miner_hotkey": miner_hotkey,
            "allocation_uuid": allocation_uuid,
            "request_type": request_type,
            "device_requirements": device_requirements,
            "expected_duration_minutes": expected_duration_minutes,
            "priority": priority,
            "requested_at": datetime.utcnow().isoformat() + "Z"
        }

        message = self.create_base_message(
            "allocation_request",
            validator_hotkey,
            data,
            priority=priority
        )

        return self.publish_message(message)

    def publish_pog_result(
        self,
        validator_hotkey: str,
        miner_hotkey: str,
        test_id: str,
        result: str,
        gpu_specs: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None
    ) -> str:
        """
        Publish PoG result message.

        Args:
            validator_hotkey: Validator's hotkey
            miner_hotkey: Tested miner's hotkey
            test_id: Unique test identifier
            result: Test result (success, failure, timeout, error)
            gpu_specs: GPU specifications discovered during test
            performance_metrics: Performance metrics from test
            error_details: Error details if test failed

        Returns:
            Message ID from Pub/Sub
        """
        data = {
            "validator_hotkey": validator_hotkey,
            "miner_hotkey": miner_hotkey,
            "test_id": test_id,
            "result": result,
            "tested_at": datetime.utcnow().isoformat() + "Z"
        }

        if gpu_specs:
            data["gpu_specs"] = gpu_specs

        if performance_metrics:
            data["performance_metrics"] = performance_metrics

        if error_details:
            data["error_details"] = error_details

        message = self.create_base_message(
            "pog_result",
            validator_hotkey,
            data,
            priority="normal"
        )

        return self.publish_message(message)

    def publish_miner_discovery(
        self,
        validator_hotkey: str,
        miner_hotkey: str,
        initial_specs: Optional[Dict[str, Any]] = None,
        network_info: Optional[Dict[str, Any]] = None,
        registration_block: Optional[int] = None
    ) -> str:
        """
        Publish miner discovery message.

        Args:
            validator_hotkey: Validator's hotkey
            miner_hotkey: Discovered miner's hotkey
            initial_specs: Initial GPU specifications
            network_info: Network connection information
            registration_block: Block number when miner was registered

        Returns:
            Message ID from Pub/Sub
        """
        data = {
            "validator_hotkey": validator_hotkey,
            "miner_hotkey": miner_hotkey,
            "discovered_at": datetime.utcnow().isoformat() + "Z"
        }

        if initial_specs:
            data["initial_specs"] = initial_specs

        if network_info:
            data["network_info"] = network_info

        if registration_block:
            data["registration_block"] = registration_block

        message = self.create_base_message(
            "miner_discovery",
            validator_hotkey,
            data,
            priority="normal"
        )

        return self.publish_message(message)

    def publish_gpu_status_change(
        self,
        validator_hotkey: str,
        miner_hotkey: str,
        allocation_uuid: Optional[str],
        previous_status: str,
        current_status: str,
        reason: Optional[str] = None
    ) -> str:
        """
        Publish GPU status change message.

        Args:
            validator_hotkey: Validator's hotkey
            miner_hotkey: Miner's hotkey
            allocation_uuid: Allocation UUID (if applicable)
            previous_status: Previous status
            current_status: Current status
            reason: Reason for status change

        Returns:
            Message ID from Pub/Sub
        """
        data = {
            "validator_hotkey": validator_hotkey,
            "miner_hotkey": miner_hotkey,
            "previous_status": previous_status,
            "current_status": current_status,
            "status_change_at": datetime.utcnow().isoformat() + "Z"
        }

        if allocation_uuid:
            data["allocation_uuid"] = allocation_uuid

        if reason:
            data["reason"] = reason

        message = self.create_base_message(
            "validator_gpu_status_change",
            validator_hotkey,
            data,
            priority="normal"
        )

        return self.publish_message(message)

    def publish_gpu_deallocation(
        self,
        validator_hotkey: str,
        miner_hotkey: str,
        allocation_uuid: str,
        deallocation_reason: str,
        gpu_model: Optional[str] = None,
        allocation_duration_minutes: Optional[int] = None
    ) -> str:
        """
        Publish GPU deallocation message.

        Args:
            validator_hotkey: Validator's hotkey
            miner_hotkey: Miner's hotkey
            allocation_uuid: Allocation UUID
            deallocation_reason: Reason for deallocation
            gpu_model: GPU model name
            allocation_duration_minutes: Duration of allocation

        Returns:
            Message ID from Pub/Sub
        """
        data = {
            "validator_hotkey": validator_hotkey,
            "miner_hotkey": miner_hotkey,
            "allocation_uuid": allocation_uuid,
            "deallocated_at": datetime.utcnow().isoformat() + "Z",
            "deallocation_reason": deallocation_reason
        }

        if gpu_model:
            data["gpu_model"] = gpu_model

        if allocation_duration_minutes:
            data["allocation_duration_minutes"] = allocation_duration_minutes

        message = self.create_base_message(
            "validator_gpu_deallocation",
            validator_hotkey,
            data,
            priority="high"
        )

        return self.publish_message(message)

    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current system resource usage."""
        try:
            return {
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        except Exception as e:
            self.logger.warning(f"Failed to get resource usage: {e}")
            return {
                "cpu_usage_percent": 0.0,
                "memory_usage_percent": 0.0,
                "disk_usage_percent": 0.0
            }


def create_validator_pubsub_client() -> ValidatorPubSubClient:
    """Create a validator pub/sub client from environment variables."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
    topic_name = os.getenv('VALIDATOR_MESSAGES_TOPIC', 'validator-messages')
    credentials_path = os.getenv('GOOGLE_CLOUD_KEY_FILE')

    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable is required")

    return ValidatorPubSubClient(
        project_id=project_id,
        topic_name=topic_name,
        credentials_path=credentials_path
    )
