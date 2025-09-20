import ipywidgets as widgets
from IPython.display import display
from typing import Dict, Optional, Any
import logging

# Import the enhanced UI components
from portfolio_config_ui import PortfolioConfigUI  # This is the enhanced v11 version
from optimization_results_ui import OptimizationResultsUI, create_analysis_results_for_batch
from crossing_results_ui import CrossingResultsUI
from dashboard_manager import UnifiedDashboardManager

# Import data structures
from orchestrator import OptimizationResult
from portfolio_analytics_engine import PortfolioComparisonResult, PortfolioAnalyticsEngine
from crossing_engine import CrossingResult
from portfolio_configs import PortfolioConfigManager
from workflow_state import WorkflowState

# Import visualization managers for chart generation
try:
    from plot_manager import PortfolioVisualizationManager
    from crossing_visualization_manager import CrossingVisualizationManager
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logging.warning("Chart visualization managers not available")

class ComprehensiveWorkflowUI:
    """
    Enhanced workflow UI with reactive tab building.
    
    Features:
    - Tab 1: Enhanced config UI with execution capabilities
    - Tabs 2-4: Dynamically built when data becomes available
    - Automatic chart generation and dashboard updates
    """
    
    def __init__(self, 
                 config_manager: Optional[PortfolioConfigManager] = None,
                 report_handler=None,
                 orchestrator=None,
                 crossing_engine=None):
        """
        Initialize the comprehensive workflow UI.
        
        Args:
            config_manager: Optional existing PortfolioConfigManager
            report_handler: ReportHandler instance for data retrieval
            orchestrator: OptimizationOrchestrator instance
            crossing_engine: PortfolioCrossingEngine instance
        """
        self.report_handler = report_handler
        self.orchestrator = orchestrator
        self.crossing_engine = crossing_engine
        
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
        """Create the main tabbed interface with enhanced config UI."""
        
        # Tab 1: Enhanced Configuration UI with execution capabilities
        self.config_container = self._create_enhanced_config_tab(config_manager)
        
        # Tabs 2-4: Start as placeholders
        self.optimization_container = self._create_placeholder_tab(
            "Optimization Results", 
            "Configure portfolios and run optimization to view results here."
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
            self.config_container,
            self.optimization_container, 
            self.crossing_container,
            self.dashboard_container
        ])
        
        # Set initial tab titles
        self._update_tab_titles()
        
        # Create main container
        self.main_container = widgets.VBox([
            widgets.HTML("<h1>Portfolio Optimization & Crossing Workflow</h1>"),
            widgets.HTML("<hr>"),
            self.tabs
        ])
    
    def _create_enhanced_config_tab(self, config_manager) -> widgets.VBox:
        """Create the enhanced configuration tab with execution capabilities."""
        
        # Create enhanced config UI with all execution components
        self.config_ui = PortfolioConfigUI(
            config_manager=config_manager,
            report_handler=self.report_handler,
            orchestrator=self.orchestrator,
            crossing_engine=self.crossing_engine,
            workflow_state=self.workflow_state,
            ui_callbacks=self.ui_callbacks
        )
        
        return widgets.VBox([self.config_ui.main_layout])
    
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
        """Update tab titles to show data availability status."""
        
        # Tab 1: Always available
        self.tabs.set_title(0, "1. Configuration & Execution")
        
        # Tab 2: Optimization results
        if self.workflow_state.is_ready_for_optimization_ui():
            self.tabs.set_title(1, "2. Optimization Results ✓")
        else:
            self.tabs.set_title(1, "2. Optimization Results")
        
        # Tab 3: Crossing results  
        if self.workflow_state.is_ready_for_crossing_ui():
            self.tabs.set_title(2, "3. Crossing Results ✓")
        else:
            self.tabs.set_title(2, "3. Crossing Results")
        
        # Tab 4: Charts dashboard
        if self.workflow_state.is_ready_for_charts_dashboard():
            self.tabs.set_title(3, "4. Charts Dashboard ✓")
        else:
            self.tabs.set_title(3, "4. Charts Dashboard")
    
    # === UI CALLBACK METHODS (Called by enhanced config UI) ===
    
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
            tab_children[1] = self.optimization_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            # Generate charts if visualization managers are available
            if CHARTS_AVAILABLE:
                self._generate_portfolio_charts(batch_results, analysis_results)
            
            self.logger.info(f"Optimization UI built successfully for {len(batch_results)} portfolios")
            
        except Exception as e:
            self.logger.error(f"Error building optimization UI: {str(e)}")
            self._show_error_in_tab(1, f"Error loading optimization results: {str(e)}")
    
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
            tab_children[2] = self.crossing_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            # Generate crossing charts if visualization managers are available
            if CHARTS_AVAILABLE:
                self._generate_crossing_charts(crossing_result)
            
            self.logger.info("Crossing UI built successfully")
            
        except Exception as e:
            self.logger.error(f"Error building crossing UI: {str(e)}")
            self._show_error_in_tab(2, f"Error loading crossing results: {str(e)}")
    
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
            tab_children[3] = self.dashboard_container
            self.tabs.children = tab_children
            
            # Update tab titles
            self._update_tab_titles()
            
            chart_count = sum(len(charts) for charts in combined_charts.values())
            self.logger.info(f"Charts dashboard built successfully with {chart_count} charts")
            
        except Exception as e:
            self.logger.error(f"Error building charts dashboard: {str(e)}")
            self._show_error_in_tab(3, f"Error loading charts dashboard: {str(e)}")
    
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
            
            # For now, generate charts for the first successful portfolio
            # You could extend this to generate charts for all portfolios
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
            
            # Clear all tabs
            self._clear_all_tabs()
            
            # Navigate back to configuration tab
            self.navigate_to_tab(0)
            
            # Reset config UI if needed
            if self.config_ui:
                self.config_ui.execution_status = "ready"
                self.config_ui._set_execution_state("ready")
            
            self.logger.info("Workflow reset completed")
            
        except Exception as e:
            self.logger.error(f"Error resetting workflow: {str(e)}")
    
    def display(self):
        """Display the comprehensive workflow UI."""
        display(self.main_container)


def create_comprehensive_workflow_ui(config_manager: Optional[PortfolioConfigManager] = None,
                                   report_handler=None,
                                   orchestrator=None, 
                                   crossing_engine=None) -> ComprehensiveWorkflowUI:
    """
    Create and display the comprehensive workflow UI with reactive tab building.
    
    Args:
        config_manager: Optional existing PortfolioConfigManager
        report_handler: ReportHandler instance for data retrieval
        orchestrator: OptimizationOrchestrator instance
        crossing_engine: PortfolioCrossingEngine instance
        
    Returns:
        ComprehensiveWorkflowUI instance
    """
    ui = ComprehensiveWorkflowUI(
        config_manager=config_manager,
        report_handler=report_handler,
        orchestrator=orchestrator,
        crossing_engine=crossing_engine
    )
    ui.display()
    return ui


# Example usage
if __name__ == "__main__":
    # Create workflow UI with execution components
    # workflow_ui = create_comprehensive_workflow_ui(
    #     report_handler=report_handler,
    #     orchestrator=orchestrator,
    #     crossing_engine=crossing_engine
    # )
    pass