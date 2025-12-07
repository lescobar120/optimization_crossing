"""
Submission Examples - Works with Your Existing Workflow

Shows how to use the enhanced OrderConverter while maintaining
full control over basket naming in the XML builder.
"""

import pandas as pd
import time
import xml.etree.ElementTree as ET
import uuid
import asyncio
import websockets
from pathlib import Path

from .order_converter import OrderConverter
from .order_config import CrossedTradesConfig, RemainingTradesConfig
from .xml_builder import BasketOrderXMLBuilder
from .order_submission_validator import OrderSubmissionValidator
from .enums import (
    FlowControlTag,
    ListProcessingLevel,
    CheckPretradeCompliance
)

DEMO_BASKETS_DIR = Path(__file__).resolve().parent
XML_REQUESTS_DIR = DEMO_BASKETS_DIR / "xml_requests"
XML_REQUESTS_DIR.mkdir(exist_ok=True)  # ensure it exists



def safe_basket_prefix(prefix, max_length=20):
    """
    Ensure basket name prefix is safe length.
    Final basket name will be: prefix + "_" + 9 char suffix
    """
    if len(prefix) <= max_length:
        return prefix
    
    truncated = prefix[:max_length]
    print(f"Truncated prefix: '{prefix}' → '{truncated}'")
    return truncated

# ============================================================================
# Backward Compatible
# ============================================================================

def example_backward_compatible(
    crosses_path="../crossed_trades_20251114_130344.csv", 
    remaining_path="../remaining_trades_20251114_130344.csv"
):
    """
    Your existing workflow - NO CHANGES REQUIRED
    """
    print("=" * 70)
    print("EXAMPLE 1: BACKWARD COMPATIBLE MODE")
    print("=" * 70)
    
    # Load data
    crossed_df = pd.read_csv(crosses_path)
    remaining_df = pd.read_csv(remaining_path)
    
    # Your existing code - works exactly the same!
    crossed_config = CrossedTradesConfig()
    remaining_config = RemainingTradesConfig()
    converter = OrderConverter(crossed_config, remaining_config)
    
    orders = converter.convert(crossed_df, remaining_df)
    
    # Validate
    is_valid, errors = OrderSubmissionValidator.validate_orders(orders)
    if not is_valid:
        print(f"Validation failed: {errors}")
        return
    
    # Your existing XML generation - NO CHANGES!
    xml_out = BasketOrderXMLBuilder.get_request_xml_string(
        custom_list_id=uuid.uuid1(),
        list_of_orders=orders,
        basket_name=None,
        basket_name_prefix="SETTLE_LE_BQuant_Demo",
        route_to_session="4571.DRAY.BQNT",
        check_pretrade_compliance=CheckPretradeCompliance.NO,
        flow_control_flag=FlowControlTag.ACTIVE_ORDER,
        list_processing_level=ListProcessingLevel.LIST,
        compliance_override_text="TestOverride",
    )
    
    # Save
    with open("xml_requests/basket_order_request.txt", "w", encoding="utf-8") as f:
        f.write(xml_out)
    
    print(f"Generated XML with {len(orders)} orders")
    print("Saved to xml_requests/basket_order_request.txt")


# ============================================================================
# Separate Baskets with custom Naming Control
# ============================================================================

def example_separate_baskets(
    crosses_path="../crossed_trades_20251114_130344.csv", 
    remaining_path="../remaining_trades_20251114_130344.csv",
    _limit=300
):
    """
    Enhanced workflow: Separate baskets, control of naming
    """
    print("=" * 70)
    print("EXAMPLE 2: SEPARATE BASKETS (YOU CONTROL NAMING)")
    print("=" * 70)
    
    # Load data
    crossed_df = pd.read_csv(crosses_path)
    remaining_df = pd.read_csv(remaining_path)
    
    # Configure
    crossed_config = CrossedTradesConfig()
    remaining_config = RemainingTradesConfig()
    
    # NEW: Enable basket separation
    converter = OrderConverter(
        crossed_config,
        remaining_config,
        separate_baskets=True
    )
    
    # Convert - returns dict instead of list
    baskets = converter.convert(crossed_df, remaining_df)
    
    # LIMIT TO FIRST X ORDERS PER BASKET FOR TESTING
    print(f"\n→ Limiting to first {_limit} orders per basket for testing...")
    for basket_type, basket_data in baskets.items():
        basket_data['orders'] = basket_data['orders'][:_limit]
        basket_data['order_count'] = len(basket_data['orders'])
        print(f"  {basket_type}: {basket_data['order_count']} orders")
    
    # Validate each basket
    # for basket_type, basket_data in baskets.items():
    #     is_valid, errors = OrderSubmissionValidator.validate_orders(basket_data['orders'])
    #     if not is_valid:
    #         print(f"{basket_type} validation failed: {errors}")
    #         return
    #     print(f"{basket_type}: {basket_data['order_count']} orders validated")
    
    # Generate XML for each basket - YOU CONTROL THE NAMING!
    for basket_type, basket_data in baskets.items():
        # YOU decide the naming convention
        if basket_type == 'crosses':
            prefix = "LE_CROSSES"
        else:
            prefix = "LE_REMAINING"
        
        # Your existing XML builder pattern
        xml = BasketOrderXMLBuilder.get_request_xml_string(
            custom_list_id=uuid.uuid1(),
            list_of_orders=basket_data['orders'],
            basket_name=None,
            #basket_name_prefix=prefix,  # ← YOU control this
            basket_name_prefix=safe_basket_prefix(prefix, max_length=20),
            route_to_session="4571.DRAY.BQNT",
            check_pretrade_compliance=CheckPretradeCompliance.NO,
            flow_control_flag=FlowControlTag.ACTIVE_ORDER,
            list_processing_level=ListProcessingLevel.LIST,
            compliance_override_text="TestOverride",
        )
        
        # Store XML
        basket_data['xml'] = xml
        
        # Save to file
        filename = XML_REQUESTS_DIR / f"basket_{basket_type}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml)

        
        print(f"{basket_type}: Saved to {filename}")
    
    print("\nCreated 2 baskets with YOUR naming convention")
    print("Ready to submit via WebSocket")
    
    return baskets


# ============================================================================
# Aggregation Mode (orders combined)
# ============================================================================

def example_aggregation(
    crosses_path="../crossed_trades_20251114_130344.csv", 
    remaining_path="../remaining_trades_20251114_130344.csv",
    _limit=300
):
    """
    Aggregation mode: Combine orders by security+side
    """
    print("=" * 70)
    print("AGGREGATION MODE")
    print("=" * 70)
    
    # Load data
    crossed_df = pd.read_csv(crosses_path)
    remaining_df = pd.read_csv(remaining_path)
    
    # Configure
    crossed_config = CrossedTradesConfig()
    remaining_config = RemainingTradesConfig()
    
    # Enable aggregation
    converter = OrderConverter(
        crossed_config,
        remaining_config,
        separate_baskets=True,
        aggregate_remaining=True  # Combine matching orders
    )
    
    baskets = converter.convert(crossed_df, remaining_df)

    # LIMIT TO FIRST X ORDERS PER BASKET FOR TESTING
    print("\nOrder counts with aggregation:")
    print(f"\n→ Limiting to first {_limit} orders per basket for testing...")
    for basket_type, basket_data in baskets.items():
        basket_data['orders'] = basket_data['orders'][:_limit]
        basket_data['order_count'] = len(basket_data['orders'])
        print(f"  {basket_type}: {basket_data['order_count']} orders")

    # Validate each basket
    # for basket_type, basket_data in baskets.items():
    #     is_valid, errors = OrderSubmissionValidator.validate_orders(basket_data['orders'])
    #     if not is_valid:
    #         print(f"{basket_type} validation failed: {errors}")
    #         return
    #     print(f"{basket_type}: {basket_data['order_count']} orders validated")
    
    # # Show aggregated orders
    # if 'remaining' in baskets:
    #     print("\nAggregated orders:")
    #     for order in baskets['remaining']['orders']:
    #         allocs = order.get('allocation_instruction', [])
    #         if len(allocs) > 1:
    #             print(f"  {order['security_id']} {order['side'].value}:")
    #             print(f"    Total: {order['quantity']}")
    #             print(f"    Accounts: {len(allocs)}")
    #             for alloc in allocs[:3]:
    #                 print(f"      - {alloc.Account}: {alloc.Quantity}")

    # Show aggregated orders (first 5 only)
    if 'remaining' in baskets:
        print("\nAggregated orders (showing first 5):")
        aggregated_orders = [
            order for order in baskets['remaining']['orders'] 
            if len(order.get('allocation_instruction', [])) > 1
        ]
        
        for order in aggregated_orders[:5]:  # ← Limit to first 5
            allocs = order.get('allocation_instruction', [])
            print(f"  {order['security_id']} {order['side'].value}:")
            print(f"    Total: {order['quantity']}")
            print(f"    Accounts: {len(allocs)}")
            for alloc in allocs[:3]:
                print(f"      - {alloc.Account}: {alloc.Quantity}")
        
        # Show count if there are more
        if len(aggregated_orders) > 5:
            print(f"\n  ... and {len(aggregated_orders) - 5} more aggregated orders")
    
    # Generate XML (same pattern as Example 2)
    for basket_type, basket_data in baskets.items():
        suffix = "_CROSSES" if basket_type == 'crosses' else "_REMAINING_AGG"
        
        xml = BasketOrderXMLBuilder.get_request_xml_string(
            custom_list_id=uuid.uuid1(),
            list_of_orders=basket_data['orders'],
            basket_name=None,
            # basket_name_prefix=f"LE{suffix}",
            basket_name_prefix = safe_basket_prefix(f"LE{suffix}", max_length=20),
            route_to_session="4571.DRAY.BQNT",
            check_pretrade_compliance=CheckPretradeCompliance.NO,
            flow_control_flag=FlowControlTag.ACTIVE_ORDER,
            list_processing_level=ListProcessingLevel.LIST,
            compliance_override_text="TestOverride",
        )
        
        basket_data['xml'] = xml

        # Save to file
        filename = XML_REQUESTS_DIR / f"basket_{basket_type}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml)

        
        print(f"{basket_type}: Saved to {filename}")
    
    print("\nGenerated XML with aggregated orders and separated baskets for crosses and remaining trades")
    print("Ready to submit via WebSocket")
    
    return baskets



def example_aggregation_sample(
    crosses_path="../crossed_trades_20251114_130344.csv", 
    remaining_path="../remaining_trades_20251114_130344.csv",
    limit_aggregated_orders=None
):
    """
    Aggregation mode: Combine orders by security+side
    
    Args:
        limit_aggregated_orders: If provided, limit remaining basket to first X aggregated orders only
    """
    print("=" * 70)
    print("AGGREGATION MODE")
    print("=" * 70)
    
    # Load data
    crossed_df = pd.read_csv(crosses_path)
    remaining_df = pd.read_csv(remaining_path)
    
    # Configure
    crossed_config = CrossedTradesConfig()
    remaining_config = RemainingTradesConfig()
    
    # Enable aggregation
    converter = OrderConverter(
        crossed_config,
        remaining_config,
        separate_baskets=True,
        aggregate_remaining=True  # Combine matching orders
    )
    
    baskets = converter.convert(crossed_df, remaining_df)
    
    # LIMIT AGGREGATED ORDERS IF REQUESTED
    if limit_aggregated_orders is not None and 'remaining' in baskets:
        original_count = baskets['remaining']['order_count']
        
        # Filter to only aggregated orders (those with multiple allocations)
        aggregated_orders = [
            order for order in baskets['remaining']['orders']
            if len(order.get('allocation_instruction', [])) > 1
        ]
        
        # Limit to first X
        limited_orders = aggregated_orders[:limit_aggregated_orders]
        
        # Update basket
        baskets['remaining']['orders'] = limited_orders
        baskets['remaining']['order_count'] = len(limited_orders)
        
        print(f"\n  LIMITED REMAINING BASKET:")
        print(f"  Original: {original_count} orders")
        print(f"  Aggregated only: {len(aggregated_orders)} orders")
        print(f"  Limited to: {len(limited_orders)} orders")
    
    print("\nOrder counts:")
    for basket_type, basket_data in baskets.items():
        print(f"  {basket_type}: {basket_data['order_count']} orders")
    
    # Validate each basket
    for basket_type, basket_data in baskets.items():
        is_valid, errors = OrderSubmissionValidator.validate_orders(basket_data['orders'])
        if not is_valid:
            print(f"{basket_type} validation failed: {errors}")
            return
        print(f"{basket_type}: {basket_data['order_count']} orders validated")
    
    # Show aggregated orders (first 5 only)
    if 'remaining' in baskets:
        print("\nAggregated orders (showing first 5):")
        aggregated_orders = [
            order for order in baskets['remaining']['orders'] 
            if len(order.get('allocation_instruction', [])) > 1
        ]
        
        for order in aggregated_orders[:5]:
            allocs = order.get('allocation_instruction', [])
            print(f"  {order['security_id']} {order['side'].value}:")
            print(f"    Total: {order['quantity']}")
            print(f"    Accounts: {len(allocs)}")
            for alloc in allocs[:3]:
                print(f"      - {alloc.Account}: {alloc.Quantity}")
        
        # Show count if there are more
        if len(aggregated_orders) > 5:
            print(f"\n  ... and {len(aggregated_orders) - 5} more aggregated orders")
    
    # Generate XML (same pattern as Example 2)
    for basket_type, basket_data in baskets.items():
        suffix = "_CROSSES" if basket_type == 'crosses' else "_REMAINING_AGG"
        
        xml = BasketOrderXMLBuilder.get_request_xml_string(
            custom_list_id=uuid.uuid1(),
            list_of_orders=basket_data['orders'],
            basket_name=None,
            # basket_name_prefix=f"TEST_AGG{suffix}",
            basket_name_prefix = safe_basket_prefix(f"LE{suffix}", max_length=20),
            route_to_session="4571.DRAY.BQNT",
            check_pretrade_compliance=CheckPretradeCompliance.NO,
            flow_control_flag=FlowControlTag.ACTIVE_ORDER,
            list_processing_level=ListProcessingLevel.LIST,
            compliance_override_text="TestOverride",
        )
        
        basket_data['xml'] = xml
        
        # Save to file
        filename = XML_REQUESTS_DIR / f"basket_{basket_type}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml)

        
        print(f"{basket_type}: Saved to {filename}")
    
    print("\nGenerated XML with aggregated orders and separated baskets")
    print("Ready to submit via WebSocket")
    
    return baskets


# ============================================================================
# SUBMISSION - Multiple Baskets
# ============================================================================

def calculate_timeout(order_count):
    """Calculate timeout based on order count"""
    base_timeout = 10
    seconds_per_order = 0.16
    buffer_multiplier = 1.03
    
    calculated = base_timeout + (order_count * seconds_per_order)
    timeout_with_buffer = calculated * buffer_multiplier
    
    # Min 10s, Max 10 min (600s)
    return int(max(10, min(600, timeout_with_buffer)))

def submit_baskets(baskets, uri, secrets, host, generate_websocket_url_func, 
                   run_request_from_file_func, delay_between_baskets=3):
    """
    Submit multiple baskets to Bloomberg with fresh JWT tokens and dynamic timeouts.
    
    Args:
        baskets: Dict from OrderConverter with 'crosses' and/or 'remaining'
        uri: URI for Bloomberg API
        secrets: Your secrets dict for authentication
        host: Bloomberg host
        generate_websocket_url_func: Your function to generate WebSocket URL with JWT
        run_request_from_file_func: Your function to run request from file
        delay_between_baskets: Seconds to wait between submissions (default 3)
        
    Returns:
        Dict with results for each basket
    """
    
    # Check basket names
    print("\n" + "="*70)
    print("CHECKING BASKET NAMES")
    print("="*70)
    
    for basket_type, basket_data in baskets.items():
        root = ET.fromstring(basket_data['xml'])
        basket_name = root.findtext(".//BasketName")
        order_count = root.findtext(".//TotNoOrders")
        timeout = calculate_timeout(basket_data['order_count'])
        print(f"{basket_type}:")
        print(f"  Name: {basket_name}")
        print(f"  Orders: {order_count}")
        print(f"  Timeout: {timeout}s ({timeout/60:.1f} min)")
    
    # Submit baskets
    print("\n" + "="*70)
    print("SUBMITTING BASKETS")
    print("="*70)
    
    results = {}
    
    for idx, (basket_type, basket_data) in enumerate(baskets.items(), 1):
        print(f"\n[{idx}/{len(baskets)}] {basket_type}...")
        
        # Save XML
        filename = XML_REQUESTS_DIR / f"basket_{basket_type}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(basket_data['xml'])

        
        # Get basket info
        root = ET.fromstring(basket_data['xml'])
        basket_name = root.findtext(".//BasketName")
        order_count = basket_data['order_count']
        
        # Calculate dynamic timeout
        timeout = calculate_timeout(order_count)
        
        print(f"  Basket: {basket_name}")
        print(f"  Orders: {order_count}")
        print(f"  Timeout: {timeout}s ({timeout/60:.1f} min)")
        
        # Generate fresh JWT token
        print(f"  → Generating fresh JWT...")
        url = generate_websocket_url_func(uri, 'GET', secrets, host)
        print(f"  ✓ JWT generated")
        
        # Submit with dynamic timeout
        print(f"  → Submitting...")
        
        try:
            api_response = run_request_from_file_func(filename, url, timeout=timeout)
            
            if api_response is not None:
                print(f"  ✓ Response ({len(api_response)} chars)")
                results[basket_type] = {'status': 'success', 'basket_name': basket_name}
            else:
                print(f"  ℹ No response (expected)")
                results[basket_type] = {'status': 'success', 'basket_name': basket_name}
        
        except Exception as e:
            print(f"  Error: {e}")
            results[basket_type] = {'status': 'error', 'error': str(e)}
        
        # Wait between baskets
        if idx < len(baskets):
            print(f"  Waiting {delay_between_baskets} seconds...")
            time.sleep(delay_between_baskets)
    
    # Summary
    print("\n" + "="*70)
    print("SUBMISSION COMPLETE")
    print("="*70)
    
    for basket_type, result in results.items():
        status_icon = "✓" if result['status'] == 'success' else "✗"
        print(f"{status_icon} {basket_type}: {result['status']}")
        if 'basket_name' in result:
            print(f"    Basket: {result['basket_name']}")
    
    print("\n" + "="*70)
    print("VERIFY IN BLOOMBERG TERMINAL (OMX NEW <GO>)")
    print("="*70)
    print("Check for these baskets:")
    for basket_type, result in results.items():
        if 'basket_name' in result:
            print(f"  - {result['basket_name']}")
    print("="*70)
    
    return results




