"""
Convert DataFrames to order dictionaries with basket separation.

Handles conversion of crossed and remaining trade DataFrames into
order dicts ready for XML building, with optional basket separation
and order aggregation.
"""

import datetime
import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict

from .enums import Side, OrderType, SecurityIdType, TimeInForce
from .order_types import SingleAllocation
from .order_config import CrossedTradesConfig, RemainingTradesConfig
from .order_validator import validate_crossed_df, validate_remaining_df, ValidationError

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
    Converts DataFrames to order dictionaries with optional basket separation.
    
    Features:
    - Optional separation into crosses and remaining baskets
    - Optional aggregation of remaining orders by security+side+price
    - Backward compatible: can return flat list like before
    
    Usage (backward compatible):
        converter = OrderConverter(crossed_config, remaining_config)
        orders = converter.convert(crossed_df, remaining_df)
        # Returns flat list like before
    
    Usage (basket separation):
        converter = OrderConverter(
            crossed_config, 
            remaining_config,
            separate_baskets=True
        )
        baskets = converter.convert(crossed_df, remaining_df)
        # Returns dict: {'crosses': {...}, 'remaining': {...}}
    
    Usage (with aggregation):
        converter = OrderConverter(
            crossed_config,
            remaining_config,
            separate_baskets=True,
            aggregate_remaining=True
        )
        baskets = converter.convert(crossed_df, remaining_df)
    """
    
    def __init__(
        self,
        crossed_config: CrossedTradesConfig,
        remaining_config: RemainingTradesConfig,
        separate_baskets: bool = False,
        aggregate_remaining: bool = False
    ):
        """
        Initialize converter with configurations.
        
        Args:
            crossed_config: Column mapping for crossed trades
            remaining_config: Column mapping for remaining trades
            separate_baskets: If True, return dict with separate baskets
            aggregate_remaining: If True, combine remaining orders by security+side+price
        """
        self.crossed_config = crossed_config
        self.remaining_config = remaining_config
        self.separate_baskets = separate_baskets
        self.aggregate_remaining = aggregate_remaining
    
    def convert(
        self,
        crossed_df: pd.DataFrame = None,
        remaining_df: pd.DataFrame = None
    ) -> List[dict] | Dict[str, Dict]:
        """
        Convert DataFrames to order dictionaries.
        
        Args:
            crossed_df: Optional DataFrame of crossed trades
            remaining_df: Optional DataFrame of remaining trades
            
        Returns:
            If separate_baskets=False: List[dict] of all orders (backward compatible)
            If separate_baskets=True: Dict with 'crosses' and/or 'remaining' keys
            
        Example (backward compatible):
            orders = converter.convert(crossed_df, remaining_df)
            # orders = [order1, order2, ...]
            
        Example (basket separation):
            baskets = converter.convert(crossed_df, remaining_df)
            # baskets = {
            #     'crosses': {'orders': [...], 'order_count': 10},
            #     'remaining': {'orders': [...], 'order_count': 15}
            # }
            
        Raises:
            ValidationError: If validation fails
        """
        # Count original rows
        crossed_rows = len(crossed_df) if crossed_df is not None and not crossed_df.empty else 0
        remaining_rows = len(remaining_df) if remaining_df is not None and not remaining_df.empty else 0
        
        logger.info(f"Starting conversion: {crossed_rows} crossed rows, {remaining_rows} remaining rows")
        if self.separate_baskets:
            logger.info(f"Mode: separate_baskets=True, aggregate_remaining={self.aggregate_remaining}")
        
        # Normalize security IDs BEFORE validation
        if crossed_df is not None and not crossed_df.empty:
            crossed_df = crossed_df.copy()
            crossed_df[self.crossed_config.security_column] = crossed_df[
                self.crossed_config.security_column
            ].apply(self._normalize_security_id)
            logger.debug(f"Normalized {crossed_rows} crossed trade security IDs")
        
        if remaining_df is not None and not remaining_df.empty:
            remaining_df = remaining_df.copy()
            remaining_df[self.remaining_config.security_column] = remaining_df[
                self.remaining_config.security_column
            ].apply(self._normalize_security_id)
            logger.debug(f"Normalized {remaining_rows} remaining trade security IDs")
        
        # Validate DataFrames
        logger.info("Validating DataFrames...")
        validate_crossed_df(crossed_df, self.crossed_config)
        validate_remaining_df(remaining_df, self.remaining_config)
        logger.info("Validation passed")
        
        # Convert to orders
        crossed_orders = []
        remaining_orders = []
        
        if crossed_df is not None and not crossed_df.empty:
            crossed_orders = self._convert_crossed_df(crossed_df)
            logger.debug(f"Converted {crossed_rows} crossed rows to {len(crossed_orders)} orders")
        
        if remaining_df is not None and not remaining_df.empty:
            if self.aggregate_remaining:
                remaining_orders = self._convert_remaining_df_aggregated(remaining_df)
                logger.debug(f"Converted {remaining_rows} remaining rows to {len(remaining_orders)} aggregated orders")
            else:
                remaining_orders = self._convert_remaining_df(remaining_df)
                logger.debug(f"Converted {remaining_rows} remaining rows to {len(remaining_orders)} orders")
        
        # Return based on mode
        if self.separate_baskets:
            # New mode: return dictionary
            result = {}
            
            if crossed_orders:
                result['crosses'] = {
                    'orders': crossed_orders,
                    'order_count': len(crossed_orders)
                }
            
            if remaining_orders:
                result['remaining'] = {
                    'orders': remaining_orders,
                    'order_count': len(remaining_orders)
                }
            
            logger.info(f"Built {len(result)} baskets: crosses={len(crossed_orders)}, remaining={len(remaining_orders)}")
            
            print(f"✓ Built {len(result)} basket(s):")
            if 'crosses' in result:
                print(f"  - CROSSES: {len(crossed_orders)} orders")
            if 'remaining' in result:
                print(f"  - REMAINING: {len(remaining_orders)} orders")
            
            return result
        else:
            # Backward compatible mode: return flat list
            all_orders = crossed_orders + remaining_orders
            total_orders = len(all_orders)
            
            logger.info(
                f"Built {total_orders} orders "
                f"(crossed rows: {crossed_rows} → {len(crossed_orders)} orders, "
                f"remaining rows: {remaining_rows} → {len(remaining_orders)} orders)"
            )
            
            print(
                f"Built {total_orders} orders "
                f"(crossed rows: {crossed_rows} → {len(crossed_orders)} orders, "
                f"remaining rows: {remaining_rows} → {len(remaining_orders)} orders)"
            )
            
            return all_orders
    
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
            
            # Extract optional price
            price = None
            order_type = OrderType.MARKET
            if self.crossed_config.price_column and self.crossed_config.price_column in df.columns:
                price_val = row[self.crossed_config.price_column]
                if pd.notna(price_val) and price_val != '':
                    price = float(price_val)
                    order_type = OrderType.LIMIT
            
            # Extract optional currency
            currency = 'USD'
            if self.crossed_config.currency_column and self.crossed_config.currency_column in df.columns:
                currency_val = row[self.crossed_config.currency_column]
                if pd.notna(currency_val) and currency_val != '':
                    currency = str(currency_val).strip().upper()
            
            # Extract optional time in force
            time_in_force = TimeInForce.DAY
            if self.crossed_config.time_in_force_column and self.crossed_config.time_in_force_column in df.columns:
                tif_val = row[self.crossed_config.time_in_force_column]
                if pd.notna(tif_val) and tif_val != '':
                    tif_str = str(tif_val).strip().upper()
                    tif_mapping = {
                        'DAY': TimeInForce.DAY,
                        'GTC': TimeInForce.GOOD_TILL_CANCEL,
                        'IOC': TimeInForce.IMMEDIATE_OR_CANCEL,
                        'FOK': TimeInForce.FILL_OR_KILL,
                    }
                    time_in_force = tif_mapping.get(tif_str, TimeInForce.DAY)
            
            # Extract optional settlement date
            settl_date = calculate_settlement_date()
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
            
            # Create instructions
            instructions = f"CROSS_ID:{cross_id}"
            long_notes = f"CROSS_ID:{cross_id} | BUYER:{buyer} | SELLER:{seller}"
            
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
                'long_notes': long_notes,
                'settl_date': settl_date,
                'security_exchange': security_exchange,
            }
            
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
                'long_notes': long_notes,
                'settl_date': settl_date,
                'security_exchange': security_exchange,
            }
            
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
            quantity_raw = float(row[self.remaining_config.quantity_column])
            quantity = abs(quantity_raw)
            portfolio = str(row[self.remaining_config.portfolio_column]).strip()
            
            # Determine side
            side = self._determine_side(row, quantity_raw)
            
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
            
            # Extract optional settlement date
            settl_date = calculate_settlement_date()
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
                instructions_val = row[self.remaining_config.instructions_column]
                if pd.notna(instructions_val) and instructions_val != '':
                    instructions = str(instructions_val).strip()

            long_notes = None
            
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
                'settl_date': settl_date,
            }
            
            # Add optional fields
            if price is not None:
                order['limit_price'] = price
            if broker is not None:
                order['broker'] = broker
            if security_exchange:
                order['security_exchange'] = security_exchange
            if instructions:
                order['instructions'] = instructions
            if instructions:
                order['long_notes'] = long_notes
            
            orders.append(order)
        
        return orders
    
    def _convert_remaining_df_aggregated(self, df: pd.DataFrame) -> List[dict]:
        """
        Convert remaining trades DataFrame to aggregated orders.
        Groups by (security, side, order_type, price) and combines allocations.
        
        Args:
            df: Remaining trades DataFrame
            
        Returns:
            List of aggregated order dictionaries
        """
        
        # Determine side for each row first and CONVERT TO STRING
        df = df.copy()
        df['_side'] = df.apply(
            lambda row: self._determine_side(row, float(row[self.remaining_config.quantity_column])).value,  # ← Add .value
            axis=1
        )
        
        # Group by key attributes
        group_cols = [
            self.remaining_config.security_column,
            '_side'  # Now it's a string ('BUY' or 'SELL')
        ]
        
        # Add optional columns to grouping if they exist
        if self.remaining_config.price_column and self.remaining_config.price_column in df.columns:
            group_cols.append(self.remaining_config.price_column)
        if self.remaining_config.currency_column and self.remaining_config.currency_column in df.columns:
            group_cols.append(self.remaining_config.currency_column)
        if self.remaining_config.time_in_force_column and self.remaining_config.time_in_force_column in df.columns:
            group_cols.append(self.remaining_config.time_in_force_column)
        if self.remaining_config.settl_date_column and self.remaining_config.settl_date_column in df.columns:
            group_cols.append(self.remaining_config.settl_date_column)
        if self.remaining_config.exchange_column and self.remaining_config.exchange_column in df.columns:
            group_cols.append(self.remaining_config.exchange_column)
        
        # Group and aggregate
        grouped = df.groupby(group_cols, dropna=False)
        
        orders = []
        for group_key, group_df in grouped:
            # Use first row as template
            template_row = group_df.iloc[0]
            
            # Extract base attributes
            security = template_row[self.remaining_config.security_column]
            
            side_value = template_row['_side']  # This is 1 or 2
            side = Side(side_value)  # Convert to Side.BUY or Side.SELL
            
            # Determine order type
            price = None
            order_type = OrderType.MARKET
            if self.remaining_config.price_column and self.remaining_config.price_column in df.columns:
                price_val = template_row[self.remaining_config.price_column]
                if pd.notna(price_val) and price_val != '':
                    price = float(price_val)
                    order_type = OrderType.LIMIT
            
            # Extract optional attributes from template
            currency = 'USD'
            if self.remaining_config.currency_column and self.remaining_config.currency_column in df.columns:
                currency_val = template_row[self.remaining_config.currency_column]
                if pd.notna(currency_val) and currency_val != '':
                    currency = str(currency_val).strip().upper()
            
            time_in_force = TimeInForce.DAY
            if self.remaining_config.time_in_force_column and self.remaining_config.time_in_force_column in df.columns:
                tif_val = template_row[self.remaining_config.time_in_force_column]
                if pd.notna(tif_val) and tif_val != '':
                    tif_str = str(tif_val).strip().upper()
                    tif_mapping = {
                        'DAY': TimeInForce.DAY,
                        'GTC': TimeInForce.GOOD_TILL_CANCEL,
                        'IOC': TimeInForce.IMMEDIATE_OR_CANCEL,
                        'FOK': TimeInForce.FILL_OR_KILL,
                    }
                    time_in_force = tif_mapping.get(tif_str, TimeInForce.DAY)
            
            settl_date = calculate_settlement_date()
            if self.remaining_config.settl_date_column and self.remaining_config.settl_date_column in df.columns:
                settl_val = template_row[self.remaining_config.settl_date_column]
                if pd.notna(settl_val) and settl_val != '':
                    settl_date = calculate_settlement_date(settl_val)
            
            security_exchange = None
            if self.remaining_config.exchange_column and self.remaining_config.exchange_column in df.columns:
                exchange_val = template_row[self.remaining_config.exchange_column]
                if pd.notna(exchange_val) and exchange_val != '':
                    security_exchange = str(exchange_val).strip()
            
            # Collect allocations from all rows in group
            allocations = []
            total_quantity = 0
            
            for _, row in group_df.iterrows():
                portfolio = str(row[self.remaining_config.portfolio_column]).strip()
                quantity = abs(float(row[self.remaining_config.quantity_column]))
                
                allocations.append(SingleAllocation(
                    Account=portfolio,
                    Quantity=int(quantity)
                ))
                total_quantity += int(quantity)
            
            # Build order
            order = {
                'security_id': security,
                'security_id_type': SecurityIdType.BLOOMBERG_SYMBOL,
                'side': side,
                'order_type': order_type,
                'quantity': total_quantity,
                'settl_currency': currency,
                'time_in_force': time_in_force,
                'allocation_instruction': allocations,
                'crossed': False,
                'settl_date': settl_date,
            }
            
            if price is not None:
                order['limit_price'] = price
            if security_exchange:
                order['security_exchange'] = security_exchange
            
            orders.append(order)
            
            logger.debug(
                f"Aggregated {len(group_df)} orders for {security} "
                f"{side.value}: {len(allocations)} allocations, total qty={total_quantity}"
            )
        
        return orders
    
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