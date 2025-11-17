"""
Order Submission Validator

Validates order dictionaries before XML submission to Bloomberg AIM.
This is the final validation step before sending to Bloomberg.
"""

import logging
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class OrderSubmissionError(Exception):
    """Raised when order submission validation fails"""
    pass


class OrderSubmissionValidator:
    """Validates orders before submission to Bloomberg"""
    
    @staticmethod
    def validate_orders(orders: List[Dict]) -> tuple[bool, List[str]]:
        """
        Validate list of orders before submission.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Run all validation checks
        errors.extend(OrderSubmissionValidator._validate_required_fields(orders))
        errors.extend(OrderSubmissionValidator._validate_quantities(orders))
        errors.extend(OrderSubmissionValidator._validate_allocations(orders))
        errors.extend(OrderSubmissionValidator._validate_crossed_orders(orders))
        errors.extend(OrderSubmissionValidator._validate_limit_orders(orders))
        errors.extend(OrderSubmissionValidator._validate_currencies(orders))
        errors.extend(OrderSubmissionValidator._validate_settlement_dates(orders))
        errors.extend(OrderSubmissionValidator._validate_duplicates(orders))
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def _validate_required_fields(orders: List[Dict]) -> List[str]:
        """Check all orders have required fields"""
        errors = []
        required = ['security_id', 'side', 'order_type', 'quantity', 'settl_currency', 'allocation_instruction']
        
        for idx, order in enumerate(orders):
            for field in required:
                if field not in order:
                    errors.append(f"Order {idx}: Missing required field '{field}'")
                elif order[field] is None or order[field] == '':
                    errors.append(f"Order {idx}: Field '{field}' is empty")
        
        return errors
    
    @staticmethod
    def _validate_quantities(orders: List[Dict]) -> List[str]:
        """Check quantities are positive"""
        errors = []
        
        for idx, order in enumerate(orders):
            qty = order.get('quantity', 0)
            if qty <= 0:
                errors.append(f"Order {idx}: Quantity must be positive (got {qty})")
        
        return errors
    
    @staticmethod
    def _validate_allocations(orders: List[Dict]) -> List[str]:
        """Check allocation quantities match order quantity"""
        errors = []
        
        for idx, order in enumerate(orders):
            order_qty = order.get('quantity', 0)
            allocations = order.get('allocation_instruction', [])
            
            if not allocations:
                errors.append(f"Order {idx}: No allocations specified")
                continue
            
            total_alloc = sum(getattr(a, 'Quantity', 0) for a in allocations)
            
            if total_alloc != order_qty:
                errors.append(
                    f"Order {idx}: Allocation total ({total_alloc}) "
                    f"does not match order quantity ({order_qty})"
                )
        
        return errors
    
    @staticmethod
    def _validate_crossed_orders(orders: List[Dict]) -> List[str]:
        """Validate crossed orders have matching quantities and prices"""
        errors = []
        
        # Group crossed orders by cross_id
        crossed_by_id = defaultdict(list)
        for idx, order in enumerate(orders):
            if order.get('crossed', False):
                instructions = order.get('instructions', '')
                # Extract cross_id from instructions
                if 'CROSS_ID:' in instructions:
                    cross_id = instructions.split('CROSS_ID:')[1].split('|')[0].strip()
                    crossed_by_id[cross_id].append((idx, order))
        
        # Validate each cross pair
        for cross_id, order_list in crossed_by_id.items():
            if len(order_list) != 2:
                errors.append(
                    f"Cross {cross_id}: Expected 2 orders (buy+sell), got {len(order_list)}"
                )
                continue
            
            idx1, order1 = order_list[0]
            idx2, order2 = order_list[1]
            
            # Check quantities match
            if order1['quantity'] != order2['quantity']:
                errors.append(
                    f"Cross {cross_id}: Quantity mismatch - "
                    f"Order {idx1} has {order1['quantity']}, "
                    f"Order {idx2} has {order2['quantity']}"
                )
            
            # Check currencies match
            if order1.get('settl_currency') != order2.get('settl_currency'):
                errors.append(
                    f"Cross {cross_id}: Currency mismatch - "
                    f"{order1.get('settl_currency')} vs {order2.get('settl_currency')}"
                )
            
            # Check securities match
            if order1.get('security_id') != order2.get('security_id'):
                errors.append(
                    f"Cross {cross_id}: Security mismatch - "
                    f"{order1.get('security_id')} vs {order2.get('security_id')}"
                )
            
            # Check opposite sides
            side1 = order1.get('side').name if hasattr(order1.get('side'), 'name') else str(order1.get('side'))
            side2 = order2.get('side').name if hasattr(order2.get('side'), 'name') else str(order2.get('side'))
            if side1 == side2:
                errors.append(
                    f"Cross {cross_id}: Both orders have same side ({side1}). "
                    f"Crossed orders must have one BUY and one SELL."
                )
            
            # If LIMIT orders, check prices match
            order_type1 = order1.get('order_type')
            order_type2 = order2.get('order_type')
            if (hasattr(order_type1, 'name') and order_type1.name == 'LIMIT' and 
                hasattr(order_type2, 'name') and order_type2.name == 'LIMIT'):
                price1 = order1.get('limit_price')
                price2 = order2.get('limit_price')
                if price1 != price2:
                    errors.append(
                        f"Cross {cross_id}: Price mismatch - "
                        f"Order {idx1} price {price1}, Order {idx2} price {price2}"
                    )
        
        return errors
    
    @staticmethod
    def _validate_limit_orders(orders: List[Dict]) -> List[str]:
        """Check LIMIT orders have prices"""
        errors = []
        
        for idx, order in enumerate(orders):
            order_type = order.get('order_type')
            if order_type and hasattr(order_type, 'name'):
                if order_type.name in ('LIMIT', 'STOP_LIMIT'):
                    if 'limit_price' not in order or order['limit_price'] is None:
                        errors.append(
                            f"Order {idx} ({order.get('security_id')}): "
                            f"{order_type.name} order requires limit_price"
                        )
                    elif order['limit_price'] <= 0:
                        errors.append(
                            f"Order {idx} ({order.get('security_id')}): "
                            f"limit_price must be positive (got {order['limit_price']})"
                        )
                
                if order_type.name in ('STOP', 'STOP_LIMIT'):
                    if 'stop_price' not in order or order['stop_price'] is None:
                        errors.append(
                            f"Order {idx} ({order.get('security_id')}): "
                            f"{order_type.name} order requires stop_price"
                        )
        
        return errors
    
    @staticmethod
    def _validate_currencies(orders: List[Dict]) -> List[str]:
        """Check currency codes are valid 3-letter ISO codes"""
        errors = []
        
        for idx, order in enumerate(orders):
            currency = order.get('settl_currency', '')
            if not currency or len(currency) != 3 or not currency.isalpha():
                errors.append(
                    f"Order {idx} ({order.get('security_id')}): "
                    f"Invalid currency code '{currency}' (must be 3-letter ISO code)"
                )
        
        return errors

    @staticmethod
    def _validate_settlement_dates(orders: List[Dict]) -> List[str]:
        """Check settlement dates are valid format if provided"""
        errors = []
        
        for idx, order in enumerate(orders):
            settl_date = order.get('settl_date')
            if settl_date:
                # Should be 8-digit string in YYYYMMDD format
                if not isinstance(settl_date, str) or not settl_date.isdigit() or len(settl_date) != 8:
                    errors.append(
                        f"Order {idx} ({order.get('security_id')}): "
                        f"Invalid settlement date format '{settl_date}' (must be YYYYMMDD)"
                    )
                else:
                    # Try to parse as valid date
                    try:
                        import datetime
                        year = int(settl_date[0:4])
                        month = int(settl_date[4:6])
                        day = int(settl_date[6:8])
                        datetime.date(year, month, day)
                    except ValueError:
                        errors.append(
                            f"Order {idx} ({order.get('security_id')}): "
                            f"Invalid settlement date '{settl_date}' (not a valid calendar date)"
                        )
        
        return errors
    
    @staticmethod
    def _validate_duplicates(orders: List[Dict]) -> List[str]:
        """Check for duplicate ClOrdIDs if specified"""
        errors = []
        clordids = []
        
        for idx, order in enumerate(orders):
            clordid = order.get('clord_id')
            if clordid:
                if clordid in clordids:
                    errors.append(
                        f"Order {idx} ({order.get('security_id')}): "
                        f"Duplicate ClOrdID '{clordid}'"
                    )
                clordids.append(clordid)
        
        return errors
    
    @staticmethod
    def get_order_summary(orders: List[Dict]) -> str:
        """
        Generate human-readable summary of orders.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            Formatted summary string
        """
        if not orders:
            return "No orders to submit"
        
        # Count by type
        crossed_orders = [o for o in orders if o.get('crossed', False)]
        external_orders = [o for o in orders if not o.get('crossed', False)]
        
        # Count by side
        buy_orders = []
        sell_orders = []
        for o in orders:
            side = o.get('side')
            side_name = side.name if hasattr(side, 'name') else str(side)
            if side_name == 'BUY':
                buy_orders.append(o)
            else:
                sell_orders.append(o)
        
        # Count by order type
        market_orders = []
        limit_orders = []
        for o in orders:
            order_type = o.get('order_type')
            type_name = order_type.name if hasattr(order_type, 'name') else str(order_type)
            if type_name == 'MARKET':
                market_orders.append(o)
            elif type_name == 'LIMIT':
                limit_orders.append(o)
        
        # Get unique securities
        securities = set(o.get('security_id') for o in orders)
        
        # Get currencies
        currencies = set(o.get('settl_currency') for o in orders)
        
        # Calculate totals
        total_buy_qty = sum(o['quantity'] for o in buy_orders)
        total_sell_qty = sum(o['quantity'] for o in sell_orders)
        
        # Count crosses
        cross_ids = set()
        for o in crossed_orders:
            instructions = o.get('instructions', '')
            if 'CROSS_ID:' in instructions:
                cross_id = instructions.split('CROSS_ID:')[1].split('|')[0].strip()
                cross_ids.add(cross_id)
        
        summary = f"""
========================================
ORDER SUBMISSION SUMMARY
========================================
Total Orders: {len(orders)}
  - Crossed Orders: {len(crossed_orders)} ({len(cross_ids)} unique crosses)
  - External Orders: {len(external_orders)}

By Side:
  - BUY:  {len(buy_orders)} orders ({total_buy_qty:,} shares)
  - SELL: {len(sell_orders)} orders ({total_sell_qty:,} shares)

By Order Type:
  - MARKET: {len(market_orders)}
  - LIMIT:  {len(limit_orders)}

Securities: {len(securities)} unique
Currencies: {', '.join(sorted(currencies))}
========================================
"""
        return summary