import xml.etree.ElementTree as ET
import asyncio
import websockets

# COMPLIANCE_STATUS translation map
compliance_status_map = {
    "0": "Compliance Passed",
    "1": "Warning was generated",
    "2": "Need Approval (The order will be generated as inactive, and the violation must be approved on the {VMGR <GO>} screen before working on the order.)",
    "3": "Order rejected (Hard Breach)",
    "4": "Trade Override",
    "5": "Compliance bypassed by user (message flag)",
    "6": "Compliance bypassed by Configuration",
    "7": "Compliance functionality Disabled for OMS."
}

# WebSocket handler: send request, receive and process messages
async def hello(url, request_data):
    """
    Send request and return Bloomberg's response.
    
    Returns:
        str: XML response from Bloomberg (the final response after sending real order)
    """
    try:
        async with websockets.client.connect(url, ping_interval=30) as websocket:
            # Send request and get the final response
            final_response = await interactive_whatif(websocket, request_data)
            
            # Listen for additional responses with a timeout
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60)
                    await handle_response(response)
                    await asyncio.sleep(1)
            except asyncio.TimeoutError:
                print("No further messages received. Closing WebSocket.")
            except websockets.ConnectionClosedOK:
                print("Connection closed normally.")
            except Exception as ex:
                print(f"WebSocket error during listening: {ex}")
            
            # RETURN final response
            return final_response

    except Exception as conn_ex:
        print(f"Failed to establish WebSocket connection: {conn_ex}")
        return None  # Return None if connection fails
        
        
# Response processor: parses XML response and prints key info
async def handle_response(response):
    """
    Parse and print response information.
    
    Returns:
        bool: True if all compliance checks passed, False otherwise
    """
    try:
        root = ET.fromstring(response)
        all_ok = True  # Track whether all compliance flags are status 0

        tickets = [e.text for e in root.findall('.//TradingSystemTicketNumber') if e.text]
        if tickets:
            print(f"\nOrders created: {', '.join(tickets)}")

        rejections = [e.text for e in root.findall('.//ListStatusText') if e.text]
        if rejections:
            print(f"\nOrder rejected due to: {', '.join(rejections)}")

        last_px = root.findtext('.//LastPx')
        order_id = root.findtext('.//OrderID')
        if last_px:
            print(f"\nFilled Price: {last_px} | Order ID: {order_id or 'Unknown'}")

        orders = root.findall('.//Order_List')
        if not orders:
            #print("\nNo specific order action taken.")
            return False

        for order in orders:
            order_id = order.findtext('OrderID') or "Unknown"
            cl_ord_id = order.findtext('ClOrdID') or "Unknown"
            print(f"\nProcessing Order - ClOrdID: {cl_ord_id}, OrderID: {order_id}")

            ticket = order.findtext('TradingSystemTicketNumber')
            if ticket:
                print(f"TradingSystemTicketNumber: {ticket}")

            compliance_flags = order.findall('.//aLegTSOpenControlFlag')
            if not compliance_flags:
                print("No compliance flags.")
                continue

            for flag in compliance_flags:
                flag_name = flag.findtext('LegTSOpenControlFlagName')
                flag_value = flag.findtext('LegTSOpenControlFlagValue')

                if flag_name:
                    flag_name = flag_name.strip()
                if flag_value:
                    flag_value = flag_value.strip()

                if flag_name == "COMPLIANCE_STATUS":
                    translated = compliance_status_map.get(flag_value, f"Unknown value: {flag_value}")
                    print(f"COMPLIANCE_STATUS: {flag_value} → {translated}")
                    if flag_value != "0":
                        all_ok = False  # Found a failed compliance check
                else:
                    print(f"Ignored flag: {flag_name} = {flag_value}")

        return all_ok

    except ET.ParseError as e:
        print(f"Failed to parse XML: {e}")
        return False

# Main workflow: sends What-If payload, waits, optionally sends real order
async def interactive_whatif(websocket, request_data):
    """
    Send order and return the final response.
    
    Returns:
        str: Final XML response from Bloomberg
    """
    # Step 1: Send the what-if version
    await websocket.send(request_data)
    # print("Sent what-if payload... waiting for compliance results.\n")

    # # Step 2: Wait for and handle the what-if response
    # response = await websocket.recv()
    # all_ok = await handle_response(response)

    # if not all_ok:
    #     print("\nCompliance check failed. Aborting real order.")
    #     return

    # print("\nAll compliance checks passed.")
    # input("Press Enter to send the real order (FLOW_CONTROL_FLAG = 0)...")

    # Step 3: Modify FLOW_CONTROL_FLAG from 1 → 0
    tree = ET.ElementTree(ET.fromstring(request_data))
    root = tree.getroot()

    # for flag in root.findall('.//aTSOpenControlFlag'):
    #     name_elem = flag.find('TSOpenControlFlagName')
    #     value_elem = flag.find('TSOpenControlFlagValue')
    #     if name_elem is not None and value_elem is not None:
    #         if name_elem.text.strip() == "FLOW_CONTROL_FLAG":
    #             value_elem.text = "0"
    #             print("Updated FLOW_CONTROL_FLAG to 0")

    updated_request = ET.tostring(root, encoding="unicode")

    # Step 4: Send the updated real order
    await websocket.send(updated_request)
    print("\nSent real order with FLOW_CONTROL_FLAG = 0")

    # Step 5: Wait for and handle the final response
    final_response = await websocket.recv()
    await handle_response(final_response)
    
    # RETURN the final response
    return final_response

