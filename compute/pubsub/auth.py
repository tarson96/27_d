"""
Authentication providers for SN27 Validator Pub/Sub communication.

This module provides authentication classes for different credential sources,
including the validator-token-gateway authentication flow.
"""

import logging
import requests
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials

from .exceptions import AuthenticationError, ConfigurationError


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

        self.jwt_token: Optional[str] = None
        self.pubsub_token: Optional[str] = None
        self._credentials: Optional[Credentials] = None

    def _get_network_config(self) -> Dict[str, str]:
        """Get domain and project ID for current network."""
        if self.config.subtensor.network == "finney":
            return {
                "domain": "https://validator-token-gateway-auth-production-pufph5srwa-uc.a.run.app",
                "project_id": "ni-sn27-frontend"
            }
        else:
            return {
                "domain": "https://validator-token-gateway-auth-development-pufph5srwa-uc.a.run.app",
                "project_id": "ni-sn27-frontend-dev"
            }

    def _authenticate_validator_gateway(self) -> Optional[str]:
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
                headers={"Authorization": auth_header}
            )
            response.raise_for_status()
            jwt_token = response.json().get("access_token")
            self.logger.info(f"Successfully authenticated with validator-token-gateway on {self.config.subtensor.network} network")
            return jwt_token
        except Exception as e:
            self.logger.error(f"Failed to authenticate with validator-token-gateway: {e}")
            raise AuthenticationError(f"Failed to authenticate with validator-token-gateway: {e}")

    def _get_pubsub_token(self) -> Optional[str]:
        """Get Google Cloud Pub/Sub impersonation token."""
        if not self.jwt_token:
            raise AuthenticationError("Cannot get Pub/Sub token: No JWT token available")

        # Get domain for current network
        network_config = self._get_network_config()
        domain = network_config["domain"]

        try:
            response = requests.post(
                f"{domain}/auth/pubsub-token",
                headers={"Authorization": f"Bearer {self.jwt_token}"}
            )
            response.raise_for_status()
            pubsub_token = response.json().get("access_token")
            self.logger.info(f"Successfully obtained Pub/Sub impersonation token for {self.config.subtensor.network} network")
            return pubsub_token
        except Exception as e:
            self.logger.error(f"Failed to get Pub/Sub token: {e}")
            raise AuthenticationError(f"Failed to get Pub/Sub token: {e}")

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
            raise AuthenticationError(f"Failed to create credentials: {e}")

    def get_project_id(self) -> str:
        """Get the project ID for the current network."""
        network_config = self._get_network_config()
        return network_config["project_id"]

    def refresh_tokens(self) -> None:
        """Refresh authentication tokens."""
        self.logger.info("Refreshing validator-token-gateway tokens")
        self.get_credentials(refresh=True)
