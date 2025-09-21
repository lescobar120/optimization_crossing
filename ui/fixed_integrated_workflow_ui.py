# fixed_integrated_workflow_ui.py
"""
Fixed Integrated Comprehensive Workflow UI that properly routes all messages to UI
and displays authentication links in the interface instead of console.
"""

import ipywidgets as widgets
from IPython.display import display, HTML
from typing import Dict, Optional, Any
import logging
import threading
import time

# Import the enhanced UI components
from .portfolio_config_ui import PortfolioConfigUI
from .optimization_results_ui import OptimizationResultsUI, create_analysis_results_for_batch
from .crossing_results_ui import CrossingResultsUI
from visualization.dashboard_manager import UnifiedDashboardManager

# Import data structures
from core.orchestrator import OptimizationResult
from analytics.portfolio_analytics_engine import PortfolioComparisonResult, PortfolioAnalyticsEngine
from analytics.crossing_engine import CrossingResult
from core.workflow_state import WorkflowState

# Import shared authentication components
from auth.shared_auth_manager import get_shared_auth_manager
from data.updated_report_handler import UpdatedReportHandler
from config.updated_api_config import get_authorization_headers, test_connection

# Import FIXED UI integration for authentication
from auth.fixed_ui_integration_auth import FixedAuthenticationUIManager, create_fixed_auth_ui_widgets

from optimization.request_builder import PortfolioOptimizerRequestBuilder
from core.orchestrator import OptimizationOrchestrator
from analytics.crossing_engine import CrossingResult, PortfolioCrossingEngine, CrossingEngineConfig
from core.portfolio_configs import PortfolioConfigManager, PORTFOLIO_CONFIGS

# Import visualization managers for chart generation
try:
    from visualization.plot_manager import PortfolioVisualizationManager
    from visualization.crossing_visualization_manager import CrossingVisualizationManager
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logging.warning("Chart visualization managers not available")


class FixedIntegratedComprehensiveWorkflowUI:
    """
    Fixed integrated workflow UI that properly displays all messages in UI sections
    instead of printing to console.
    
    Features:
    - Authentication links appear in UI instead of console
    - Component loading messages update proper UI sections
    - Status messages clear and update appropriately
    - Single authentication flow shared across all components
    """
    
    def __init__(self, 
                 config_manager: Optional[PortfolioConfigManager] = None,
                 config_path: str = "config/port_v2_config.json"):
        """
        Initialize the fixed integrated comprehensive workflow UI.
        
        Args:
            config_manager: Optional existing PortfolioConfigManager
            config_path: Path to Bloomberg configuration file
        """
        self.config_path = config_path
        
        # Get shared authentication manager (singleton)
        self.shared_auth = get_shared_auth_manager(config_path)
        
        # Component references - will be loaded after authentication
        self.report_handler = None
        self.orchestrator = None
        self.crossing_engine = None
        
        # Component loading state
        self.components_loaded = False
        self.loading_error = None
        
        # Initialize workflow state for sharing data
        self.workflow_state = WorkflowState()
        
        # Initialize analytics engine for generating analysis results
        self.analytics_engine = PortfolioAnalyticsEngine()
        
        # Create UI callbacks dictionary
        self.ui_callbacks = {
            'build_optimization_ui': self._build_optimization_ui,
            'build_crossing_ui': self._build_crossing_ui, 
            'build_charts_dashboard': self._build_charts_dashboard,
            'clear_all_tabs': self._clear_all_tabs
        }
        
        # UI component references
        self.config_ui = None
        self.optimization_ui = None
        self.crossing_ui = None
        self.dashboard_ui = None
        
        self.logger = logging.getLogger(__name__)
        
        # Create main UI structure
        self._create_main_interface(config_manager)
    
    def _create_main_interface(self, config_manager):
        """Create the main tabbed interface with fixed authentication UI."""
        
        # Tab 1: Fixed Authentication & Setup
        self.auth_container = self._create_fixed_auth_tab()
        
        # Tab 2: Configuration & Execution (starts disabled until authentication completes)
        self.config_container = self._create_config_placeholder()
        
        # Tabs 3-5: Start as placeholders
        self.optimization_container = self._create_placeholder_tab(
            "Optimization Results", 
            "Complete authentication and configuration, then run optimization to view results here."
        )
        
        self.crossing_container = self._create_placeholder_tab(
            "Crossing Results",
            "Run crossing analysis after optimization to view trade crossing opportunities."
        )
        
        self.dashboard_container = self._create_placeholder_tab(
            "Charts Dashboard",
            "Interactive charts will be available after running optimization and crossing analysis."
        )
        
        # Create tab widget
        self.tabs = widgets.Tab([
            self.auth_container,
            self.config_container,
            self.optimization_container, 
            self.crossing_container,
            self.dashboard_container
        ])
        
        # Add custom CSS class to the tab widget
        self.tabs.add_class("wide-tabs")
        
        # Set initial tab titles
        self._update_tab_titles()
        
        # CSS targeting the custom class
        css_style = """
        <style>
        .wide-tabs .p-TabBar-tab {
            min-width: 200px !important;
            flex: 0 0 auto !important;
            max-width: none !important;
        }
        
        .wide-tabs .p-TabBar-tabLabel {
            overflow: visible !important;
            text-overflow: clip !important;
        }
        
        .wide-tabs .p-TabBar {
            overflow-x: auto !important;
        }
        </style>
        """
        
        # Create main container
        self.main_container = widgets.VBox([
            widgets.HTML(css_style),
            widgets.HTML("<h1>Integrated Portfolio Optimization & Crossing Workflow</h1>"),
            widgets.HTML("<hr>"),
            self.tabs
        ])
    
    def _create_fixed_auth_tab(self) -> widgets.VBox:
        """Create fixed authentication tab with proper UI message routing."""
        
        # Overall status display
        self.overall_status = widgets.HTML(
            value="<b>Workflow Status:</b> Ready - authentication required",
            layout=widgets.Layout(margin='10px 0px')
        )
        
        # Create FIXED UI-based authentication manager 
        self.ui_auth_manager = FixedAuthenticationUIManager(self.config_path)
        
        # Create fixed authentication widgets
        self.auth_widgets = create_fixed_auth_ui_widgets(self.ui_auth_manager)
        
        # Component loading section with dedicated status and output
        self.component_status = widgets.HTML(
            value="<b>Component Status:</b> Waiting for authentication...",
            layout=widgets.Layout(margin='10px 0px')
        )
        
        self.component_output = widgets.HTML(
            value="<div style='font-family: monospace; font-size: 12px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px;'>Components will load automatically after authentication.</div>",
            layout=widgets.Layout(margin='10px 0px')
        )
        
        # Integrate authentication with component loading
        self._integrate_auth_with_component_loading()
        
        # Create the complete tab layout
        return widgets.VBox([
            widgets.HTML("<h2>Authentication & Setup</h2>"),
            widgets.HTML("<hr>"),
            self.overall_status,
            widgets.HTML("<hr>"),
            
            # Authentication section
            self.auth_widgets['full_container'],
            
            widgets.HTML("<hr>"),
            
            # Component loading section  
            widgets.HTML("<h3>Step 2: Component Loading</h3>"),
            widgets.HTML("<p>After authentication, workflow components will load automatically.</p>"),
            self.component_status,
            self.component_output
        ])
    
    def _integrate_auth_with_component_loading(self):
        """Integrate authentication completion with automatic component loading."""
        
        # Override the UI auth manager's completion to trigger component loading
        original_start_auth = self.ui_auth_manager.start_authentication_async
        
        def integrated_auth_start(completion_callback=None):
            """Enhanced authentication that automatically loads components."""
            
            def enhanced_completion_callback(success: bool, error: str):
                if success:
                    self._update_status("Authentication successful - loading components...")
                    
                    # IMPORTANT: Set the authenticated OAuth client in shared manager
                    if self.ui_auth_manager.oauth_client and self.ui_auth_manager.oauth_client.is_authenticated():
                        print("[DEBUG] Setting OAuth client in shared auth manager...")
                        self.shared_auth.set_oauth_client(self.ui_auth_manager.oauth_client)
                    else:
                        print("[DEBUG] UI auth manager OAuth client not properly authenticated")
                    
                    # Automatically load components in background
                    self._auto_load_components()
                    
                    if completion_callback:
                        completion_callback(True, None)
                else:
                    self._update_status(f"Authentication failed: {error}")
                    
                    if completion_callback:
                        completion_callback(False, error)
            
            return original_start_auth(enhanced_completion_callback)
        
        # Replace the UI auth manager's method
        self.ui_auth_manager.start_authentication_async = integrated_auth_start
    
    def _auto_load_components(self):
        """Automatically load workflow components after authentication with UI updates."""
        
        def load_components_worker():
            try:
                self._update_component_status("Loading workflow components...")
                self._add_component_log("Starting component loading...")
                
                # Load components using shared authentication
                self._load_all_components_with_shared_auth()
                
                # Create config UI
                self._create_enhanced_config_tab()
                
                # Update status
                self._update_status("Ready for portfolio configuration and execution")
                self._update_component_status("All components loaded successfully")
                self._add_component_log("All workflow components loaded successfully!")
                self._add_component_log("Ready for portfolio optimization workflow!")
                
                self.components_loaded = True
                
            except Exception as e:
                self.loading_error = str(e)
                self._update_status(f"Component loading failed: {str(e)}")
                self._update_component_status(f"Component loading failed: {str(e)}")
                self._add_component_log(f"ERROR: Component loading failed: {str(e)}")
        
        # Start component loading in background thread
        load_thread = threading.Thread(target=load_components_worker)
        load_thread.daemon = True
        load_thread.start()

    def get_oauth_client(self):
        """
        Get the authenticated OAuth client.
        
        Returns:
            CustomDeviceOAuth instance if authenticated, None otherwise
        """
        if self.oauth_client and self.oauth_client.is_authenticated():
            return self.oauth_client
        return None
    
    def _load_all_components_with_shared_auth(self):
        """Load all workflow components using shared authentication with UI updates."""
        
        self._add_component_log("Loading workflow components with shared authentication...")
        
        # Import here to avoid import issues
        # from optimization.request_builder import PortfolioOptimizerRequestBuilder
        # from core.orchestrator import OptimizationOrchestrator
        # from analytics.crossing_engine import CrossingResult, PortfolioCrossingEngine, CrossingEngineConfig
        # from core.portfolio_configs import PortfolioConfigManager, PORTFOLIO_CONFIGS
        
        self._add_component_log("Initializing UpdatedReportHandler with shared auth...")
        
        # Create report handler that uses shared authentication (no redundant auth)
        self.report_handler = UpdatedReportHandler(self.config_path)
        
        self._add_component_log("Setting up portfolio configuration manager...")
        config_manager = PortfolioConfigManager(PORTFOLIO_CONFIGS)
        
        self._add_component_log("Initializing request builder...")
        builder = PortfolioOptimizerRequestBuilder(
            template_path="config/portfolio_optimization_template.yml",
            config_manager=config_manager
        )
        
        self._add_component_log("Setting up optimization orchestrator...")
        self.orchestrator = OptimizationOrchestrator(
            report_handler=self.report_handler,
            config_manager=config_manager,
            builder=builder
        )
        
        self._add_component_log("Configuring crossing engine...")
        priority_list = ["S-17147", "P-36182", "P-47227", "P-93050", "P-61230"]
        crossing_config = CrossingEngineConfig(portfolio_priority=priority_list)
        self.crossing_engine = PortfolioCrossingEngine(crossing_config)
        
        self._add_component_log("Testing API connection via shared auth...")
        # Use the shared auth manager's test method directly
        success, details = self.shared_auth.test_connection()
        if success:
            self._add_component_log(f"API connection test successful: {details}")
        else:
            self._add_component_log(f"API connection test failed: {details}")
            raise RuntimeError(f"API connection failed: {details}")
    
    def _update_status(self, message: str):
        """Update the overall workflow status."""
        self.overall_status.value = f"<b>Workflow Status:</b> {message}"
    
    def _update_component_status(self, message: str):
        """Update the component loading status."""
        self.component_status.value = f"<b>Component Status:</b> {message}"
    
    def _add_component_log(self, message: str):
        """Add message to component loading log."""
        timestamp = time.strftime("%H:%M:%S")
        
        # Get current log content
        current_log = self.component_output.value
        
        # Extract existing content
        start_tag = "<div style='font-family: monospace"
        if start_tag in current_log:
            start_idx = current_log.find('>') + 1
            end_idx = current_log.rfind('</div>')
            
            if start_idx > 0 and end_idx > start_idx:
                existing_content = current_log[start_idx:end_idx]
                # Replace initial message if it's still there
                if "Components will load automatically" in existing_content:
                    existing_content = ""
            else:
                existing_content = ""
        else:
            existing_content = ""
        
        # Add new log line
        log_line = f"<div style='color: #343a40; margin: 1px 0;'>[{timestamp}] {message}</div>"
        new_content = existing_content + log_line
        
        # Update display
        self.component_output.value = f"<div style='font-family: monospace; font-size: 12px; padding: 10px; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px; max-height: 300px; overflow-y: auto;'>{new_content}</div>"
    
    def _create_config_placeholder(self) -> widgets.VBox:
        """Create placeholder for config UI until authentication completes."""
        return widgets.VBox([
            widgets.HTML(f"""
                <div style='text-align: center; padding: 50px; color: #666;'>
                    <h3>Portfolio Configuration - Not Available Yet</h3>
                    <p>Complete authentication in the first tab to enable configuration.</p>
                </div>
            """)
        ])
    
    def _create_enhanced_config_tab(self):
        """Create the enhanced configuration tab after authentication completes."""
        
        # Get config manager
        config_manager = PortfolioConfigManager(PORTFOLIO_CONFIGS)
        
        # Create enhanced config UI with all execution components
        self.config_ui = PortfolioConfigUI(
            config_manager=config_manager,
            report_handler=self.report_handler,
            orchestrator=self.orchestrator,
            crossing_engine=self.crossing_engine,
            workflow_state=self.workflow_state,
            ui_callbacks=self.ui_callbacks
        )
        
        # Replace the placeholder with the real config UI
        self.config_container = widgets.VBox([self.config_ui.main_layout])
        
        # Update the tab
        tab_children = list(self.tabs.children)
        tab_children[1] = self.config_container
        self.tabs.children = tab_children
        
        # Update tab titles
        self._update_tab_titles()
    
    def _create_placeholder_tab(self, title: str, message: str) -> widgets.VBox:
        """Create placeholder tab content."""
        return widgets.VBox([
            widgets.HTML(f"""
                <div style='text-align: center; padding: 50px; color: #666;'>
                    <h3>{title} - Not Available Yet</h3>
                    <p>{message}</p>
                </div>
            """)
        ])
    
    def _update_tab_titles(self):
        """Update tab titles to show progress and availability."""
        
        # Tab 1: Authentication & Setup
        if self.shared_auth.is_ready() and self.components_loaded:
            self.tabs.set_title(0, "Auth & Setup ✓")
        elif self.shared_auth.is_ready():
            self.tabs.set_title(0, "Auth ✓ - Loading...")
        else:
            self.tabs.set_title(0, "Auth & Setup")
        
        # Tab 2: Configuration
        if self.components_loaded:
            self.tabs.set_title(1, "Config & Execution ✓")
        else:
            self.tabs.set_title(1, "Config & Execution")
        
        # Tab 3: Optimization results
        if self.workflow_state.is_ready_for_optimization_ui():
            self.tabs.set_title(2, "Optimization Results ✓")
        else:
            self.tabs.set_title(2, "Optimization Results")
        
        # Tab 4: Crossing results  
        if self.workflow_state.is_ready_for_crossing_ui():
            self.tabs.set_title(3, "Crossing Results ✓")
        else:
            self.tabs.set_title(3, "Crossing Results")
        
        # Tab 5: Charts dashboard
        if self.workflow_state.is_ready_for_charts_dashboard():
            self.tabs.set_title(4, "Charts Dashboard ✓")
        else:
            self.tabs.set_title(4, "Charts Dashboard")
    
    # === UI CALLBACK METHODS (Called by config UI) ===
    
    def _build_optimization_ui(self):
        """Build optimization results UI when data becomes available."""
        try:
            self.logger.info("Building optimization results UI...")
            
            # Get data from workflow state
            batch_results = self.workflow_state.optimization_results
            analysis_results = self.workflow_state.analysis_results
            
            if not batch_results:
                self.logger.warning("No optimization results available for UI building")
                return
            
            # Create optimization results UI
            self.optimization_ui = OptimizationResultsUI(batch_results, analysis_results)
            
            # Replace placeholder with real UI
            self.optimization_container = widgets.VBox([self.optimization_ui.main_widget])
            
            # Update the tab
            tab_children = list(self.tabs.children)
            tab_children[2] = self.optimization_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            # Generate charts if visualization managers are available
            if CHARTS_AVAILABLE:
                self._generate_portfolio_charts(batch_results, analysis_results)
            
            self.logger.info(f"Optimization UI built successfully for {len(batch_results)} portfolios")
            
        except Exception as e:
            self.logger.error(f"Error building optimization UI: {str(e)}")
            self._show_error_in_tab(2, f"Error loading optimization results: {str(e)}")
    
    def _build_crossing_ui(self):
        """Build crossing results UI when data becomes available."""
        try:
            self.logger.info("Building crossing results UI...")
            
            # Get crossing result from workflow state
            crossing_result = self.workflow_state.crossing_result
            
            if not crossing_result:
                self.logger.warning("No crossing result available for UI building")
                return
            
            # Create crossing results UI
            self.crossing_ui = CrossingResultsUI(crossing_result)
            
            # Replace placeholder with real UI
            self.crossing_container = widgets.VBox([self.crossing_ui.main_widget])
            
            # Update the tab
            tab_children = list(self.tabs.children)
            tab_children[3] = self.crossing_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            # Generate crossing charts if visualization managers are available
            if CHARTS_AVAILABLE:
                self._generate_crossing_charts(crossing_result)
            
            self.logger.info("Crossing UI built successfully")
            
        except Exception as e:
            self.logger.error(f"Error building crossing UI: {str(e)}")
            self._show_error_in_tab(3, f"Error loading crossing results: {str(e)}")
    
    def _build_charts_dashboard(self):
        """Build charts dashboard when chart data becomes available."""
        try:
            self.logger.info("Building charts dashboard...")
            
            # Get available charts from workflow state
            combined_charts = self.workflow_state.get_combined_charts()
            
            if not combined_charts:
                self.logger.warning("No charts available for dashboard building")
                return
            
            # Create dashboard with available charts
            self.dashboard_ui = UnifiedDashboardManager(
                chart_sources=combined_charts,
                dashboard_title="Comprehensive Analysis Dashboard"
            )
            
            # Replace placeholder with dashboard
            self.dashboard_container = widgets.VBox([self.dashboard_ui.dashboard])
            
            # Update the tab
            tab_children = list(self.tabs.children)
            tab_children[4] = self.dashboard_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            chart_count = sum(len(charts) for charts in combined_charts.values())
            self.logger.info(f"Charts dashboard built successfully with {chart_count} charts")
            
        except Exception as e:
            self.logger.error(f"Error building charts dashboard: {str(e)}")
            self._show_error_in_tab(4, f"Error loading charts dashboard: {str(e)}")
    
    def _clear_all_tabs(self):
        """Clear all result tabs back to placeholder state (called on errors)."""
        try:
            self.logger.info("Clearing all result tabs...")
            
            # Reset to placeholders
            self.optimization_container = self._create_placeholder_tab(
                "Optimization Results",
                "Optimization failed or was reset. Configure and run optimization again."
            )
            
            self.crossing_container = self._create_placeholder_tab(
                "Crossing Results", 
                "No crossing data available. Run optimization first, then crossing analysis."
            )
            
            self.dashboard_container = self._create_placeholder_tab(
                "Charts Dashboard",
                "No charts available. Run optimization and crossing to generate interactive charts."
            )
            
            # Update all tabs
            self.tabs.children = [
                self.auth_container,
                self.config_container,
                self.optimization_container,
                self.crossing_container, 
                self.dashboard_container
            ]
            
            # Clear UI references
            self.optimization_ui = None
            self.crossing_ui = None
            self.dashboard_ui = None
            
            # Update tab titles
            self._update_tab_titles()
            
            self.logger.info("All result tabs cleared successfully")
            
        except Exception as e:
            self.logger.error(f"Error clearing tabs: {str(e)}")
    
    # === CHART GENERATION METHODS ===
    
    def _generate_portfolio_charts(self, batch_results, analysis_results):
        """Generate portfolio analysis charts and store in workflow state."""
        try:
            if not CHARTS_AVAILABLE:
                self.logger.info("Chart generation skipped - visualization managers not available")
                return
            
            self.logger.info("Generating portfolio analysis charts...")
            
            # Generate charts for the first successful portfolio
            for portfolio_id, result in batch_results.items():
                if (result.status == "SUCCESS" and 
                    result.clean_holdings_data is not None and
                    result.proposed_trades_df is not None):
                    
                    # Get analysis result for this portfolio
                    analysis_result = analysis_results.get(portfolio_id)
                    if analysis_result:
                        # Generate charts using portfolio visualization manager
                        viz_manager = PortfolioVisualizationManager(analysis_result)
                        portfolio_charts = viz_manager.create_all_charts()
                        
                        # Store in workflow state
                        self.workflow_state.set_portfolio_charts(portfolio_charts)
                        
                        self.logger.info(f"Generated {len(portfolio_charts)} portfolio charts")
                        
                        # Trigger dashboard build
                        self._build_charts_dashboard()
                        break
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio charts: {str(e)}")
    
    def _generate_crossing_charts(self, crossing_result):
        """Generate crossing analysis charts and store in workflow state."""
        try:
            if not CHARTS_AVAILABLE:
                self.logger.info("Crossing chart generation skipped - visualization managers not available")
                return
            
            self.logger.info("Generating crossing analysis charts...")
            
            # Generate charts using crossing visualization manager
            viz_manager = CrossingVisualizationManager(crossing_result)
            crossing_charts = viz_manager.create_all_charts()
            
            # Store in workflow state
            self.workflow_state.set_crossing_charts(crossing_charts)
            
            self.logger.info(f"Generated {len(crossing_charts)} crossing charts")
            
            # Trigger dashboard build/update
            self._build_charts_dashboard()
            
        except Exception as e:
            self.logger.error(f"Error generating crossing charts: {str(e)}")
    
    # === UTILITY METHODS ===
    
    def _show_error_in_tab(self, tab_index: int, error_message: str):
        """Show error message in specific tab."""
        error_container = widgets.VBox([
            widgets.HTML(f"""
                <div style='text-align: center; padding: 50px; color: #d32f2f;'>
                    <h3>Error</h3>
                    <p>{error_message}</p>
                    <p><i>Check the execution log in the configuration tab for details.</i></p>
                </div>
            """)
        ])
        
        # Update the specific tab
        tab_children = list(self.tabs.children)
        tab_children[tab_index] = error_container
        self.tabs.children = tab_children
    
    def navigate_to_tab(self, tab_index: int):
        """Navigate to a specific tab."""
        if 0 <= tab_index < len(self.tabs.children):
            self.tabs.selected_index = tab_index
        else:
            self.logger.warning(f"Invalid tab index: {tab_index}")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get comprehensive workflow status."""
        return {
            'authentication_completed': self.shared_auth.is_ready(),
            'components_loaded': self.components_loaded,
            'workflow_state': self.workflow_state.get_status_summary(),
            'ui_components': {
                'config_ui': self.config_ui is not None,
                'optimization_ui': self.optimization_ui is not None,
                'crossing_ui': self.crossing_ui is not None,
                'dashboard_ui': self.dashboard_ui is not None
            },
            'execution_components': {
                'report_handler': self.report_handler is not None,
                'orchestrator': self.orchestrator is not None,
                'crossing_engine': self.crossing_engine is not None
            }
        }
    
    def reset_workflow(self):
        """Reset entire workflow to initial state."""
        try:
            self.logger.info("Resetting entire workflow...")
            
            # Reset workflow state
            self.workflow_state.reset_all()
            
            # Clear authentication
            self.shared_auth.clear_authentication()
            
            # Reset component loading state
            self.components_loaded = False
            self.loading_error = None
            
            # Clear all tabs
            self._clear_all_tabs()
            
            # Reset config UI placeholder
            self.config_container = self._create_config_placeholder()
            
            # Navigate back to authentication tab
            self.navigate_to_tab(0)
            
            # Update status
            self._update_status("Reset complete - authentication required")
            
            self.logger.info("Workflow reset completed")
            
        except Exception as e:
            self.logger.error(f"Error resetting workflow: {str(e)}")
    
    def display(self):
        """Display the fixed integrated comprehensive workflow UI."""
        display(self.main_container)


def create_fixed_integrated_comprehensive_workflow_ui(config_manager: Optional[PortfolioConfigManager] = None,
                                                    config_path: str = "config/port_v2_config.json") -> FixedIntegratedComprehensiveWorkflowUI:
    """
    Create and display the fixed integrated comprehensive workflow UI.
    
    This version fixes all UI message routing issues:
    - Authentication links appear in UI instead of console
    - Component loading messages update proper UI sections  
    - Status messages clear and update appropriately
    - Single authentication flow shared across all components
    
    Args:
        config_manager: Optional existing PortfolioConfigManager
        config_path: Path to Bloomberg configuration file
        
    Returns:
        FixedIntegratedComprehensiveWorkflowUI instance
    """
    ui = FixedIntegratedComprehensiveWorkflowUI(
        config_manager=config_manager,
        config_path=config_path
    )
    ui.display()
    return ui



if __name__ == "__main__":
    # Create fixed integrated workflow UI
    workflow_ui = create_fixed_integrated_comprehensive_workflow_ui()
    pass