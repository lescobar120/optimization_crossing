import ipywidgets as widgets
from IPython.display import display
from typing import Dict, Optional, Any
import logging

# Import the individual UI components
from portfolio_config_ui import PortfolioConfigUI, create_portfolio_config_ui
from optimization_results_ui import OptimizationResultsUI, create_optimization_results_ui
from crossing_results_ui import CrossingResultsUI, create_crossing_results_ui
from dashboard_manager import UnifiedDashboardManager, create_mixed_dashboard

# Import data structures
from orchestrator import OptimizationResult
from portfolio_analytics_engine import PortfolioComparisonResult
from crossing_engine import CrossingResult
from portfolio_configs import PortfolioConfigManager

class ComprehensiveWorkflowUI:
    """
    Comprehensive tabbed UI for the complete portfolio optimization and crossing workflow.
    
    Provides four main tabs:
    1. Configuration - Portfolio settings and parameters
    2. Optimization Results - Detailed optimization output and analysis
    3. Crossing Results - Trade crossing analysis and external liquidity needs
    4. Charts Dashboard - Interactive visualization dashboard
    """
    
    def __init__(self, 
                 config_manager: Optional[PortfolioConfigManager] = None,
                 optimization_results: Optional[Dict[str, OptimizationResult]] = None,
                 analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None,
                 crossing_result: Optional[CrossingResult] = None,
                 crossing_charts: Optional[Dict[str, Any]] = None,
                 portfolio_charts: Optional[Dict[str, Any]] = None):
        """
        Initialize the comprehensive workflow UI.
        
        Args:
            config_manager: Optional existing PortfolioConfigManager
            optimization_results: Optional optimization results to pre-load
            analysis_results: Optional analysis results to pre-load
            crossing_result: Optional crossing result to pre-load
            crossing_charts: Optional crossing charts to pre-load
            portfolio_charts: Optional portfolio charts to pre-load
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Data storage for results
        self.optimization_results = optimization_results or {}
        self.analysis_results = analysis_results or {}
        self.crossing_result = crossing_result
        
        # Charts data
        self.charts_data = {}
        if crossing_charts:
            self.charts_data['crossing'] = crossing_charts
        if portfolio_charts:
            self.charts_data['portfolio'] = portfolio_charts
        
        # UI component references
        self.config_ui = None
        self.optimization_ui = None
        self.crossing_ui = None
        self.dashboard_ui = None
        
        # Create main UI structure
        self._create_main_interface()
    
    def _create_main_interface(self):
        """Create the main tabbed interface using VBox containers."""
        
        # Create content containers for each tab
        self.config_container = self._create_config_tab()
        self.optimization_container = self._create_optimization_tab()
        self.crossing_container = self._create_crossing_tab()
        self.dashboard_container = self._create_dashboard_tab()
        
        # Create tab widget
        self.tabs = widgets.Tab([
            self.config_container,
            self.optimization_container,
            self.crossing_container,
            self.dashboard_container
        ])
        
        # Set tab titles with checkmarks for available data
        self._update_tab_titles()
        
        # Create main container with header
        self.main_container = widgets.VBox([
            widgets.HTML("<h1>Portfolio Optimization & Crossing Workflow</h1>"),
            widgets.HTML("<hr>"),
            self.tabs
        ])
    
    def _create_config_tab(self) -> widgets.VBox:
        """Create the configuration tab content."""
        if self.config_ui is None:
            self.config_ui = PortfolioConfigUI(self.config_manager)
            if self.config_manager is None:
                self.config_manager = self.config_ui.get_config_manager()
        
        return widgets.VBox([self.config_ui.main_layout])
    
    def _create_optimization_tab(self) -> widgets.VBox:
        """Create the optimization results tab content."""
        if not self.optimization_results:
            return widgets.VBox([
                widgets.HTML("""
                    <div style='text-align: center; padding: 50px; color: #666;'>
                        <h3>No Optimization Results Available</h3>
                        <p>Run portfolio optimization to view results here.</p>
                        <p>Use the <code>update_optimization_results()</code> method to populate this tab.</p>
                    </div>
                """)
            ])
        else:
            if self.optimization_ui is None:
                self.optimization_ui = OptimizationResultsUI(
                    self.optimization_results, 
                    self.analysis_results
                )
            return widgets.VBox([self.optimization_ui.main_widget])
    
    def _create_crossing_tab(self) -> widgets.VBox:
        """Create the crossing results tab content."""
        if self.crossing_result is None:
            return widgets.VBox([
                widgets.HTML("""
                    <div style='text-align: center; padding: 50px; color: #666;'>
                        <h3>No Crossing Results Available</h3>
                        <p>Run crossing analysis to view results here.</p>
                        <p>Use the <code>update_crossing_results()</code> method to populate this tab.</p>
                    </div>
                """)
            ])
        else:
            if self.crossing_ui is None:
                self.crossing_ui = CrossingResultsUI(self.crossing_result)
            return widgets.VBox([self.crossing_ui.main_widget])
    
    def _create_dashboard_tab(self) -> widgets.VBox:
        """Create the charts dashboard tab content."""
        if not self.charts_data:
            return widgets.VBox([
                widgets.HTML("""
                    <div style='text-align: center; padding: 50px; color: #666;'>
                        <h3>No Charts Available</h3>
                        <p>Generate analysis charts to view dashboard here.</p>
                        <p>Use the <code>update_charts_data()</code> method to populate this tab.</p>
                    </div>
                """)
            ])
        else:
            if self.dashboard_ui is None:
                self.dashboard_ui = UnifiedDashboardManager(
                    chart_sources=self.charts_data,
                    dashboard_title="Comprehensive Analysis Dashboard"
                )
            return widgets.VBox([self.dashboard_ui.dashboard])
    
    def _update_tab_titles(self):
        """Update tab titles to show data availability."""
        self.tabs.set_title(0, "1. Configuration")
        
        opt_title = "2. Optimization Results"
        if self.optimization_results:
            opt_title += ""
        self.tabs.set_title(1, opt_title)
        
        crossing_title = "3. Crossing Results"
        if self.crossing_result:
            crossing_title += ""
        self.tabs.set_title(2, crossing_title)
        
        charts_title = "4. Charts Dashboard"
        if self.charts_data:
            charts_title += ""
        self.tabs.set_title(3, charts_title)
    
    def update_optimization_results(self, 
                                  batch_results: Dict[str, OptimizationResult],
                                  analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None):
        """
        Update optimization results data and refresh the tab.
        
        Args:
            batch_results: Dictionary of portfolio_id -> OptimizationResult
            analysis_results: Optional dictionary of portfolio_id -> PortfolioComparisonResult
        """
        self.optimization_results = batch_results
        if analysis_results:
            self.analysis_results = analysis_results
        
        # Recreate the optimization UI
        self.optimization_ui = None
        new_container = self._create_optimization_tab()
        
        # Replace the tab content
        tab_children = list(self.tabs.children)
        tab_children[1] = new_container
        self.tabs.children = tab_children
        
        # Update tab title
        self._update_tab_titles()
        
        self.logger.info(f"Updated optimization results for {len(batch_results)} portfolios")
    
    def update_crossing_results(self, crossing_result: CrossingResult):
        """
        Update crossing results data and refresh the tab.
        
        Args:
            crossing_result: CrossingResult from crossing analysis
        """
        self.crossing_result = crossing_result
        
        # Recreate the crossing UI
        self.crossing_ui = None
        new_container = self._create_crossing_tab()
        
        # Replace the tab content
        tab_children = list(self.tabs.children)
        tab_children[2] = new_container
        self.tabs.children = tab_children
        
        # Update tab title
        self._update_tab_titles()
        
        self.logger.info("Updated crossing results")
    
    def update_charts_data(self, 
                          crossing_charts: Optional[Dict[str, Any]] = None,
                          portfolio_charts: Optional[Dict[str, Any]] = None):
        """
        Update charts data and refresh the dashboard.
        
        Args:
            crossing_charts: Dictionary of crossing analysis charts
            portfolio_charts: Dictionary of portfolio analysis charts
        """
        if crossing_charts:
            self.charts_data['crossing'] = crossing_charts
        
        if portfolio_charts:
            self.charts_data['portfolio'] = portfolio_charts
        
        # Recreate the dashboard UI
        self.dashboard_ui = None
        new_container = self._create_dashboard_tab()
        
        # Replace the tab content
        tab_children = list(self.tabs.children)
        tab_children[3] = new_container
        self.tabs.children = tab_children
        
        # Update tab title
        self._update_tab_titles()
        
        chart_sources = []
        if crossing_charts:
            chart_sources.append(f"{len(crossing_charts)} crossing")
        if portfolio_charts:
            chart_sources.append(f"{len(portfolio_charts)} portfolio")
        
        self.logger.info(f"Updated charts data: {', '.join(chart_sources)} charts")
    
    def refresh_all_tabs(self):
        """Force refresh all tabs by recreating their content."""
        # Recreate all tab containers
        new_children = [
            self._create_config_tab(),
            self._create_optimization_tab(),
            self._create_crossing_tab(),
            self._create_dashboard_tab()
        ]
        
        self.tabs.children = new_children
        self._update_tab_titles()
        
        self.logger.info("Refreshed all tabs")
    
    def get_config_manager(self) -> Optional[PortfolioConfigManager]:
        """Get the current configuration manager."""
        if self.config_ui:
            return self.config_ui.get_config_manager()
        return self.config_manager
    
    def get_global_settings(self) -> Optional[Dict[str, Any]]:
        """Get the current global settings from configuration."""
        if self.config_ui:
            return self.config_ui.get_global_settings()
        return None
    
    def navigate_to_tab(self, tab_index: int):
        """
        Navigate to a specific tab.
        
        Args:
            tab_index: Tab index (0=Config, 1=Optimization, 2=Crossing, 3=Charts)
        """
        if 0 <= tab_index < len(self.tabs.children):
            self.tabs.selected_index = tab_index
        else:
            self.logger.warning(f"Invalid tab index: {tab_index}")
    
    def get_workflow_status(self) -> Dict[str, bool]:
        """
        Get the status of each workflow component.
        
        Returns:
            Dictionary indicating completion status of each step
        """
        return {
            'configuration_set': self.config_ui is not None,
            'optimization_complete': bool(self.optimization_results),
            'crossing_complete': self.crossing_result is not None,
            'charts_available': bool(self.charts_data)
        }
    
    def reset_workflow(self):
        """Reset all workflow data and UI components."""
        # Clear data
        self.optimization_results = {}
        self.analysis_results = {}
        self.crossing_result = None
        self.charts_data = {}
        
        # Clear UI references
        self.optimization_ui = None
        self.crossing_ui = None
        self.dashboard_ui = None
        
        # Refresh all tabs
        self.refresh_all_tabs()
        
        # Navigate back to configuration
        self.navigate_to_tab(0)
        
        self.logger.info("Workflow reset")
    
    def display(self):
        """Display the comprehensive workflow UI."""
        display(self.main_container)


def create_comprehensive_workflow_ui(config_manager: Optional[PortfolioConfigManager] = None,
                                   optimization_results: Optional[Dict[str, OptimizationResult]] = None,
                                   analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None,
                                   crossing_result: Optional[CrossingResult] = None,
                                   crossing_charts: Optional[Dict[str, Any]] = None,
                                   portfolio_charts: Optional[Dict[str, Any]] = None) -> ComprehensiveWorkflowUI:
    """
    Convenience function to create and display the comprehensive workflow UI.
    
    Args:
        config_manager: Optional existing PortfolioConfigManager
        optimization_results: Optional optimization results to pre-load
        analysis_results: Optional analysis results to pre-load
        crossing_result: Optional crossing result to pre-load
        crossing_charts: Optional crossing charts to pre-load
        portfolio_charts: Optional portfolio charts to pre-load
        
    Returns:
        ComprehensiveWorkflowUI instance
    """
    ui = ComprehensiveWorkflowUI(
        config_manager=config_manager,
        optimization_results=optimization_results,
        analysis_results=analysis_results,
        crossing_result=crossing_result,
        crossing_charts=crossing_charts,
        portfolio_charts=portfolio_charts
    )
    ui.display()
    return ui


# Example usage functions for integration
def example_workflow_integration():
    """
    Example of how to use the comprehensive UI with pre-loaded data.
    """
    # Option 1: Create empty workflow and populate later
    workflow_ui = create_comprehensive_workflow_ui()
    
    # Option 2: Pre-load with optimization results
    # workflow_ui = create_comprehensive_workflow_ui(
    #     optimization_results=batch_results,
    #     analysis_results=analysis_results
    # )
    
    # Option 3: Pre-load with all data
    # workflow_ui = create_comprehensive_workflow_ui(
    #     config_manager=config_manager,
    #     optimization_results=batch_results,
    #     analysis_results=analysis_results,
    #     crossing_result=crossing_result,
    #     crossing_charts=crossing_charts,
    #     portfolio_charts=portfolio_charts
    # )
    
    return workflow_ui


if __name__ == "__main__":
    # This would be used in a Jupyter notebook like:
    # workflow_ui = create_comprehensive_workflow_ui()
    pass