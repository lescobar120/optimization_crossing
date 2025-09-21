# custom_bloomberg_auth.py
"""
Custom Bloomberg OAuth Device Flow Authentication

This module provides a direct implementation of Bloomberg's OAuth device flow
without requiring the bloomberg.enterprise.oauth package.
"""

from __future__ import annotations
import time
import json
import logging
from typing import Dict, Optional, Tuple
import httpx


logger = logging.getLogger(__name__)


def _form_headers() -> Dict[str, str]:
    """Standard form headers for OAuth requests."""
    return {"Content-Type": "application/x-www-form-urlencoded"}


def _extract_oauth_error(resp: httpx.Response) -> str:
    """Extract error message from OAuth response."""
    try:
        j = resp.json()
        return j.get("error_description") or j.get("error") or resp.text[:300]
    except Exception:
        return resp.text[:300]


class CustomDeviceOAuth:
    """
    Custom OAuth Device Code implementation for Bloomberg API.
    
    Replaces bloomberg.enterprise.oauth with direct HTTP implementation.
    Provides device flow authentication with user code display capability.
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize OAuth client.
        
        Args:
            client_id: Bloomberg OAuth client ID
            client_secret: Bloomberg OAuth client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Bloomberg OAuth endpoints
        self.url_auth = "https://bsso.blpprofessional.com/as/device_authz.oauth2"
        self.url_token = "https://bsso.blpprofessional.com/as/token.oauth2"
        
        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0.0
        
        # Device flow data
        self._device_code: Optional[str] = None
        self._user_code: Optional[str] = None
        self._verification_uri: Optional[str] = None
        self._verification_uri_complete: Optional[str] = None
        self._interval: int = 5

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests.
        
        Returns:
            Dictionary with Authorization header
            
        Raises:
            RuntimeError: If not authenticated
        """
        token = self.get_valid_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_valid_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.
        
        Returns:
            Valid access token
            
        Raises:
            RuntimeError: If not authenticated
        """
        if self._access_token and time.time() < (self._expires_at - 15):
            return self._access_token
        
        if self._refresh_token:
            self._refresh_access_token()
            if self._access_token:
                return self._access_token
        
        raise RuntimeError("Not authenticated. Please complete device flow authentication.")

    def start_device_flow(self) -> Dict[str, str]:
        """
        Start the OAuth device flow.
        
        Returns:
            Dictionary containing device flow information:
            - device_code: Code for polling
            - user_code: Code user sees for verification
            - verification_uri: Base verification URL
            - verification_uri_complete: Complete verification URL (if available)
            - interval: Polling interval in seconds
            
        Raises:
            RuntimeError: If device flow initiation fails
        """
        logger.info("Starting OAuth device flow")
        
        data = {"scope": "openid"}
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        
        with httpx.Client(timeout=30) as client:
            try:
                # Try primary endpoint
                r = client.post(self.url_auth, data=data, headers=_form_headers(), auth=auth)
                
                if r.status_code in (400, 404):
                    # Try alternative endpoint
                    base = self.url_auth.rsplit("/", 1)[0]
                    alt_url = base + "/device_authorization.oauth2"
                    logger.info(f"Trying alternative endpoint: {alt_url}")
                    
                    r = client.post(alt_url, data=data, headers=_form_headers(), auth=auth)
                
                if not r.is_success:
                    error_msg = _extract_oauth_error(r)
                    raise RuntimeError(f"Device flow start failed: {r.status_code} {error_msg}")
                
                device_data = r.json()
                
                # Store device flow data
                self._device_code = device_data.get("device_code")
                self._user_code = device_data.get("user_code")
                self._verification_uri = device_data.get("verification_uri")
                self._verification_uri_complete = device_data.get("verification_uri_complete")
                self._interval = int(device_data.get("interval", 5))
                
                logger.info(f"Device flow started. User code: {self._user_code}")
                
                return {
                    "device_code": self._device_code,
                    "user_code": self._user_code,
                    "verification_uri": self._verification_uri,
                    "verification_uri_complete": self._verification_uri_complete,
                    "interval": str(self._interval)
                }
                
            except httpx.RequestError as e:
                raise RuntimeError(f"Network error during device flow start: {str(e)}")

    def get_verification_url(self) -> Optional[str]:
        """
        Get the complete verification URL for user authentication.
        
        Returns:
            Complete verification URL or None if not available
        """
        if self._verification_uri_complete:
            return self._verification_uri_complete
        
        if self._verification_uri and self._user_code:
            # Construct URL manually if complete URL not provided
            base = self.url_auth.rsplit("/", 1)[0]
            return f"{base}/user_authz.oauth2?user_code={self._user_code}"
        
        return None

    def poll_for_token(self, max_wait: int = 600) -> bool:
        """
        Poll for access token after user approval.
        
        Args:
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if authentication successful, False if timed out
            
        Raises:
            RuntimeError: If polling fails due to error
        """
        if not self._device_code:
            raise RuntimeError("Device flow not started. Call start_device_flow() first.")
        
        logger.info("Polling for access token")
        start_time = time.time()
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        
        with httpx.Client(timeout=30) as client:
            while time.time() - start_time < max_wait:
                data = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": self._device_code,
                }
                
                try:
                    r = client.post(self.url_token, data=data, headers=_form_headers(), auth=auth)
                    
                    if r.status_code == 200:
                        # Success - store tokens
                        self._store_tokens(r.json())
                        logger.info("Authentication successful")
                        return True
                    
                    elif r.status_code in (400, 401, 428):
                        # Still waiting for user approval
                        logger.debug("Still waiting for user approval")
                        time.sleep(max(1, self._interval))
                        continue
                    
                    else:
                        # Unexpected error
                        error_msg = _extract_oauth_error(r)
                        raise RuntimeError(f"Token polling failed: {r.status_code} {error_msg}")
                
                except httpx.RequestError as e:
                    logger.warning(f"Network error during polling: {str(e)}")
                    time.sleep(self._interval)
                    continue
        
        logger.warning("Token polling timed out")
        return False

    def _refresh_access_token(self) -> None:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise RuntimeError("No refresh token available")
        
        logger.debug("Refreshing access token")
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        
        with httpx.Client(timeout=30) as client:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token
            }
            
            r = client.post(self.url_token, data=data, headers=_form_headers(), auth=auth)
            
            if not r.is_success:
                error_msg = _extract_oauth_error(r)
                raise RuntimeError(f"Token refresh failed: {r.status_code} {error_msg}")
            
            self._store_tokens(r.json())
            logger.info("Access token refreshed")

    def _store_tokens(self, token_data: Dict) -> None:
        """Store access and refresh tokens."""
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        
        expires_in = int(token_data.get("expires_in", 900))
        self._expires_at = time.time() + expires_in
        
        logger.debug(f"Tokens stored. Expires in {expires_in} seconds")

    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid token."""
        try:
            self.get_valid_access_token()
            return True
        except RuntimeError:
            return False

    def clear_tokens(self) -> None:
        """Clear stored authentication tokens."""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = 0.0
        self._device_code = None
        self._user_code = None
        self._verification_uri = None
        self._verification_uri_complete = None
        logger.info("Authentication tokens cleared")


class CustomBloombergClient:
    """
    Custom Bloomberg API client using direct HTTP implementation.
    
    Replaces the need for bloomberg.enterprise packages with direct API calls.
    """

    def __init__(self, oauth_client: CustomDeviceOAuth):
        """
        Initialize Bloomberg API client.
        
        Args:
            oauth_client: Authenticated CustomDeviceOAuth instance
        """
        self.oauth = oauth_client
        self.base_url = "https://api.bloomberg.com"
        self.client = httpx.Client(timeout=60.0)

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test API connection.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            headers = self.oauth.get_auth_headers()
            url = f"{self.base_url}/enterprise/portfolio/optimization/tasks"
            
            r = self.client.get(url, headers=headers)
            
            if r.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"HTTP {r.status_code}: {r.text[:200]}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def search_catalog(self, portfolio: str, report: str, benchmark: str = None) -> httpx.Response:
        """
        Search report catalog (equivalent to ReportHandler.search_catalog).
        
        Args:
            portfolio: Portfolio identifier
            report: Report name
            benchmark: Optional benchmark identifier
            
        Returns:
            HTTP response object
        """
        try:
            headers = self.oauth.get_auth_headers()
            url = f"{self.base_url}/enterprise/portfolio/report/info"
            
            params = {
                "portfolio": portfolio,
                "reportName": report
            }
            
            if benchmark:
                params["benchmark"] = benchmark
            
            return self.client.get(url, headers=headers, params=params)
            
        except Exception as e:
            # Create a mock response for error cases
            class MockResponse:
                def __init__(self, status_code, text):
                    self.status_code = status_code
                    self.text = text
                def json(self):
                    return {"error": text}
            
            return MockResponse(500, str(e))

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def load_credentials_from_config(config_path: str) -> Tuple[str, str]:
    """
    Load Bloomberg credentials from config file.
    
    Args:
        config_path: Path to JSON config file
        
    Returns:
        Tuple of (client_id, client_secret)
        
    Raises:
        FileNotFoundError: If config file not found
        KeyError: If required credentials not in config
        json.JSONDecodeError: If config file is invalid JSON
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        client_id = config["client_id"]
        client_secret = config["client_secret"]
        
        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret cannot be empty")
        
        return client_id, client_secret
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except KeyError as e:
        raise KeyError(f"Missing required credential in config: {str(e)}")


# Convenience function for easy testing
def create_authenticated_client(config_path: str = "config/port_v2_config.json") -> Tuple[CustomDeviceOAuth, CustomBloombergClient]:
    """
    Create authenticated Bloomberg client from config file.
    
    This is a convenience function for testing the authentication flow.
    
    Args:
        config_path: Path to Bloomberg config file
        
    Returns:
        Tuple of (oauth_client, api_client)
        
    Usage:
        oauth, client = create_authenticated_client()
        # oauth will have device flow started, user needs to authenticate
        # then poll for token completion
    """
    client_id, client_secret = load_credentials_from_config(config_path)
    oauth_client = CustomDeviceOAuth(client_id, client_secret)
    api_client = CustomBloombergClient(oauth_client)
    
    return oauth_client, api_client