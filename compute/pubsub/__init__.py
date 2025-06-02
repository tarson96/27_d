"""
SN27 Validator Pub/Sub Library

A Python library for bittensor validators to communicate with the SN27 backend
via GCP Pub/Sub API. This library provides type-safe message creation and
publishing capabilities for validator-side operations.

Usage:
    # For validators using validator-token-gateway authentication:
    from compute.pubsub import ValidatorGatewayPubSubClient, MessageFactory

    client = ValidatorGatewayPubSubClient(wallet=wallet, config=config)
    factory = MessageFactory(validator_hotkey=wallet.hotkey.ss58_address)

    # Publish new miner discovery
    message = factory.create_new_miner_discovery(
        miner_hotkey="miner123",
        gpu_specs={"model": "RTX 4090", "vram_gb": 24, "cpu_cores": 16, "ram_gb": 64}
    )
    await client.publish_to_miner_events(message)

    # Subscribe to messages
    await client.subscribe_to_messages_topic()

    # For standard service account authentication:
    from compute.pubsub import ValidatorPubSubClient, MessageFactory

    client = ValidatorPubSubClient(
        project_id="your-project-id",
        credentials_path="path/to/credentials.json"
    )
    # ... same usage as above
"""

from .client import ValidatorPubSubClient
from .validator_gateway_client import ValidatorGatewayPubSubClient
from .auth import ValidatorGatewayAuth
from .message_factory import MessageFactory

from .message_types import *
from .exceptions import PubSubError, MessageValidationError, PublishError

__version__ = "1.0.0"
__author__ = "SN27 Team"

__all__ = [
    "ValidatorPubSubClient",
    "ValidatorGatewayPubSubClient",
    "ValidatorGatewayAuth",
    "MessageFactory",

    "PubSubError",
    "MessageValidationError",
    "PublishError",
    # Message types (4 core messages)
    "BasePubSubMessage",
    "ValidatorStatusMessage",        # 📊 Periodic health and performance reporting
    "AllocationRequestMessage",      # 🎯 Track allocation requests before they're made
    "PogResultMessage",              # ✅ Report Proof of GPU test results
    "MinerDiscoveryMessage",         # 🔍 Announce new miners joining the network
    "TOPICS",
    "MESSAGE_TYPES",
]
