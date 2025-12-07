"""
Validation for order DataFrames.

Validates DataFrame structure and data before converting to orders.
Strict validation - fails fast with clear error messages.
"""

import pandas as pd
import re
from typing import List, Tuple

from .order_config import CrossedTradesConfig, RemainingTradesConfig


class ValidationError(Exception):
    """Raised when DataFrame validation fails"""
    pass


def validate_security_id(security: str, row_idx: int = None) -> Tuple[bool, str]:
    """
    Validate security ID format: TICKER EXCH_CODE EQUITY
    
    Examples:
        AAPL US Equity
        CAT US Equity
        TSLA UN Equity
        VOD LN Equity
    
    Args:
        security: Security identifier to validate
        row_idx: Optional row index for error messages
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not security or not isinstance(security, str):
        row_msg = f"Row {row_idx}: " if row_idx is not None else ""
        return False, f"{row_msg}Security ID is empty or not a string"
    
    security = security.strip()
    
    # Must end with " Equity"
    if not security.endswith(" Equity"):
        row_msg = f"Row {row_idx}: " if row_idx is not None else ""
        return False, f"{row_msg}Security ID must end with ' Equity', got: {security}"
    
    # Split into parts
    parts = security.split()
    
    # Must have at least 3 parts: TICKER EXCH_CODE Equity
    if len(parts) < 3:
        row_msg = f"Row {row_idx}: " if row_idx is not None else ""
        return False, f"{row_msg}Security ID must have format 'TICKER EXCH_CODE Equity', got: {security}"
    
    ticker = parts[0]
    exch_code = parts[1]
    
    # Ticker should be alphanumeric with optional slash for share classes
    if not re.match(r'^[A-Z0-9/]+$', ticker):
        row_msg = f"Row {row_idx}: " if row_idx is not None else ""
        return False, f"{row_msg}Ticker must be alphanumeric (with optional /), got: {ticker}"
    
    # Exchange code should be 2-3 uppercase letters
    if not re.match(r'^[A-Z]{2,3}$', exch_code):
        row_msg = f"Row {row_idx}: " if row_idx is not None else ""
        return False, f"{row_msg}Exchange code must be 2-3 uppercase letters, got: {exch_code}"
    
    return True, ""


def validate_crossed_df(df: pd.DataFrame, config: CrossedTradesConfig) -> None:
    """
    Validate crossed trades DataFrame.
    
    Checks:
    - Required columns present
    - No empty DataFrames
    - Valid security IDs
    - Quantities > 0
    - Buyer != Seller
    - Cross IDs not empty
    
    Args:
        df: DataFrame to validate
        config: Column mapping configuration
        
    Raises:
        ValidationError: If validation fails
    """
    if df is None:
        return  # Empty DataFrame is ok
    
    if df.empty:
        return  # Empty DataFrame is ok
    
    # Check required columns exist
    required_columns = [
        config.security_column,
        config.quantity_column,
        config.buyer_column,
        config.seller_column,
        config.cross_id_column,
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValidationError(
            f"crossed_df is missing required columns: {missing_columns}. "
            f"Available columns: {list(df.columns)}"
        )
    
    # Validate each row
    errors = []
    
    for idx, row in df.iterrows():
        row_num = idx + 1  # 1-indexed for user display
        
        # Validate security ID
        security = row[config.security_column]
        is_valid, error_msg = validate_security_id(security, row_num)
        if not is_valid:
            errors.append(error_msg)
        
        # Validate quantity
        try:
            quantity = float(row[config.quantity_column])
            if abs(quantity) <= 0:
                errors.append(f"Row {row_num}: quantity_crossed must be non-zero, got: {quantity}")
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: quantity_crossed must be numeric, got: {row[config.quantity_column]}")
        
        # Validate buyer portfolio
        buyer = row[config.buyer_column]
        if not buyer or pd.isna(buyer) or str(buyer).strip() == "":
            errors.append(f"Row {row_num}: buyer_portfolio cannot be empty")
        
        # Validate seller portfolio
        seller = row[config.seller_column]
        if not seller or pd.isna(seller) or str(seller).strip() == "":
            errors.append(f"Row {row_num}: seller_portfolio cannot be empty")
        
        # Validate buyer != seller
        if buyer and seller and str(buyer).strip() == str(seller).strip():
            errors.append(
                f"Row {row_num}: buyer_portfolio and seller_portfolio cannot be the same "
                f"(both are '{buyer}')"
            )
        
        # Validate cross_id
        cross_id = row[config.cross_id_column]
        if not cross_id or pd.isna(cross_id) or str(cross_id).strip() == "":
            errors.append(f"Row {row_num}: cross_id cannot be empty")
    
    if errors:
        error_summary = f"Validation failed for crossed_df with {len(errors)} error(s):\n"
        error_summary += "\n".join(f"  - {err}" for err in errors)
        raise ValidationError(error_summary)


def validate_remaining_df(df: pd.DataFrame, config: RemainingTradesConfig) -> None:
    """
    Validate remaining trades DataFrame.
    
    Checks:
    - Required columns present
    - No empty DataFrames
    - Valid security IDs
    - Quantities > 0
    - Valid sides (BUY/SELL)
    - Portfolio IDs not empty
    
    Args:
        df: DataFrame to validate
        config: Column mapping configuration
        
    Raises:
        ValidationError: If validation fails
    """
    if df is None:
        return  # Empty DataFrame is ok
    
    if df.empty:
        return  # Empty DataFrame is ok
    
    # Check required columns exist
    required_columns = [
        config.security_column,
        config.quantity_column,
        config.portfolio_column,
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValidationError(
            f"remaining_df is missing required columns: {missing_columns}. "
            f"Available columns: {list(df.columns)}"
        )
    
    # Validate each row
    errors = []
    
    for idx, row in df.iterrows():
        row_num = idx + 1  # 1-indexed for user display
        
        # Validate security ID
        security = row[config.security_column]
        is_valid, error_msg = validate_security_id(security, row_num)
        if not is_valid:
            errors.append(error_msg)
        
        # Validate quantity
        try:
            quantity = float(row[config.quantity_column])
            if abs(quantity) <= 0:
                errors.append(f"Row {row_num}: remaining_quantity must be non-zero, got: {quantity}")
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: remaining_quantity must be numeric, got: {row[config.quantity_column]}")
        
        # Validate portfolio
        portfolio = row[config.portfolio_column]
        if not portfolio or pd.isna(portfolio) or str(portfolio).strip() == "":
            errors.append(f"Row {row_num}: portfolio_id cannot be empty")
        
        # Validate side column if present
        if config.side_column and config.side_column in df.columns:
            side = row[config.side_column]
            if side and not pd.isna(side):
                side_str = str(side).strip().upper()
                valid_sides = ['BUY', 'SELL', 'B', 'S', '1', '2', 'LONG', 'SHORT']
                if side_str not in valid_sides:
                    errors.append(
                        f"Row {row_num}: trade_direction must be one of {valid_sides}, "
                        f"got: {side}"
                    )
    
    if errors:
        error_summary = f"Validation failed for remaining_df with {len(errors)} error(s):\n"
        error_summary += "\n".join(f"  - {err}" for err in errors)
        raise ValidationError(error_summary)