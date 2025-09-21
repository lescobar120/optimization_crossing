"""
Standalone authentication helper for Bloomberg API.
Provides simple functions to handle device flow authentication separately from main UI.
"""

import ipywidgets as widgets
from IPython.display import display
from typing import Optional
import logging

from config.api_config import auth_manager, start_device_flow, poll_for_token, test_connection, is_authenticated

logger = logging.getLogger(__name__)

class AuthenticationHelper:
    """Simple helper class for handling Bloomberg authentication."""
    
    def __init__(self):
        self.device_flow_data = {}
        self.is_authenticated = False
        
    def check_authentication_status(self) -> bool:
        """Check if we're currently authenticated."""
        return is_authenticated()
    
    def trigger_authentication_flow(self):
        """
        Trigger the device flow authentication process.
        
        This will:
        1. Start the device flow
        2. Display the authentication link
        3. Provide instructions for the user
        """
        try:
            print("🔐 Starting Bloomberg API authentication...")
            
            # Start device flow
            device_response = start_device_flow()
            
            # Store device flow data
            self.device_flow_data = {
                'device_code': device_response['device_code'],
                'interval': device_response.get('interval', 5)
            }
            
            # Get verification URL
            verification_url = (
                device_response.get('verification_uri_complete') or 
                device_response.get('verification_uri')
            )
            
            if not verification_url and device_response.get('user_code'):
                # Fallback URL construction
                verification_url = f"https://bsso.blpprofessional.com/as/user_authz.oauth2?user_code={device_response['user_code']}"
            
            # Display instructions
            print("\n" + "="*80)
            print("📋 BLOOMBERG AUTHENTICATION REQUIRED")
            print("="*80)
            
            if verification_url:
                print(f"1. Open this link in your browser:")
                print(f"   {verification_url}")
                print(f"\n2. Sign in to Bloomberg and approve the application")
                print(f"3. Return here and run: auth_helper.complete_authentication()")
            else:
                print("❌ No verification URL received from Bloomberg")
                return False
            
            print("\n" + "="*80)
            
            return True
            
        except Exception as e:
            print(f"❌ Authentication start failed: {str(e)}")
            logger.error(f"Authentication start failed: {e}")
            return False
    
    def complete_authentication(self) -> bool:
        """
        Complete the authentication process after user approval.
        
        Returns:
            bool: True if authentication was successful
        """
        try:
            if not self.device_flow_data.get('device_code'):
                print("❌ No device flow started. Please run trigger_authentication_flow() first.")
                return False
            
            print("⏳ Polling for authentication token...")
            
            # Poll for token
            poll_for_token(
                self.device_flow_data['device_code'],
                interval=self.device_flow_data['interval'],
                max_wait=600
            )
            
            # Test the connection
            if test_connection():
                print("✅ Authentication successful!")
                print("🚀 You can now run your portfolio optimization workflows.")
                self.is_authenticated = True
                return True
            else:
                print("❌ Authentication completed but connection test failed.")
                return False
                
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            logger.error(f"Authentication failed: {e}")
            return False
    
    def test_api_connection(self) -> bool:
        """Test the current API connection."""
        try:
            if test_connection():
                print("✅ API connection is working")
                return True
            else:
                print("❌ API connection failed")
                return False
        except Exception as e:
            print(f"❌ Connection test error: {str(e)}")
            return False

def create_authentication_ui() -> widgets.VBox:
    """
    Create a simple authentication UI widget.
    This is optional - you can also use the helper functions directly.
    """
    
    auth_helper = AuthenticationHelper()
    
    # Status display
    status_html = widgets.HTML(
        value="<i>Authentication status: Not checked</i>",
        layout=widgets.Layout(margin='10px 0px')
    )
    
    # Buttons
    check_status_btn = widgets.Button(
        description='Check Auth Status',
        button_style='info',
        layout=widgets.Layout(width='150px', margin='5px')
    )
    
    start_auth_btn = widgets.Button(
        description='Start Authentication',
        button_style='primary',
        layout=widgets.Layout(width='150px', margin='5px')
    )
    
    complete_auth_btn = widgets.Button(
        description='Complete Authentication',
        button_style='success',
        layout=widgets.Layout(width='150px', margin='5px'),
        disabled=True
    )
    
    test_connection_btn = widgets.Button(
        description='Test Connection',
        button_style='warning',
        layout=widgets.Layout(width='150px', margin='5px')
    )
    
    # Event handlers
    def on_check_status(button):
        if auth_helper.check_authentication_status():
            status_html.value = "<span style='color: green;'>✅ Authenticated and ready</span>"
            complete_auth_btn.disabled = True
        else:
            status_html.value = "<span style='color: orange;'>⚠️ Not authenticated</span>"
    
    def on_start_auth(button):
        if auth_helper.trigger_authentication_flow():
            status_html.value = "<span style='color: blue;'>🔐 Authentication started - check console for link</span>"
            complete_auth_btn.disabled = False
        else:
            status_html.value = "<span style='color: red;'>❌ Failed to start authentication</span>"
    
    def on_complete_auth(button):
        if auth_helper.complete_authentication():
            status_html.value = "<span style='color: green;'>✅ Authentication completed successfully</span>"
            complete_auth_btn.disabled = True
        else:
            status_html.value = "<span style='color: red;'>❌ Authentication failed</span>"
    
    def on_test_connection(button):
        if auth_helper.test_api_connection():
            status_html.value = "<span style='color: green;'>✅ Connection test passed</span>"
        else:
            status_html.value = "<span style='color: red;'>❌ Connection test failed</span>"
    
    # Wire up events
    check_status_btn.on_click(on_check_status)
    start_auth_btn.on_click(on_start_auth)
    complete_auth_btn.on_click(on_complete_auth)
    test_connection_btn.on_click(on_test_connection)
    
    # Create UI
    auth_ui = widgets.VBox([
        widgets.HTML("<h3>Bloomberg API Authentication</h3>"),
        widgets.HTML("<p>Use the buttons below to authenticate with Bloomberg API.</p>"),
        widgets.HBox([
            check_status_btn,
            start_auth_btn,
            complete_auth_btn,
            test_connection_btn
        ]),
        status_html
    ], layout=widgets.Layout(
        border='1px solid #ddd',
        padding='15px',
        margin='10px'
    ))
    
    return auth_ui

# Convenience functions for direct usage
def authenticate_bloomberg_api() -> bool:
    """
    Complete Bloomberg API authentication flow.
    
    Returns:
        bool: True if authentication was successful
    """
    helper = AuthenticationHelper()
    
    # Check if already authenticated
    if helper.check_authentication_status():
        print("✅ Already authenticated!")
        return True
    
    # Start authentication flow
    if not helper.trigger_authentication_flow():
        return False
    
    # Wait for user input
    input("\nPress Enter after you've approved the application in your browser...")
    
    # Complete authentication
    return helper.complete_authentication()

# Create a global instance for convenience
auth_helper = AuthenticationHelper()