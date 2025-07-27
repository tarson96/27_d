"""
Authentication providers for SN27 Validator Pub/Sub communication.

This module provides authentication classes for different credential sources,
including the validator-token-gateway authentication flow.
"""

import logging
import requests
from google.oauth2.credentials import Credentials

from .exceptions import AuthenticationError


class ValidatorGatewayAuth:
    """
    Authentication provider for validator-token-gateway based credentials.

    This class handles the full authentication flow for validators:
    1. Authenticate with validator-token-gateway using signed message
    2. Get pubsub impersonation token using JWT
    3. Create OAuth2 credentials for pubsub clients
    """

    def __init__(self, wallet, config):
        """
        Initialize the validator gateway auth provider.

        Args:
            wallet: Bittensor wallet instance with hotkey for signing
            config: Validator config containing network information
        """
        self.wallet = wallet
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.jwt_token: str | None = None
        self.pubsub_token: str | None = None
        self._credentials: Credentials | None = None

    def _get_network_config(self) -> dict:
        """Get domain and project ID for current network."""
        if self.config.subtensor.network == "finney":
            project_id = "ni-sn27-frontend-prod"
            env = "production"
        else:
            project_id = "ni-sn27-frontend-dev"
            env = "development"
        return {
            "domain": f"https://us-central1-{project_id}.cloudfunctions.net/validator-token-gateway-auth-{env}",
            "project_id": project_id
        }

    def _authenticate_validator_gateway(self) -> str | None:
        """Authenticate with validator-token-gateway to get JWT token."""
        try:
            # Message to sign
            message = f"Authenticate to Bittensor Subnet {self.config.netuid}"
            # Sign the message with validator's hotkey
            signature = self.wallet.hotkey.sign(message).hex()

            # Get domain for current network
            network_config = self._get_network_config()
            domain = network_config["domain"]

            # Create authorization header
            auth_header = f"Bittensor {self.wallet.hotkey.ss58_address}:{signature}"

            response = requests.post(
                f"{domain}/auth/token",
                headers={"Authorization": auth_header},
                timeout=30
            )
            response.raise_for_status()
            jwt_token = response.json().get("access_token")
            self.logger.info(
                "Successfully authenticated with validator-token-gateway on %s network",
                self.config.subtensor.network
            )
            return jwt_token
        except Exception as e:
            self.logger.error("Failed to authenticate with validator-token-gateway: %s", e)
            raise AuthenticationError(f"Failed to authenticate with validator-token-gateway: {e}") from e

    def _get_pubsub_token(self) -> str | None:
        """Get Google Cloud Pub/Sub impersonation token."""
        if not self.jwt_token:
            raise AuthenticationError("Cannot get Pub/Sub token: No JWT token available")

        # Get domain for current network
        network_config = self._get_network_config()
        domain = network_config["domain"]

        try:
            response = requests.post(
                f"{domain}/auth/pubsub-token",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                timeout=30
            )
            response.raise_for_status()
            pubsub_token = response.json().get("access_token")
            self.logger.info(
                "Successfully obtained Pub/Sub impersonation token for %s network",
                self.config.subtensor.network
            )
            return pubsub_token
        except Exception as e:
            self.logger.error("Failed to get Pub/Sub token: %s", e)
            raise AuthenticationError(f"Failed to get Pub/Sub token: {e}") from e

    def get_credentials(self, refresh: bool = False) -> Credentials:
        """
        Get OAuth2 credentials for pubsub clients.

        Args:
            refresh: Whether to refresh tokens even if they exist

        Returns:
            OAuth2 credentials for pubsub clients
        """
        if self._credentials and not refresh:
            return self._credentials

        try:
            # Get fresh tokens
            self.jwt_token = self._authenticate_validator_gateway()
            self.pubsub_token = self._get_pubsub_token()

            # Create OAuth2 credentials
            self._credentials = Credentials(
                token=self.pubsub_token,
                scopes=["https://www.googleapis.com/auth/pubsub"]
            )

            return self._credentials
        except Exception as e:
            raise AuthenticationError(f"Failed to create credentials: {e}") from e

    def get_project_id(self) -> str:
        """Get the project ID for the current network."""
        network_config = self._get_network_config()
        return network_config["project_id"]

    def refresh_tokens(self) -> None:
        """Refresh authentication tokens."""
        self.logger.info("Refreshing validator-token-gateway tokens")
        self.get_credentials(refresh=True)
