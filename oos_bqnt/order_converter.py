"""
Convert DataFrames to order dictionaries.

Handles conversion of crossed and remaining trade DataFrames into
order dicts ready for XML building.
"""

import datetime
import pandas as pd
from typing import List, Dict

from enums import Side, OrderType, SecurityIdType, TimeInForce
from order_types import SingleAllocation
from order_config import CrossedTradesConfig, RemainingTradesConfig
from order_validator import validate_crossed_df, validate_remaining_df, ValidationError

import logging

logger = logging.getLogger(__name__)




def calculate_settlement_date(settl_date_value=None, default_days: int = 2) -> str:
    """
    Calculate settlement date in YYYYMMDD format.
    
    Args:
        settl_date_value: Either None (use default), specific date (YYYYMMDD), or +N for T+N
        default_days: Default number of days to add (default is 2 for T+2)
        
    Returns:
        Settlement date string in YYYYMMDD format
        
    Examples:
        calculate_settlement_date(None) -> T+2 date
        calculate_settlement_date("20250120") -> "20250120"
        calculate_settlement_date("T+1") -> T+1 date
        calculate_settlement_date("+3") -> T+3 date
    """
    # If specific date provided in YYYYMMDD format
    if settl_date_value and isinstance(settl_date_value, str):
        settl_str = str(settl_date_value).strip()
        
        # Check if it's YYYYMMDD format (8 digits)
        if settl_str.isdigit() and len(settl_str) == 8:
            return settl_str
        
        # Check if it's T+N or +N format
        if settl_str.upper().startswith('T+') or settl_str.startswith('+'):
            days_str = settl_str.upper().replace('T+', '').replace('+', '')
            try:
                days = int(days_str)
            except ValueError:
                days = default_days
        else:
            days = default_days
    else:
        days = default_days
    
    # Calculate date
    today = datetime.date.today()
    settlement_date = today + datetime.timedelta(days=days)
    return settlement_date.strftime("%Y%m%d")


class OrderConverter:
    """
    Converts DataFrames to order dictionaries.
    
    Usage:
        config_crossed = CrossedTradesConfig()
        config_remaining = RemainingTradesConfig()
        converter = OrderConverter(config_crossed, config_remaining)
        orders = converter.convert(crossed_df, remaining_df)
    """
    
    def __init__(
        self,
        crossed_config: CrossedTradesConfig,
        remaining_config: RemainingTradesConfig
    ):
        """
        Initialize converter with column configurations.
        
        Args:
            crossed_config: Column mapping for crossed trades
            remaining_config: Column mapping for remaining trades
        """
        self.crossed_config = crossed_config
        self.remaining_config = remaining_config
    
    def convert(
        self,
        crossed_df: pd.DataFrame = None,
        remaining_df: pd.DataFrame = None
    ) -> List[dict]:
        """
        Convert DataFrames to list of order dictionaries.
        
        Args:
            crossed_df: Optional DataFrame of crossed trades
            remaining_df: Optional DataFrame of remaining trades
            
        Returns:
            List of order dictionaries ready for XML builder
            
        Raises:
            ValidationError: If validation fails
        """
        orders = []
        
        # Count original rows
        crossed_rows = len(crossed_df) if crossed_df is not None and not crossed_df.empty else 0
        remaining_rows = len(remaining_df) if remaining_df is not None and not remaining_df.empty else 0
        
        logger.info(f"Starting conversion: {crossed_rows} crossed rows, {remaining_rows} remaining rows")
        
        # Normalize security IDs BEFORE validation
        if crossed_df is not None and not crossed_df.empty:
            crossed_df = crossed_df.copy()  # Don't modify original
            crossed_df[self.crossed_config.security_column] = crossed_df[
                self.crossed_config.security_column
            ].apply(self._normalize_security_id)
            logger.debug(f"Normalized {crossed_rows} crossed trade security IDs")
        
        if remaining_df is not None and not remaining_df.empty:
            remaining_df = remaining_df.copy()  # Don't modify original
            remaining_df[self.remaining_config.security_column] = remaining_df[
                self.remaining_config.security_column
            ].apply(self._normalize_security_id)
            logger.debug(f"Normalized {remaining_rows} remaining trade security IDs")
        
        # NOW validate DataFrames (after normalization)
        logger.info("Validating DataFrames...")
        validate_crossed_df(crossed_df, self.crossed_config)
        validate_remaining_df(remaining_df, self.remaining_config)
        logger.info("Validation passed")
        
        # Convert crossed trades
        crossed_orders_count = 0
        if crossed_df is not None and not crossed_df.empty:
            crossed_orders = self._convert_crossed_df(crossed_df)
            crossed_orders_count = len(crossed_orders)
            orders.extend(crossed_orders)
            logger.debug(f"Converted {crossed_rows} crossed rows to {crossed_orders_count} orders")
        
        # Convert remaining trades
        remaining_orders_count = 0
        if remaining_df is not None and not remaining_df.empty:
            remaining_orders = self._convert_remaining_df(remaining_df)
            remaining_orders_count = len(remaining_orders)
            orders.extend(remaining_orders)
            logger.debug(f"Converted {remaining_rows} remaining rows to {remaining_orders_count} orders")
        
        # Summary log
        total_orders = len(orders)
        logger.info(
            f"Built {total_orders} orders "
            f"(crossed rows: {crossed_rows} → {crossed_orders_count} orders, "
            f"remaining rows: {remaining_rows} → {remaining_orders_count} orders)"
        )
        
        # Also print to console for visibility
        print(
            f"Built {total_orders} orders "
            f"(crossed rows: {crossed_rows} → {crossed_orders_count} orders, "
            f"remaining rows: {remaining_rows} → {remaining_orders_count} orders)"
        )
        
        return orders

    
    def _convert_crossed_df(self, df: pd.DataFrame) -> List[dict]:
        """
        Convert crossed trades DataFrame to orders.
        
        Each row creates 2 orders: BUY + SELL
        
        Args:
            df: Crossed trades DataFrame
            
        Returns:
            List of order dictionaries
        """
        orders = []
        
        for _, row in df.iterrows():
            # Extract data
            security = row[self.crossed_config.security_column]
            quantity = abs(float(row[self.crossed_config.quantity_column]))
            buyer = str(row[self.crossed_config.buyer_column]).strip()
            seller = str(row[self.crossed_config.seller_column]).strip()
            cross_id = str(row[self.crossed_config.cross_id_column]).strip()
            
            # Extract optional price (if column exists, use LIMIT order)
            price = None
            order_type = OrderType.MARKET
            if self.crossed_config.price_column and self.crossed_config.price_column in df.columns:
                price_val = row[self.crossed_config.price_column]
                if pd.notna(price_val) and price_val != '':
                    price = float(price_val)
                    order_type = OrderType.LIMIT
            
            # Extract optional currency (default to USD)
            currency = 'USD'
            if self.crossed_config.currency_column and self.crossed_config.currency_column in df.columns:
                currency_val = row[self.crossed_config.currency_column]
                if pd.notna(currency_val) and currency_val != '':
                    currency = str(currency_val).strip().upper()
            
            # Extract optional time in force (default to DAY)
            time_in_force = TimeInForce.DAY
            if self.crossed_config.time_in_force_column and self.crossed_config.time_in_force_column in df.columns:
                tif_val = row[self.crossed_config.time_in_force_column]
                if pd.notna(tif_val) and tif_val != '':
                    tif_str = str(tif_val).strip().upper()
                    # Map common values to enum
                    tif_mapping = {
                        'DAY': TimeInForce.DAY,
                        'GTC': TimeInForce.GOOD_TILL_CANCEL,
                        'IOC': TimeInForce.IMMEDIATE_OR_CANCEL,
                        'FOK': TimeInForce.FILL_OR_KILL,
                    }
                    time_in_force = tif_mapping.get(tif_str, TimeInForce.DAY)

            # Extract optional settlement date (default T+2)
            settl_date = calculate_settlement_date()  # Default T+2
            if self.crossed_config.settl_date_column and self.crossed_config.settl_date_column in df.columns:
                settl_val = row[self.crossed_config.settl_date_column]
                if pd.notna(settl_val) and settl_val != '':
                    settl_date = calculate_settlement_date(settl_val)

            # Extract optional security exchange
            security_exchange = None
            if self.crossed_config.exchange_column and self.crossed_config.exchange_column in df.columns:
                exchange_val = row[self.crossed_config.exchange_column]
                if pd.notna(exchange_val) and exchange_val != '':
                    security_exchange = str(exchange_val).strip()
            
            # Create instructions with cross_id and portfolio info
            instructions = f"CROSS_ID:{cross_id} | BUYER:{buyer} | SELLER:{seller}"
            
            # BUY order for buyer
            buy_order = {
                'security_id': security,
                'security_id_type': SecurityIdType.BLOOMBERG_SYMBOL,
                'side': Side.BUY,
                'order_type': order_type,
                'quantity': int(quantity),
                'settl_currency': currency,
                'time_in_force': time_in_force,
                'allocation_instruction': [SingleAllocation(Account=buyer, Quantity=int(quantity))],
                'crossed': True,
                'instructions': instructions,
                'settl_date': settl_date,
                'security_exchange': security_exchange,
            }
            
            # Add price if LIMIT order
            if price is not None:
                buy_order['limit_price'] = price
            orders.append(buy_order)
            
            # SELL order for seller
            sell_order = {
                'security_id': security,
                'security_id_type': SecurityIdType.BLOOMBERG_SYMBOL,
                'side': Side.SELL,
                'order_type': order_type,
                'quantity': int(quantity),
                'settl_currency': currency,
                'time_in_force': time_in_force,
                'allocation_instruction': [SingleAllocation(Account=seller, Quantity=int(quantity))],
                'crossed': True,
                'instructions': instructions,
                'settl_date': settl_date,
                'security_exchange': security_exchange,
            }
            
            # Add price if LIMIT order
            if price is not None:
                sell_order['limit_price'] = price
            orders.append(sell_order)
        
        return orders
    
    def _convert_remaining_df(self, df: pd.DataFrame) -> List[dict]:
        """
        Convert remaining trades DataFrame to orders.
        
        Each row creates 1 order.
        
        Args:
            df: Remaining trades DataFrame
            
        Returns:
            List of order dictionaries
        """
        orders = []
        
        for _, row in df.iterrows():
            # Extract data
            security = row[self.remaining_config.security_column]
            quantity = abs(float(row[self.remaining_config.quantity_column]))
            portfolio = str(row[self.remaining_config.portfolio_column]).strip()
            side_str = str(row[self.remaining_config.side_column]).strip().upper()
            
            # Convert side string to enum
            side = Side.BUY if side_str in ('BUY', 'B', '1') else Side.SELL
            
            # Extract optional broker
            broker = None
            if self.remaining_config.broker_column and self.remaining_config.broker_column in df.columns:
                broker_val = row[self.remaining_config.broker_column]
                if pd.notna(broker_val) and broker_val != '':
                    broker = str(broker_val).strip()
            
            # Extract optional price
            price = None
            order_type = OrderType.MARKET
            if self.remaining_config.price_column and self.remaining_config.price_column in df.columns:
                price_val = row[self.remaining_config.price_column]
                if pd.notna(price_val) and price_val != '':
                    price = float(price_val)
                    order_type = OrderType.LIMIT
            
            # Extract optional currency
            currency = 'USD'
            if self.remaining_config.currency_column and self.remaining_config.currency_column in df.columns:
                currency_val = row[self.remaining_config.currency_column]
                if pd.notna(currency_val) and currency_val != '':
                    currency = str(currency_val).strip().upper()
            
            # Extract optional time in force
            time_in_force = TimeInForce.DAY
            if self.remaining_config.time_in_force_column and self.remaining_config.time_in_force_column in df.columns:
                tif_val = row[self.remaining_config.time_in_force_column]
                if pd.notna(tif_val) and tif_val != '':
                    tif_str = str(tif_val).strip().upper()
                    tif_mapping = {
                        'DAY': TimeInForce.DAY,
                        'GTC': TimeInForce.GOOD_TILL_CANCEL,
                        'IOC': TimeInForce.IMMEDIATE_OR_CANCEL,
                        'FOK': TimeInForce.FILL_OR_KILL,
                    }
                    time_in_force = tif_mapping.get(tif_str, TimeInForce.DAY)

            # Extract optional settlement date (default T+2)
            settl_date = calculate_settlement_date()  # Default T+2
            if self.remaining_config.settl_date_column and self.remaining_config.settl_date_column in df.columns:
                settl_val = row[self.remaining_config.settl_date_column]
                if pd.notna(settl_val) and settl_val != '':
                    settl_date = calculate_settlement_date(settl_val)
            
            # Extract optional security exchange
            security_exchange = None
            if self.remaining_config.exchange_column and self.remaining_config.exchange_column in df.columns:
                exchange_val = row[self.remaining_config.exchange_column]
                if pd.notna(exchange_val) and exchange_val != '':
                    security_exchange = str(exchange_val).strip()
            
            # Get instructions if configured
            instructions = None
            if (self.remaining_config.instructions_column and 
                self.remaining_config.instructions_column in df.columns):
                instructions = str(row[self.remaining_config.instructions_column]).strip()

            # Extract broker if column exists
            broker = None
            if self.remaining_config.broker_column and self.remaining_config.broker_column in df.columns:
                broker = str(row[self.remaining_config.broker_column]).strip()
            
            # Create order
            order = {
                'security_id': security,
                'security_id_type': SecurityIdType.BLOOMBERG_SYMBOL,
                'side': side,
                'order_type': order_type,
                'quantity': int(quantity),
                'settl_currency': currency,
                'time_in_force': time_in_force,
                'allocation_instruction': [SingleAllocation(Account=portfolio, Quantity=int(quantity))],
                'crossed': False,
            }
            
            # Add price if LIMIT order
            if price is not None:
                order['limit_price'] = price
            
            # Add broker if specified
            if broker is not None:
                order['broker'] = broker

            # Add settlement date
            order['settl_date'] = settl_date
            
            # Add security exchange if provided
            if security_exchange:
                order['security_exchange'] = security_exchange
            
            # Add instructions if present
            if instructions:
                order['instructions'] = instructions
            
            orders.append(order)
        
        return orders
    
    def _normalize_security_id(self, security) -> str:
        """
        Normalize security ID format.
        
        Ensures format: TICKER EXCH_CODE Equity
        Adds ' Equity' suffix if missing.
        
        Args:
            security: Raw security identifier
            
        Returns:
            Normalized security identifier
        """
        if pd.isna(security):
            return ""
        
        security = str(security).strip()
        
        if not security:
            return ""
        
        # Add ' Equity' suffix if not present
        if not security.endswith(" Equity"):
            security = f"{security} Equity"
        
        return security
    
    def _determine_side(self, row: pd.Series, quantity_raw: float) -> Side:
        """
        Determine order side (BUY/SELL).
        
        Priority:
        1. Use side column if present
        2. Use quantity sign (negative = SELL, positive = BUY)
        
        Args:
            row: DataFrame row
            quantity_raw: Raw quantity value (may be negative)
            
        Returns:
            Side enum (BUY or SELL)
        """
        # Try side column first
        if (self.remaining_config.side_column and 
            self.remaining_config.side_column in row.index):
            side_value = row[self.remaining_config.side_column]
            
            if not pd.isna(side_value):
                side_str = str(side_value).strip().upper()
                
                # Map to Side enum
                if side_str in ['BUY', 'B', '1', 'LONG']:
                    return Side.BUY
                elif side_str in ['SELL', 'S', '2', 'SHORT']:
                    return Side.SELL
        
        # Fall back to quantity sign
        return Side.SELL if quantity_raw < 0 else Side.BUY


