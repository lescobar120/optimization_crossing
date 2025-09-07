import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

@dataclass
class PortfolioComposition:
    """Structure for portfolio composition data."""
    portfolio_id: str
    composition_df: pd.DataFrame  # Security-level weights and positions
    total_weight: float
    benchmark_tracking_error: float
    active_share: float

@dataclass
class DeviationAnalysis:
    """Structure for deviation analysis results."""
    portfolio_id: str
    original_deviations: pd.DataFrame
    optimized_deviations: pd.DataFrame
    deviation_improvements: pd.DataFrame
    tolerance_violations: pd.DataFrame
    summary_metrics: Dict[str, float]

@dataclass
class PortfolioComparisonResult:
    """Complete portfolio analysis result."""
    portfolio_id: str
    original_composition: PortfolioComposition
    optimized_composition: PortfolioComposition
    deviation_analysis: DeviationAnalysis
    optimization_summary: Dict[str, Any]

class PortfolioAnalyticsEngine:
    """
    Analyzes portfolio composition changes and benchmark deviations.
    
    Calculates optimized portfolio weights, benchmark deviations, and provides
    comprehensive analysis of optimization effectiveness.
    """
    
    def __init__(self, tolerance_threshold: float = 0.01):
        """
        Initialize the analytics engine.
        
        Args:
            tolerance_threshold: Weight deviation tolerance (e.g., 0.01 for ±1%)
        """
        self.tolerance_threshold = tolerance_threshold
        self.logger = logging.getLogger(__name__)
    
    def analyze_portfolio_optimization(self, portfolio_id: str,
                                     original_holdings_df: pd.DataFrame,
                                     proposed_trades_df: pd.DataFrame) -> PortfolioComparisonResult:
        """
        Complete analysis of portfolio optimization results.
        
        Args:
            portfolio_id: Portfolio identifier
            original_holdings_df: Original holdings data (clean_holdings_data)
            proposed_trades_df: Proposed trades from optimization
            
        Returns:
            PortfolioComparisonResult with comprehensive analysis
        """
        self.logger.info(f"Starting portfolio analysis for {portfolio_id}")
        
        # Step 1: Calculate original portfolio composition
        original_composition = self._extract_original_composition(
            portfolio_id, original_holdings_df
        )
        
        # Step 2: Calculate optimized portfolio composition
        optimized_composition = self._calculate_optimized_composition(
            portfolio_id, original_holdings_df, proposed_trades_df
        )
        
        # Step 3: Perform deviation analysis
        deviation_analysis = self._analyze_deviations(
            portfolio_id, original_composition, optimized_composition, original_holdings_df
        )
        
        # Step 4: Generate optimization summary
        optimization_summary = self._generate_optimization_summary(
            original_composition, optimized_composition, deviation_analysis
        )
        
        self.logger.info(f"Portfolio analysis completed for {portfolio_id}")
        
        return PortfolioComparisonResult(
            portfolio_id=portfolio_id,
            original_composition=original_composition,
            optimized_composition=optimized_composition,
            deviation_analysis=deviation_analysis,
            optimization_summary=optimization_summary
        )
    
    def _extract_original_composition(self, portfolio_id: str,
                                    holdings_df: pd.DataFrame) -> PortfolioComposition:
        """Extract original portfolio composition from holdings data."""
        
        # Get ALL securities: union of portfolio holdings AND benchmark securities
        all_security_ids = set(holdings_df['OUTPUT_ID'].tolist())
        
        # Filter to all relevant securities
        all_securities = holdings_df[
            holdings_df['OUTPUT_ID'].isin(all_security_ids)
        ].copy()
        
        if all_securities.empty:
            self.logger.warning(f"No securities found for {portfolio_id}")
            return PortfolioComposition(
                portfolio_id=portfolio_id,
                composition_df=pd.DataFrame(),
                total_weight=0.0,
                benchmark_tracking_error=0.0,
                active_share=0.0
            )
        
        # Create composition dataframe for ALL securities
        composition_data = []
        for _, row in all_securities.iterrows():
            portfolio_weight = row.get('PCT_WGT_P', 0) / 100 if pd.notna(row.get('PCT_WGT_P')) else 0
            benchmark_weight = row.get('PCT_WGT_B', 0) / 100 if pd.notna(row.get('PCT_WGT_B')) else 0
            
            # Calculate active weight manually to ensure consistency
            active_weight = portfolio_weight - benchmark_weight
            
            composition_data.append({
                'security_id': row.get('OUTPUT_ID', row.get('TICKER', 'UNKNOWN')),
                'portfolio_weight': portfolio_weight,
                'benchmark_weight': benchmark_weight,
                'active_weight': active_weight,
                'position': row.get('POS_P', 0) if pd.notna(row.get('POS_P')) else 0,
                'market_value': row.get('MKT_VAL_P', 0) if pd.notna(row.get('MKT_VAL_P')) else 0,
                'sector': row.get('SECTOR', 'Unknown'),
                'industry_group': row.get('GROUP', 'Unknown'),
                'industry': row.get('SUBGROUP', 'Unknown')
            })
        
        composition_df = pd.DataFrame(composition_data)
        
        # Calculate portfolio metrics
        total_weight = composition_df['portfolio_weight'].sum()
        active_share = composition_df['active_weight'].abs().sum() / 2
        tracking_error = np.sqrt((composition_df['active_weight'] ** 2).sum())
        
        return PortfolioComposition(
            portfolio_id=portfolio_id,
            composition_df=composition_df,
            total_weight=total_weight,
            benchmark_tracking_error=tracking_error,
            active_share=active_share
        )
    
    def _calculate_optimized_composition(self, portfolio_id: str,
                                    holdings_df: pd.DataFrame,
                                    trades_df: pd.DataFrame) -> PortfolioComposition:
        """Calculate optimized portfolio composition after applying trades."""
        
        if trades_df.empty:
            self.logger.warning(f"No trades found for {portfolio_id}")
            return self._extract_original_composition(portfolio_id, holdings_df)
        
        # Start with original composition
        original_comp = self._extract_original_composition(portfolio_id, holdings_df)
        
        # Create mapping from ticker to security data
        ticker_to_security = {}
        for _, row in original_comp.composition_df.iterrows():
            ticker_to_security[row['security_id']] = row.to_dict()
        
        # Get ALL benchmark securities (not just those originally held or traded)
        benchmark_securities = holdings_df[
            holdings_df['PCT_WGT_B'].notna() & 
            (holdings_df['PCT_WGT_B'] != 0)
        ].copy()
        
        # Create comprehensive security universe
        all_securities = set()
        
        # Add traded securities
        for _, trade in trades_df.iterrows():
            ticker = trade.get('ticker', trade.get('instrumentUniqueId', 'UNKNOWN'))
            all_securities.add(ticker)
        
        # Add benchmark securities
        for _, row in benchmark_securities.iterrows():
            ticker = row.get('OUTPUT_ID', row.get('TICKER', 'UNKNOWN'))
            all_securities.add(ticker)
        
        # Add originally held securities
        all_securities.update(ticker_to_security.keys())
        
        optimized_data = []
        
        for ticker in all_securities:
            # Get trade data if it exists
            trade_data = trades_df[
                (trades_df['ticker'] == ticker) | 
                (trades_df['instrumentUniqueId'] == ticker)
            ]
            
            # Get original holding data if it exists
            original_security = ticker_to_security.get(ticker, {})
            
            # Get benchmark data
            benchmark_row = benchmark_securities[
                benchmark_securities['OUTPUT_ID'] == ticker
            ]
            
            if not benchmark_row.empty:
                benchmark_row = benchmark_row.iloc[0]
                benchmark_weight = benchmark_row.get('PCT_WGT_B', 0) / 100 if pd.notna(benchmark_row.get('PCT_WGT_B')) else 0
                sector = benchmark_row.get('SECTOR', 'Unknown')
                industry_group = benchmark_row.get('GROUP', 'Unknown')
                industry = benchmark_row.get('SUBGROUP', 'Unknown')
            else:
                benchmark_weight = 0
                sector = original_security.get('sector', 'Unknown')
                industry_group = original_security.get('industry_group', 'Unknown')
                industry = original_security.get('industry', 'Unknown')
            
            # Determine optimized weight
            if not trade_data.empty:
                # Security was traded - use finalWeight
                optimized_weight = trade_data.iloc[0].get('finalWeight', 0)
                was_traded = True
            else:
                # Security was not traded - use original weight (or 0 if not originally held)
                optimized_weight = original_security.get('portfolio_weight', 0)
                was_traded = False
            
            original_weight = original_security.get('portfolio_weight', 0)
            active_weight = optimized_weight - benchmark_weight
            
            optimized_data.append({
                'security_id': ticker,
                'portfolio_weight': optimized_weight,
                'benchmark_weight': benchmark_weight,
                'active_weight': active_weight,
                'original_weight': original_weight,
                'weight_change': optimized_weight - original_weight,
                'position': original_security.get('position', 0),
                'market_value': original_security.get('market_value', 0),
                'sector': sector,
                'industry_group': industry_group,
                'industry': industry,
                'was_traded': was_traded
            })
        
        optimized_df = pd.DataFrame(optimized_data)
        
        # Calculate optimized portfolio metrics
        total_weight = optimized_df['portfolio_weight'].sum()
        active_share = optimized_df['active_weight'].abs().sum() / 2
        tracking_error = np.sqrt((optimized_df['active_weight'] ** 2).sum())
        
        return PortfolioComposition(
            portfolio_id=portfolio_id,
            composition_df=optimized_df,
            total_weight=total_weight,
            benchmark_tracking_error=tracking_error,
            active_share=active_share
        )
    def print_detailed_analysis_report(self, analysis_result: PortfolioComparisonResult) -> None:
        """
        Print a comprehensive, detailed breakdown of the portfolio analysis results.
        
        Args:
            analysis_result: PortfolioComparisonResult from analyze_portfolio_optimization
        """
        portfolio_id = analysis_result.portfolio_id
        summary = analysis_result.optimization_summary
        metrics = analysis_result.deviation_analysis.summary_metrics
        
        print("=" * 80)
        print(f"PORTFOLIO ANALYSIS REPORT: {portfolio_id}")
        print("=" * 80)
        
        # Portfolio Overview
        print("\nPORTFOLIO OVERVIEW")
        print("-" * 40)
        print(f"Original Total Weight:     {summary['portfolio_metrics']['original_total_weight']:.4f}")
        print(f"Optimized Total Weight:    {summary['portfolio_metrics']['optimized_total_weight']:.4f}")
        print(f"Weight Difference:         {summary['portfolio_metrics']['weight_difference']:.4f}")
        print(f"Securities Count Change:   {summary['portfolio_changes']['securities_count_change']:+d}")
        
        # Benchmark Tracking Performance
        print("\nBENCHMARK TRACKING PERFORMANCE")
        print("-" * 40)
        print(f"Original Active Share:     {metrics['original_active_share']:.4f} ({metrics['original_active_share']*100:.2f}%)")
        print(f"Optimized Active Share:    {metrics['optimized_active_share']:.4f} ({metrics['optimized_active_share']*100:.2f}%)")
        print(f"Active Share Reduction:    {metrics['active_share_reduction']:.4f} ({summary['benchmark_tracking']['active_share_improvement_pct']*100:.1f}% improvement)")
        print(f"Original Tracking Error:   {metrics['original_tracking_error']:.4f}")
        print(f"Optimized Tracking Error:  {metrics['optimized_tracking_error']:.4f}")
        print(f"Tracking Error Reduction:  {metrics['tracking_error_reduction']:.4f} ({summary['benchmark_tracking']['tracking_error_improvement_pct']*100:.1f}% improvement)")
        
        # Constraint Compliance
        print("\nCONSTRAINT COMPLIANCE")
        print("-" * 40)
        print(f"Original Tolerance Violations:  {metrics['original_violations_count']:,}")
        print(f"Optimized Tolerance Violations: {metrics['optimized_violations_count']:,}")
        print(f"Violations Reduced:             {metrics['violations_reduction']:,}")
        print(f"Violation Reduction Rate:       {summary['constraint_compliance']['violation_reduction_pct']*100:.1f}%")
        print(f"Optimization Effectiveness:     {summary['portfolio_changes']['optimization_effectiveness']}")
        
        # Top Improvements
        improvements_df = analysis_result.deviation_analysis.deviation_improvements
        top_improvements = improvements_df.nlargest(10, 'deviation_improvement')
        
        print("\nTOP 10 DEVIATION IMPROVEMENTS")
        print("-" * 40)
        print(f"{'Security':<12} {'Original Dev':<12} {'Optimized Dev':<13} {'Improvement':<12} {'Improvement %':<15}")
        print("-" * 70)
        for _, row in top_improvements.iterrows():
            security = row['security_id'][:10]
            orig_dev = row['abs_active_weight_original']
            opt_dev = row['abs_active_weight_optimized']
            improvement = row['deviation_improvement']
            improvement_pct = row['improvement_pct']
            print(f"{security:<12} {orig_dev:<12.4f} {opt_dev:<13.4f} {improvement:<12.4f} {improvement_pct*100:<15.1f}%")
        
        # Remaining Violations
        violations_df = analysis_result.deviation_analysis.tolerance_violations
        
        if not violations_df.empty:
            print(f"\nREMAINING TOLERANCE VIOLATIONS ({len(violations_df)} securities)")
            print("-" * 40)
            print(f"{'Security':<12} {'Sector':<15} {'Active Weight':<12} {'Violation Amt':<15}")
            print("-" * 60)
            for _, row in violations_df.head(10).iterrows():
                security = row['security_id'][:10]
                sector = row['sector'][:13] if pd.notna(row['sector']) else 'Unknown'
                active_weight = row['active_weight']
                violation = row['violation_amount']
                print(f"{security:<12} {sector:<15} {active_weight:<12.4f} {violation:<15.4f}")
            
            if len(violations_df) > 10:
                print(f"... and {len(violations_df) - 10} more violations")
        else:
            print("\nNO REMAINING TOLERANCE VIOLATIONS")
            print("-" * 40)
            print("All securities are within the specified tolerance threshold!")
        
        # Sector Analysis
        original_df = analysis_result.original_composition.composition_df
        optimized_df = analysis_result.optimized_composition.composition_df
        
        # Calculate sector-level active weights
        original_sector = original_df.groupby('sector').agg({
            'active_weight': 'sum',
            'portfolio_weight': 'sum',
            'benchmark_weight': 'sum'
        }).round(4)
        
        optimized_sector = optimized_df.groupby('sector').agg({
            'active_weight': 'sum',
            'portfolio_weight': 'sum', 
            'benchmark_weight': 'sum'
        }).round(4)
        
        sector_comparison = original_sector.merge(
            optimized_sector, 
            left_index=True, 
            right_index=True, 
            suffixes=('_orig', '_opt'),
            how='outer'
        ).fillna(0)
        
        sector_comparison['active_weight_improvement'] = (
            sector_comparison['active_weight_orig'].abs() - sector_comparison['active_weight_opt'].abs()
        )
        
        top_sector_improvements = sector_comparison.nlargest(5, 'active_weight_improvement')
        
        print("\nTOP SECTOR IMPROVEMENTS")
        print("-" * 40)
        print(f"{'Sector':<20} {'Original AW':<12} {'Optimized AW':<13} {'Improvement':<12}")
        print("-" * 60)
        for sector, row in top_sector_improvements.iterrows():
            sector_name = sector[:18] if pd.notna(sector) else 'Unknown'
            orig_aw = row['active_weight_orig']
            opt_aw = row['active_weight_opt']
            improvement = row['active_weight_improvement']
            print(f"{sector_name:<20} {orig_aw:<12.4f} {opt_aw:<13.4f} {improvement:<12.4f}")
        
        # New Securities Added
        new_securities = optimized_df[
            (optimized_df['original_weight'] == 0) & 
            (optimized_df['portfolio_weight'] > 0)
        ]
        
        if not new_securities.empty:
            print(f"\nNEW SECURITIES ADDED ({len(new_securities)} securities)")
            print("-" * 40)
            print(f"{'Security':<12} {'Sector':<15} {'Final Weight':<12} {'Active Weight':<13}")
            print("-" * 55)
            for _, row in new_securities.head(10).iterrows():
                security = row['security_id'][:10]
                sector = row['sector'][:13] if pd.notna(row['sector']) else 'Unknown'
                final_weight = row['portfolio_weight']
                active_weight = row['active_weight']
                print(f"{security:<12} {sector:<15} {final_weight:<12.4f} {active_weight:<13.4f}")
        
        # Securities Eliminated
        eliminated_securities = optimized_df[
            (optimized_df['original_weight'] > 0) & 
            (optimized_df['portfolio_weight'] == 0)
        ]
        
        if not eliminated_securities.empty:
            print(f"\nSECURITIES ELIMINATED ({len(eliminated_securities)} securities)")
            print("-" * 40)
            print(f"{'Security':<12} {'Sector':<15} {'Original Weight':<15} {'Was Traded':<15}")
            print("-" * 60)
            for _, row in eliminated_securities.head(10).iterrows():
                security = row['security_id'][:10]
                sector = row['sector'][:13] if pd.notna(row['sector']) else 'Unknown'
                orig_weight = row['original_weight']
                was_traded = 'Yes' if row.get('was_traded', False) else 'No'
                print(f"{security:<12} {sector:<15} {orig_weight:<15.4f} {was_traded:<15}")
        
        print("\n" + "=" * 80)
        print("END OF ANALYSIS REPORT")
        print("=" * 80)

    def get_analysis_summary_dict(self, analysis_result: PortfolioComparisonResult) -> Dict[str, Any]:
        """
        Return a structured dictionary summary for programmatic use.
        
        Args:
            analysis_result: PortfolioComparisonResult from analyze_portfolio_optimization
            
        Returns:
            Dictionary with key metrics organized by category
        """
        metrics = analysis_result.deviation_analysis.summary_metrics
        summary = analysis_result.optimization_summary
        
        return {
            'portfolio_id': analysis_result.portfolio_id,
            'portfolio_metrics': {
                'total_weight_change': summary['portfolio_metrics']['weight_difference'],
                'securities_count_change': summary['portfolio_changes']['securities_count_change'],
                'optimization_effectiveness': summary['portfolio_changes']['optimization_effectiveness']
            },
            'benchmark_tracking': {
                'active_share_original': metrics['original_active_share'],
                'active_share_optimized': metrics['optimized_active_share'],
                'active_share_reduction': metrics['active_share_reduction'],
                'active_share_improvement_pct': summary['benchmark_tracking']['active_share_improvement_pct'],
                'tracking_error_original': metrics['original_tracking_error'],
                'tracking_error_optimized': metrics['optimized_tracking_error'],
                'tracking_error_reduction': metrics['tracking_error_reduction'],
                'tracking_error_improvement_pct': summary['benchmark_tracking']['tracking_error_improvement_pct']
            },
            'constraint_compliance': {
                'violations_original': metrics['original_violations_count'],
                'violations_optimized': metrics['optimized_violations_count'],
                'violations_reduced': metrics['violations_reduction'],
                'violation_reduction_pct': summary['constraint_compliance']['violation_reduction_pct']
            },
            'composition_changes': {
                'securities_added': len(analysis_result.optimized_composition.composition_df[
                    (analysis_result.optimized_composition.composition_df['original_weight'] == 0) & 
                    (analysis_result.optimized_composition.composition_df['portfolio_weight'] > 0)
                ]),
                'securities_eliminated': len(analysis_result.optimized_composition.composition_df[
                    (analysis_result.optimized_composition.composition_df['original_weight'] > 0) & 
                    (analysis_result.optimized_composition.composition_df['portfolio_weight'] == 0)
                ]),
                'securities_traded': len(analysis_result.optimized_composition.composition_df[
                    analysis_result.optimized_composition.composition_df.get('was_traded', False)
                ])
            }
        }

    def _analyze_deviations(self, portfolio_id: str,
                          original_comp: PortfolioComposition,
                          optimized_comp: PortfolioComposition,
                          holdings_df: pd.DataFrame) -> DeviationAnalysis:
        """Analyze benchmark deviations before and after optimization."""
        
        # Extract original deviations
        original_deviations = original_comp.composition_df[
            ['security_id', 'sector', 'industry_group','industry','portfolio_weight', 
             'benchmark_weight', 'active_weight']
        ].copy()
        original_deviations['abs_active_weight'] = original_deviations['active_weight'].abs()
        original_deviations['exceeds_tolerance'] = original_deviations['abs_active_weight'] > self.tolerance_threshold
        
        # Extract optimized deviations
        optimized_deviations = optimized_comp.composition_df[
            ['security_id', 'sector', 'industry_group','industry', 'portfolio_weight', 
             'benchmark_weight', 'active_weight']
        ].copy()
        optimized_deviations['abs_active_weight'] = optimized_deviations['active_weight'].abs()
        optimized_deviations['exceeds_tolerance'] = optimized_deviations['abs_active_weight'] > self.tolerance_threshold
        
        # Calculate improvements
        merged = original_deviations.merge(
            optimized_deviations, 
            on='security_id', 
            how='outer', 
            suffixes=('_original', '_optimized')
        ).fillna(0)
        
        merged['deviation_improvement'] = (
            merged['abs_active_weight_original'] - merged['abs_active_weight_optimized']
        )
        merged['improvement_pct'] = np.where(
            merged['abs_active_weight_original'] != 0,
            merged['deviation_improvement'] / merged['abs_active_weight_original'],
            0
        )
        
        # Identify tolerance violations
        tolerance_violations = optimized_deviations[
            optimized_deviations['exceeds_tolerance']
        ].copy()
        tolerance_violations['violation_amount'] = (
            tolerance_violations['abs_active_weight'] - self.tolerance_threshold
        )
        
        # Calculate summary metrics
        summary_metrics = {
            'original_active_share': original_comp.active_share,
            'optimized_active_share': optimized_comp.active_share,
            'active_share_reduction': original_comp.active_share - optimized_comp.active_share,
            'original_tracking_error': original_comp.benchmark_tracking_error,
            'optimized_tracking_error': optimized_comp.benchmark_tracking_error,
            'tracking_error_reduction': original_comp.benchmark_tracking_error - optimized_comp.benchmark_tracking_error,
            'original_violations_count': original_deviations['exceeds_tolerance'].sum(),
            'optimized_violations_count': optimized_deviations['exceeds_tolerance'].sum(),
            'violations_reduction': original_deviations['exceeds_tolerance'].sum() - optimized_deviations['exceeds_tolerance'].sum(),
            'average_deviation_improvement': merged['deviation_improvement'].mean(),
            'total_securities_original': len(original_deviations),
            'total_securities_optimized': len(optimized_deviations)
        }
        
        return DeviationAnalysis(
            portfolio_id=portfolio_id,
            original_deviations=original_deviations,
            optimized_deviations=optimized_deviations,
            deviation_improvements=merged,
            tolerance_violations=tolerance_violations,
            summary_metrics=summary_metrics
        )
    
    def _generate_optimization_summary(self, original_comp: PortfolioComposition,
                                     optimized_comp: PortfolioComposition,
                                     deviation_analysis: DeviationAnalysis) -> Dict[str, Any]:
        """Generate comprehensive optimization summary."""
        
        metrics = deviation_analysis.summary_metrics
        
        return {
            'portfolio_metrics': {
                'original_total_weight': original_comp.total_weight,
                'optimized_total_weight': optimized_comp.total_weight,
                'weight_difference': optimized_comp.total_weight - original_comp.total_weight
            },
            'benchmark_tracking': {
                'active_share_improvement': metrics['active_share_reduction'],
                'active_share_improvement_pct': metrics['active_share_reduction'] / metrics['original_active_share'] if metrics['original_active_share'] > 0 else 0,
                'tracking_error_improvement': metrics['tracking_error_reduction'],
                'tracking_error_improvement_pct': metrics['tracking_error_reduction'] / metrics['original_tracking_error'] if metrics['original_tracking_error'] > 0 else 0
            },
            'constraint_compliance': {
                'tolerance_violations_reduced': metrics['violations_reduction'],
                'remaining_violations': metrics['optimized_violations_count'],
                'violation_reduction_pct': metrics['violations_reduction'] / metrics['original_violations_count'] if metrics['original_violations_count'] > 0 else 0
            },
            'portfolio_changes': {
                'securities_count_change': metrics['total_securities_optimized'] - metrics['total_securities_original'],
                'average_deviation_improvement': metrics['average_deviation_improvement'],
                'optimization_effectiveness': 'Excellent' if metrics['active_share_reduction'] > 0.02 else 'Good' if metrics['active_share_reduction'] > 0.01 else 'Moderate'
            }
        }
    


    
    def export_analysis_to_excel(self, analysis_result: PortfolioComparisonResult, 
                               filename: str = None) -> str:
        """Export complete analysis to Excel file with multiple sheets."""
        
        if filename is None:
            filename = f"portfolio_analysis_{analysis_result.portfolio_id}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Original composition
            analysis_result.original_composition.composition_df.to_excel(
                writer, sheet_name='Original_Composition', index=False
            )
            
            # Optimized composition
            analysis_result.optimized_composition.composition_df.to_excel(
                writer, sheet_name='Optimized_Composition', index=False
            )
            
            # Deviation analysis
            analysis_result.deviation_analysis.deviation_improvements.to_excel(
                writer, sheet_name='Deviation_Analysis', index=False
            )
            
            # Tolerance violations
            analysis_result.deviation_analysis.tolerance_violations.to_excel(
                writer, sheet_name='Tolerance_Violations', index=False
            )
            
            # Summary metrics
            summary_df = pd.DataFrame([analysis_result.optimization_summary])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        self.logger.info(f"Analysis exported to {filename}")
        return filename


def example_usage():
    """Example of how to use the portfolio analytics engine."""
    
    # Initialize analytics engine
    analytics_engine = PortfolioAnalyticsEngine(tolerance_threshold=0.01)
    
    # Analyze single portfolio (using data from optimization result)
    # analysis_result = analytics_engine.analyze_portfolio_optimization(
    #     portfolio_id="P-93050",
    #     original_holdings_df=optimization_result.clean_holdings_data,
    #     proposed_trades_df=optimization_result.proposed_trades_df
    # )
    
    # Print summary
    # print("Portfolio Analysis Summary:")
    # print(f"Active Share Reduction: {analysis_result.optimization_summary['benchmark_tracking']['active_share_improvement']:.3f}")
    # print(f"Tolerance Violations Reduced: {analysis_result.optimization_summary['constraint_compliance']['tolerance_violations_reduced']}")
    
    # Export to Excel
    # filename = analytics_engine.export_analysis_to_excel(analysis_result)
    # print(f"Analysis exported to: {filename}")
    
    pass

if __name__ == "__main__":
    example_usage()