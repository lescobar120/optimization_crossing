import ipywidgets as widgets
import pandas as pd
from IPython.display import display
from typing import Dict, List, Optional, Any
import json
from datetime import datetime

# Import your optimization result structures
from core.orchestrator import OptimizationResult
from analytics.portfolio_analytics_engine import PortfolioComparisonResult

class OptimizationResultsUI:
    """
    UI for displaying portfolio optimization results without using Output widgets.
    
    Uses HTML widgets with custom CSS for rich table formatting and data display.
    """
    
    def __init__(self, batch_results: Dict[str, OptimizationResult], 
                 analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None):
        """
        Initialize the optimization results UI.
        
        Args:
            batch_results: Dictionary of portfolio_id -> OptimizationResult
            analysis_results: Optional dictionary of portfolio_id -> PortfolioComparisonResult
        """
        self.batch_results = batch_results
        self.analysis_results = analysis_results or {}
        self.portfolio_ids = list(batch_results.keys())
        self.current_portfolio = self.portfolio_ids[0] if self.portfolio_ids else None
        
        # Create UI components
        self._create_widgets()
        self._setup_layout()
        self._setup_event_handlers()
        
        # Initialize display
        if self.current_portfolio:
            self._update_display()
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Portfolio selection
        self.portfolio_dropdown = widgets.Dropdown(
            options=[(f"{pid} ({self.batch_results[pid].status})", pid) for pid in self.portfolio_ids],
            value=self.current_portfolio,
            description='Portfolio:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='300px', margin='5px')
        )
        
        # Status indicator
        self.status_display = widgets.HTML(
            layout=widgets.Layout(margin='5px 0px')
        )
        
        # Export button
        self.export_btn = widgets.Button(
            description='Export Results',
            button_style='success',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        # Refresh button
        self.refresh_btn = widgets.Button(
            description='Refresh Display',
            button_style='info',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        # HTML widgets for different sections (replacing Output widgets)
        self.summary_html = widgets.HTML(
            value="<p>Loading summary...</p>",
            layout=widgets.Layout(
                border='1px solid #ddd', 
                padding='15px', 
                margin='5px 0px',
                max_height='400px',
                overflow='auto'
            )
        )
        
        self.goals_html = widgets.HTML(
            value="<p>Loading goals...</p>",
            layout=widgets.Layout(
                border='1px solid #ddd', 
                padding='15px', 
                margin='5px 0px',
                max_height='300px',
                overflow='auto'
            )
        )
        
        self.constraints_html = widgets.HTML(
            value="<p>Loading constraints...</p>",
            layout=widgets.Layout(
                border='1px solid #ddd', 
                padding='15px', 
                margin='5px 0px',
                max_height='300px',
                overflow='auto'
            )
        )
        
        self.trades_html = widgets.HTML(
            value="<p>Loading trades...</p>",
            layout=widgets.Layout(
                border='1px solid #ddd', 
                padding='15px', 
                margin='5px 0px',
                max_height='500px',
                overflow='auto'
            )
        )
        
        self.analysis_html = widgets.HTML(
            value="<p>Loading analysis...</p>",
            layout=widgets.Layout(
                border='1px solid #ddd', 
                padding='15px', 
                margin='5px 0px',
                max_height='400px',
                overflow='auto'
            )
        )
    
    def _setup_layout(self):
        """Create the UI layout."""
        
        # Header section
        header = widgets.VBox([
            widgets.HTML("<h2>Portfolio Optimization Results</h2>"),
            widgets.HBox([
                self.portfolio_dropdown,
                self.refresh_btn,
                self.export_btn,
                self.status_display
            ], layout=widgets.Layout(align_items='center'))
        ])
        
        # Results sections with collapsible accordions
        self.results_accordion = widgets.Accordion([
            self.summary_html,
            self.goals_html, 
            self.constraints_html,
            self.trades_html,
            self.analysis_html
        ])
        
        self.results_accordion.set_title(0, "Optimization Summary")
        self.results_accordion.set_title(1, "Goals & Objectives")
        self.results_accordion.set_title(2, "Constraints")
        self.results_accordion.set_title(3, "Proposed Trades")
        self.results_accordion.set_title(4, "Performance Analysis")
        
        # Main layout
        self.main_widget = widgets.VBox([
            header,
            self.results_accordion
        ])
    
    def _setup_event_handlers(self):
        """Setup event handlers."""
        self.portfolio_dropdown.observe(self._on_portfolio_change, names='value')
        self.refresh_btn.on_click(self._on_refresh)
        self.export_btn.on_click(self._on_export)
    
    def _on_portfolio_change(self, change):
        """Handle portfolio selection change."""
        self.current_portfolio = change['new']
        self._update_display()
    
    def _on_refresh(self, button):
        """Handle refresh button click."""
        self._update_display()
    
    def _on_export(self, button):
        """Handle export button click."""
        if self.current_portfolio:
            self._export_current_results()
    
    def _update_display(self):
        """Update the display with current portfolio results."""
        if not self.current_portfolio or self.current_portfolio not in self.batch_results:
            return
        
        result = self.batch_results[self.current_portfolio]
        analysis = self.analysis_results.get(self.current_portfolio)
        
        # Update status
        status_color = {'SUCCESS': 'green', 'WARNING': 'orange', 'FAILED': 'red'}.get(result.status, 'gray')
        self.status_display.value = f"<b>Status:</b> <span style='color: {status_color};'>{result.status}</span>"
        
        # Update each section
        self._update_summary_section(result)
        self._update_goals_section(result)
        self._update_constraints_section(result)
        self._update_trades_section(result)
        self._update_analysis_section(analysis)
    
    def _format_dataframe_as_html(self, df: pd.DataFrame, title: str = "", 
                                 format_dict: Optional[Dict] = None) -> str:
        """Convert DataFrame to styled HTML table."""
        if df.empty:
            return f"<h4>{title}</h4><p>No data available</p>"
        
        html_content = f"<h4>{title}</h4>" if title else ""
        
        # Apply formatting if provided
        if format_dict:
            df_display = df.copy()
            for col, fmt in format_dict.items():
                if col in df_display.columns:
                    if callable(fmt):
                        df_display[col] = df_display[col].apply(fmt)
                    else:
                        df_display[col] = df_display[col].apply(lambda x: fmt.format(x) if pd.notna(x) else '')
        else:
            df_display = df
        
        # Generate HTML table with CSS classes
        table_html = df_display.to_html(
            classes='optimization-table table-striped',
            table_id='opt-results-table',
            escape=False,
            border=0,
            index=False  # Remove DataFrame index
        )
        
        html_content += table_html
        return html_content
    
    def _create_metrics_table_html(self, metrics_dict: Dict, title: str = "") -> str:
        """Create HTML table from metrics dictionary."""
        html_content = f"<h4>{title}</h4>" if title else ""
        
        html_content += """
        <table class='metrics-table'>
            <thead>
                <tr><th>Property</th><th>Value</th></tr>
            </thead>
            <tbody>
        """
        
        for key, value in metrics_dict.items():
            # Format value appropriately
            if isinstance(value, float):
                formatted_value = f"{value:,.4f}"
            elif isinstance(value, int):
                formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            
            html_content += f"<tr><td>{key}</td><td>{formatted_value}</td></tr>"
        
        html_content += "</tbody></table>"
        return html_content
    
    def _update_summary_section(self, result: OptimizationResult):
        """Update optimization summary section."""
        html_content = self._get_custom_css()
        
        if result.summary:
            # Convert summary to DataFrame and format
            summary_df = pd.DataFrame([result.summary]).T
            summary_df.columns = ['Value']
            summary_df.index.name = 'Metric'
            summary_df = summary_df.reset_index()
            
            format_dict = {
                'Value': lambda x: f"{x:,.4f}" if isinstance(x, (int, float)) else str(x)
            }
            
            html_content += self._format_dataframe_as_html(
                summary_df, "Optimization Summary", format_dict
            )
        else:
            html_content += "<h4>Optimization Summary</h4><p>No summary data available</p>"
        
        # Additional metadata
        metadata = {
            'Portfolio ID': result.portfolio_id,
            'Optimization ID': result.optimization_id or 'N/A',
            'Execution Time (seconds)': f"{result.execution_time:.2f}" if result.execution_time else 'N/A',
            'Optimization Date': result.optimization_date or 'N/A',
            'Restriction Compliance': 'Yes' if result.restriction_compliance else 'No'
        }
        
        if result.restriction_violations:
            metadata['Restriction Violations'] = len(result.restriction_violations)
        
        html_content += self._create_metrics_table_html(metadata, "Execution Metadata")
        
        # Security Replacement section
        if result.replacements_found:
            html_content += "<h4>Security Restrictions/Replacements</h4>"
            replacements_html = "<div class='replacements-container'>"
            for restricted, replacement_info in result.replacements_found.items():
                # Get ticker information
                restricted_ticker = replacement_info.get('restricted_ticker', '')
                replacement_ticker = replacement_info.get('replacement_ticker', 'N/A')
                
                replacements_html += f"""
                <div class='replacement-item'>
                    <strong>Restricted Security:</strong> {restricted} ({restricted_ticker})<br>
                    <strong>Replacement Security:</strong> {replacement_info.get('replacement_security', 'N/A')} ({replacement_ticker})<br>
                    <strong>Combined Weight:</strong> {replacement_info.get('combined_weight', 0):.4f}%<br>
                    <strong>Match Level:</strong> {replacement_info.get('match_level', 'N/A')}
                </div>
                """
            replacements_html += "</div>"
            html_content += replacements_html
        else:
            html_content += "<h4>Security Restrictions/Replacements</h4><p>No security restrictions applied</p>"
        
        self.summary_html.value = html_content
    
    def _update_goals_section(self, result: OptimizationResult):
        """Update goals section."""
        html_content = self._get_custom_css()
        
        if result.goals:
            goals_df = pd.DataFrame(result.goals)
            html_content += self._format_dataframe_as_html(goals_df, "Optimization Goals")
        else:
            html_content += "<h4>Optimization Goals</h4><p>No goals data available</p>"
        
        self.goals_html.value = html_content
    
    def _update_constraints_section(self, result: OptimizationResult):
        """Update constraints section."""
        html_content = self._get_custom_css()
        
        if result.constraints:
            constraints_df = pd.DataFrame(result.constraints)
            html_content += self._format_dataframe_as_html(constraints_df, "Applied Constraints")
        else:
            html_content += "<h4>Applied Constraints</h4><p>No constraints data available</p>"
        
        self.constraints_html.value = html_content
    
    def _update_trades_section(self, result: OptimizationResult):
        """Update proposed trades section."""
        html_content = self._get_custom_css()
        
        if result.proposed_trades_df is not None and not result.proposed_trades_df.empty:
            trades_df = result.proposed_trades_df.copy()
            
            # Format numeric columns
            numeric_columns = ['initialWeight', 'finalWeight', 'changedWeight', 
                             'changedAmount', 'transactionCost', 'changedQuantity_value']
            for col in numeric_columns:
                if col in trades_df.columns:
                    trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
            
            html_content += f"<h4>Proposed Trades ({len(trades_df)} trades)</h4>"
            
            # Summary statistics
            if 'changedQuantity_value' in trades_df.columns:
                total_volume = trades_df['changedQuantity_value'].abs().sum()
                buy_volume = trades_df[trades_df['changedQuantity_value'] > 0]['changedQuantity_value'].sum()
                sell_volume = trades_df[trades_df['changedQuantity_value'] < 0]['changedQuantity_value'].abs().sum()
                
                summary_stats = {
                    'Total Volume': f"{total_volume:,.0f}",
                    'Buy Volume': f"{buy_volume:,.0f}",
                    'Sell Volume': f"{sell_volume:,.0f}",
                    'Net Volume': f"{buy_volume - sell_volume:,.0f}"
                }
                
                html_content += self._create_metrics_table_html(summary_stats, "Trade Summary")
            
            # Format trades table
            format_dict = {col: lambda x: f"{x:,.4f}" if pd.notna(x) else '' 
                          for col in numeric_columns if col in trades_df.columns}
            
            html_content += self._format_dataframe_as_html(
                trades_df, "Detailed Trades", format_dict
            )
            
        else:
            html_content += "<h4>Proposed Trades</h4><p>No proposed trades available</p>"
        
        self.trades_html.value = html_content
    
    def _update_analysis_section(self, analysis: Optional[PortfolioComparisonResult]):
        """Update performance analysis section."""
        html_content = self._get_custom_css()
        
        if analysis:
            html_content += "<h4>Portfolio Performance Analysis</h4>"
            
            # Key metrics
            summary = analysis.optimization_summary
            key_metrics = {
                'Active Share Improvement': f"{summary['benchmark_tracking']['active_share_improvement']:.4f}",
                'Active Share Improvement %': f"{summary['benchmark_tracking']['active_share_improvement_pct']*100:.2f}%",
                'Tracking Error Improvement': f"{summary['benchmark_tracking']['tracking_error_improvement']:.4f}",
                'Violations Reduced': f"{summary['constraint_compliance']['tolerance_violations_reduced']}",
                'Optimization Effectiveness': summary['portfolio_changes']['optimization_effectiveness']
            }
            
            html_content += self._create_metrics_table_html(key_metrics, "Key Performance Metrics")
            
            # Top improvements
            if hasattr(analysis.deviation_analysis, 'deviation_improvements'):
                improvements_df = analysis.deviation_analysis.deviation_improvements
                if not improvements_df.empty:
                    top_improvements = improvements_df.nlargest(10, 'deviation_improvement')[
                        ['security_id', 'abs_active_weight_original', 'abs_active_weight_optimized', 'deviation_improvement']
                    ]
                    
                    format_dict = {
                        'abs_active_weight_original': lambda x: f"{x:.4f}",
                        'abs_active_weight_optimized': lambda x: f"{x:.4f}",
                        'deviation_improvement': lambda x: f"{x:.4f}"
                    }
                    
                    html_content += self._format_dataframe_as_html(
                        top_improvements, "Top 10 Improvements", format_dict
                    )
            
        else:
            html_content += "<h4>Portfolio Performance Analysis</h4><p>No performance analysis available</p>"
        
        self.analysis_html.value = html_content
    
    def _get_custom_css(self) -> str:
        """Return custom CSS styles for tables and layout."""
        return """
        <style>
        .optimization-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 13px;
        }
        
        .optimization-table th,
        .optimization-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .optimization-table th {
            background-color: #4a4a4a;
            color: white;
            font-weight: bold;
        }
        
        .optimization-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .optimization-table tr:hover {
            background-color: #f5f5f5;
        }
        
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        
        .metrics-table th,
        .metrics-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .metrics-table th {
            background-color: #4a4a4a;
            color: white;
            font-weight: bold;
        }
        
        .metrics-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .replacements-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .replacement-item {
            border: 1px solid #ccc;
            padding: 10px;
            border-radius: 5px;
            background-color: #fff3cd;
            min-width: 200px;
        }
        
        h4 {
            color: #1976d2;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        </style>
        """
    
    def _export_current_results(self):
        """Export current portfolio results."""
        if not self.current_portfolio:
            return
        
        result = self.batch_results[self.current_portfolio]
        
        export_data = {
            'portfolio_id': result.portfolio_id,
            'status': result.status,
            'optimization_id': result.optimization_id,
            'execution_time': result.execution_time,
            'optimization_date': result.optimization_date,
            'summary': result.summary,
            'goals': result.goals,
            'constraints': result.constraints,
            'restriction_compliance': result.restriction_compliance,
            'restriction_violations': result.restriction_violations,
            'export_timestamp': datetime.now().isoformat()
        }
        
        # Export trades to CSV if available
        if result.proposed_trades_df is not None and not result.proposed_trades_df.empty:
            filename = f"optimization_trades_{self.current_portfolio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result.proposed_trades_df.to_csv(filename, index=False)
            print(f"Trades exported to: {filename}")
        
        # Export summary to JSON
        json_filename = f"optimization_summary_{self.current_portfolio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Summary exported to: {json_filename}")
    
    def update_results(self, batch_results: Dict[str, OptimizationResult], 
                      analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None):
        """
        Update the results data and refresh display.
        
        Args:
            batch_results: Updated optimization results
            analysis_results: Updated analysis results
        """
        self.batch_results = batch_results
        if analysis_results:
            self.analysis_results = analysis_results
        
        # Update portfolio dropdown options
        self.portfolio_ids = list(batch_results.keys())
        self.portfolio_dropdown.options = [(f"{pid} ({batch_results[pid].status})", pid) for pid in self.portfolio_ids]
        
        # Update current selection if it still exists
        if self.current_portfolio not in self.portfolio_ids and self.portfolio_ids:
            self.current_portfolio = self.portfolio_ids[0]
            self.portfolio_dropdown.value = self.current_portfolio
        
        self._update_display()
    
    def display(self):
        """Display the UI."""
        display(self.main_widget)


def create_optimization_results_ui(batch_results: Dict[str, OptimizationResult],
                                 analysis_results: Optional[Dict[str, PortfolioComparisonResult]] = None) -> OptimizationResultsUI:
    """
    Convenience function to create and display optimization results UI.
    
    Args:
        batch_results: Dictionary of optimization results
        analysis_results: Optional dictionary of analysis results
        
    Returns:
        OptimizationResultsUI instance
    """
    ui = OptimizationResultsUI(batch_results, analysis_results)
    ui.display()
    return ui


def create_analysis_results_for_batch(batch_results: Dict[str, OptimizationResult],
                                    analytics_engine,
                                    portfolio_ids: Optional[List[str]] = None) -> Dict[str, PortfolioComparisonResult]:
    """
    Helper function to create analysis results for multiple portfolios.
    
    Args:
        batch_results: Dictionary of optimization results
        analytics_engine: PortfolioAnalyticsEngine instance
        portfolio_ids: Optional list of portfolio IDs to analyze (defaults to all)
        
    Returns:
        Dictionary of portfolio_id -> PortfolioComparisonResult
    """
    if portfolio_ids is None:
        portfolio_ids = list(batch_results.keys())
    
    analysis_results = {}
    
    for portfolio_id in portfolio_ids:
        if portfolio_id in batch_results:
            optimization_result = batch_results[portfolio_id]
            
            # Only analyze if we have the required data
            if (optimization_result.clean_holdings_data is not None and 
                optimization_result.proposed_trades_df is not None):
                
                try:
                    analysis_result = analytics_engine.analyze_portfolio_optimization(
                        portfolio_id=portfolio_id,
                        original_holdings_df=optimization_result.clean_holdings_data,
                        proposed_trades_df=optimization_result.proposed_trades_df
                    )
                    analysis_results[portfolio_id] = analysis_result
                    
                except Exception as e:
                    print(f"Warning: Could not analyze portfolio {portfolio_id}: {str(e)}")
    
    return analysis_results