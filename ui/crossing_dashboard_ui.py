import ipywidgets as widgets
import plotly.graph_objects as go
from IPython.display import display
from typing import Dict, List, Optional, Any
import logging

class CrossingDashboardUI:
    """
    Interactive 2x2 dashboard for displaying crossing analysis charts.
    
    Provides dropdown selection for each quadrant with real-time chart updates
    and responsive layout for Jupyter notebook environments.
    """
    
    def __init__(self, charts: Dict[str, go.Figure], default_charts: Optional[List[str]] = None):
        """
        Initialize the crossing dashboard UI.
        
        Args:
            charts: Dictionary of chart_name -> plotly Figure from CrossingVisualizationManager
            default_charts: List of 4 chart names for default display, or None for auto-selection
        """
        self.charts = charts
        self.chart_names = list(charts.keys())
        
        # Set default charts (pick 4 most useful ones if not specified)
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
    
    def _get_default_chart_selection(self) -> List[str]:
        """Select 4 most useful charts as defaults."""
        # Prioritize charts in order of usefulness
        priority_order = [
            'comprehensive_crossing_dashboard',
            'crossing_flow_sankey', 
            'portfolio_crossing_matrix',
            'portfolio_volume_breakdown',
            'trade_direction_network',
            'external_liquidity_waterfall',
            'crossing_efficiency_kpis',
            'volume_distribution_histogram'
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
        
        return defaults[:4]  # Ensure exactly 4 charts
    
    def _create_widgets(self):
        """Create all dashboard widgets."""
        
        # Chart selection dropdowns
        self.dropdowns = []
        self.figure_widgets = []
        self.containers = []
        
        for i in range(4):
            # Create dropdown with chart options
            dropdown = widgets.Dropdown(
                options=[(self._format_chart_name(name), name) for name in self.chart_names],
                value=self.default_charts[i] if i < len(self.default_charts) else self.chart_names[0],
                description=f'Chart {i+1}:',
                style={'description_width': '60px'},
                layout=widgets.Layout(width='280px', margin='5px 0px')
            )
            
            # Create figure widget with initial chart
            initial_chart = self.charts[dropdown.value]
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
        
        # Status display
        self.status_display = widgets.HTML(
            value=f"<b>Dashboard Status:</b> Displaying {len(self.chart_names)} available charts",
            layout=widgets.Layout(margin='10px 5px')
        )
    
    def _format_chart_name(self, chart_name: str) -> str:
        """Format chart name for display in dropdown."""
        # Convert snake_case to Title Case
        return chart_name.replace('_', ' ').title()
    
    def _setup_layout(self):
        """Create the dashboard layout."""
        
        # Control panel at the top
        control_panel = widgets.HBox([
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
            widgets.HTML("<h2>Crossing Analysis Dashboard</h2>"),
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
    
    def _create_chart_change_handler(self, position: int):
        """Create chart change handler for specific position."""
        def handler(change):
            new_chart_name = change['new']
            new_chart = self.charts[new_chart_name]
            
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
            if chart_name in self.charts:
                updated_chart = self.charts[chart_name]
                
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
        for i, dropdown in enumerate(self.dropdowns):
            if i < len(self.default_charts):
                dropdown.value = self.default_charts[i]
        
        self._update_status("Layout reset to defaults")
    
    def _on_export_layout(self, button):
        """Export current layout configuration."""
        current_layout = [dropdown.value for dropdown in self.dropdowns]
        
        export_info = {
            'dashboard_layout': current_layout,
            'chart_positions': {
                'top_left': current_layout[0],
                'top_right': current_layout[1], 
                'bottom_left': current_layout[2],
                'bottom_right': current_layout[3]
            }
        }
        
        print("=== DASHBOARD LAYOUT EXPORT ===")
        print(f"Layout Configuration: {current_layout}")
        print(f"To recreate this layout, use:")
        print(f"dashboard = CrossingDashboardUI(charts, default_charts={current_layout})")
        
        self._update_status("Layout exported to output")
    
    def _update_status(self, message: str = None):
        """Update status display."""
        if message:
            self.status_display.value = f"<b>Dashboard Status:</b> {message}"
        else:
            selected_charts = [dropdown.value for dropdown in self.dropdowns]
            unique_charts = len(set(selected_charts))
            self.status_display.value = (
                f"<b>Dashboard Status:</b> Displaying {unique_charts} unique charts "
                f"from {len(self.chart_names)} available"
            )
    
    def update_charts(self, new_charts: Dict[str, go.Figure]):
        """
        Update the available charts (useful when crossing data changes).
        
        Args:
            new_charts: Updated dictionary of charts from CrossingVisualizationManager
        """
        self.charts = new_charts
        self.chart_names = list(new_charts.keys())
        
        # Update dropdown options
        new_options = [(self._format_chart_name(name), name) for name in self.chart_names]
        for dropdown in self.dropdowns:
            current_value = dropdown.value
            dropdown.options = new_options
            # Restore selection if chart still exists
            if current_value in self.chart_names:
                dropdown.value = current_value
            else:
                dropdown.value = self.chart_names[0] if self.chart_names else None
        
        self._update_status("Charts updated with new data")
    
    def get_current_layout(self) -> List[str]:
        """Get current chart selection layout."""
        return [dropdown.value for dropdown in self.dropdowns]
    
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


def create_crossing_dashboard(charts: Dict[str, go.Figure], 
                            default_charts: Optional[List[str]] = None) -> CrossingDashboardUI:
    """
    Convenience function to create and display crossing dashboard.
    
    Args:
        charts: Dictionary of charts from CrossingVisualizationManager.create_all_charts()
        default_charts: Optional list of 4 chart names for default display
    
    Returns:
        CrossingDashboardUI instance
    """
    dashboard = CrossingDashboardUI(charts, default_charts)
    dashboard.display()
    return dashboard


# Example usage
if __name__ == "__main__":
    # This would be used in a Jupyter notebook like:
    # from crossing_visualization_manager import CrossingVisualizationManager
    # 
    # viz_manager = CrossingVisualizationManager(crossing_result)
    # charts = viz_manager.create_all_charts()
    # dashboard = create_crossing_dashboard(charts)
    pass