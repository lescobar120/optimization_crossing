import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from collections import defaultdict

class CrossingVisualizationManager:
    """
    Manages creation of portfolio crossing visualization charts.
    
    Provides charts for analyzing crossing opportunities, external liquidity needs,
    and portfolio interaction patterns for trade execution planning.
    """
    
    def __init__(self, crossing_result):
        """
        Initialize visualization manager with crossing results.
        
        Args:
            crossing_result: CrossingResult from PortfolioCrossingEngine
        """
        self.crossing_result = crossing_result
        self.crossed_trades = crossing_result.crossed_trades
        self.remaining_trades = crossing_result.remaining_trades
        self.external_liquidity_flags = crossing_result.external_liquidity_flags
        self.summary = crossing_result.crossing_summary
        
        # Convert to DataFrames for easier manipulation
        self.crossed_df = self._create_crossed_trades_df()
        self.remaining_df = self._create_remaining_trades_df()
        self.external_df = self._create_external_liquidity_df()
        
        # Common styling
        self.chart_template = "plotly_white"
        self.font_family = "Arial"
        self.title_font_size = 16
        self.axis_font_size = 12
        
        # Color scheme
        self.colors = {
            'crossed': '#2E8B57',      # Sea Green
            'remaining': '#FF6B35',     # Orange Red  
            'buy': '#1f77b4',          # Blue
            'sell': '#d62728',         # Red
            'external': '#9467bd'       # Purple
        }
        
        self.logger = logging.getLogger(__name__)
    
    def _create_crossed_trades_df(self) -> pd.DataFrame:
        """Convert crossed trades to DataFrame."""
        if not self.crossed_trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.crossed_trades:
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
        if not self.remaining_trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.remaining_trades:
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
        if not self.external_liquidity_flags:
            return pd.DataFrame()
        
        data = []
        for flag in self.external_liquidity_flags:
            data.append({
                'security': flag.security,
                'direction': flag.direction,
                'total_quantity': flag.total_quantity,
                'portfolio_count': len(flag.portfolios),
                'portfolios': ', '.join(flag.portfolios)
            })
        
        return pd.DataFrame(data)
    
    def create_all_charts(self) -> Dict[str, go.Figure]:
        """
        Generate all crossing visualization charts.
        
        Returns:
            Dictionary mapping chart names to Plotly figures
        """
        charts = {}
        
        try:
            charts['comprehensive_summary'] = self.create_comprehensive_crossing_dashboard()
            charts['crossing_flow_sankey'] = self.create_crossing_flow_sankey()
            charts['portfolio_crossing_matrix'] = self.create_portfolio_crossing_matrix()
            charts['portfolio_volume_breakdown'] = self.create_portfolio_volume_breakdown()
            charts['trade_direction_network'] = self.create_trade_direction_network()
            charts['external_liquidity_waterfall'] = self.create_external_liquidity_waterfall()
            charts['volume_distribution_histogram'] = self.create_volume_distribution_histogram()
            charts['crossing_efficiency_kpis'] = self.create_crossing_efficiency_kpis()
            charts['sector_crossing_analysis'] = self.create_sector_crossing_analysis()
            
            self.logger.info(f"Generated {len(charts)} crossing charts")
            
        except Exception as e:
            self.logger.error(f"Error generating crossing charts: {str(e)}")
            
        return charts
    
    def create_comprehensive_crossing_dashboard(self) -> go.Figure:
        """
        Create comprehensive dashboard showing all crossing analysis metrics.
        """
        # Create subplot with 3x3 layout for comprehensive metrics
        fig = make_subplots(
            rows=3, cols=3,
            # subplot_titles=(
            #     "Total Portfolios", "Original Trade Count", "Original Volume",
            #     "Crossed Trade Count", "Crossed Volume", "Crossing Rate",
            #     "Remaining Trades", "Remaining Volume", "Securities Analysis"
            # ),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "pie"}]
            ]
        )
        
        # Row 1: Portfolio and Original Trade Data
        # Total Portfolios
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['total_portfolios'],
            number={'font': {'size': 48, 'color': self.colors['buy']}},
            title={'text': "Portfolios Processed", 'font': {'size': 14}}
        ), row=1, col=1)
        
        # Original Trade Count
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['original_trade_count'],
            number={'font': {'size': 48, 'color': '#FF6B35'},'valueformat': ',.0f',},
            title={'text': "Original Trades", 'font': {'size': 14}}
        ), row=1, col=2)
        
        # Original Volume
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['original_volume']/1000000,
            number={'suffix': "M", 'font': {'size': 42, 'color': '#FF6B35'}, 'valueformat': '.1f'},
            title={'text': "Original Volume (M shares)", 'font': {'size': 14}}
        ), row=1, col=3)
        
        # Row 2: Crossing Results
        # Crossed Trade Count
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=self.summary['crossed_trade_count'],
            number={'font': {'size': 48, 'color': self.colors['crossed']}},
            delta={
                'reference': 0,
                'relative': False,
                'valueformat': '.0f',
                'font': {'size': 20, 'color': self.colors['crossed']}
            },
            title={'text': "Crossed Trades", 'font': {'size': 14}}
        ), row=2, col=1)
        
        # Crossed Volume
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=self.summary['crossed_volume'] / 1000,  # Convert to millions
            number={'suffix': "K", 'font': {'size': 42, 'color': self.colors['crossed']}, 'valueformat': '.2f'},
            delta={
                'reference': 0,
                'relative': False,
                'valueformat': '.2f',
                'suffix': "K",
                'font': {'size': 18, 'color': self.colors['crossed']}
            },
            title={'text': "Crossed Volume (M shares)", 'font': {'size': 14}}
        ), row=2, col=2)
        
        # Crossing Rate
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=self.summary['crossing_rate'] * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'suffix': "%", 'font': {'size': 32}},
            delta={
                'reference': 5,  # Target crossing rate
                'relative': False,
                'valueformat': '.1f',
                'suffix': "%"
            },
            title={'text': "Crossing Rate", 'font': {'size': 14}},
            gauge={
                'axis': {'range': [None, 20]},
                'bar': {'color': self.colors['crossed']},
                'steps': [
                    {'range': [0, 2], 'color': "lightgray"},
                    {'range': [2, 5], 'color': "yellow"},
                    {'range': [5, 20], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 10
                }
            }
        ), row=2, col=3)
        
        # Row 3: Remaining Trades and Analysis
        # Remaining Trade Count
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['remaining_trade_count'],
            number={'font': {'size': 48, 'color': self.colors['remaining']},'valueformat': ',.0f',},
            title={'text': "Remaining Trades", 'font': {'size': 14}}
        ), row=3, col=1)
        
        # Remaining Volume
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['remaining_volume'] / 1000000,  # Convert to millions
            number={'suffix': "M", 'font': {'size': 42, 'color': self.colors['remaining']}, 'valueformat': '.1f'},
            title={'text': "External Liquidity Needed (M shares)", 'font': {'size': 14}}
        ), row=3, col=2)
        
        # Securities Analysis (Pie Chart)
        securities_labels = ['Securities Crossed', 'Securities Requiring External Liquidity']
        securities_values = [
            self.summary['securities_with_crosses'],
            self.summary['securities_needing_external_liquidity']
        ]
        securities_colors = [self.colors['crossed'], self.colors['external']]
        
        fig.add_trace(go.Pie(
            labels=securities_labels,
            values=securities_values,
            marker=dict(colors=securities_colors),
            textinfo='label+percent+value',
            textfont={'size': 12},
            title = "Securities Analysis",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
        ), row=3, col=3)
        
        # Calculate volume reduction percentage for subtitle
        volume_reduction_pct = (self.summary['volume_reduction'] / self.summary['original_volume']) * 100
        
        fig.update_layout(
            title=f"Comprehensive Crossing Analysis Dashboard<br><sub>Volume Reduction: {self.summary['volume_reduction']:,.0f} shares ({volume_reduction_pct:.1f}%)</sub>",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=800,
            showlegend=False
        )
        
        return fig

    def create_crossing_flow_sankey(self) -> go.Figure:
        """
        Create Sankey diagram showing flow from original trades through crossing to final state.
        """
        if self.crossed_df.empty and self.remaining_df.empty:
            return self._create_empty_chart("Sankey Flow", "No crossing data available")
        
        # Create nodes
        labels = ["Original Trades"]
        colors = ["lightblue"]
        
        # Add crossed trades and remaining trades as intermediate nodes
        labels.extend(["Crossed Volume", "External Liquidity Needed"])
        colors.extend([self.colors['crossed'], self.colors['external']])
        
        # Create flows
        source = []
        target = []
        value = []
        
        # Original -> Crossed
        if self.summary['crossed_volume'] > 0:
            source.append(0)  # Original Trades
            target.append(1)  # Crossed Volume
            value.append(self.summary['crossed_volume'])
        
        # Original -> External Liquidity
        if self.summary['remaining_volume'] > 0:
            source.append(0)  # Original Trades
            target.append(2)  # External Liquidity
            value.append(self.summary['remaining_volume'])
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=colors
            ),
            link=dict(
                source=source,
                target=target,
                value=value,
                color="rgba(135, 135, 135, 0.3)"
            )
        )])
        
        fig.update_layout(
            title="Portfolio Crossing Flow Analysis",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=400
        )
        
        return fig
    
    def create_portfolio_crossing_matrix(self) -> go.Figure:
        """
        Create heatmap showing crossing volumes between portfolio pairs.
        """
        if self.crossed_df.empty:
            return self._create_empty_chart("Crossing Matrix", "No crossed trades to display")
        
        # Create portfolio crossing matrix
        portfolios = sorted(set(self.crossed_df['buyer_portfolio'].tolist() + 
                               self.crossed_df['seller_portfolio'].tolist()))
        
        matrix = pd.DataFrame(0, index=portfolios, columns=portfolios)
        
        for _, row in self.crossed_df.iterrows():
            buyer = row['buyer_portfolio']
            seller = row['seller_portfolio']
            volume = row['quantity_crossed']
            matrix.loc[seller, buyer] += volume
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale='Greens',
            text=matrix.values,
            texttemplate="%{text:,.0f}",
            textfont={"size": 10},
            hovertemplate="<b>Seller:</b> %{y}<br><b>Buyer:</b> %{x}<br><b>Volume:</b> %{z:,.0f}<extra></extra>"
        ))
        
        fig.update_layout(
            title="Portfolio Crossing Matrix<br><sub>Rows = Sellers, Columns = Buyers</sub>",
            xaxis_title="Buyer Portfolio",
            yaxis_title="Seller Portfolio",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=500,
            xaxis=dict(side='top')
        )
        
        return fig
    
    def create_portfolio_volume_breakdown(self) -> go.Figure:
        """
        Create stacked bar chart showing volume breakdown by portfolio.
        """
        # Aggregate data by portfolio
        portfolio_data = defaultdict(lambda: {'original': 0, 'crossed': 0, 'remaining': 0})
        
        # Add crossed volumes
        if not self.crossed_df.empty:
            for _, row in self.crossed_df.iterrows():
                buyer = row['buyer_portfolio']
                seller = row['seller_portfolio']
                volume = row['quantity_crossed']
                
                portfolio_data[buyer]['crossed'] += volume
                portfolio_data[seller]['crossed'] += volume
                portfolio_data[buyer]['original'] += row['buyer_original_quantity']
                portfolio_data[seller]['original'] += abs(row['seller_original_quantity'])
        
        # Add remaining volumes
        if not self.remaining_df.empty:
            remaining_by_portfolio = self.remaining_df.groupby('portfolio_id')['remaining_quantity'].apply(
                lambda x: x.abs().sum()
            )
            for portfolio, volume in remaining_by_portfolio.items():
                portfolio_data[portfolio]['remaining'] += volume
        
        # Convert to DataFrame
        portfolios = list(portfolio_data.keys())
        data_df = pd.DataFrame({
            'Portfolio': portfolios,
            'Crossed': [portfolio_data[p]['crossed'] for p in portfolios],
            'Remaining': [portfolio_data[p]['remaining'] for p in portfolios]
        })
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Crossed Volume',
            x=data_df['Portfolio'],
            y=data_df['Crossed'],
            marker_color=self.colors['crossed']
        ))
        
        fig.add_trace(go.Bar(
            name='Remaining Volume',
            x=data_df['Portfolio'],
            y=data_df['Remaining'],
            marker_color=self.colors['remaining']
        ))
        
        fig.update_layout(
            title="Portfolio Volume Breakdown",
            xaxis_title="Portfolio",
            yaxis_title="Volume",
            barmode='stack',
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=500
        )
        
        return fig
    
    def create_trade_direction_network(self) -> go.Figure:
        """
        Create network diagram showing trade flows between portfolios.
        """
        if self.crossed_df.empty:
            return self._create_empty_chart("Trade Network", "No crossed trades to display")
        
        # Calculate portfolio positions for circular layout
        portfolios = sorted(set(self.crossed_df['buyer_portfolio'].tolist() + 
                               self.crossed_df['seller_portfolio'].tolist()))
        n_portfolios = len(portfolios)
        
        # Create circular positions
        positions = {}
        for i, portfolio in enumerate(portfolios):
            angle = 2 * np.pi * i / n_portfolios
            positions[portfolio] = (np.cos(angle), np.sin(angle))
        
        # Create edges for connections
        edge_x = []
        edge_y = []
        edge_info = []
        
        for _, row in self.crossed_df.iterrows():
            buyer = row['buyer_portfolio']
            seller = row['seller_portfolio']
            volume = row['quantity_crossed']
            
            x0, y0 = positions[seller]
            x1, y1 = positions[buyer]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_info.append(f"{seller} → {buyer}: {volume:,.0f}")
        
        # Create nodes
        node_x = [positions[p][0] for p in portfolios]
        node_y = [positions[p][1] for p in portfolios]
        
        # Calculate node sizes based on total volume
        node_volumes = {}
        for portfolio in portfolios:
            volume = 0
            volume += self.crossed_df[self.crossed_df['buyer_portfolio'] == portfolio]['quantity_crossed'].sum()
            volume += self.crossed_df[self.crossed_df['seller_portfolio'] == portfolio]['quantity_crossed'].sum()
            node_volumes[portfolio] = volume
        
        max_volume = max(node_volumes.values()) if node_volumes else 1
        node_sizes = [20 + (node_volumes[p] / max_volume) * 30 for p in portfolios]
        
        fig = go.Figure()
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color=self.colors['crossed']),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            marker=dict(
                size=node_sizes,
                color=self.colors['buy'],
                line=dict(width=2, color='black')
            ),
            text=portfolios,
            textposition="middle center",
            hovertemplate="<b>%{text}</b><br>Total Crossed Volume: %{customdata:,.0f}<extra></extra>",
            customdata=[node_volumes[p] for p in portfolios],
            showlegend=False
        ))
        
        fig.update_layout(
            title="Portfolio Trade Flow Network<br><sub>Node size = Total crossing volume</sub>",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Arrows show direction: Seller → Buyer",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor='left', yanchor='bottom',
                font=dict(size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig
    
    def create_external_liquidity_waterfall(self) -> go.Figure:
        """
        Create waterfall chart showing external liquidity needs breakdown.
        """
        if self.external_df.empty:
            return self._create_empty_chart("External Liquidity", "No external liquidity needs")
        
        # Aggregate by direction
        buy_volume = self.external_df[self.external_df['direction'] == 'BUY']['total_quantity'].sum()
        sell_volume = self.external_df[self.external_df['direction'] == 'SELL']['total_quantity'].sum()
        total_volume = buy_volume + sell_volume
        
        # Create waterfall data
        labels = ['Total External Liquidity', 'Buy Orders', 'Sell Orders']
        values = [total_volume, buy_volume, sell_volume]
        measures = ['absolute', 'relative', 'relative']
        
        fig = go.Figure(go.Waterfall(
            name="External Liquidity",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"{v:,.0f}" for v in values],
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": self.colors['buy']}},
            decreasing={"marker": {"color": self.colors['sell']}},
            totals={"marker": {"color": self.colors['external']}}
        ))
        
        fig.update_layout(
            title="External Liquidity Requirements",
            xaxis_title="Category",
            yaxis_title="Volume",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=500
        )
        
        return fig
    
    def create_volume_distribution_histogram(self) -> go.Figure:
        """
        Create histogram showing distribution of crossed trade sizes.
        """
        if self.crossed_df.empty:
            return self._create_empty_chart("Volume Distribution", "No crossed trades to analyze")
        
        volumes = self.crossed_df['quantity_crossed']
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=volumes,
            nbinsx=30,
            marker_color=self.colors['crossed'],
            opacity=0.7,
            name="Crossed Trade Volumes"
        ))
        
        # Add mean line
        mean_volume = volumes.mean()
        fig.add_vline(
            x=mean_volume,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Mean: {mean_volume:,.0f}"
        )
        
        fig.update_layout(
            title="Distribution of Crossed Trade Volumes",
            xaxis_title="Trade Volume",
            yaxis_title="Number of Trades",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=500
        )
        
        return fig
    
    def create_crossing_efficiency_kpis(self) -> go.Figure:
        """
        Create KPI dashboard with key crossing metrics.
        """
        # Create subplot with 2x2 layout for KPIs
        fig = make_subplots(
            rows=2, cols=2,
            #subplot_titles=("Crossing Rate", "Volume Reduction", "External Liquidity", "Crossed Securities"),
            specs=[[{"type": "indicator"}, {"type": "indicator"}],
                   [{"type": "indicator"}, {"type": "indicator"}]]
        )
        
        # Crossing Rate
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=self.summary['crossing_rate'] * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'suffix': "%",},
            title={'text': "Crossing Rate (%)"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': self.colors['crossed']},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "gray"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}
        ), row=1, col=1)
        
        # Volume Reduction
        reduction_pct = (self.summary['volume_reduction'] / self.summary['original_volume']) * 100
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=self.summary['volume_reduction'],
            number={'suffix': " shares"},
            title={'text': "Volume Reduction"},
            delta={'reference': 0, 'relative': False}
        ), row=1, col=2)
        
        # External Liquidity
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['remaining_volume'],
            number={'suffix': " shares"},
            title={'text': "External Liquidity Needed"}
        ), row=2, col=1)
        
        # Crossed Securities
        fig.add_trace(go.Indicator(
            mode="number",
            value=self.summary['securities_with_crosses'],
            title={'text': "Securities Crossed"}
        ), row=2, col=2)
        
        fig.update_layout(
            title="Crossing Efficiency Dashboard",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig
    
    def create_sector_crossing_analysis(self) -> go.Figure:
        """
        Create analysis of crossing performance by sector (if sector data available).
        Note: This requires sector information to be added to the crossing data structure.
        """
        # For now, create a placeholder that shows top securities by crossing volume
        if self.crossed_df.empty:
            return self._create_empty_chart("Sector Analysis", "No crossed trades to analyze")
        
        # Aggregate by security
        security_volumes = self.crossed_df.groupby('security')['quantity_crossed'].sum().sort_values(ascending=False)
        top_securities = security_volumes.head(20)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=top_securities.index,
            y=top_securities.values,
            marker_color=self.colors['crossed'],
            name="Crossing Volume"
        ))
        
        fig.update_layout(
            title="Top 20 Securities by Crossing Volume",
            xaxis_title="Security",
            yaxis_title="Total Crossed Volume",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=500,
            xaxis=dict(tickangle=45)
        )
        
        return fig
    
    def _create_empty_chart(self, chart_type: str, message: str) -> go.Figure:
        """Create placeholder chart for empty data scenarios."""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            title=f"{chart_type} - Crossing Analysis",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=400,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig
    
    def save_all_charts(self, output_dir: str = "crossing_charts", format: str = "html") -> Dict[str, str]:
        """
        Save all charts to files.
        
        Args:
            output_dir: Directory to save charts
            format: File format ('html', 'png', 'pdf', 'svg')
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        charts = self.create_all_charts()
        file_paths = {}
        
        for chart_name, fig in charts.items():
            filename = f"crossing_{chart_name}.{format}"
            filepath = os.path.join(output_dir, filename)
            
            if format == "html":
                fig.write_html(filepath)
            elif format == "png":
                fig.write_image(filepath)
            elif format == "pdf":
                fig.write_image(filepath)
            elif format == "svg":
                fig.write_image(filepath)
            
            file_paths[chart_name] = filepath
        
        self.logger.info(f"Saved {len(charts)} crossing charts to {output_dir}")
        return file_paths


