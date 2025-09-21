# shared_auth_manager.py
"""
Shared authentication manager that maintains a single authentication state
across all workflow components to avoid redundant authentication.
"""

import threading
from typing import Optional, Dict, Any, Tuple
from .custom_bloomberg_auth import CustomDeviceOAuth, CustomBloombergClient, load_credentials_from_config


class SharedAuthenticationManager:
    """
    Singleton authentication manager that maintains authentication state
    across all components in the workflow.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path: str = "config/port_v2_config.json"):
        """Ensure only one instance exists (singleton pattern)."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config_path: str = "config/port_v2_config.json"):
        """Initialize the shared authentication manager."""
        if self._initialized:
            return
            
        self.config_path = config_path
        self.oauth_client: Optional[CustomDeviceOAuth] = None
        self.api_client: Optional[CustomBloombergClient] = None
        
        # Authentication state
        self.is_authenticated = False
        self.auth_error: Optional[str] = None
        
        # Thread safety
        self.auth_lock = threading.Lock()
        
        self._initialized = True
    
    def authenticate_if_needed(self) -> bool:
        """
        Authenticate if not already authenticated.
        
        Returns:
            True if authenticated (either already or just completed), False otherwise
        """
        with self.auth_lock:
            # Debug: Check current state
            print(f"[DEBUG] Auth check - is_authenticated: {self.is_authenticated}")
            if self.oauth_client:
                print(f"[DEBUG] OAuth client exists, is_authenticated(): {self.oauth_client.is_authenticated()}")
            else:
                print("[DEBUG] No OAuth client exists")
                
            if self.is_authenticated and self.oauth_client and self.oauth_client.is_authenticated():
                print("[DEBUG] Already authenticated, returning True")
                return True
            
            # If we have an oauth_client but it's not authenticated, we have a problem
            if self.oauth_client and not self.oauth_client.is_authenticated():
                print("[DEBUG] OAuth client exists but not authenticated - clearing state")
                self.clear_authentication()
            
            try:
                # Load credentials
                print("[DEBUG] Loading credentials...")
                client_id, client_secret = load_credentials_from_config(self.config_path)
                
                # Initialize OAuth client if needed
                if not self.oauth_client:
                    print("[DEBUG] Creating new OAuth client...")
                    self.oauth_client = CustomDeviceOAuth(client_id, client_secret)
                
                # Check if already authenticated
                if self.oauth_client.is_authenticated():
                    print("[DEBUG] OAuth client is authenticated, setting up API client...")
                    self.is_authenticated = True
                    if not self.api_client:
                        self.api_client = CustomBloombergClient(self.oauth_client)
                    return True
                
                # If we reach here, we're not authenticated
                print("[DEBUG] Not authenticated - authentication required but not starting device flow")
                self.auth_error = "Authentication required - please complete authentication in UI first"
                return False
                    
            except Exception as e:
                error_msg = f"Authentication check failed: {str(e)}"
                print(f"[DEBUG] Exception during auth check: {error_msg}")
                self.auth_error = error_msg
                return False

    def set_oauth_client(self, oauth_client):
        """
        Set the OAuth client from external authentication.
        
        This allows the FixedAuthenticationUIManager to provide the authenticated client.
        """
        with self.auth_lock:
            self.oauth_client = oauth_client
            if oauth_client and oauth_client.is_authenticated():
                self.is_authenticated = True
                self.api_client = CustomBloombergClient(oauth_client)
                self.auth_error = None
                print("[DEBUG] OAuth client set from external source")
            else:
                print("[DEBUG] Invalid OAuth client provided")
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test API connection using the underlying client.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print("[DEBUG] Starting connection test...")
            
            if not self.is_authenticated or not self.oauth_client:
                print("[DEBUG] Not authenticated for connection test")
                return False, "Not authenticated - complete authentication first"
            
            if not self.oauth_client.is_authenticated():
                print("[DEBUG] OAuth client not authenticated")
                return False, "OAuth client not authenticated"
            
            # Test using the Bloomberg API endpoints
            headers = self.get_auth_headers()
            print("[DEBUG] Got auth headers, testing connection...")
            
            import requests
            
            test_url = "https://api.bloomberg.com/enterprise/portfolio/optimization/tasks"
            response = requests.get(test_url, headers=headers, timeout=10)
            
            print(f"[DEBUG] Connection test response: {response.status_code}")
            
            if response.status_code == 200:
                return True, f"Connection successful (status: {response.status_code})"
            else:
                return False, f"Connection failed with status: {response.status_code}"
                
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            print(f"[DEBUG] Connection test exception: {error_msg}")
            return False, error_msg
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers, authenticating if necessary.
        
        Returns:
            Dictionary with authorization headers
            
        Raises:
            RuntimeError: If authentication fails
        """
        if not self.authenticate_if_needed():
            error_msg = self.auth_error or "Authentication failed"
            raise RuntimeError(f"Bloomberg authentication failed: {error_msg}")
        
        return self.oauth_client.get_auth_headers()
    
    def get_api_client(self) -> CustomBloombergClient:
        """
        Get API client, authenticating if necessary.
        
        Returns:
            CustomBloombergClient instance
            
        Raises:
            RuntimeError: If authentication fails
        """
        if not self.authenticate_if_needed():
            error_msg = self.auth_error or "Authentication failed"
            raise RuntimeError(f"Bloomberg authentication failed: {error_msg}")
        
        if not self.api_client:
            self.api_client = CustomBloombergClient(self.oauth_client)
        
        return self.api_client
    
    def is_ready(self) -> bool:
        """Check if authentication is ready for use."""
        return self.is_authenticated and self.oauth_client and self.oauth_client.is_authenticated()
    
    def clear_authentication(self):
        """Clear authentication state."""
        with self.auth_lock:
            if self.oauth_client:
                self.oauth_client.clear_tokens()
            
            if self.api_client:
                self.api_client.close()
            
            self.oauth_client = None
            self.api_client = None
            self.is_authenticated = False
            self.auth_error = None
    
    def force_reauthenticate(self):
        """Force re-authentication by clearing current state."""
        self.clear_authentication()
        return self.authenticate_if_needed()


# Global instance for shared use
_shared_auth_manager = None

def get_shared_auth_manager(config_path: str = "config/port_v2_config.json") -> SharedAuthenticationManager:
    """
    Get the global shared authentication manager instance.
    
    Args:
        config_path: Path to Bloomberg configuration file
        
    Returns:
        SharedAuthenticationManager instance
    """
    global _shared_auth_manager
    if _shared_auth_manager is None:
        _shared_auth_manager = SharedAuthenticationManager(config_path)
    return _shared_auth_manager