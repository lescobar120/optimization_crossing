import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import uuid
import logging
import os
from datetime import datetime

@dataclass
class CrossedTrade:
    """Structure for a crossed trade between two portfolios."""
    cross_id: str
    security: str
    quantity_crossed: int
    buyer_portfolio: str
    seller_portfolio: str
    buyer_original_quantity: int
    seller_original_quantity: int

@dataclass
class RemainingTrade:
    """Structure for trades remaining after crossing."""
    portfolio_id: str
    security: str
    original_quantity: int
    crossed_quantity: int
    remaining_quantity: int
    trade_direction: str  # 'BUY' or 'SELL'

@dataclass
class ExternalLiquidityFlag:
    """Structure for flagging same-direction trades needing external liquidity."""
    security: str
    direction: str  # 'BUY' or 'SELL'
    total_quantity: int
    portfolios: List[str]

@dataclass
class CrossingResult:
    """Complete result of the crossing engine."""
    crossed_trades: List[CrossedTrade]
    remaining_trades: List[RemainingTrade]
    external_liquidity_flags: List[ExternalLiquidityFlag]
    crossing_summary: Dict[str, Any]

class CrossingEngineConfig:
    """Configuration for the crossing engine."""
    
    def __init__(self, portfolio_priority: List[str]):
        """
        Initialize crossing engine configuration.
        
        Args:
            portfolio_priority: Ordered list of portfolio IDs by priority
                               (highest to lowest priority for filling orders)
        """
        self.portfolio_priority = portfolio_priority
        self.excluded_securities = ['USD']  # Securities to exclude from crossing
        
    def get_portfolio_priority_score(self, portfolio_id: str) -> int:
        """Get priority score for a portfolio (lower score = higher priority)."""
        try:
            return self.portfolio_priority.index(portfolio_id)
        except ValueError:
            # If portfolio not in priority list, assign lowest priority
            return len(self.portfolio_priority)

class PortfolioCrossingEngine:
    """
    Engine for identifying and executing crossing opportunities between portfolios.
    
    Maximizes total volume crossed while respecting portfolio priorities.
    """
    
    def __init__(self, config: CrossingEngineConfig, log_file: str = None):
        """
        Initialize the crossing engine.
        
        Args:
            config: Crossing engine configuration
        """
        self.config = config
        self.logger = setup_crossing_logger(log_file=log_file)
        self.logger.info("PortfolioCrossingEngine initialized")
        
    def execute_crossing(self, portfolio_trades: Dict[str, pd.DataFrame]) -> CrossingResult:
        """
        Execute crossing analysis on portfolio trades.
        
        Args:
            portfolio_trades: Dictionary mapping portfolio_id -> proposed_trades_df
            
        Returns:
            CrossingResult with crossed trades, remaining trades, and flags
        """
        self.logger.info(f"Starting crossing analysis for {len(portfolio_trades)} portfolios")
        
        # Step 1: Aggregate and clean trade data
        aggregated_trades = self._aggregate_trades(portfolio_trades)
        
        # Step 2: Identify crossing opportunities by security
        crossed_trades = []
        remaining_trades = []
        
        for security in aggregated_trades.keys():
            if security in self.config.excluded_securities:
                # Add excluded securities directly to remaining trades
                for portfolio_id, trade_info in aggregated_trades[security].items():
                    remaining_trades.append(RemainingTrade(
                        portfolio_id=portfolio_id,
                        security=security,
                        original_quantity=trade_info['quantity'],
                        crossed_quantity=0,
                        remaining_quantity=trade_info['quantity'],
                        trade_direction=trade_info['direction']
                    ))
                continue
                
            security_crosses, security_remaining = self._cross_security_trades(
                security, aggregated_trades[security]
            )
            crossed_trades.extend(security_crosses)
            remaining_trades.extend(security_remaining)
        
        # Step 3: Identify external liquidity needs
        external_liquidity_flags = self._identify_external_liquidity_needs(remaining_trades)
        
        # Step 4: Generate summary statistics
        crossing_summary = self._generate_crossing_summary(
            crossed_trades, remaining_trades, portfolio_trades
        )
        
        self.logger.info(f"Crossing completed: {len(crossed_trades)} crosses identified")
        
        return CrossingResult(
            crossed_trades=crossed_trades,
            remaining_trades=remaining_trades,
            external_liquidity_flags=external_liquidity_flags,
            crossing_summary=crossing_summary
        )
    
    def _aggregate_trades(self, portfolio_trades: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Dict]]:
        """
        Aggregate trades by security and portfolio.
        
        Returns:
            Dict[security -> Dict[portfolio_id -> trade_info]]
        """
        aggregated = {}
        
        for portfolio_id, trades_df in portfolio_trades.items():
            if trades_df.empty:
                continue
                
            # Filter out zero quantity trades and excluded securities
            active_trades = trades_df[
                (trades_df['changedQuantity_value'] != 0) & 
                (~trades_df['instrumentUniqueId'].isin(self.config.excluded_securities))
            ].copy()
            
            for _, trade in active_trades.iterrows():
                security = trade['instrumentUniqueId']
                quantity = int(trade['changedQuantity_value'])
                
                if security not in aggregated:
                    aggregated[security] = {}
                
                aggregated[security][portfolio_id] = {
                    'quantity': quantity,
                    'direction': 'BUY' if quantity > 0 else 'SELL',
                    'abs_quantity': abs(quantity)
                }
        
        return aggregated
    
    def _cross_security_trades(self, security: str, 
                             security_trades: Dict[str, Dict]) -> Tuple[List[CrossedTrade], List[RemainingTrade]]:
        """
        Execute crossing for a specific security.
        
        Args:
            security: Security identifier
            security_trades: Dict[portfolio_id -> trade_info] for this security
            
        Returns:
            Tuple of (crossed_trades, remaining_trades) for this security
        """
        # Separate buyers and sellers
        buyers = [(portfolio_id, info) for portfolio_id, info in security_trades.items() 
                 if info['direction'] == 'BUY']
        sellers = [(portfolio_id, info) for portfolio_id, info in security_trades.items() 
                  if info['direction'] == 'SELL']
        
        # Sort buyers by quantity (largest first to maximize volume crossed)
        buyers.sort(key=lambda x: x[1]['abs_quantity'], reverse=True)
        
        # Sort sellers by priority, then by quantity (largest first)
        sellers.sort(key=lambda x: (
            self.config.get_portfolio_priority_score(x[0]),
            -x[1]['abs_quantity']
        ))
        
        crossed_trades = []
        
        # Track remaining quantities for each portfolio
        remaining_quantities = {
            portfolio_id: info['quantity'] 
            for portfolio_id, info in security_trades.items()
        }
        
        # Execute crossing: match largest buyers with prioritized sellers
        for buyer_portfolio, buyer_info in buyers:
            buyer_remaining = remaining_quantities[buyer_portfolio]
            
            if buyer_remaining <= 0:
                continue
                
            for seller_portfolio, seller_info in sellers:
                seller_remaining = remaining_quantities[seller_portfolio]
                
                if seller_remaining >= 0:  # No more to sell
                    continue
                    
                # Calculate crossing quantity (limited by both buyer and seller capacity)
                cross_quantity = min(buyer_remaining, abs(seller_remaining))
                
                if cross_quantity > 0:
                    # Create crossed trade
                    crossed_trade = CrossedTrade(
                        cross_id=str(uuid.uuid4()),
                        security=security,
                        quantity_crossed=cross_quantity,
                        buyer_portfolio=buyer_portfolio,
                        seller_portfolio=seller_portfolio,
                        buyer_original_quantity=buyer_info['quantity'],
                        seller_original_quantity=seller_info['quantity']
                    )
                    crossed_trades.append(crossed_trade)
                    
                    # Update remaining quantities
                    remaining_quantities[buyer_portfolio] -= cross_quantity
                    remaining_quantities[seller_portfolio] += cross_quantity
                    
                    self.logger.debug(
                        f"Crossed {cross_quantity} shares of {security} "
                        f"from {seller_portfolio} to {buyer_portfolio}"
                    )
                    
                    # If buyer is fully satisfied, move to next buyer
                    if remaining_quantities[buyer_portfolio] <= 0:
                        break


                ## Note:
                    ## Seller continuation: 
                    ## Inside the inner loop, after a partial cross, the code proceeds to the next seller even if the current seller still has inventory. 
                    # If you want to exhaust the current priority seller before moving on, loop while the current seller has remaining supply
        
        # Create remaining trades
        remaining_trades = []
        for portfolio_id, remaining_qty in remaining_quantities.items():
            if remaining_qty != 0:
                original_qty = security_trades[portfolio_id]['quantity']
                crossed_qty = original_qty - remaining_qty
                
                remaining_trades.append(RemainingTrade(
                    portfolio_id=portfolio_id,
                    security=security,
                    original_quantity=original_qty,
                    crossed_quantity=crossed_qty,
                    remaining_quantity=remaining_qty,
                    trade_direction='BUY' if remaining_qty > 0 else 'SELL'
                ))
        
        return crossed_trades, remaining_trades
    
    def _identify_external_liquidity_needs(self, remaining_trades: List[RemainingTrade]) -> List[ExternalLiquidityFlag]:
        """
        Identify securities where all portfolios are trading in the same direction.
        
        Args:
            remaining_trades: List of remaining trades after crossing
            
        Returns:
            List of external liquidity flags
        """
        # Aggregate remaining trades by security and direction
        security_directions = {}
        
        for trade in remaining_trades:
            if trade.remaining_quantity == 0:
                continue
                
            security = trade.security
            direction = trade.trade_direction
            
            if security not in security_directions:
                security_directions[security] = {'BUY': [], 'SELL': []}
            
            security_directions[security][direction].append({
                'portfolio': trade.portfolio_id,
                'quantity': abs(trade.remaining_quantity)
            })
        
        # Identify securities with only one direction
        external_liquidity_flags = []
        
        for security, directions in security_directions.items():
            # Check if only buying or only selling
            has_buyers = len(directions['BUY']) > 0
            has_sellers = len(directions['SELL']) > 0
            
            if has_buyers and not has_sellers:
                # Only buyers - need external sellers
                total_quantity = sum(trade['quantity'] for trade in directions['BUY'])
                portfolios = [trade['portfolio'] for trade in directions['BUY']]
                
                external_liquidity_flags.append(ExternalLiquidityFlag(
                    security=security,
                    direction='BUY',
                    total_quantity=total_quantity,
                    portfolios=portfolios
                ))
                
            elif has_sellers and not has_buyers:
                # Only sellers - need external buyers
                total_quantity = sum(trade['quantity'] for trade in directions['SELL'])
                portfolios = [trade['portfolio'] for trade in directions['SELL']]
                
                external_liquidity_flags.append(ExternalLiquidityFlag(
                    security=security,
                    direction='SELL',
                    total_quantity=total_quantity,
                    portfolios=portfolios
                ))
        
        return external_liquidity_flags
    
    def _generate_crossing_summary(self, crossed_trades: List[CrossedTrade],
                                 remaining_trades: List[RemainingTrade],
                                 original_trades: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Generate summary statistics for the crossing analysis."""
        
        # Calculate original trade volumes
        original_volume = 0
        original_trade_count = 0
        
        for trades_df in original_trades.values():
            if not trades_df.empty:
                # Exclude USD and zero quantity trades
                active_trades = trades_df[
                    (trades_df['changedQuantity_value'] != 0) & 
                    (trades_df['instrumentUniqueId'] != 'USD') # update this to look at exclusion list instead
                ]
                original_volume += active_trades['changedQuantity_value'].abs().sum()
                original_trade_count += len(active_trades)
        
        # Calculate crossed volumes
        crossed_volume = sum(trade.quantity_crossed for trade in crossed_trades)
        crossed_trade_count = len(crossed_trades)
        
        # Calculate remaining volumes
        remaining_volume = sum(abs(trade.remaining_quantity) for trade in remaining_trades)
        remaining_trade_count = len([t for t in remaining_trades if t.remaining_quantity != 0])
        
        # Calculate crossing efficiency
        crossing_rate = crossed_volume / original_volume if original_volume > 0 else 0
        
        return {
            'total_portfolios': len(original_trades),
            'original_trade_count': original_trade_count,
            'original_volume': original_volume,
            'crossed_trade_count': crossed_trade_count,
            'crossed_volume': crossed_volume,
            'remaining_trade_count': remaining_trade_count,
            'remaining_volume': remaining_volume,
            'crossing_rate': crossing_rate,
            'volume_reduction': crossed_volume / 2,  # Each cross eliminates volume from both sides
            'securities_with_crosses': len(set(trade.security for trade in crossed_trades)),
            'securities_needing_external_liquidity': len(set(
                trade.security for trade in remaining_trades if trade.remaining_quantity != 0
            ))
        }
    
    def export_crossed_trades_to_dataframe(self, crossed_trades: List[CrossedTrade]) -> pd.DataFrame:
        """Export crossed trades to DataFrame for analysis."""
        if not crossed_trades:
            return pd.DataFrame()
        
        data = []
        for trade in crossed_trades:
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
    
    def export_remaining_trades_to_dataframe(self, remaining_trades: List[RemainingTrade]) -> pd.DataFrame:
        """Export remaining trades to DataFrame for analysis."""
        if not remaining_trades:
            return pd.DataFrame()
        
        data = []
        for trade in remaining_trades:
            data.append({
                'portfolio_id': trade.portfolio_id,
                'security': trade.security,
                'original_quantity': trade.original_quantity,
                'crossed_quantity': trade.crossed_quantity,
                'remaining_quantity': trade.remaining_quantity,
                'trade_direction': trade.trade_direction
            })
        
        return pd.DataFrame(data)
    
    def print_crossing_summary(self, crossing_result: CrossingResult):
        """Print to Consol Crossing Analysis Summary"""
        print("=== CROSSING ANALYSIS SUMMARY ===")
        summary = crossing_result.crossing_summary

        print(f"Portfolio Analysis:")
        print(f"  Total portfolios processed: {summary['total_portfolios']}")

        print(f"\nOriginal Trade Data:")
        print(f"  Original trade count: {summary['original_trade_count']:,}")
        print(f"  Original volume: {summary['original_volume']:,.0f}")

        print(f"\nCrossing Results:")
        print(f"  Crossed trade count: {summary['crossed_trade_count']:,}")
        print(f"  Crossed volume: {summary['crossed_volume']:,.0f}")
        print(f"  Crossing rate: {summary['crossing_rate']:.1%}")
        print(f"  Volume reduction: {summary['volume_reduction']:,.0f}")

        print(f"\nRemaining Trades:")
        print(f"  Remaining trade count: {summary['remaining_trade_count']:,}")
        print(f"  Remaining volume: {summary['remaining_volume']:,.0f}")

        print(f"\nSecurity Analysis:")
        print(f"  Securities with crosses: {summary['securities_with_crosses']}")
        print(f"  Securities needing external liquidity: {summary['securities_needing_external_liquidity']}")




def setup_crossing_logger(name: str = "crossing_engine", 
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
        timestamp = datetime.now().strftime('%H%M%S')
        log_file = f'logs/crossing_engine_{today_date}_{timestamp}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def example_usage():
    """Example of how to use the crossing engine."""
    
    # Setup configuration
    priority_list = ["S17147", "P36182", "P47227", "P93050", "P-61230"]
    config = CrossingEngineConfig(portfolio_priority=priority_list)
    
    # Initialize crossing engine
    crossing_engine = PortfolioCrossingEngine(config)
    
    # Example input (would come from optimization results)
    # portfolio_trades = {
    #     "S17147": proposed_trades_df_1,
    #     "P93050": proposed_trades_df_2,
    #     # ... other portfolios
    # }
    
    # Execute crossing
    # result = crossing_engine.execute_crossing(portfolio_trades)
    
    # Analyze results
    # print(f"Crossing Summary: {result.crossing_summary}")
    # print(f"Crossed Trades: {len(result.crossed_trades)}")
    # print(f"External Liquidity Needed: {len(result.external_liquidity_flags)}")
    
    # Export to DataFrames for further analysis
    # crossed_df = crossing_engine.export_crossed_trades_to_dataframe(result.crossed_trades)
    # remaining_df = crossing_engine.export_remaining_trades_to_dataframe(result.remaining_trades)
    
    pass

if __name__ == "__main__":
    example_usage()