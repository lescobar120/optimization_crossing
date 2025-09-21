import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import time
import logging
from dataclasses import dataclass

@dataclass
class OptimizationResult:
    """Structure for optimization results."""
    portfolio_id: str
    status: str  # SUCCESS, FAILED, WARNING
    optimization_id: Optional[str] = None
    summary: Optional[Dict] = None
    goals: Optional[List] = None
    constraints: Optional[List] = None
    proposed_trades: Optional[List] = None
    proposed_trades_df: Optional[pd.DataFrame] = None
    replacements_found: Optional[Dict] = None
    restriction_compliance: Optional[bool] = None
    restriction_violations: Optional[List[str]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    optimization_date: Optional[str] = None
    clean_holdings_data: Optional[pd.DataFrame] = None

class OptimizationOrchestrator:
    """
    Orchestrates the complete portfolio optimization workflow.
    Handles data retrieval, constraint generation, optimization execution, and result validation.
    """
    
    def __init__(self, report_handler, config_manager, builder, log_file: str = None):
        """
        Initialize the orchestrator with required components.
        
        Args:
            report_handler: ReportHandler instance for data retrieval
            config_manager: PortfolioConfigManager instance  
            builder: PortfolioOptimizerRequestBuilder instance
            log_file: Optional log file path
        """
        self.report_handler = report_handler
        self.config_manager = config_manager
        self.builder = builder
        
        # Import here to avoid circular dependencies
        from data.holdings_processor import HoldingsDataProcessor
        from optimization.matcher import SecurityReplacementMatcher
        from .optimization_workflow import get_optimization_response
        
        self.processor = HoldingsDataProcessor()
        self._get_optimization_response = get_optimization_response
        
        # Setup logging
        self.logger = setup_logger(log_file=log_file)
        self.logger.info("OptimizationOrchestrator initialized")
    
    def run_single_optimization(self, portfolio_id: str, 
                              optimization_date: Optional[str] = None,
                              report_name: str = "pre_optimization_crossing_msr") -> OptimizationResult:
        """
        Run optimization for a single portfolio.
        
        Args:
            portfolio_id: Portfolio identifier
            optimization_date: Date for optimization (defaults to today)
            report_name: Name of the MSR report to retrieve portfolio and benchmark holdings info
            
        Returns:
            OptimizationResult with execution details
        """
        start_time = time.time()
        
        # Set default date to today if not provided
        if optimization_date is None:
            optimization_date = date.today().strftime("%Y-%m-%d")
        
        try:
            # Step 1: Validate portfolio exists in config
            if portfolio_id not in self.config_manager.configs:
                return OptimizationResult(
                    portfolio_id=portfolio_id,
                    status="FAILED",
                    error_message=f"Portfolio {portfolio_id} not found in configuration",
                    execution_time=time.time() - start_time,
                    optimization_date=optimization_date
                )
            
            portfolio_config = self.config_manager.get_config(portfolio_id)
            
            # Step 2: Retrieve holdings data
            self.logger.info(f"Retrieving holdings data for {portfolio_id}")
            rpt_res = self.report_handler.get_report(
                portfolio=portfolio_id,
                report=report_name,
                dates=[optimization_date]
            )
            
            # Check if report retrieval was successful
            if not (200 <= rpt_res.status_code < 300):
                return OptimizationResult(
                    portfolio_id=portfolio_id,
                    status="FAILED",
                    error_message=f"Failed to retrieve report data: {rpt_res.status_code}",
                    execution_time=time.time() - start_time,
                    optimization_date=optimization_date
                )
            
            # Step 3: Process holdings data
            report_records = self.report_handler.get_records_from_response(rpt_res)
            frame = pd.DataFrame(report_records)
            
            if frame.empty:
                return OptimizationResult(
                    portfolio_id=portfolio_id,
                    status="FAILED", 
                    error_message="No holdings data retrieved from report",
                    execution_time=time.time() - start_time,
                    optimization_date=optimization_date
                )
            
            frame_clean = self.processor.clean_holdings_dataframe(frame)
            
            # Step 4: Build optimization request with constraints
            self.logger.info(f"Building optimization request for {portfolio_id}")
            
            # Get restricted securities from config
            restricted_securities = portfolio_config.restricted_securities or []

            # handles both scenarios of restricted securities and no restrictions
            api_request, replacements = self.builder.build_request_with_security_constraints(
                portfolio_id=portfolio_id,
                frame_clean=frame_clean,
                restricted_securities=restricted_securities,
                as_of_date=optimization_date
            )
            
            # Step 5: Execute optimization
            self.logger.info(f"Executing optimization for {portfolio_id}")
            optimization_response = self._get_optimization_response(api_request)

            proposed_trades = optimization_response.get('proposedTrades', [])
            proposed_trades_df = self._convert_proposed_trades_to_dataframe(proposed_trades)
            
            # Step 6: Validate restriction compliance
            compliance_result = self._validate_restriction_compliance(
                optimization_response.get('proposedTrades', []),
                restricted_securities,
                frame_clean
            )
            
            # Step 7: Determine final status
            final_status = "SUCCESS"
            if not compliance_result['compliant']:
                final_status = "WARNING"
                self.logger.warning(f"Restriction violations found for {portfolio_id}: {compliance_result['violations']}")
            
            execution_time = time.time() - start_time
            self.logger.info(f"Optimization completed for {portfolio_id} in {execution_time:.2f} seconds")
            
            return OptimizationResult(
                portfolio_id=portfolio_id,
                status=final_status,
                optimization_id=optimization_response.get('optimizationId'),
                summary=optimization_response.get('summary'),
                goals=optimization_response.get('goals'),
                constraints=optimization_response.get('constraints'),
                proposed_trades=proposed_trades,
                proposed_trades_df=proposed_trades_df,
                replacements_found=replacements,
                restriction_compliance=compliance_result['compliant'],
                restriction_violations=compliance_result['violations'],
                execution_time=execution_time,
                optimization_date=optimization_date,
                clean_holdings_data=frame_clean
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = f"Optimization failed for {portfolio_id}: {str(e)}"
            self.logger.error(error_message)
            
            return OptimizationResult(
                portfolio_id=portfolio_id,
                status="FAILED",
                error_message=error_message,
                execution_time=execution_time,
                optimization_date=optimization_date,
                clean_holdings_data=frame_clean if 'frame_clean' in locals() else None
            )
    
    def run_batch_optimizations(self, portfolio_ids: List[str],
                              optimization_date: Optional[str] = None,
                              report_name: str = "pre_optimization_crossing_msr") -> Dict[str, OptimizationResult]:
        """
        Run optimizations for multiple portfolios.
        
        Args:
            portfolio_ids: List of portfolio identifiers
            optimization_date: Date for optimization (defaults to today)
            report_name: Name of the report to retrieve
            
        Returns:
            Dictionary mapping portfolio_id -> OptimizationResult
        """
        self.logger.info(f"Starting batch optimization for {len(portfolio_ids)} portfolios")
        
        results = {}
        
        for portfolio_id in portfolio_ids:
            self.logger.info(f"Processing portfolio {portfolio_id}")
            
            result = self.run_single_optimization(
                portfolio_id=portfolio_id,
                optimization_date=optimization_date,
                report_name=report_name
            )
            
            results[portfolio_id] = result
            
            # Log progress
            self.logger.info(f"Portfolio {portfolio_id} completed with status: {result.status}")
            if result.status == "FAILED":
                self.logger.error(f"Portfolio {portfolio_id} failed: {result.error_message}")
            elif result.status == "WARNING":
                self.logger.warning(f"Portfolio {portfolio_id} has warnings: {result.restriction_violations}")
        
        # Log batch summary
        success_count = sum(1 for r in results.values() if r.status == "SUCCESS")
        warning_count = sum(1 for r in results.values() if r.status == "WARNING") 
        failed_count = sum(1 for r in results.values() if r.status == "FAILED")
        
        self.logger.info(f"Batch optimization completed: {success_count} success, {warning_count} warnings, {failed_count} failures")
        
        return results
    
    def _convert_proposed_trades_to_dataframe(self, proposed_trades: List[Dict]) -> pd.DataFrame:
        """
        Convert proposed trades list to a pandas DataFrame.
        
        Args:
            proposed_trades: List of proposed trade dictionaries from optimization response
            
        Returns:
            DataFrame with proposed trades data
        """
        if not proposed_trades:
            return pd.DataFrame()
        
        # Convert list of dictionaries to DataFrame
        trades_df = pd.DataFrame(proposed_trades)
        
        # Handle the nested 'changedQuantity' field
        if 'changedQuantity' in trades_df.columns:
            # Extract 'type' and 'value' from changedQuantity dictionary
            trades_df['changedQuantity_type'] = trades_df['changedQuantity'].apply(
                lambda x: x.get('type', None) if isinstance(x, dict) else None
            )
            trades_df['changedQuantity_value'] = trades_df['changedQuantity'].apply(
                lambda x: x.get('value', None) if isinstance(x, dict) else None
            )
            
            # Drop the original nested column
            trades_df = trades_df.drop('changedQuantity', axis=1)
        
        # Ensure numeric columns are properly typed
        numeric_columns = [
            'initialWeight', 'finalWeight', 'changedWeight', 
            'changedAmount', 'transactionCost', 'changedQuantity_value'
        ]
        
        for col in numeric_columns:
            if col in trades_df.columns:
                trades_df[col] = pd.to_numeric(trades_df[col], errors='coerce')
        
        return trades_df

    def _validate_restriction_compliance(self, proposed_trades: List[Dict],
                                    restricted_securities: List[str],
                                    frame_clean: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate that restricted securities have finalWeight = 0.
        
        Args:
            proposed_trades: List of proposed trades from optimization response
            restricted_securities: List of restricted security identifiers (ID059 format)
            frame_clean: Clean holdings dataframe for identifier mapping
            
        Returns:
            Dictionary with compliance status and any violations
        """
        violations = []
        
        if not restricted_securities:
            return {'compliant': True, 'violations': []}
        
        # Create mapping from ID059 to ticker (OUTPUT_ID column)
        id059_to_ticker = {}
        for _, row in frame_clean.iterrows():
            id059_to_ticker[row['ID059']] = row['OUTPUT_ID']
        
        # Create a lookup of ticker -> finalWeight from proposed trades
        trade_lookup = {
            trade.get('ticker', ''): trade.get('finalWeight', 0)
            for trade in proposed_trades
        }
        
        # Check each restricted security
        for restricted_id059 in restricted_securities:
            # Convert ID059 to ticker using mapping
            ticker = id059_to_ticker.get(restricted_id059)
            
            if ticker is None:
                # Couldn't find mapping - this is a problem
                violations.append({
                    'security_id': restricted_id059,
                    'ticker': 'UNKNOWN',
                    'final_weight': 'N/A',
                    'expected_weight': 0.0,
                    'issue': 'Could not map ID059 to ticker'
                })
                continue
            
            # Get final weight from proposed trades
            final_weight = trade_lookup.get(ticker, 0)
            
            # Allow for small floating point tolerance
            if abs(final_weight) > 1e-6:  # 0.0001% tolerance
                violations.append({
                    'security_id': restricted_id059,
                    'ticker': ticker,
                    'final_weight': final_weight,
                    'expected_weight': 0.0,
                    'issue': 'Final weight not zero'
                })
        
        return {
            'compliant': len(violations) == 0,
            'violations': violations
        }
    
    def get_batch_summary(self, results: Dict[str, OptimizationResult]) -> Dict[str, Any]:
        """
        Generate summary statistics for batch optimization results.
        
        Args:
            results: Dictionary of optimization results
            
        Returns:
            Summary statistics
        """
        if not results:
            return {'total': 0, 'success': 0, 'warnings': 0, 'failures': 0}
        
        status_counts = {'SUCCESS': 0, 'WARNING': 0, 'FAILED': 0}
        total_execution_time = 0
        total_replacements = 0
        portfolios_with_restrictions = 0
        
        for result in results.values():
            status_counts[result.status] += 1
            
            if result.execution_time:
                total_execution_time += result.execution_time
            
            if result.replacements_found:
                total_replacements += len(result.replacements_found)
                
            if result.replacements_found or (result.restriction_violations and len(result.restriction_violations) > 0):
                portfolios_with_restrictions += 1
        
        return {
            'total_portfolios': len(results),
            'success_count': status_counts['SUCCESS'],
            'warning_count': status_counts['WARNING'],
            'failure_count': status_counts['FAILED'],
            'total_execution_time': total_execution_time,
            'average_execution_time': total_execution_time / len(results) if results else 0,
            'total_replacements_made': total_replacements,
            'portfolios_with_restrictions': portfolios_with_restrictions,
            'success_rate': status_counts['SUCCESS'] / len(results) if results else 0
        }
    
    def export_results_to_dataframe(self, results: Dict[str, OptimizationResult]) -> pd.DataFrame:
        """
        Export optimization results to a pandas DataFrame for analysis.
        
        Args:
            results: Dictionary of optimization results
            
        Returns:
            DataFrame with key result metrics
        """
        data = []
        
        for portfolio_id, result in results.items():
            row = {
                'portfolio_id': portfolio_id,
                'status': result.status,
                'optimization_id': result.optimization_id,
                'execution_time': result.execution_time,
                'optimization_date': result.optimization_date,
                'restriction_compliance': result.restriction_compliance,
                'num_violations': len(result.restriction_violations) if result.restriction_violations else 0,
                'num_replacements': len(result.replacements_found) if result.replacements_found else 0,
                'error_message': result.error_message
            }
            
            # Add summary metrics if available
            if result.summary:
                row.update({
                    'turnover_rate': result.summary.get('turnoverRate'),
                    'trades_value': result.summary.get('tradesValue'),
                    'buy_number': result.summary.get('buyNumber'),
                    'sell_number': result.summary.get('sellNumber')
                })
            
            # Add goal metrics if available
            if result.goals:
                for goal in result.goals:
                    field_code = goal.get('fieldCode', 'unknown')
                    row[f'{field_code}_initial'] = goal.get('initialValue')
                    row[f'{field_code}_final'] = goal.get('finalValue')
            
            data.append(row)
        
        return pd.DataFrame(data)


import logging
import os
from datetime import datetime

def setup_logger(name: str = "optimization_orchestrator", 
                log_level: int = logging.INFO,
                log_file: str = None) -> logging.Logger:
    """
    Setup logger that outputs to both console and file.
    
    Args:
        name: Logger name
        log_level: Logging level (INFO, DEBUG, etc.)
        log_file: Log file path (defaults to timestamped file)
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        today_date = datetime.now().strftime('%Y-%m-%d')
        log_file = f'logs/optimization_{today_date}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger