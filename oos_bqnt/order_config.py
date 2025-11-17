"""
Configuration for DataFrame column mapping.

Defines expected column names for crossed and remaining trade DataFrames.
"""

from dataclasses import dataclass


@dataclass
class CrossedTradesConfig:
    """
    Column mapping for crossed trades DataFrame.
    
    Expected DataFrame structure:
    - One row per crossed trade
    - Creates 2 orders (BUY + SELL) per row
    """
    security_column: str = "security"
    quantity_column: str = "quantity_crossed"
    buyer_column: str = "buyer_portfolio"
    seller_column: str = "seller_portfolio"
    cross_id_column: str = "cross_id"


@dataclass
class RemainingTradesConfig:
    """
    Column mapping for remaining trades DataFrame.
    
    Expected DataFrame structure:
    - One row per remaining trade
    - Creates 1 order per row
    """
    security_column: str = "security"
    quantity_column: str = "remaining_quantity"
    portfolio_column: str = "portfolio_id"
    side_column: str = "trade_direction"
    instructions_column: str = None  # Optional: for future use