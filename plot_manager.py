import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging

class PortfolioVisualizationManager:
    """
    Manages creation of portfolio optimization visualization charts.
    
    Provides consistent styling, color schemes, and data preparation
    across multiple chart types for portfolio analysis.
    """
    
    def __init__(self, analysis_result):
        """
        Initialize visualization manager with analysis results.
        
        Args:
            analysis_result: PortfolioComparisonResult from PortfolioAnalyticsEngine
        """
        self.analysis_result = analysis_result
        self.portfolio_id = analysis_result.portfolio_id
        
        # Prepare data for visualizations
        self.original_df = analysis_result.original_composition.composition_df.copy()
        self.optimized_df = analysis_result.optimized_composition.composition_df.copy()
        self.deviation_df = analysis_result.deviation_analysis.deviation_improvements.copy()
        
        # Generate consistent color scheme for sectors
        self.sector_colors = self._generate_sector_color_scheme()
        
        # Common styling
        self.chart_template = "plotly_white"
        # self.chart_template = "plotly_dark"
        self.font_family = "Arial"
        self.title_font_size = 16
        self.axis_font_size = 12
        
        self.logger = logging.getLogger(__name__)
    
    def _generate_sector_color_scheme(self) -> Dict[str, str]:
        """Generate consistent color mapping for sectors across all charts."""
        
        # Get unique sectors from both original and optimized data
        sectors = set()
        if not self.original_df.empty:
            sectors.update(self.original_df['sector'].unique())
        if not self.optimized_df.empty:
            sectors.update(self.optimized_df['sector'].unique())
        
        sectors = sorted([s for s in sectors if pd.notna(s) and s != 'Unknown'])
        
        # Use Plotly's qualitative color palette
        # colors = px.colors.qualitative.Set3
        colors = px.colors.qualitative.Set2
        if len(sectors) > len(colors):
            colors = colors * ((len(sectors) // len(colors)) + 1)

        custom_colors = {
            'Communications': '#1f77b4',  # Blue instead of yellow
            'Technology': '#ff7f0e',     # Orange
            'Financials': '#2ca02c',     # Green
            'Healthcare': '#d62728',     # Red
            'Consumer Discretionary': '#9467bd',  # Purple
            'Industrials': '#8c564b',    # Brown
            'Consumer Staples': '#e377c2',  # Pink
            'Energy': '#7f7f7f',         # Gray
            'Materials': '#bcbd22',      # Olive
            'Real Estate': '#17becf',    # Cyan
            'Utilities': '#ff9896'       # Light red
        }
        
        return {sector: colors[i] for i, sector in enumerate(sectors)}
        # return custom_colors
    
    def create_all_charts(self) -> Dict[str, go.Figure]:
        """
        Generate all visualization charts.
        
        Returns:
            Dictionary mapping chart names to Plotly figures
        """
        charts = {}
        
        try:
            charts['treemap'] = self.create_treemap()
            charts['box_whisker'] = self.create_box_whisker_plot()
            charts['parallel_coordinates'] = self.create_parallel_coordinates()
            charts['sunburst'] = self.create_sunburst_chart()
            charts['sankey'] = self.create_sankey_diagram()
            charts['radar'] = self.create_radar_chart()
            
            self.logger.info(f"Generated {len(charts)} charts for portfolio {self.portfolio_id}")
            
        except Exception as e:
            self.logger.error(f"Error generating charts: {str(e)}")
            
        return charts
    
    def create_treemap(self, size_metric: str = 'deviation_improvement') -> go.Figure:
        """
        Create hierarchical treemap with multiple nested levels.
        
        Args:
            size_metric: Metric to use for box sizing
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Treemap", "No data available for treemap")
        
        # Prepare data for treemap
        df = self.deviation_df.copy()
        
        # Handle missing values and ensure positive sizing
        df[size_metric] = df[size_metric].fillna(0)
        df['size_value'] = df[size_metric].abs() + 0.001
        
        # Clean hierarchical labels
        df['sector_clean'] = df['sector_original'].fillna('Unknown')
        df['group_clean'] = df.get('industry_group_original', 'Unknown').fillna('Unknown')
        df['subgroup_clean'] = df.get('industry_original', 'Unknown').fillna('Unknown')
        df['security_clean'] = df['security_id']
        
        # Build hierarchical structure
        labels = []
        parents = []
        values = []
        ids = []
        
        # Add root level
        labels.append("Portfolio")
        parents.append("")
        values.append(df['size_value'].sum())
        ids.append("root")
        
        # Add sectors
        sector_data = df.groupby('sector_clean')['size_value'].sum()
        for sector in sector_data.index:
            labels.append(sector)
            parents.append("root")
            values.append(sector_data[sector])
            ids.append(f"sector_{sector}")
        
        # Add groups within sectors
        group_data = df.groupby(['sector_clean', 'group_clean'])['size_value'].sum()
        for (sector, group), value in group_data.items():
            group_id = f"group_{sector}_{group}"
            labels.append(group)
            parents.append(f"sector_{sector}")
            values.append(value)
            ids.append(group_id)
        
        # Add subgroups within groups
        subgroup_data = df.groupby(['sector_clean', 'group_clean', 'subgroup_clean'])['size_value'].sum()
        for (sector, group, subgroup), value in subgroup_data.items():
            subgroup_id = f"subgroup_{sector}_{group}_{subgroup}"
            labels.append(subgroup)
            parents.append(f"group_{sector}_{group}")
            values.append(value)
            ids.append(subgroup_id)
        
        # Add individual securities
        for _, row in df.iterrows():
            security = row['security_clean']
            sector = row['sector_clean']
            group = row['group_clean']
            subgroup = row['subgroup_clean']
            value = row['size_value']
            
            labels.append(security)
            parents.append(f"subgroup_{sector}_{group}_{subgroup}")
            values.append(value)
            ids.append(f"security_{security}")
        
        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            ids=ids,
            textinfo="label+value",
            hovertemplate=(
                "<b>%{label}</b><br>" +
                f"{size_metric}: %{{value:.4f}}<br>" +
                "Parent: %{parent}<br>" +
                "<extra></extra>"
            ),
            maxdepth=5,
            branchvalues="total"
        ))
        
        fig.update_layout(
            title=f"Portfolio Optimization Impact - {self.portfolio_id}<br><sub>Hierarchy: Sector → Group → Subgroup → Security</sub>",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=700  # Increased height for more levels
        )
        
        return fig
    
    def create_box_whisker_plot(self) -> go.Figure:
        """Create sector-level active weight distribution comparison."""
        
        if self.original_df.empty or self.optimized_df.empty:
            return self._create_empty_chart("Box Plot", "No data available for box plot")
        
        fig = go.Figure()
        
        # Prepare data for box plots - filter out None and 'Unknown' sectors
        original_data = self.original_df[
            (self.original_df['sector'].notna()) & 
            (self.original_df['sector'] != 'Unknown')
        ].copy()
        optimized_data = self.optimized_df[
            (self.optimized_df['sector'].notna()) & 
            (self.optimized_df['sector'] != 'Unknown')
        ].copy()
        
        # Get unique sectors, handling empty DataFrames
        orig_sectors = set(original_data['sector'].unique()) if not original_data.empty else set()
        opt_sectors = set(optimized_data['sector'].unique()) if not optimized_data.empty else set()
        
        sectors = sorted(orig_sectors | opt_sectors)
        
        if not sectors:
            return self._create_empty_chart("Box Plot", "No sector data available after filtering")
        
        for sector in sectors:
            color = self.sector_colors.get(sector, '#1f77b4')
            
            # Original portfolio active weights
            orig_sector_data = original_data[original_data['sector'] == sector]['active_weight']
            if not orig_sector_data.empty:
                fig.add_trace(go.Box(
                    y=orig_sector_data,
                    name=f"{sector} (Original)",
                    legendgroup=sector,
                    legendgrouptitle_text=sector,
                    marker_color=color,
                    line=dict(color=color),
                    boxpoints='all',
                    jitter=0.3,
                    pointpos=-0.3,
                    showlegend=True
                ))
            
            # Optimized portfolio active weights
            opt_sector_data = optimized_data[optimized_data['sector'] == sector]['active_weight']
            if not opt_sector_data.empty:
                fig.add_trace(go.Box(
                    y=opt_sector_data,
                    name=f"{sector} (Optimized)",
                    legendgroup=sector,
                    marker_color=color,
                    line=dict(color=color),
                    boxpoints='all',
                    jitter=0.3,
                    pointpos=0.3,
                    showlegend=True
                ))
        
        fig.update_layout(
            title=f"Active Weight Distribution by Sector - {self.portfolio_id}",
            yaxis_title="Active Weight (Portfolio - Benchmark)",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            hovermode='closest'
        )
        
        # Add horizontal line at zero
        fig.add_hline(y=0, line_dash="dot", line_color="black", opacity=0.5)
        
        return fig
    
    def create_parallel_coordinates(self) -> go.Figure:
        """Create parallel coordinates plot with sector coloring and grouping."""
        
        if self.deviation_df.empty:
            return self._create_empty_chart("Parallel Coordinates", "No data available")
        
        # Prepare data
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Clean and prepare dimensions
        df['sector_clean'] = df['sector_original'].fillna('Unknown')
        df['violation_status'] = df.apply(
            lambda row: 'Violation' if row.get('exceeds_tolerance_optimized', False) else 'Compliant', 
            axis=1
        )
        
        # Handle mixed data types in sector_clean column
        def clean_sector_name(sector):
            if pd.isna(sector):
                return 'Unknown'
            elif sector == 0 or sector == '0':
                return 'USD/Cash'
            else:
                return str(sector)
        
        df['sector_clean'] = df['sector_clean'].apply(clean_sector_name)
        
        # Create sector number mapping for coloring
        sector_names = sorted(df['sector_clean'].unique())
        sector_to_num = {sector: i for i, sector in enumerate(sector_names)}
        df['sector_num'] = df['sector_clean'].map(sector_to_num)
        
        # Define dimensions
        dimensions = [
            dict(label="Original Active Weight", 
                 values=df['abs_active_weight_original'].fillna(0),
                 range=[df['abs_active_weight_original'].min(), df['abs_active_weight_original'].max()]),
            dict(label="Optimized Active Weight", 
                 values=df['abs_active_weight_optimized'].fillna(0),
                 range=[df['abs_active_weight_optimized'].min(), df['abs_active_weight_optimized'].max()]),
            dict(label="Deviation Improvement", 
                 values=df['deviation_improvement'].fillna(0),
                 range=[df['deviation_improvement'].min(), df['deviation_improvement'].max()]),
            dict(label="Sector", 
                 values=df['sector_num'],
                 range=[0, len(sector_names)-1],
                 tickvals=list(range(len(sector_names))),
                 ticktext=sector_names)
        ]
        
        fig = go.Figure(data=go.Parcoords(
            line=dict(color=df['sector_num'],
                     colorscale='turbo',
                     showscale=True,
                     colorbar=dict(title="Sector",
                                   tickvals=list(range(len(sector_names))),
                                   ticktext=sector_names)),
            dimensions=dimensions,
            # labelangle=45,
            labelside='top'
        ))
        
        fig.update_layout(
            title=f"Multi-Dimensional Security Analysis - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig
    
    def create_sunburst_chart(self) -> go.Figure:
        """Create radial hierarchical portfolio composition chart."""
        
        if self.optimized_df.empty:
            return self._create_empty_chart("Sunburst", "No data available for sunburst")
        
        # Prepare hierarchical data
        df = self.optimized_df[self.optimized_df['portfolio_weight'] > 0].copy()
        
        if df.empty:
            return self._create_empty_chart("Sunburst", "No portfolio holdings to display")
        
        # Create hierarchical structure
        labels = []
        parents = []
        values = []
        colors = []
        
        # Add root
        labels.append("Portfolio")
        parents.append("")
        values.append(df['portfolio_weight'].sum())
        colors.append("#f0f0f0")
        
        # Add sectors
        sector_data = df.groupby('sector')['portfolio_weight'].sum()
        for sector, weight in sector_data.items():
            labels.append(sector)
            parents.append("Portfolio")
            values.append(weight)
            colors.append(self.sector_colors.get(sector, '#1f77b4'))
        
        # Add individual securities
        for _, row in df.iterrows():
            security = row['security_id']
            sector = row['sector']
            weight = row['portfolio_weight']
            
            labels.append(security)
            parents.append(sector)
            values.append(weight)
            colors.append(self.sector_colors.get(sector, '#1f77b4'))
        
        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(colors=colors, line=dict(color="#000000", width=1)),
            hovertemplate="<b>%{label}</b><br>Weight: %{value:.3f}<br><extra></extra>",
            maxdepth=3
        ))
        
        fig.update_layout(
            title=f"Optimized Portfolio Composition - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig
    
    def create_sankey_diagram(self, threshold):
        """Create Sankey diagram showing portfolio weight changes from original to optimized"""
        
        # Get the complete portfolio data
        if self.deviation_df.empty:
            return self._create_empty_chart("Sankey", "No data available for Sankey diagram")
        
        # Prepare data for securities with significant weight changes
        df = self.deviation_df.copy()
        
        # Calculate weight change (optimized - original)
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        
        # Filter to securities with meaningful weight changes (> threhold absolute change)
        significant_changes = df[df['weight_change'].abs() > threshold].copy()
        
        if significant_changes.empty:
            return self._create_empty_chart("Sankey", "No significant weight changes to display")
        
        # Separate increases and decreases
        increases = significant_changes[significant_changes['weight_change'] > 0]
        decreases = significant_changes[significant_changes['weight_change'] < 0]
        
        # Create nodes
        source_nodes = []
        target_nodes = []
        values = []
        
        # Add decreases (from original to "Sold/Reduced")
        for _, row in decreases.iterrows():
            source_nodes.append(f"{row['security_id']} (Original)")
            target_nodes.append("Sold/Reduced")
            values.append(abs(row['weight_change']) * 100)  # Convert to percentage
        
        # Add increases (from "Bought/Increased" to optimized)  
        for _, row in increases.iterrows():
            source_nodes.append("Bought/Increased")
            target_nodes.append(f"{row['security_id']} (Optimized)")
            values.append(row['weight_change'] * 100)  # Convert to percentage
        
        # Create unique node list
        all_nodes = list(set(source_nodes + target_nodes))
        node_dict = {node: i for i, node in enumerate(all_nodes)}
        
        # Map to indices
        source_indices = [node_dict[node] for node in source_nodes]
        target_indices = [node_dict[node] for node in target_nodes]
        
        # Create colors
        node_colors = []
        for node in all_nodes:
            if "Original" in node:
                node_colors.append("rgba(255, 99, 132, 0.8)")  # Red for original
            elif "Optimized" in node:
                node_colors.append("rgba(75, 192, 192, 0.8)")  # Green for optimized
            elif "Sold" in node:
                node_colors.append("rgba(255, 159, 64, 0.8)")  # Orange for sold
            else:  # Bought
                node_colors.append("rgba(153, 102, 255, 0.8)")  # Purple for bought
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color=node_colors
            ),
            link=dict(
                source=source_indices,
                target=target_indices, 
                value=values,
                color="rgba(135, 135, 135, 0.6)"
            )
        )])
        
        fig.update_layout(
            title=f"Portfolio Weight Changes: Original → Optimized - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig

    def create_radar_chart(self) -> go.Figure:
        """Create sector-level active weight comparison radar chart."""
        
        if self.original_df.empty or self.optimized_df.empty:
            return self._create_empty_chart("Radar Chart", "No data available for radar chart")
        
        # Aggregate by sector
        orig_sector = self.original_df.groupby('sector')['active_weight'].sum()
        opt_sector = self.optimized_df.groupby('sector')['active_weight'].sum()
        
        # Get common sectors
        sectors = sorted(set(orig_sector.index) | set(opt_sector.index))
        sectors = [s for s in sectors if s != 'Unknown']
        
        if not sectors:
            return self._create_empty_chart("Radar Chart", "No sector data available")
        
        # Prepare data
        orig_values = [orig_sector.get(sector, 0) for sector in sectors]
        opt_values = [opt_sector.get(sector, 0) for sector in sectors]
        
        # Close the radar chart by repeating first value
        sectors_closed = sectors + [sectors[0]]
        orig_values_closed = orig_values + [orig_values[0]]
        opt_values_closed = opt_values + [opt_values[0]]
        
        fig = go.Figure()
        
        # Original portfolio trace
        fig.add_trace(go.Scatterpolar(
            r=orig_values_closed,
            theta=sectors_closed,
            fill='toself',
            name='Original Portfolio',
            line_color='blue',
            fillcolor='rgba(0, 0, 255, 0.1)'
        ))
        
        # Optimized portfolio trace
        fig.add_trace(go.Scatterpolar(
            r=opt_values_closed,
            theta=sectors_closed,
            fill='toself',
            name='Optimized Portfolio',
            line_color='red',
            fillcolor='rgba(255, 0, 0, 0.1)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[min(min(orig_values), min(opt_values)) * 1.1,
                           max(max(orig_values), max(opt_values)) * 1.1]
                )),
            title=f"Sector Active Weights Comparison - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            showlegend=True
        )
        
        return fig
    
    def create_scatter_matrix(self) -> go.Figure:
        """
        Create scatter plot matrix showing original vs optimized weights.
        
        X-axis: Original weights
        Y-axis: Optimized weights  
        Color: Sector or violation status
        Size: Magnitude of change
        Diagonal line: Shows where weights stayed the same
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Scatter Matrix", "No data available for scatter matrix")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Calculate weight change magnitude for sizing
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        df['weight_change_magnitude'] = df['weight_change'].abs()
        
        # Clean sector names
        df['sector_clean'] = df['sector_original'].fillna('Unknown').astype(str)
        
        # Create violation status
        df['violation_status'] = df.apply(
            lambda row: 'Violation' if row.get('exceeds_tolerance_optimized', False) else 'Compliant', 
            axis=1
        )
        
        # Color by sector
        df['color'] = df['sector_clean'].map(self.sector_colors).fillna('#1f77b4')
        
        # Size scaling (normalize to reasonable range)
        min_size, max_size = 5, 25
        if df['weight_change_magnitude'].max() > 0:
            df['marker_size'] = min_size + (df['weight_change_magnitude'] / df['weight_change_magnitude'].max()) * (max_size - min_size)
        else:
            df['marker_size'] = min_size
        
        fig = go.Figure()
        
        # Add scatter points for each sector
        for sector in df['sector_clean'].unique():
            sector_data = df[df['sector_clean'] == sector]
            
            fig.add_trace(go.Scatter(
                x=sector_data['portfolio_weight_original'].fillna(0),
                y=sector_data['portfolio_weight_optimized'].fillna(0),
                mode='markers',
                name=sector,
                marker=dict(
                    size=sector_data['marker_size'],
                    color=self.sector_colors.get(sector, '#1f77b4'),
                    opacity=0.7,
                    line=dict(width=1, color='black')
                ),
                text=sector_data['security_id'],
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    "Original Weight: %{x:.3f}<br>" +
                    "Optimized Weight: %{y:.3f}<br>" +
                    f"Sector: {sector}<br>" +
                    "Weight Change: %{customdata:.3f}<br>" +
                    "<extra></extra>"
                ),
                customdata=sector_data['weight_change']
            ))
        
        # Add diagonal reference line (y = x)
        max_weight = max(df['portfolio_weight_original'].max(), df['portfolio_weight_optimized'].max())
        min_weight = min(df['portfolio_weight_original'].min(), df['portfolio_weight_optimized'].min())
        
        fig.add_trace(go.Scatter(
            x=[min_weight, max_weight],
            y=[min_weight, max_weight],
            mode='lines',
            name='No Change Line',
            line=dict(color='red', dash='dash', width=2),
            showlegend=True
        ))
        
        fig.update_layout(
            title=f"Original vs Optimized Weights - {self.portfolio_id}",
            xaxis_title="Original Portfolio Weight",
            yaxis_title="Optimized Portfolio Weight",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            hovermode='closest'
        )
        
        return fig

    def create_side_by_side_bars(self) -> go.Figure:
        """
        Create side-by-side bar chart comparing original vs optimized weights.
        
        Left bars: Original portfolio weights
        Right bars: Optimized portfolio weights
        Color coding: By sector
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Side-by-Side Bars", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Filter to top holdings for readability
        df['total_weight'] = df['portfolio_weight_original'].fillna(0) + df['portfolio_weight_optimized'].fillna(0)
        df = df.nlargest(20, 'total_weight')  # Top 20 by combined weight
        
        # Clean sector names
        df['sector_clean'] = df['sector_original'].fillna('Unknown').astype(str)
        
        fig = go.Figure()
        
        # Add original weights
        fig.add_trace(go.Bar(
            name='Original Portfolio',
            x=df['security_id'],
            y=df['portfolio_weight_original'].fillna(0),
            marker_color='lightblue',
            opacity=0.8,
            yaxis='y',
            offsetgroup=1
        ))
        
        # Add optimized weights
        fig.add_trace(go.Bar(
            name='Optimized Portfolio',
            x=df['security_id'],
            y=df['portfolio_weight_optimized'].fillna(0),
            marker_color='darkblue',
            opacity=0.8,
            yaxis='y',
            offsetgroup=2
        ))
        
        fig.update_layout(
            title=f"Portfolio Weight Comparison (Top 20 Holdings) - {self.portfolio_id}",
            xaxis_title="Securities",
            yaxis_title="Portfolio Weight",
            barmode='group',
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            xaxis=dict(tickangle=45)
        )
        
        return fig

    def create_interactive_waterfall_chart(self, threshold) -> go.Figure:
        """Create waterfall chart with interactive toggle for totals."""
        if self.deviation_df.empty:
            return self._create_empty_chart("Interactive Waterfall", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Calculate weight changes
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        significant_changes = df[df['weight_change'].abs() > threshold].copy()
        significant_changes = significant_changes.sort_values('weight_change', ascending=False)
        
        # Create data for both versions
        # With totals
        labels_with = ['Original Portfolio']
        values_with = [df['portfolio_weight_original'].sum()]
        measures_with = ['absolute']
        
        for _, row in significant_changes.iterrows():
            labels_with.append(row['security_id'])
            values_with.append(row['weight_change'])
            measures_with.append('relative')
        
        labels_with.append('Optimized Portfolio')
        values_with.append(df['portfolio_weight_optimized'].sum())
        measures_with.append('total')
        
        # Without totals (changes only)
        labels_without = [row['security_id'] for _, row in significant_changes.iterrows()]
        values_without = [row['weight_change'] for _, row in significant_changes.iterrows()]
        measures_without = ['relative'] * len(labels_without)
        
        # Create figure with both traces (initially show with totals)
        fig = go.Figure()
        
        # Trace with totals
        fig.add_trace(go.Waterfall(
            name="With Totals",
            orientation="v",
            measure=measures_with,
            x=labels_with,
            textposition="outside",
            text=[f"{v:.3f}" for v in values_with],
            y=values_with,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "lightgreen"}},
            decreasing={"marker": {"color": "lightcoral"}},
            totals={"marker": {"color": "blue"}},
            visible=True
        ))
        
        # Trace without totals
        fig.add_trace(go.Waterfall(
            name="Changes Only",
            orientation="v",
            measure=measures_without,
            x=labels_without,
            textposition="outside",
            text=[f"{v:.3f}" for v in values_without],
            y=values_without,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "lightgreen"}},
            decreasing={"marker": {"color": "lightcoral"}},
            visible=False
        ))
        
        # Add toggle buttons
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    buttons=list([
                        dict(
                            args=[{"visible": [True, False]}],
                            label="With Totals",
                            method="restyle"
                        ),
                        dict(
                            args=[{"visible": [False, True]}],
                            label="Changes Only",
                            method="restyle"
                        )
                    ]),
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=0.01,
                    xanchor="left",
                    y=1.02,
                    yanchor="top"
                ),
            ],
            title=f"Portfolio Rebalancing Flow (Interactive) - {self.portfolio_id}",
            xaxis_title="Securities",
            yaxis_title="Weight",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=650,  # Slightly taller for buttons
            xaxis=dict(tickangle=45)
        )
        
        return fig

    def create_waterfall_chart(self, show_totals: bool = True, threshold=0.001) -> go.Figure:
        """
        Create waterfall chart showing cumulative effect of weight changes.
        
        Args:
            show_totals: Whether to include starting and ending totals
        
        Start with original portfolio total
        Add/subtract each security's weight change
        End with optimized portfolio total
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Waterfall Chart", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Calculate weight changes
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        
        # Filter to significant changes and sort by magnitude
        significant_changes = df[df['weight_change'].abs() > threshold].copy()
        significant_changes = significant_changes.sort_values('weight_change', ascending=False)
        
        # Prepare waterfall data
        labels = []
        values = []
        measures = []
        
        # Conditionally add starting total
        if show_totals:
            labels.append('Original Portfolio')
            values.append(df['portfolio_weight_original'].sum())
            measures.append('absolute')
        
        # Add each security's change
        for _, row in significant_changes.iterrows():
            change = row['weight_change']
            labels.append(row['security_id'])
            values.append(change)
            measures.append('relative')
        
        # Conditionally add final total
        if show_totals:
            labels.append('Optimized Portfolio')
            values.append(df['portfolio_weight_optimized'].sum())
            measures.append('total')
        
        fig = go.Figure(go.Waterfall(
            name="Weight Changes",
            orientation="v",
            measure=measures,
            x=labels,
            textposition="outside",
            text=[f"{v:.3f}" for v in values],
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "lightgreen"}},
            decreasing={"marker": {"color": "lightcoral"}},
            totals={"marker": {"color": "blue"}}
        ))
        
        title_suffix = " (Changes Only)" if not show_totals else ""
        
        fig.update_layout(
            title=f"Portfolio Rebalancing Flow{title_suffix} - {self.portfolio_id}",
            xaxis_title="Securities",
            yaxis_title="Weight Change" if not show_totals else "Cumulative Weight",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            xaxis=dict(tickangle=45)
        )
        
        return fig

    def create_waterfall_changes_only(self, threshold) -> go.Figure:
        """Create waterfall chart showing only weight changes (no totals)."""
        return self.create_waterfall_chart(show_totals=False, threshold=threshold)

    def create_waterfall_with_totals(self, threshold) -> go.Figure:
        """Create waterfall chart showing changes with starting/ending totals."""
        return self.create_waterfall_chart(show_totals=True, threshold=threshold)

    ## NOT SURE IF THIS IS VERY HELPFUL ##
    def create_enhanced_sankey_sectors(self) -> go.Figure:
        """
        Create enhanced Sankey diagram showing sector allocation changes.
        
        Left: Original sector allocations
        Right: Optimized sector allocations  
        Flows: Show how much moved between sectors
        Width: Proportional to weight magnitude
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Enhanced Sankey", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Clean sector names
        df['sector_clean'] = df['sector_original'].fillna('Unknown').astype(str)
        
        # Aggregate by sector
        orig_sectors = df.groupby('sector_clean')['portfolio_weight_original'].sum()
        opt_sectors = df.groupby('sector_clean')['portfolio_weight_optimized'].sum()
        
        # Prepare Sankey data
        all_sectors = sorted(set(orig_sectors.index) | set(opt_sectors.index))
        
        # Create node labels
        labels = []
        colors = []
        
        # Original sector nodes
        for sector in all_sectors:
            labels.append(f"{sector} (Original)")
            colors.append(self.sector_colors.get(sector, '#1f77b4'))
        
        # Optimized sector nodes  
        for sector in all_sectors:
            labels.append(f"{sector} (Optimized)")
            colors.append(self.sector_colors.get(sector, '#1f77b4'))
        
        # Create flows (assume sectors maintain their allocations for simplicity)
        sources = []
        targets = []
        values = []
        
        for i, sector in enumerate(all_sectors):
            orig_weight = orig_sectors.get(sector, 0)
            opt_weight = opt_sectors.get(sector, 0)
            
            if orig_weight > 0 and opt_weight > 0:
                # Flow from original to optimized version of same sector
                sources.append(i)  # Original sector index
                targets.append(i + len(all_sectors))  # Optimized sector index
                values.append(min(orig_weight, opt_weight))
        
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=colors
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color="rgba(135, 135, 135, 0.3)"
            )
        )])
        
        fig.update_layout(
            title=f"Sector Allocation Flow: Original → Optimized - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
        )
        
        return fig


    def create_arrow_plot(self, threshold) -> go.Figure:
        """
        Create arrow plot showing weight change vectors.
        
        Base: Original position (x, y coordinates)
        Arrow: Points to optimized position
        Length: Magnitude of change
        Color: Direction (increase/decrease)
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Arrow Plot", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Calculate changes
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        
        # Filter to significant changes
        df = df[df['weight_change'].abs() > threshold]
        
        if df.empty:
            return self._create_empty_chart("Arrow Plot", "No significant changes to display")
        
        # Use original weight as x-coordinate and some risk measure as y (or use index)
        df['x_orig'] = df['portfolio_weight_original'].fillna(0)
        df['y_orig'] = range(len(df))  # Simple positioning
        df['x_opt'] = df['portfolio_weight_optimized'].fillna(0) 
        df['y_opt'] = df['y_orig']  # Keep same y-position
        
        fig = go.Figure()
        
        # Add arrows for increases (green)
        increases = df[df['weight_change'] > 0]
        if not increases.empty:
            for _, row in increases.iterrows():
                # Add arrow without text
                fig.add_annotation(
                    x=row['x_opt'], y=row['y_opt'],
                    ax=row['x_orig'], ay=row['y_orig'],
                    xref='x', yref='y',
                    axref='x', ayref='y',
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor='green',
                    showarrow=True,
                    text=""  # No text on arrow
                )
                # Add separate text annotation above the marker
                fig.add_annotation(
                    x=row['x_opt'], 
                    y=row['y_opt'] + 0.1,  # Position slightly above
                    xref='x', yref='y',
                    text=row['security_id'],
                    showarrow=False,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='green',
                    borderwidth=1,
                    font=dict(size=10, color='black'),
                    xanchor='center',
                    yanchor='bottom'
                )
        
        # Add arrows for decreases (red)
        decreases = df[df['weight_change'] < 0]
        if not decreases.empty:
            for _, row in decreases.iterrows():
                # Add arrow without text
                fig.add_annotation(
                    x=row['x_opt'], y=row['y_opt'],
                    ax=row['x_orig'], ay=row['y_orig'],
                    xref='x', yref='y',
                    axref='x', ayref='y',
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor='red',
                    showarrow=True,
                    text=""  # No text on arrow
                )
                # Add separate text annotation above the marker
                fig.add_annotation(
                    x=row['x_opt'], 
                    y=row['y_opt'] + 0.1,  # Position slightly above
                    xref='x', yref='y',
                    text=row['security_id'],
                    showarrow=False,
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='red',
                    borderwidth=1,
                    font=dict(size=10, color='black'),
                    xanchor='center',
                    yanchor='bottom'
                )
        
        # Add scatter points for reference
        fig.add_trace(go.Scatter(
            x=df['x_orig'],
            y=df['y_orig'],
            mode='markers',
            name='Original Position',
            marker=dict(size=8, color='blue', opacity=0.6),
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=df['x_opt'],
            y=df['y_opt'],
            mode='markers',
            name='Optimized Position',
            marker=dict(size=8, color='red', opacity=0.6),
            showlegend=True
        ))
        
        fig.update_layout(
            title=f"Weight Change Vectors - {self.portfolio_id}",
            xaxis_title="Portfolio Weight",
            yaxis_title="Security (Index)",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            showlegend=True
        )
        
        return fig

    def create_tolerance_band_chart(self, tolerance_pct: float = 2.0) -> go.Figure:
        """
        Create tolerance band chart showing constraint violations.
        
        Center line: Target weights
        Bands: Upper/lower tolerance limits
        Dots: Actual optimized weights
        Color: Red for violations, green for compliant
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Tolerance Bands", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Assume benchmark weights as targets (could be modified based on your data)
        df['target_weight'] = df.get('benchmark_weight', df['portfolio_weight_original']).fillna(0)
        df['actual_weight'] = df['portfolio_weight_optimized'].fillna(0)
        
        # Calculate tolerance bands
        df['upper_band'] = df['target_weight'] + (tolerance_pct / 100)
        df['lower_band'] = df['target_weight'] - (tolerance_pct / 100)
        
        # Determine violations
        df['violation'] = (df['actual_weight'] > df['upper_band']) | (df['actual_weight'] < df['lower_band'])
        
        # Sort by target weight for better visualization
        df = df.sort_values('target_weight', ascending=False)
        
        # Limit to top holdings for readability
        df = df.head(40)
        
        fig = go.Figure()
        
        # Add tolerance bands
        fig.add_trace(go.Scatter(
            x=df['security_id'],
            y=df['upper_band'],
            mode='lines',
            name='Upper Tolerance',
            line=dict(color='orange', dash='dash'),
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=df['security_id'],
            y=df['lower_band'],
            mode='lines',
            name='Lower Tolerance',
            line=dict(color='orange', dash='dash'),
            fill='tonexty',
            fillcolor='rgba(255,165,0,0.1)',
            showlegend=True
        ))
        
        # Add target line
        fig.add_trace(go.Scatter(
            x=df['security_id'],
            y=df['target_weight'],
            mode='lines',
            name='Target Weight',
            line=dict(color='blue', width=2),
            showlegend=True
        ))
        
        # Add actual weights with violation coloring
        compliant = df[~df['violation']]
        violations = df[df['violation']]
        
        if not compliant.empty:
            fig.add_trace(go.Scatter(
                x=compliant['security_id'],
                y=compliant['actual_weight'],
                mode='markers',
                name='Compliant',
                marker=dict(size=10, color='green'),
                showlegend=True
            ))
        
        if not violations.empty:
            fig.add_trace(go.Scatter(
                x=violations['security_id'],
                y=violations['actual_weight'],
                mode='markers',
                name='Violations',
                marker=dict(size=10, color='red'),
                showlegend=True
            ))
        
        fig.update_layout(
            title=f"Weight Tolerance Analysis (±{tolerance_pct}%) - {self.portfolio_id}",
            xaxis_title="Securities",
            yaxis_title="Portfolio Weight",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600,
            xaxis=dict(tickangle=45)
        )
        
        return fig

    def create_deviation_histogram(self) -> go.Figure:
        """
        Create histogram showing distribution of weight changes.
        
        X-axis: Magnitude of weight changes
        Y-axis: Number of securities
        Color: By sector or violation status
        """
        if self.deviation_df.empty:
            return self._create_empty_chart("Deviation Histogram", "No data available")
        
        df = self.deviation_df.copy()
        df = df.dropna(subset=['security_id'])
        
        # Calculate weight changes
        df['weight_change'] = df['portfolio_weight_optimized'].fillna(0) - df['portfolio_weight_original'].fillna(0)
        df['weight_change_magnitude'] = df['weight_change'].abs()
        
        # Clean sector names
        df['sector_clean'] = df['sector_original'].fillna('Unknown').astype(str)
        
        fig = go.Figure()
        
        # Create histogram for each sector
        for sector in df['sector_clean'].unique():
            sector_data = df[df['sector_clean'] == sector]['weight_change_magnitude']
            
            fig.add_trace(go.Histogram(
                x=sector_data,
                name=sector,
                marker_color=self.sector_colors.get(sector, '#1f77b4'),
                opacity=0.7,
                # nbinsx=20
                nbinsx=30
            ))
        
        fig.update_layout(
            title=f"Distribution of Weight Changes by Sector - {self.portfolio_id}",
            xaxis_title="Weight Change Magnitude",
            yaxis_title="Number of Securities",
            barmode='overlay',
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=600
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
            title=f"{chart_type} - {self.portfolio_id}",
            template=self.chart_template,
            font=dict(family=self.font_family, size=self.axis_font_size),
            height=400,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        
        return fig
    
    def save_all_charts(self, output_dir: str = "charts", format: str = "html") -> Dict[str, str]:
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
            filename = f"{self.portfolio_id}_{chart_name}.{format}"
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
        
        self.logger.info(f"Saved {len(charts)} charts to {output_dir}")
        return file_paths

