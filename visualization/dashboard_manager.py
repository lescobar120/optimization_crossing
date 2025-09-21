import ipywidgets as widgets
import plotly.graph_objects as go
from IPython.display import display
from typing import Dict, List, Optional, Any, Union
import logging
from enum import Enum

class DashboardType(Enum):
    """Enum for different dashboard types."""
    CROSSING = "crossing"
    PORTFOLIO = "portfolio"
    MIXED = "mixed"

class UnifiedDashboardManager:
    """
    Unified dashboard manager for displaying analysis charts from multiple sources.
    
    Supports crossing analysis, portfolio optimization analysis, and mixed dashboards
    with consistent 2x2 grid layout and chart selection capabilities.
    """
    
    def __init__(self, 
                 chart_sources: Dict[str, Dict[str, go.Figure]], 
                 dashboard_type: DashboardType = DashboardType.MIXED,
                 default_charts: Optional[List[str]] = None,
                 dashboard_title: str = "Analysis Dashboard"):
        """
        Initialize the unified dashboard manager.
        
        Args:
            chart_sources: Dictionary of source_name -> {chart_name -> Figure}
                          e.g., {"crossing": crossing_charts, "portfolio": portfolio_charts}
            dashboard_type: Type of dashboard (CROSSING, PORTFOLIO, or MIXED)
            default_charts: List of 4 chart names for default display
            dashboard_title: Title for the dashboard
        """
        self.chart_sources = chart_sources
        self.dashboard_type = dashboard_type
        self.dashboard_title = dashboard_title
        
        # Flatten all charts into single dictionary with prefixed names
        self.all_charts = self._flatten_chart_sources()
        self.chart_names = list(self.all_charts.keys())
        
        # Set default charts
        if default_charts is None:
            self.default_charts = self._get_default_chart_selection()
        else:
            if len(default_charts) != 4:
                raise ValueError("default_charts must contain exactly 4 chart names")
            self.default_charts = default_charts
        
        # Create UI components
        self._create_widgets()
        self._setup_layout()
        self._setup_event_handlers()
        
        self.logger = logging.getLogger(__name__)
    
    def _flatten_chart_sources(self) -> Dict[str, go.Figure]:
        """Flatten chart sources into single dictionary with prefixed names."""
        flattened = {}
        
        for source_name, charts in self.chart_sources.items():
            for chart_name, figure in charts.items():
                # Create prefixed name: "crossing_portfolio_matrix" or "portfolio_treemap"
                prefixed_name = f"{source_name}_{chart_name}"
                flattened[prefixed_name] = figure
        
        return flattened
    
    def _get_default_chart_selection(self) -> List[str]:
        """Select 4 most useful charts as defaults based on dashboard type."""
        
        if self.dashboard_type == DashboardType.CROSSING:
            priority_order = [
                'crossing_crossing_efficiency_kpis',
                'crossing_portfolio_crossing_matrix',
                'crossing_crossing_flow_sankey',
                'crossing_external_liquidity_waterfall'
            ]
        elif self.dashboard_type == DashboardType.PORTFOLIO:
            priority_order = [
                'portfolio_deviation_impact_treemap',
                'portfolio_weight_change_sankey',
                'portfolio_active_sector_weight_distribution',
                'portfolio_sector_weight_radar_comparison'
            ]
        else:  # MIXED
            priority_order = [
                'portfolio_sector_weight_radar_comparison'
                'portfolio_active_sector_weight_distribution',
                'crossing_crossing_efficiency_kpis',
                'crossing_portfolio_crossing_matrix', 
            ]
        
        defaults = []
        for chart_name in priority_order:
            if chart_name in self.chart_names:
                defaults.append(chart_name)
                if len(defaults) == 4:
                    break
        
        # Fill remaining slots if needed
        while len(defaults) < 4 and len(defaults) < len(self.chart_names):
            for chart_name in self.chart_names:
                if chart_name not in defaults:
                    defaults.append(chart_name)
                    if len(defaults) == 4:
                        break
        
        return defaults[:4]
    
    def _create_widgets(self):
        """Create all dashboard widgets."""
        
        # Chart selection dropdowns
        self.dropdowns = []
        self.figure_widgets = []
        self.containers = []
        
        for i in range(4):
            # Create dropdown with chart options (grouped by source)
            dropdown = widgets.Dropdown(
                options=self._create_grouped_options(),
                value=self.default_charts[i] if i < len(self.default_charts) else self.chart_names[0],
                description=f'Chart {i+1}:',
                style={'description_width': '60px'},
                layout=widgets.Layout(width='280px', margin='5px 0px')
            )
            
            # Create figure widget with initial chart
            initial_chart = self.all_charts[dropdown.value]
            fig_widget = go.FigureWidget(initial_chart)
            fig_widget.layout.height = 500  # Standardize height
            
            # Create container for dropdown + chart
            container = widgets.VBox([
                dropdown,
                fig_widget
            ], layout=widgets.Layout(
                border='1px solid #ddd',
                padding='10px',
                margin='5px',
                width='1000px'
            ))
            
            self.dropdowns.append(dropdown)
            self.figure_widgets.append(fig_widget)
            self.containers.append(container)
        
        # Control panel widgets
        self.refresh_btn = widgets.Button(
            description='Refresh All Charts',
            button_style='info',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        self.reset_btn = widgets.Button(
            description='Reset to Defaults',
            button_style='warning', 
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        self.export_btn = widgets.Button(
            description='Export Layout',
            button_style='success',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        # Dashboard type selector
        self.type_selector = widgets.Dropdown(
            options=[
                ('Mixed Dashboard', DashboardType.MIXED),
                ('Crossing Analysis', DashboardType.CROSSING),
                ('Portfolio Analysis', DashboardType.PORTFOLIO)
            ],
            value=self.dashboard_type,
            description='Type:',
            style={'description_width': '40px'},
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        # Status display
        chart_count = len(self.chart_names)
        source_count = len(self.chart_sources)
        self.status_display = widgets.HTML(
            value=f"<b>Status:</b> {chart_count} charts from {source_count} sources",
            layout=widgets.Layout(margin='10px 5px')
        )
    
    def _create_grouped_options(self) -> List[tuple]:
        """Create grouped dropdown options by chart source."""
        options = []
        
        # Group charts by source
        for source_name in self.chart_sources.keys():
            # Add source header (disabled option)
            source_display = source_name.replace('_', ' ').title()
            options.append((f"── {source_display} ──", None))
            
            # Add charts from this source
            for chart_name in self.chart_names:
                if chart_name.startswith(f"{source_name}_"):
                    display_name = self._format_chart_name(chart_name)
                    options.append((f"  {display_name}", chart_name))
        
        # Filter out None values (headers)
        return [(name, value) for name, value in options if value is not None]
    
    def _format_chart_name(self, chart_name: str) -> str:
        """Format chart name for display, removing source prefix."""
        # Remove source prefix (e.g., "crossing_" or "portfolio_")
        for source_name in self.chart_sources.keys():
            if chart_name.startswith(f"{source_name}_"):
                clean_name = chart_name[len(f"{source_name}_"):]
                return clean_name.replace('_', ' ').title()
        
        return chart_name.replace('_', ' ').title()
    
    def _setup_layout(self):
        """Create the dashboard layout."""
        
        # Control panel at the top
        control_panel = widgets.HBox([
            self.type_selector,
            self.refresh_btn,
            self.reset_btn,
            self.export_btn,
            self.status_display
        ], layout=widgets.Layout(
            justify_content='flex-start',
            align_items='center',
            border='1px solid #ccc',
            padding='10px',
            margin='5px 0px',
            width='auto'
        ))
        
        # 2x2 chart grid
        top_row = widgets.HBox([
            self.containers[0],  # Top-left
            self.containers[1]   # Top-right
        ], layout=widgets.Layout(justify_content='space-around'))
        
        bottom_row = widgets.HBox([
            self.containers[2],  # Bottom-left  
            self.containers[3]   # Bottom-right
        ], layout=widgets.Layout(justify_content='space-around'))
        
        chart_grid = widgets.VBox([top_row, bottom_row])
        
        # Main dashboard layout
        self.dashboard = widgets.VBox([
            widgets.HTML(f"<h2>{self.dashboard_title}</h2>"),
            control_panel,
            chart_grid
        ])
    
    def _setup_event_handlers(self):
        """Setup event handlers for interactive elements."""
        
        # Chart selection handlers
        for i, dropdown in enumerate(self.dropdowns):
            dropdown.observe(self._create_chart_change_handler(i), names='value')
        
        # Button handlers
        self.refresh_btn.on_click(self._on_refresh_charts)
        self.reset_btn.on_click(self._on_reset_layout)
        self.export_btn.on_click(self._on_export_layout)
        self.type_selector.observe(self._on_type_change, names='value')
    
    def _create_chart_change_handler(self, position: int):
        """Create chart change handler for specific position."""
        def handler(change):
            new_chart_name = change['new']
            if new_chart_name is None:  # Skip if it's a header
                return
                
            new_chart = self.all_charts[new_chart_name]
            
            # Create new FigureWidget with the selected chart
            new_fig_widget = go.FigureWidget(new_chart)
            new_fig_widget.layout.height = 500  # Standardize height
            
            # Replace the FigureWidget in the container
            self.figure_widgets[position] = new_fig_widget
            self.containers[position].children = [
                self.dropdowns[position],
                new_fig_widget
            ]
            
            self._update_status()
            
        return handler
    
    def _on_refresh_charts(self, button):
        """Refresh all charts with latest data."""
        for i, dropdown in enumerate(self.dropdowns):
            chart_name = dropdown.value
            if chart_name and chart_name in self.all_charts:
                updated_chart = self.all_charts[chart_name]
                
                # Create new FigureWidget with updated chart
                new_fig_widget = go.FigureWidget(updated_chart)
                new_fig_widget.layout.height = 500
                
                # Replace the FigureWidget in the container
                self.figure_widgets[i] = new_fig_widget
                self.containers[i].children = [
                    self.dropdowns[i],
                    new_fig_widget
                ]
        
        self._update_status("Charts refreshed successfully")
    
    def _on_reset_layout(self, button):
        """Reset dashboard to default chart selection."""
        # Regenerate defaults based on current dashboard type
        self.default_charts = self._get_default_chart_selection()
        
        for i, dropdown in enumerate(self.dropdowns):
            if i < len(self.default_charts):
                dropdown.value = self.default_charts[i]
        
        self._update_status("Layout reset to defaults")
    
    def _on_type_change(self, change):
        """Handle dashboard type change."""
        self.dashboard_type = change['new']
        
        # Update dropdown options based on new type
        new_options = self._create_grouped_options()
        for dropdown in self.dropdowns:
            current_value = dropdown.value
            dropdown.options = new_options
            # Restore selection if chart still exists
            if current_value in self.chart_names:
                dropdown.value = current_value
            else:
                dropdown.value = self.chart_names[0] if self.chart_names else None
        
        # Reset to appropriate defaults
        self._on_reset_layout(None)
        self._update_status(f"Switched to {self.dashboard_type.value} dashboard")
    
    def _on_export_layout(self, button):
        """Export current layout configuration."""
        current_layout = [dropdown.value for dropdown in self.dropdowns]
        
        print("=== DASHBOARD LAYOUT EXPORT ===")
        print(f"Dashboard Type: {self.dashboard_type.value}")
        print(f"Layout Configuration: {current_layout}")
        print(f"Chart Sources: {list(self.chart_sources.keys())}")
        print(f"To recreate this layout, use:")
        print(f"dashboard = UnifiedDashboardManager(chart_sources, "
              f"dashboard_type=DashboardType.{self.dashboard_type.name}, "
              f"default_charts={current_layout})")
        
        self._update_status("Layout exported to output")
    
    def _update_status(self, message: str = None):
        """Update status display."""
        if message:
            self.status_display.value = f"<b>Status:</b> {message}"
        else:
            selected_charts = [dropdown.value for dropdown in self.dropdowns if dropdown.value]
            unique_charts = len(set(selected_charts))
            total_charts = len(self.chart_names)
            source_count = len(self.chart_sources)
            self.status_display.value = (
                f"<b>Status:</b> {unique_charts} unique charts displayed "
                f"({total_charts} available from {source_count} sources)"
            )
    
    def update_chart_sources(self, new_chart_sources: Dict[str, Dict[str, go.Figure]]):
        """
        Update the available chart sources (useful when analysis data changes).
        
        Args:
            new_chart_sources: Updated dictionary of source_name -> charts
        """
        self.chart_sources = new_chart_sources
        self.all_charts = self._flatten_chart_sources()
        self.chart_names = list(self.all_charts.keys())
        
        # Update dropdown options
        new_options = self._create_grouped_options()
        for dropdown in self.dropdowns:
            current_value = dropdown.value
            dropdown.options = new_options
            # Restore selection if chart still exists
            if current_value in self.chart_names:
                dropdown.value = current_value
            else:
                dropdown.value = self.chart_names[0] if self.chart_names else None
        
        self._update_status("Chart sources updated with new data")
    
    def add_chart_source(self, source_name: str, charts: Dict[str, go.Figure]):
        """
        Add a new chart source to the dashboard.
        
        Args:
            source_name: Name for the chart source
            charts: Dictionary of chart_name -> Figure
        """
        self.chart_sources[source_name] = charts
        self.update_chart_sources(self.chart_sources)
    
    def remove_chart_source(self, source_name: str):
        """
        Remove a chart source from the dashboard.
        
        Args:
            source_name: Name of the chart source to remove
        """
        if source_name in self.chart_sources:
            del self.chart_sources[source_name]
            self.update_chart_sources(self.chart_sources)
    
    def get_current_layout(self) -> Dict[str, Any]:
        """Get current dashboard configuration."""
        return {
            'dashboard_type': self.dashboard_type,
            'current_charts': [dropdown.value for dropdown in self.dropdowns],
            'available_sources': list(self.chart_sources.keys()),
            'total_charts': len(self.chart_names)
        }
    
    def set_layout(self, chart_names: List[str]):
        """
        Set specific chart layout.
        
        Args:
            chart_names: List of 4 chart names for each position
        """
        if len(chart_names) != 4:
            raise ValueError("Must provide exactly 4 chart names")
        
        for i, chart_name in enumerate(chart_names):
            if chart_name in self.chart_names:
                self.dropdowns[i].value = chart_name
            else:
                self.logger.warning(f"Chart '{chart_name}' not found, skipping position {i}")
    
    def display(self):
        """Display the dashboard."""
        display(self.dashboard)


def create_crossing_dashboard(crossing_charts: Dict[str, go.Figure], 
                            default_charts: Optional[List[str]] = None) -> UnifiedDashboardManager:
    """
    Create dashboard for crossing analysis only.
    
    Args:
        crossing_charts: Charts from CrossingVisualizationManager.create_all_charts()
        default_charts: Optional list of 4 chart names for default display
    
    Returns:
        UnifiedDashboardManager configured for crossing analysis
    """
    chart_sources = {"crossing": crossing_charts}
    dashboard = UnifiedDashboardManager(
        chart_sources=chart_sources,
        dashboard_type=DashboardType.CROSSING,
        default_charts=default_charts,
        dashboard_title="Crossing Analysis Dashboard"
    )
    dashboard.display()
    return dashboard


def create_portfolio_dashboard(portfolio_charts: Dict[str, go.Figure],
                             default_charts: Optional[List[str]] = None) -> UnifiedDashboardManager:
    """
    Create dashboard for portfolio analysis only.
    
    Args:
        portfolio_charts: Charts from PortfolioVisualizationManager.create_all_charts()
        default_charts: Optional list of 4 chart names for default display
    
    Returns:
        UnifiedDashboardManager configured for portfolio analysis
    """
    chart_sources = {"portfolio": portfolio_charts}
    dashboard = UnifiedDashboardManager(
        chart_sources=chart_sources,
        dashboard_type=DashboardType.PORTFOLIO,
        default_charts=default_charts,
        dashboard_title="Portfolio Analysis Dashboard"
    )
    dashboard.display()
    return dashboard


def create_mixed_dashboard(crossing_charts: Dict[str, go.Figure],
                         portfolio_charts: Dict[str, go.Figure],
                         default_charts: Optional[List[str]] = None) -> UnifiedDashboardManager:
    """
    Create dashboard combining crossing and portfolio analysis.
    
    Args:
        crossing_charts: Charts from CrossingVisualizationManager
        portfolio_charts: Charts from PortfolioVisualizationManager  
        default_charts: Optional list of 4 chart names for default display
    
    Returns:
        UnifiedDashboardManager configured for mixed analysis
    """
    chart_sources = {
        "crossing": crossing_charts,
        "portfolio": portfolio_charts
    }
    dashboard = UnifiedDashboardManager(
        chart_sources=chart_sources,
        dashboard_type=DashboardType.MIXED,
        default_charts=default_charts,
        dashboard_title="Comprehensive Analysis Dashboard"
    )
    dashboard.display()
    return dashboard



if __name__ == "__main__":
    # # Single source dashboards
    # crossing_dashboard = create_crossing_dashboard(crossing_charts)
    # portfolio_dashboard = create_portfolio_dashboard(portfolio_charts)
    # 
    # # Mixed dashboard
    # mixed_dashboard = create_mixed_dashboard(crossing_charts, portfolio_charts)
    # 
    # # Or create custom dashboard with additional sources
    # custom_sources = {
    #     "crossing": crossing_charts,
    #     "portfolio": portfolio_charts,
    # #     "risk": risk_charts  # hypothetical third source
    # }
    # custom_dashboard = UnifiedDashboardManager(custom_sources)
    # custom_dashboard.display()
    pass