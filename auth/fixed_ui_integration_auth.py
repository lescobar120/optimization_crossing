# fixed_ui_integration_auth.py
"""
Fixed UI Integration module for custom Bloomberg authentication.

This fixes the issues with authentication links appearing in console instead of UI
and component loading messages not updating the proper sections.
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable, Tuple
import ipywidgets as widgets
from IPython.display import HTML

from .custom_bloomberg_auth import CustomDeviceOAuth, CustomBloombergClient, load_credentials_from_config


class FixedAuthenticationUIManager:
    """
    Fixed authentication manager that properly displays auth links in UI
    instead of printing to console.
    """
    
    def __init__(self, config_path: str = "config/port_v2_config.json"):
        """
        Initialize authentication manager.
        
        Args:
            config_path: Path to Bloomberg credentials config file
        """
        self.config_path = config_path
        self.oauth_client: Optional[CustomDeviceOAuth] = None
        self.api_client: Optional[CustomBloombergClient] = None
        
        # Authentication state
        self.is_authenticating = False
        self.auth_completed = False
        self.auth_error: Optional[str] = None
        
        # Device flow data
        self.verification_url: Optional[str] = None
        self.user_code: Optional[str] = None
        
        # UI callback for status updates
        self.status_callback: Optional[Callable[[str], None]] = None
        self.log_callback: Optional[Callable[[str], None]] = None
        self.auth_link_callback: Optional[Callable[[str, str], None]] = None

    def set_callbacks(self, status_callback: Callable[[str], None] = None, 
                     log_callback: Callable[[str], None] = None,
                     auth_link_callback: Callable[[str, str], None] = None):
        """
        Set callback functions for UI updates.
        
        Args:
            status_callback: Function to call with status updates
            log_callback: Function to call with log messages
            auth_link_callback: Function to call with (verification_url, user_code)
        """
        self.status_callback = status_callback
        self.log_callback = log_callback
        self.auth_link_callback = auth_link_callback

    def start_authentication_async(self, completion_callback: Optional[Callable[[bool, str], None]] = None):
        """
        Start authentication process in background thread.
        
        Args:
            completion_callback: Function called when authentication completes
                                Called with (success: bool, error_message: str)
        """
        if self.is_authenticating:
            self._log("Authentication already in progress")
            return
        
        def _authenticate():
            try:
                self.is_authenticating = True
                self.auth_completed = False
                self.auth_error = None
                
                self._log("Starting Bloomberg authentication...")
                self._update_status("Initializing authentication...")
                
                # Load credentials
                self._log("Loading credentials from config...")
                client_id, client_secret = load_credentials_from_config(self.config_path)
                
                # Initialize OAuth client
                self._log("Initializing OAuth client...")
                self.oauth_client = CustomDeviceOAuth(client_id, client_secret)
                
                # Start device flow
                self._log("Starting device flow...")
                self._update_status("Starting device flow...")
                device_info = self.oauth_client.start_device_flow()
                
                # Store device flow data
                self.user_code = device_info['user_code']
                self.verification_url = self.oauth_client.get_verification_url()
                
                self._log(f"Device flow started. User code: {self.user_code}")
                self._update_status("Device flow started - user authentication required")
                
                # Notify UI about authentication URL (IN UI, NOT CONSOLE)
                if self.verification_url and self.auth_link_callback:
                    self.auth_link_callback(self.verification_url, self.user_code)
                
                # Poll for token
                self._log("Waiting for user authentication...")
                self._update_status("Waiting for user authentication...")
                
                success = self.oauth_client.poll_for_token(max_wait=600)
                
                if success:
                    # Create API client
                    self.api_client = CustomBloombergClient(self.oauth_client)
                    
                    # Test connection
                    self._log("Testing API connection...")
                    test_success, test_message = self.api_client.test_connection()
                    
                    if test_success:
                        self.auth_completed = True
                        self._log("Authentication completed successfully!")
                        self._update_status("Authentication successful")
                        
                        if completion_callback:
                            completion_callback(True, None)
                    else:
                        error_msg = f"API test failed: {test_message}"
                        self.auth_error = error_msg
                        self._log(error_msg)
                        self._update_status("Authentication failed - API test failed")
                        
                        if completion_callback:
                            completion_callback(False, error_msg)
                else:
                    error_msg = "Authentication timed out - user did not complete authentication"
                    self.auth_error = error_msg
                    self._log(error_msg)
                    self._update_status("Authentication timed out")
                    
                    if completion_callback:
                        completion_callback(False, error_msg)
                        
            except Exception as e:
                error_msg = f"Authentication failed: {str(e)}"
                self.auth_error = error_msg
                self._log(error_msg)
                self._update_status("Authentication failed")
                
                if completion_callback:
                    completion_callback(False, error_msg)
            
            finally:
                self.is_authenticating = False
        
        # Start authentication in background thread
        auth_thread = threading.Thread(target=_authenticate)
        auth_thread.daemon = True
        auth_thread.start()

    def _update_status(self, message: str):
        """Update status via callback."""
        if self.status_callback:
            self.status_callback(message)

    def _log(self, message: str):
        """Log message via callback."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if self.log_callback:
            self.log_callback(formatted_message)

    def get_auth_headers(self) -> dict:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary with authorization headers
            
        Raises:
            RuntimeError: If not authenticated
        """
        if not self.oauth_client or not self.auth_completed:
            raise RuntimeError("Not authenticated. Complete authentication first.")
        
        return self.oauth_client.get_auth_headers()

    def search_catalog(self, portfolio: str, report: str, benchmark: str = None):
        """
        Search Bloomberg report catalog.
        
        This method provides the same interface as ReportHandler.search_catalog
        but uses the custom authentication.
        
        Args:
            portfolio: Portfolio identifier
            report: Report name  
            benchmark: Optional benchmark identifier
            
        Returns:
            HTTP response object
        """
        if not self.api_client or not self.auth_completed:
            raise RuntimeError("Not authenticated. Complete authentication first.")
        
        return self.api_client.search_catalog(portfolio, report, benchmark)

    def is_ready(self) -> bool:
        """Check if authentication is complete and ready for use."""
        return self.auth_completed and self.api_client is not None

    def clear_authentication(self):
        """Clear authentication state."""
        if self.oauth_client:
            self.oauth_client.clear_tokens()
        
        if self.api_client:
            self.api_client.close()
        
        self.oauth_client = None
        self.api_client = None
        self.auth_completed = False
        self.auth_error = None
        self.verification_url = None
        self.user_code = None
        
        self._log("Authentication cleared")
        self._update_status("Authentication cleared")


def create_fixed_auth_ui_widgets(auth_manager: FixedAuthenticationUIManager) -> dict:
    """
    Create fixed UI widgets for authentication management.
    
    This fixes all the UI issues:
    - Auth links appear in UI instead of console
    - Status updates properly in UI sections
    - Messages clear when appropriate
    
    Args:
        auth_manager: FixedAuthenticationUIManager instance
        
    Returns:
        Dictionary of widgets for UI integration
    """
    
    # Status display
    status_display = widgets.HTML(
        value="<b>Status:</b> Ready to authenticate",
        layout=widgets.Layout(margin='5px 0px')
    )
    
    # Authentication link display (initially hidden)
    auth_link_display = widgets.HTML(
        value="",
        layout=widgets.Layout(margin='10px 0px')
    )
    
    # Log display  
    log_display = widgets.HTML(
        value="<div style='font-family: monospace; font-size: 12px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px;'>Ready for authentication.</div>",
        layout=widgets.Layout(margin='10px 0px')
    )
    
    # Start authentication button
    auth_button = widgets.Button(
        description='Start Authentication',
        button_style='primary',
        layout=widgets.Layout(width='200px', margin='5px')
    )
    
    # Clear authentication button
    clear_button = widgets.Button(
        description='Clear Authentication',
        button_style='warning',
        layout=widgets.Layout(width='200px', margin='5px'),
        disabled=True
    )
    
    # Test connection button
    test_button = widgets.Button(
        description='Test Connection',
        button_style='info',
        layout=widgets.Layout(width='200px', margin='5px'),
        disabled=True
    )
    
    def update_status(message: str):
        """Update status display."""
        status_display.value = f"<b>Status:</b> {message}"
    
    def add_log(message: str):
        """Add log message to display."""
        # Clean log message (remove timestamp if present for cleaner display)
        clean_message = message
        if "] " in message:
            clean_message = message.split("] ", 1)[1] if "] " in message else message
        
        # Get current log content
        current_log = log_display.value
        
        # Extract existing content
        start_tag = "<div style='font-family: monospace"
        if start_tag in current_log:
            start_idx = current_log.find('>') + 1
            end_idx = current_log.rfind('</div>')
            
            if start_idx > 0 and end_idx > start_idx:
                existing_content = current_log[start_idx:end_idx]
                # Replace initial message if it's still there
                if "Ready for authentication." in existing_content:
                    existing_content = ""
            else:
                existing_content = ""
        else:
            existing_content = ""
        
        # Add new log line
        log_line = f"<div style='color: #343a40; margin: 2px 0;'>{clean_message}</div>"
        new_content = existing_content + log_line
        
        # Update display
        log_display.value = f"<div style='font-family: monospace; font-size: 12px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px; max-height: 300px; overflow-y: auto;'>{new_content}</div>"
    
    def show_auth_link(verification_url: str, user_code: str):
        """Display authentication link in UI instead of console."""
        auth_link_html = f'''
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #1976d2;">
            <h4 style="color: #1976d2; margin-top: 0;">B-Unit Authentication Required</h4>
            <p><strong>Authorization Code:</strong> <code style="background-color: #f5f5f5; padding: 2px 6px; font-size: 14px; font-weight: bold;">{user_code}</code></p>
            <p><strong>Click the link below to authenticate:</strong></p>
            <p>
                <a href="{verification_url}" target="_blank" 
                   style="display: inline-block; background-color: #1976d2; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 14px;">
                    Launch B-Unit Authentication
                </a>
            </p>
            <div style="margin-top: 15px; padding: 10px; background-color: #fff3e0; border-radius: 4px; font-size: 13px;">
                <strong>Instructions:</strong>
                <ol style="margin: 5px 0; padding-left: 20px;">
                    <li>Click the authentication link above</li>
                    <li>Verify the authorization code matches: <strong>{user_code}</strong></li>
                    <li>Complete the authentication process</li>
                    <li>Return to this page - the system will auto-detect completion</li>
                </ol>
            </div>
        </div>
        '''
        auth_link_display.value = auth_link_html
    
    def clear_auth_link():
        """Clear the authentication link display."""
        auth_link_display.value = ""
    
    # Set callbacks
    auth_manager.set_callbacks(
        status_callback=update_status, 
        log_callback=add_log,
        auth_link_callback=show_auth_link
    )
    
    def on_auth_start(button):
        """Handle start authentication button click."""
        auth_button.disabled = True
        auth_button.description = "Authenticating..."
        clear_button.disabled = True
        test_button.disabled = True
        
        # Clear any previous auth link
        clear_auth_link()
        
        def completion_callback(success: bool, error: str):
            if success:
                auth_button.description = "Authenticated"
                auth_button.button_style = "success"
                clear_button.disabled = False
                test_button.disabled = False
                # Clear auth link on success
                clear_auth_link()
            else:
                auth_button.description = "Authentication Failed"
                auth_button.button_style = "danger"
                auth_button.disabled = False
                clear_button.disabled = False
        
        auth_manager.start_authentication_async(completion_callback)
    
    def on_clear_auth(button):
        """Handle clear authentication button click."""
        auth_manager.clear_authentication()
        auth_button.description = "Start Authentication"
        auth_button.button_style = "primary"
        auth_button.disabled = False
        clear_button.disabled = True
        test_button.disabled = True
        
        # Clear auth link and reset log
        clear_auth_link()
        log_display.value = "<div style='font-family: monospace; font-size: 12px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px;'>Ready for authentication.</div>"
        update_status("Authentication cleared")
    
    def on_test_connection(button):
        """Handle test connection button click."""
        if auth_manager.is_ready():
            success, message = auth_manager.api_client.test_connection()
            if success:
                update_status(f"Connection test successful: {message}")
            else:
                update_status(f"Connection test failed: {message}")
        else:
            update_status("Not authenticated - cannot test connection")
    
    # Wire up event handlers
    auth_button.on_click(on_auth_start)
    clear_button.on_click(on_clear_auth)
    test_button.on_click(on_test_connection)
    
    return {
        'auth_button': auth_button,
        'clear_button': clear_button,
        'test_button': test_button,
        'status_display': status_display,
        'log_display': log_display,
        'auth_link_display': auth_link_display,
        'button_container': widgets.HBox([auth_button, clear_button, test_button]),
        'full_container': widgets.VBox([
            widgets.HTML("<h3>Bloomberg Authentication</h3>"),
            widgets.HBox([auth_button, clear_button, test_button]),
            status_display,
            auth_link_display,  # Add the auth link display here
            log_display
        ])
    }


# Create aliases for drop-in replacement
AuthenticationUIManager = FixedAuthenticationUIManager
create_auth_ui_widgets = create_fixed_auth_ui_widgets


if __name__ == "__main__":
    # Test the fixed UI integration
    print("Testing Fixed UI Integration Module...")
    
    # Create auth manager
    auth_manager = FixedAuthenticationUIManager()
    
    # Create widgets
    widgets_dict = create_fixed_auth_ui_widgets(auth_manager)
    
    # Display the UI
    from IPython.display import display
    display(widgets_dict['full_container'])
    
    print("Fixed UI widgets created successfully!")