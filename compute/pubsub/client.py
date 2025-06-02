"""
GCP Pub/Sub client for SN27 validator communication.

This module provides an async client class for publishing messages
to GCP Pub/Sub topics from validators using service account credentials.
"""

import json
import logging
from typing import Optional, Dict, Any
from google.cloud import pubsub_v1
from google.oauth2 import service_account

from .message_types import (
    BasePubSubMessage,
    ValidatorMessage,
    TOPICS,
)
from .exceptions import (
    PublishError,
    AuthenticationError,
    TopicNotFoundError,
    ConfigurationError,
)


class ValidatorPubSubClient:
    """
    GCP Pub/Sub client for validator-backend communication.

    This client handles publishing messages from validators to the SN27 backend
    via GCP Pub/Sub topics.
    """

    def __init__(
        self,
        project_id: str,
        credentials_path: Optional[str] = None,
        credentials_dict: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the Pub/Sub client.

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON file
            credentials_dict: Service account credentials as dict
            timeout: Timeout for publish operations in seconds

        Raises:
            ConfigurationError: If configuration is invalid
            AuthenticationError: If authentication fails
        """
        self.project_id = project_id
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        if not project_id:
            raise ConfigurationError("project_id is required")

        try:
            # Initialize credentials
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
            elif credentials_dict:
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict
                )
            else:
                # Use default credentials (e.g., from environment)
                credentials = None

            # Initialize publisher client
            self.publisher = pubsub_v1.PublisherClient(credentials=credentials)

            # Cache topic paths
            self._topic_paths = {
                TOPICS.ALLOCATION_EVENTS: self.publisher.topic_path(project_id, TOPICS.ALLOCATION_EVENTS),
                TOPICS.MINER_EVENTS: self.publisher.topic_path(project_id, TOPICS.MINER_EVENTS),
                TOPICS.SYSTEM_EVENTS: self.publisher.topic_path(project_id, TOPICS.SYSTEM_EVENTS),
                TOPICS.VALIDATION_EVENTS: self.publisher.topic_path(project_id, TOPICS.VALIDATION_EVENTS),
            }

        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Pub/Sub client: {e}")

    async def _publish_message(
        self,
        topic_name: str,
        message: BasePubSubMessage,
    ) -> str:
        """
        Publish a message to the specified topic.

        Args:
            topic_name: Name of the topic to publish to
            message: Message to publish

        Returns:
            Message ID of the published message

        Raises:
            PublishError: If publishing fails
            TopicNotFoundError: If topic doesn't exist
        """
        try:
            topic_path = self._topic_paths.get(topic_name)
            if not topic_path:
                raise TopicNotFoundError(f"Topic {topic_name} not found")

            # Convert message to JSON
            message_data = json.dumps(message.to_dict()).encode('utf-8')

            # Prepare message attributes
            attributes = {
                'messageType': message.message_type,
                'timestamp': message.timestamp,
                'source': message.source,
            }

            if message.priority and message.priority != 'normal':
                attributes['priority'] = message.priority

            if message.correlation_id:
                attributes['correlation_id'] = message.correlation_id

            # Publish message
            future = self.publisher.publish(
                topic_path,
                data=message_data,
                **attributes
            )

            # Wait for publish to complete
            message_id = future.result(timeout=self.timeout)

            self.logger.info(
                f"Published {message.message_type} message to {topic_name} with ID: {message_id}"
            )

            return message_id

        except Exception as e:
            error_msg = f"Failed to publish message to {topic_name}: {e}"
            self.logger.error(error_msg)
            raise PublishError(error_msg)

    async def publish_to_miner_events(self, message: ValidatorMessage) -> str:
        """
        Publish a message to the miner-events topic.

        Args:
            message: Message to publish

        Returns:
            Message ID
        """
        return await self._publish_message(TOPICS.MINER_EVENTS, message)

    async def publish_to_validation_events(self, message: ValidatorMessage) -> str:
        """
        Publish a message to the validation-events topic.

        Args:
            message: Message to publish

        Returns:
            Message ID
        """
        return await self._publish_message(TOPICS.VALIDATION_EVENTS, message)

    async def publish_to_allocation_events(self, message: ValidatorMessage) -> str:
        """
        Publish a message to the allocation-events topic.

        Args:
            message: Message to publish

        Returns:
            Message ID
        """
        return await self._publish_message(TOPICS.ALLOCATION_EVENTS, message)

    async def publish_to_system_events(self, message: ValidatorMessage) -> str:
        """
        Publish a message to the system-events topic.

        Args:
            message: Message to publish

        Returns:
            Message ID
        """
        return await self._publish_message(TOPICS.SYSTEM_EVENTS, message)

    def close(self):
        """Close the publisher client."""
        if hasattr(self, 'publisher'):
            self.publisher.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()
