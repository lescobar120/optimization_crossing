# workflow_state.py
from typing import Dict, Optional, Any
from datetime import datetime

# Import result structures
from .orchestrator import OptimizationResult
from analytics.portfolio_analytics_engine import PortfolioComparisonResult
from analytics.crossing_engine import CrossingResult

class WorkflowState:
    """
    Shared state container for portfolio optimization workflow.
    
    Manages data flow between configuration UI and results display tabs.
    Does not persist between sessions - starts fresh each time.
    """
    
    def __init__(self):
        """Initialize empty workflow state."""
        # Optimization results from orchestrator
        self.optimization_results: Dict[str, OptimizationResult] = {}
        
        # Analysis results from portfolio analytics engine
        self.analysis_results: Dict[str, PortfolioComparisonResult] = {}
        
        # Crossing results from crossing engine
        self.crossing_result: Optional[CrossingResult] = None
        
        # Generated charts data
        self.charts_data: Dict[str, Dict[str, Any]] = {
            'portfolio': {},  # Portfolio analysis charts
            'crossing': {}    # Crossing analysis charts
        }
        
        # State tracking
        self.optimization_complete: bool = False
        self.analysis_complete: bool = False
        self.crossing_complete: bool = False
        self.charts_built: Dict[str, bool] = {
            'portfolio': False,
            'crossing': False
        }
        
        # Timestamps for tracking
        self.optimization_timestamp: Optional[datetime] = None
        self.crossing_timestamp: Optional[datetime] = None
    
    def set_optimization_results(self, results: Dict[str, OptimizationResult]) -> None:
        """
        Set optimization results and update state.
        
        Args:
            results: Dictionary of portfolio_id -> OptimizationResult
        """
        self.optimization_results = results
        self.optimization_complete = True
        self.optimization_timestamp = datetime.now()
        
        # Reset dependent states
        self.analysis_complete = False
        self.crossing_complete = False
        self.crossing_result = None
        self.charts_built = {'portfolio': False, 'crossing': False}
        
        # Clear dependent data
        self.analysis_results = {}
        self.charts_data = {'portfolio': {}, 'crossing': {}}
    
    def set_analysis_results(self, results: Dict[str, PortfolioComparisonResult]) -> None:
        """
        Set portfolio analysis results.
        
        Args:
            results: Dictionary of portfolio_id -> PortfolioComparisonResult
        """
        self.analysis_results = results
        self.analysis_complete = True
    
    def set_crossing_result(self, result: CrossingResult) -> None:
        """
        Set crossing analysis result and update state.
        
        Args:
            result: CrossingResult from crossing engine
        """
        self.crossing_result = result
        self.crossing_complete = True
        self.crossing_timestamp = datetime.now()
        
        # Reset crossing charts
        self.charts_built['crossing'] = False
        self.charts_data['crossing'] = {}
    
    def set_portfolio_charts(self, charts: Dict[str, Any]) -> None:
        """
        Set portfolio analysis charts.
        
        Args:
            charts: Dictionary of chart_name -> plotly Figure
        """
        self.charts_data['portfolio'] = charts
        self.charts_built['portfolio'] = True
    
    def set_crossing_charts(self, charts: Dict[str, Any]) -> None:
        """
        Set crossing analysis charts.
        
        Args:
            charts: Dictionary of chart_name -> plotly Figure
        """
        self.charts_data['crossing'] = charts
        self.charts_built['crossing'] = True
    
    def get_combined_charts(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available charts organized by source.
        
        Returns:
            Dictionary of source_name -> charts for dashboard manager
        """
        combined = {}
        
        if self.charts_built['portfolio']:
            combined['portfolio'] = self.charts_data['portfolio']
        
        if self.charts_built['crossing']:
            combined['crossing'] = self.charts_data['crossing']
        
        return combined
    
    def is_ready_for_optimization_ui(self) -> bool:
        """Check if data is ready for optimization results UI."""
        return self.optimization_complete and self.analysis_complete
    
    def is_ready_for_crossing_ui(self) -> bool:
        """Check if data is ready for crossing results UI."""
        return self.crossing_complete
    
    def is_ready_for_charts_dashboard(self) -> bool:
        """Check if any charts are available for dashboard."""
        return any(self.charts_built.values())
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary statistics for optimization results."""
        if not self.optimization_complete:
            return {}
        
        total_portfolios = len(self.optimization_results)
        successful = sum(1 for r in self.optimization_results.values() if r.status == "SUCCESS")
        failed = sum(1 for r in self.optimization_results.values() if r.status == "FAILED")
        warnings = sum(1 for r in self.optimization_results.values() if r.status == "WARNING")
        
        return {
            'total_portfolios': total_portfolios,
            'successful': successful,
            'failed': failed,
            'warnings': warnings,
            'success_rate': successful / total_portfolios if total_portfolios > 0 else 0,
            'timestamp': self.optimization_timestamp
        }
    
    def get_crossing_summary(self) -> Dict[str, Any]:
        """Get summary statistics for crossing results."""
        if not self.crossing_complete or not self.crossing_result:
            return {}
        
        summary = self.crossing_result.crossing_summary
        summary['timestamp'] = self.crossing_timestamp
        return summary
    
    def reset_all(self) -> None:
        """Reset all workflow state to initial empty state."""
        self.optimization_results = {}
        self.analysis_results = {}
        self.crossing_result = None
        self.charts_data = {'portfolio': {}, 'crossing': {}}
        
        self.optimization_complete = False
        self.analysis_complete = False
        self.crossing_complete = False
        self.charts_built = {'portfolio': False, 'crossing': False}
        
        self.optimization_timestamp = None
        self.crossing_timestamp = None
    
    def reset_crossing_data(self) -> None:
        """Reset only crossing-related data (for re-running crossing)."""
        self.crossing_result = None
        self.crossing_complete = False
        self.charts_built['crossing'] = False
        self.charts_data['crossing'] = {}
        self.crossing_timestamp = None
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get overall workflow status summary."""
        return {
            'optimization_complete': self.optimization_complete,
            'analysis_complete': self.analysis_complete,
            'crossing_complete': self.crossing_complete,
            'portfolio_charts_ready': self.charts_built['portfolio'],
            'crossing_charts_ready': self.charts_built['crossing'],
            'optimization_timestamp': self.optimization_timestamp,
            'crossing_timestamp': self.crossing_timestamp,
            'total_portfolios': len(self.optimization_results),
            'charts_available': sum(len(charts) for charts in self.charts_data.values())
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        status = self.get_status_summary()
        return f"WorkflowState(opt={status['optimization_complete']}, crossing={status['crossing_complete']}, charts={status['charts_available']})"