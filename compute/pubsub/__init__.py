"""
SN27 Pub/Sub Library

A Python library for bittensor validators to communicate with the SN27 backend
via GCP Pub/Sub API. This library provides type-safe message creation and
publishing capabilities for validator-side operations.

Usage:
    # For validators using SN27 token gateway authentication:
    from compute.pubsub import PubSubClient, MessageFactory

    client = PubSubClient(wallet=wallet, config=config)
    factory = MessageFactory(validator_hotkey=wallet.hotkey.ss58_address)

    # Publish new miner discovery
    message = factory.create_new_miner_discovery(
        miner_hotkey="miner123",
        gpu_specs={"model": "RTX 4090", "vram_gb": 24, "cpu_cores": 16, "ram_gb": 64}
    )
    await client.publish_to_miner_events(message)

    # Subscribe to messages
    await client.subscribe_to_messages_topic()
"""

from .client import PubSubClient
from .auth import SN27TokenAuth
from .message_factory import MessageFactory

from .message_types import (
    BasePubSubMessage,
    MinerAllocationMessage,
    MinerDeallocationMessage,
    PogResultMessage,
    TOPICS,
    MESSAGE_TYPES,
)
from .exceptions import PubSubError, MessageValidationError, PublishError

__version__ = "1.0.0"
__author__ = "SN27 Team"

__all__ = [
    "PubSubClient",
    "SN27TokenAuth",
    "MessageFactory",

    "PubSubError",
    "MessageValidationError",
    "PublishError",
    # Message types (4 core messages)
    "BasePubSubMessage",
    "MinerAllocationMessage",           # Announce validator allocated miner
    "MinerDeallocationMessage",         # Announce validator deallocated miner
    "PogResultMessage",                 # Report Proof of GPU test results
    "TOPICS",
    "MESSAGE_TYPES",
]
