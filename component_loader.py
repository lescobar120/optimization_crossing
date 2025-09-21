import io
import threading
import re
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import ipywidgets as widgets
from IPython.display import HTML, display

class ComponentLoader:
    """Handles loading Bloomberg components with authentication link capture."""
    
    def __init__(self, log_display_widget):
        self.log_display = log_display_widget
        self.auth_link = None
        self.auth_code = None
        self.components_loaded = False
        self.log_messages = []
        
        # Component references
        self.report_handler = None
        self.orchestrator = None
        self.crossing_engine = None
    
    def load_components_async(self, auth_config_path, completion_callback=None):
        """Load components in background thread with auth link capture."""
        
        def _load_components():
            try:
                self._add_log("Starting component initialization...")
                
                # Try loading components step by step with individual captures
                self._load_all_components_step_by_step(auth_config_path)
                
                if self.components_loaded:
                    self._add_log("All components loaded successfully!")
                    if completion_callback:
                        completion_callback(True, None)
                else:
                    self._add_log("Component loading failed")
                    if completion_callback:
                        completion_callback(False, "Component loading failed")
                        
            except Exception as e:
                error_msg = f"Error loading components: {str(e)}"
                self._add_log(error_msg)
                if completion_callback:
                    completion_callback(False, error_msg)
        
        # Start loading in background thread
        load_thread = threading.Thread(target=_load_components)
        load_thread.daemon = True
        load_thread.start()
    
    def _load_all_components_step_by_step(self, auth_config_path):
        """Load components step by step with individual output capture."""
        
        # Import here to avoid import issues
        from ReportHandler import ReportHandler
        from request_builder import PortfolioOptimizerRequestBuilder
        from orchestrator import OptimizationOrchestrator
        from crossing_engine import PortfolioCrossingEngine, CrossingEngineConfig
        from portfolio_configs import PortfolioConfigManager, PORTFOLIO_CONFIGS
        
        self._add_log("Initializing Bloomberg ReportHandler...")
        
        # Capture just the ReportHandler initialization
        import sys
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        captured_output = io.StringIO()
        captured_error = io.StringIO()
        
        try:
            sys.stdout = captured_output
            sys.stderr = captured_error
            
            # This is where the auth link should appear
            self.report_handler = ReportHandler(auth_config_path)
            
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        # Get the captured output immediately
        auth_output = captured_output.getvalue() + captured_error.getvalue()
        self._add_log(f"ReportHandler output captured: {len(auth_output)} characters")
        
        if auth_output.strip():
            self._add_log("Processing ReportHandler output...")
            self._parse_auth_output(auth_output)
        else:
            self._add_log("No output captured from ReportHandler initialization")
        
        # Continue with other components
        self._add_log("Setting up portfolio configuration manager...")
        config_manager = PortfolioConfigManager(PORTFOLIO_CONFIGS)
        
        # Inject restrictions
        PORTFOLIO_RESTRICTIONS = {
            "S-17147": None,
            "P-93050": ['EQ0010054600001000', 'EQ0000000026033823'],
            "P-61230": None,
            "P-47227": None,
            "P-36182": None
        }
        config_manager.inject_restrictions(PORTFOLIO_RESTRICTIONS)
        
        self._add_log("Initializing request builder...")
        builder = PortfolioOptimizerRequestBuilder(
            template_path='portfolio_optimization_template.yml',
            config_manager=config_manager
        )
        
        self._add_log("Setting up optimization orchestrator...")
        self.orchestrator = OptimizationOrchestrator(
            self.report_handler,
            config_manager,
            builder
        )
        
        self._add_log("Initializing crossing engine...")
        priority_list = ["S17147", "P36182", "P47227", "P93050", "P-61230"]
        config = CrossingEngineConfig(portfolio_priority=priority_list)
        self.crossing_engine = PortfolioCrossingEngine(config)
        
        self._add_log("Testing API connection...")
        # Test the connection
        test_response = self.report_handler.search_catalog(
            portfolio="S-17147", 
            report="pre_optimization_crossing_msr"
        )
        
        if test_response.status_code == 200:
            self.components_loaded = True
            self._add_log("API connection verified!")
        else:
            raise Exception(f"API connection test failed: {test_response.status_code}")
    
    def _parse_auth_output(self, output_text):
        """Parse captured output for authentication information."""
        
        self._add_log(f"Parsing output: {len(output_text)} characters")
        
        # Show the raw output for debugging
        if output_text.strip():
            self._add_log("Raw output content:")
            lines = output_text.strip().split('\n')
            for i, line in enumerate(lines[:10]):  # Show first 10 lines
                self._add_log(f"Line {i}: {repr(line)}")
            
            if len(lines) > 10:
                self._add_log(f"... and {len(lines) - 10} more lines")
        
        # Look for authentication link pattern
        link_pattern = r'https://bsso\.blpprofessional\.com/as/user_authz\.oauth2\?user_code=([A-Z0-9-]+)'
        link_match = re.search(link_pattern, output_text)
        
        if link_match:
            self._add_log("AUTH LINK FOUND!")
            self.auth_link = link_match.group(0)
            self.auth_code = link_match.group(1)
            
            # Create clickable link HTML
            auth_link_html = f'''
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #1976d2;">
                <h4 style="color: #1976d2; margin-top: 0;">Bloomberg Authentication Required</h4>
                <p><strong>Authorization Code:</strong> <code style="background-color: #f5f5f5; padding: 2px 4px;">{self.auth_code}</code></p>
                <p><strong>Please click the link below to authenticate:</strong></p>
                <p>
                    <a href="{self.auth_link}" target="_blank" 
                       style="display: inline-block; background-color: #1976d2; color: white; padding: 10px 20px; 
                              text-decoration: none; border-radius: 4px; font-weight: bold;">
                        Open Bloomberg Authentication
                    </a>
                </p>
            </div>
            '''
            
            # Update the log display with the authentication link
            current_log = self.log_display.value
            self.log_display.value = current_log + auth_link_html
            
            self._add_log("Authentication link displayed above")
        else:
            self._add_log("No auth link pattern found")
            # Show what we're searching in
            self._add_log(f"Search text sample: {repr(output_text[:200])}")
    
    def _add_log(self, message):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_messages.append(formatted_message)
        
        # Keep only last 50 messages
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
        
        # Update the HTML display
        log_html = "<div style='font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto; background-color: #f8f9fa; padding: 10px; border: 1px solid #ddd; border-radius: 4px;'>"
        
        for msg in self.log_messages:
            log_html += f"<div style='color: #343a40;'>{msg}</div>"
        
        log_html += "</div>"
        
        # Update only the log part, preserve any auth HTML
        current_value = self.log_display.value
        if '<div style="background-color: #e3f2fd' in current_value:
            # Split and preserve auth section
            parts = current_value.split('<div style="background-color: #e3f2fd')
            if len(parts) > 1:
                auth_html = '<div style="background-color: #e3f2fd' + parts[1]
                self.log_display.value = log_html + auth_html
            else:
                self.log_display.value = log_html
        else:
            self.log_display.value = log_html
        
        # Force the widget to refresh
        import time
        time.sleep(0.01)


