# updated_api_config.py
"""
Updated API config that uses shared authentication to avoid redundant authentication.
This should replace your enhanced_api_config.py
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from auth.shared_auth_manager import get_shared_auth_manager


# API Endpoints - EXACT COMPATIBILITY
OPTIMIZATION_TRIGGER_ENDPOINT = 'https://api.bloomberg.com/enterprise/portfolio/optimization/executions'
RESULTS_RETRIEVAL_ENDPOINT = 'https://api.bloomberg.com/enterprise/portfolio/optimization/executions/'
WORKFLOWS_PATH = 'https://api.bloomberg.com/enterprise/workflow/workflows'
WORKFLOW_RUNS_PATH = 'https://api.bloomberg.com/enterprise/workflow/workflow-runs'
CATALOG_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/info'
REPORT_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/data'

# Connection Testing Path
CONNECTION_TEST_PATH = 'https://api.bloomberg.com/enterprise/portfolio/optimization/tasks'

# Authentication config path
AUTH_CONFIG_PATH = 'config/port_v2_config.json'

# Time between response polling
WAIT_TIME_SECONDS = 10


class UpdatedAuthManager:
    """
    Updated authentication manager that uses shared authentication.
    
    This eliminates redundant authentication by delegating to the shared manager.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize AuthManager with shared authentication.
        
        Args:
            config_path: Path to authentication configuration file.
                         If None, will look for default path.
        """
        self.logger = logging.getLogger(__name__)
        
        # Use provided path or default
        self.config_path = config_path or AUTH_CONFIG_PATH
        
        # Get shared authentication manager
        self.shared_auth = get_shared_auth_manager(self.config_path)
        
        self.logger.info("Updated AuthManager initialized with shared authentication")
    
    def get_authorization_headers(self) -> Dict[str, str]:
        """
        Get authorization headers using shared authentication - EXACT COMPATIBILITY.
        
        Returns:
            Dictionary containing authorization headers
            
        Raises:
            ValueError: If authentication credentials are not available
            RuntimeError: If token generation fails
        """
        try:
            # The shared manager handles all authentication logic
            headers = self.shared_auth.get_auth_headers()
            self.logger.debug("Generated authorization token via shared manager")
            return headers
            
        except Exception as e:
            self.logger.error(f"Error generating authentication token: {e}")
            raise RuntimeError(f"Failed to generate authentication token: {e}")

    def test_connection(self, test_url: str = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Test the API connection and return detailed results - EXACT COMPATIBILITY.
        
        Args:
            test_url: URL to use for connection testing. If None, uses a default endpoint.
            
        Returns:
            Tuple containing:
                - bool: True if connection was successful, False otherwise
                - Optional[Dict]: Response details if available, None on exception
        """
        if test_url is None:
            test_url = CONNECTION_TEST_PATH
        
        try:
            headers = self.get_authorization_headers()
            response = requests.get(test_url, headers=headers, timeout=10)
            
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"text": response.text[:1000]}
                
            result = {
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers)
            }
            
            success = response.status_code == 200
            return success, result
                
        except requests.RequestException as e:
            self.logger.error(f"API connection test failed with exception: {e}")
            return False, None


# Create a default instance using shared authentication - EXACT COMPATIBILITY
try:
    auth_manager = UpdatedAuthManager(config_path=AUTH_CONFIG_PATH)
    logger = logging.getLogger(__name__)
    logger.info(f"Initialized Updated AuthManager with shared authentication: {AUTH_CONFIG_PATH}")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize default Updated AuthManager: {e}")
    auth_manager = None


def get_authorization_headers() -> Dict[str, str]:
    """
    Get authorization headers using shared authentication - EXACT COMPATIBILITY.
    
    This function provides exact compatibility with your existing get_authorization_headers().
    
    Returns:
        Dictionary containing authorization headers
        
    Raises:
        RuntimeError: If authentication is not properly configured
    """
    if auth_manager is None:
        raise RuntimeError(
            "Authentication manager not properly initialized. "
            "Ensure proper credentials are provided."
        )
    return auth_manager.get_authorization_headers()


def test_connection(test_url: str = None) -> bool:
    """
    Test the API connection using shared authentication - EXACT COMPATIBILITY.
    
    Args:
        test_url: URL to use for connection testing. If None, uses a default endpoint.
        
    Returns:
        bool: True if connection was successful, False otherwise
        
    Raises:
        RuntimeError: If authentication is not properly configured
    """
    if auth_manager is None:
        raise RuntimeError(
            "Authentication manager not properly initialized. "
            "Ensure proper credentials are provided."
        )
    success, _ = auth_manager.test_connection(test_url)
    return success


# For backward compatibility, create aliases
AuthManager = UpdatedAuthManager
EnhancedAuthManager = UpdatedAuthManager  # For migration compatibility