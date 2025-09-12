import ipywidgets as widgets
import pandas as pd
from IPython.display import display, HTML
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

# Import your crossing result structures
from crossing_engine import CrossingResult

class CrossingResultsUI:
    """
    UI for displaying portfolio crossing results in a structured format.
    
    Provides tabular display of crossed trades, remaining trades, and external
    liquidity needs with security-specific filtering capabilities.
    """
    
    def __init__(self, crossing_result: CrossingResult):
        """
        Initialize the crossing results UI.
        
        Args:
            crossing_result: CrossingResult from PortfolioCrossingEngine
        """
        self.crossing_result = crossing_result
        
        # Convert to DataFrames for easier handling
        self.crossed_df = self._create_crossed_trades_df()
        self.remaining_df = self._create_remaining_trades_df()
        self.external_df = self._create_external_liquidity_df()
        
        # Get unique securities for filtering
        self.all_securities = self._get_all_securities()
        
        # Create UI components
        self._create_widgets()
        self._setup_layout()
        self._setup_event_handlers()
        
        # Initialize display
        self._update_display()
    
    def _create_crossed_trades_df(self) -> pd.DataFrame:
        """Convert crossed trades to DataFrame."""
        if not self.crossing_result.crossed_trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.crossing_result.crossed_trades:
            data.append({
                'cross_id': trade.cross_id,
                'security': trade.security,
                'quantity_crossed': trade.quantity_crossed,
                'buyer_portfolio': trade.buyer_portfolio,
                'seller_portfolio': trade.seller_portfolio,
                'buyer_original_quantity': trade.buyer_original_quantity,
                'seller_original_quantity': trade.seller_original_quantity
            })
        
        return pd.DataFrame(data)
    
    def _create_remaining_trades_df(self) -> pd.DataFrame:
        """Convert remaining trades to DataFrame."""
        if not self.crossing_result.remaining_trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.crossing_result.remaining_trades:
            data.append({
                'portfolio_id': trade.portfolio_id,
                'security': trade.security,
                'original_quantity': trade.original_quantity,
                'crossed_quantity': trade.crossed_quantity,
                'remaining_quantity': trade.remaining_quantity,
                'trade_direction': trade.trade_direction
            })
        
        return pd.DataFrame(data)
    
    def _create_external_liquidity_df(self) -> pd.DataFrame:
        """Convert external liquidity flags to DataFrame."""
        if not self.crossing_result.external_liquidity_flags:
            return pd.DataFrame()
        
        data = []
        for flag in self.crossing_result.external_liquidity_flags:
            data.append({
                'security': flag.security,
                'direction': flag.direction,
                'total_quantity': flag.total_quantity,
                'portfolio_count': len(flag.portfolios),
                'portfolios': ', '.join(flag.portfolios)
            })
        
        return pd.DataFrame(data)
    
    def _get_all_securities(self) -> List[str]:
        """Get all unique securities across all trade types."""
        securities = set()
        
        if not self.crossed_df.empty:
            securities.update(self.crossed_df['security'].unique())
        
        if not self.remaining_df.empty:
            securities.update(self.remaining_df['security'].unique())
        
        if not self.external_df.empty:
            securities.update(self.external_df['security'].unique())
        
        return sorted(list(securities))
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Security filter dropdown
        security_options = [('All Securities', None)] + [(sec, sec) for sec in self.all_securities]
        self.security_filter = widgets.Dropdown(
            options=security_options,
            value=None,
            description='Filter Security:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='300px', margin='5px')
        )
        
        # Export buttons
        self.export_crossed_btn = widgets.Button(
            description='Send Crosses',
            button_style='success',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        self.export_remaining_btn = widgets.Button(
            description='Stage Remaining Orders',
            button_style='success',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        self.export_all_btn = widgets.Button(
            description='Export All Results',
            button_style='primary',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        # Refresh button
        self.refresh_btn = widgets.Button(
            description='Refresh Display',
            button_style='info',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        # Summary statistics display
        self.summary_display = widgets.HTML(
            layout=widgets.Layout(margin='10px 5px')
        )
        
        # Output areas for different sections
        self.overview_output = widgets.Output(
            layout=widgets.Layout(border='1px solid #ddd', padding='10px', margin='5px 0px')
        )
        
        self.crossed_output = widgets.Output(
            layout=widgets.Layout(border='1px solid #ddd', padding='10px', margin='5px 0px')
        )
        
        self.remaining_output = widgets.Output(
            layout=widgets.Layout(border='1px solid #ddd', padding='10px', margin='5px 0px')
        )
        
        self.external_output = widgets.Output(
            layout=widgets.Layout(border='1px solid #ddd', padding='10px', margin='5px 0px')
        )
    
    def _setup_layout(self):
        """Create the UI layout."""
        
        # Header section
        header = widgets.VBox([
            widgets.HTML("<h2>Portfolio Crossing Results</h2>"),
            widgets.HBox([
                self.security_filter,
                self.refresh_btn,
                self.export_crossed_btn,
                self.export_remaining_btn,
                self.export_all_btn
            ], layout=widgets.Layout(align_items='center')),
            self.summary_display
        ])
        
        # Results sections with accordion
        self.results_accordion = widgets.Accordion([
            self.overview_output,
            self.crossed_output,
            self.remaining_output,
            self.external_output
        ])
        
        self.results_accordion.set_title(0, "Crossing Overview & Summary")
        self.results_accordion.set_title(1, "Crossed Trades")
        self.results_accordion.set_title(2, "Remaining Trades")
        self.results_accordion.set_title(3, "External Liquidity Needs")
        
        # Main layout
        self.main_widget = widgets.VBox([
            header,
            self.results_accordion
        ])
    
    def _setup_event_handlers(self):
        """Setup event handlers."""
        self.security_filter.observe(self._on_security_filter_change, names='value')
        self.refresh_btn.on_click(self._on_refresh)
        self.export_crossed_btn.on_click(self._on_export_crossed)
        self.export_remaining_btn.on_click(self._on_export_remaining)
        self.export_all_btn.on_click(self._on_export_all)
    
    def _on_security_filter_change(self, change):
        """Handle security filter change."""
        self._update_display()
    
    def _on_refresh(self, button):
        """Handle refresh button click."""
        self._update_display()
    
    def _on_export_crossed(self, button):
        """Export crossed trades to CSV."""
        filtered_df = self._apply_security_filter(self.crossed_df)
        if not filtered_df.empty:
            filename = f"crossed_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filtered_df.to_csv(filename, index=False)
            print(f"Crossed trades exported to: {filename}")
        else:
            print("No crossed trades to export")
    
    def _on_export_remaining(self, button):
        """Export remaining trades to CSV."""
        filtered_df = self._apply_security_filter(self.remaining_df)
        if not filtered_df.empty:
            filename = f"remaining_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filtered_df.to_csv(filename, index=False)
            print(f"Remaining trades exported to: {filename}")
        else:
            print("No remaining trades to export")
    
    def _on_export_all(self, button):
        """Export all crossing results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export DataFrames
        if not self.crossed_df.empty:
            self.crossed_df.to_csv(f"crossed_trades_{timestamp}.csv", index=False)
        
        if not self.remaining_df.empty:
            self.remaining_df.to_csv(f"remaining_trades_{timestamp}.csv", index=False)
        
        if not self.external_df.empty:
            self.external_df.to_csv(f"external_liquidity_{timestamp}.csv", index=False)
        
        # Export summary
        summary_data = {
            'crossing_summary': self.crossing_result.crossing_summary,
            'export_timestamp': datetime.now().isoformat(),
            'total_crossed_trades': len(self.crossed_df),
            'total_remaining_trades': len(self.remaining_df),
            'external_liquidity_needs': len(self.external_df)
        }
        
        with open(f"crossing_summary_{timestamp}.json", 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        print(f"All crossing results exported with timestamp: {timestamp}")
    
    def _apply_security_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply security filter to DataFrame."""
        if df.empty:
            return df
        
        selected_security = self.security_filter.value
        if selected_security is None:
            return df
        
        return df[df['security'] == selected_security].copy()
    
    def _update_display(self):
        """Update all display sections."""
        self._update_summary_display()
        self._update_overview_section()
        self._update_crossed_section()
        self._update_remaining_section()
        self._update_external_section()
    
    def _update_summary_display(self):
        """Update the summary statistics display."""
        selected_security = self.security_filter.value
        summary = self.crossing_result.crossing_summary
        
        if selected_security:
            # Security-specific summary
            crossed_for_security = len(self.crossed_df[self.crossed_df['security'] == selected_security])
            remaining_for_security = len(self.remaining_df[self.remaining_df['security'] == selected_security])
            
            self.summary_display.value = (
                f"<b>Security Filter:</b> {selected_security} | "
                f"<b>Crossed:</b> {crossed_for_security} trades | "
                f"<b>Remaining:</b> {remaining_for_security} trades"
            )
        else:
            # Overall summary
            self.summary_display.value = (
                f"<b>Overall Summary:</b> "
                f"{summary['crossed_trade_count']:,} crossed trades | "
                f"{summary['remaining_trade_count']:,} remaining trades | "
                f"Crossing rate: {summary['crossing_rate']:.1%}"
            )
    
    def _update_overview_section(self):
        """Update crossing overview section."""
        with self.overview_output:
            self.overview_output.clear_output()
            
            summary = self.crossing_result.crossing_summary
            
            display(HTML("<h4>Crossing Analysis Summary</h4>"))
            
            # Key metrics
            metrics_data = {
                'Total Portfolios Processed': summary['total_portfolios'],
                'Original Trade Count': f"{summary['original_trade_count']:,}",
                'Original Volume': f"{summary['original_volume']:,}",
                'Crossed Trade Count': f"{summary['crossed_trade_count']:,}",
                'Crossed Volume': f"{summary['crossed_volume']:,}",
                'Crossing Rate': f"{summary['crossing_rate']:.1%}",
                'Volume Reduction': f"{summary['volume_reduction']:,}",
                'Remaining Trade Count': f"{summary['remaining_trade_count']:,}",
                'Remaining Volume': f"{summary['remaining_volume']:,}",
                'Securities with Crosses': summary['securities_with_crosses'],
                'Securities Needing External Liquidity': summary['securities_needing_external_liquidity']
            }
            
            metrics_df = pd.DataFrame(list(metrics_data.items()), columns=['Metric', 'Value'])
            display(metrics_df)
    
    def _update_crossed_section(self):
        """Update crossed trades section."""
        with self.crossed_output:
            self.crossed_output.clear_output()
            
            filtered_df = self._apply_security_filter(self.crossed_df)
            
            if filtered_df.empty:
                display(HTML("<p>No crossed trades available</p>"))
                return
            
            display(HTML(f"<h4>Crossed Trades ({len(filtered_df)} trades)</h4>"))
            
            # Summary by security if showing all
            if self.security_filter.value is None and len(filtered_df) > 0:
                security_summary = filtered_df.groupby('security').agg({
                    'quantity_crossed': 'sum',
                    'cross_id': 'count'
                }).rename(columns={'cross_id': 'trade_count'})
                security_summary = security_summary.sort_values('quantity_crossed', ascending=False)
                
                display(HTML("<h5>Summary by Security</h5>"))
                display(security_summary.head(10).style.format({
                    'quantity_crossed': '{:,.0f}',
                    'trade_count': '{:,.0f}'
                }))
            
            # Detailed trades table
            display(HTML("<h5>Detailed Crossed Trades</h5>"))
            display(filtered_df.style.format({
                'quantity_crossed': '{:,.0f}',
                'buyer_original_quantity': '{:,.0f}',
                'seller_original_quantity': '{:,.0f}'
            }))
    
    def _update_remaining_section(self):
        """Update remaining trades section."""
        with self.remaining_output:
            self.remaining_output.clear_output()
            
            filtered_df = self._apply_security_filter(self.remaining_df)
            
            if filtered_df.empty:
                display(HTML("<p>No remaining trades available</p>"))
                return
            
            display(HTML(f"<h4>Remaining Trades ({len(filtered_df)} trades)</h4>"))
            
            # Summary by direction if showing all
            if self.security_filter.value is None and len(filtered_df) > 0:
                direction_summary = filtered_df.groupby('trade_direction').agg({
                    'remaining_quantity': lambda x: x.abs().sum(),
                    'portfolio_id': 'count'
                }).rename(columns={'portfolio_id': 'trade_count'})
                
                display(HTML("<h5>Summary by Direction</h5>"))
                display(direction_summary.style.format({
                    'remaining_quantity': '{:,.0f}',
                    'trade_count': '{:,.0f}'
                }))
            
            # Detailed remaining trades table
            display(HTML("<h5>Detailed Remaining Trades</h5>"))
            display(filtered_df.style.format({
                'original_quantity': '{:,.0f}',
                'crossed_quantity': '{:,.0f}',
                'remaining_quantity': '{:,.0f}'
            }))
    
    def _update_external_section(self):
        """Update external liquidity section."""
        with self.external_output:
            self.external_output.clear_output()
            
            filtered_df = self._apply_security_filter(self.external_df)
            
            if filtered_df.empty:
                display(HTML("<p>No external liquidity needs</p>"))
                return
            
            display(HTML(f"<h4>External Liquidity Needs ({len(filtered_df)} securities)</h4>"))
            
            # Summary by direction if showing all
            if self.security_filter.value is None and len(filtered_df) > 0:
                direction_summary = filtered_df.groupby('direction').agg({
                    'total_quantity': 'sum',
                    'security': 'count',
                    'portfolio_count': 'sum'
                }).rename(columns={'security': 'securities_count'})
                
                display(HTML("<h5>Summary by Direction</h5>"))
                display(direction_summary.style.format({
                    'total_quantity': '{:,.0f}',
                    'securities_count': '{:,.0f}',
                    'portfolio_count': '{:,.0f}'
                }))
            
            # Detailed external liquidity table
            display(HTML("<h5>Detailed External Liquidity Needs</h5>"))
            display(filtered_df.style.format({
                'total_quantity': '{:,.0f}',
                'portfolio_count': '{:,.0f}'
            }))
    
    def update_crossing_result(self, crossing_result: CrossingResult):
        """
        Update the crossing results and refresh display.
        
        Args:
            crossing_result: Updated CrossingResult
        """
        self.crossing_result = crossing_result
        
        # Recreate DataFrames
        self.crossed_df = self._create_crossed_trades_df()
        self.remaining_df = self._create_remaining_trades_df()
        self.external_df = self._create_external_liquidity_df()
        
        # Update securities list and filter options
        self.all_securities = self._get_all_securities()
        security_options = [('All Securities', None)] + [(sec, sec) for sec in self.all_securities]
        self.security_filter.options = security_options
        
        # Reset filter and refresh display
        self.security_filter.value = None
        self._update_display()
    
    def display(self):
        """Display the UI."""
        display(self.main_widget)


def create_crossing_results_ui(crossing_result: CrossingResult) -> CrossingResultsUI:
    """
    Convenience function to create and display crossing results UI.
    
    Args:
        crossing_result: CrossingResult from PortfolioCrossingEngine
        
    Returns:
        CrossingResultsUI instance
    """
    ui = CrossingResultsUI(crossing_result)
    ui.display()
    return ui


# Example usage
if __name__ == "__main__":
    # This would be used in a Jupyter notebook like:
    # crossing_results_ui = create_crossing_results_ui(crossing_result)
    pass