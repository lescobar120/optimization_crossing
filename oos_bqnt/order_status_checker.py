"""
Bloomberg Order Status Checker

Queries Bloomberg AIM to check order status after submission.
Uses the same authentication as order submission.
"""

import time
import asyncio
import websockets
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional


class OrderStatusChecker:
    """Check order status via Bloomberg WebSocket API"""
    
    def __init__(self):
        pass
    
    async def check_basket_status_async(
        self, 
        url: str,
        basket_name: str,
        pricing_no: str,
        uuid_val: str,
        max_retries: int = 5,
        retry_delay: float = 2.0
    ) -> Optional[str]:
        """
        Check status of basket orders by basket name via WebSocket.
        
        Args:
            url: WebSocket URL with JWT token
            basket_name: Name of basket submitted
            pricing_no: Bloomberg pricing number
            uuid_val: Bloomberg UUID
            max_retries: Number of times to retry checking
            retry_delay: Seconds to wait between retries
            
        Returns:
            XML response string or None
        """
        # Build ListStatusRequest XML
        request_xml = self._build_status_request(basket_name, pricing_no, uuid_val)
        
        print(f"\nChecking status for basket: {basket_name}")
        
        for attempt in range(max_retries):
            try:
                print(f"  Attempt {attempt + 1}/{max_retries}...", end=" ")
                
                async with websockets.client.connect(url, ping_interval=20) as websocket:
                    # Send status request
                    await websocket.send(request_xml)
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        print("✓ Response received")
                        return response
                    except asyncio.TimeoutError:
                        print("✗ Timeout")
                        
            except websockets.exceptions.InvalidStatusCode as e:
                if e.status_code == 401:
                    print("✗ Authentication expired")
                    # JWT token expired, caller needs to regenerate URL
                    return None
                else:
                    print(f"✗ HTTP {e.status_code}")
            except Exception as e:
                print(f"✗ Error: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
        
        print(f"\nFailed to get status after {max_retries} attempts")
        return None
    
    def check_basket_status(
        self,
        url: str,
        basket_name: str,
        pricing_no: str,
        uuid_val: str,
        max_retries: int = 5,
        retry_delay: float = 2.0
    ) -> Optional[str]:
        """
        Synchronous wrapper for check_basket_status_async.
        
        Args:
            url: WebSocket URL with JWT token
            basket_name: Name of basket submitted
            pricing_no: Bloomberg pricing number
            uuid_val: Bloomberg UUID
            max_retries: Number of times to retry checking
            retry_delay: Seconds to wait between retries
        
        Returns:
            XML response string or None
        """
        return asyncio.run(
            self.check_basket_status_async(
                url,
                basket_name,
                pricing_no,
                uuid_val,
                max_retries,
                retry_delay
            )
        )
    
    def _build_status_request(
        self,
        basket_name: str,
        pricing_no: str,
        uuid_val: str
    ) -> str:
        """Build ListStatusRequest XML"""
        import datetime
        
        now = datetime.datetime.now(datetime.timezone.utc)
        sending_time = now.strftime("%Y%m%d-%H:%M:%S")
        
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ListStatusRequest>
    <FIXMessageHeader>
        <MsgType>M</MsgType>
        <SenderCompID>MQ_UPL_TSORD</SenderCompID>
        <TargetCompID>MQ_INT_TSORD</TargetCompID>
        <SendingTime>{sending_time}</SendingTime>
        <RouteToSession>{pricing_no}.DRAY.BQNT</RouteToSession>
    </FIXMessageHeader>
    <BasketName>{basket_name}</BasketName>
    <PricingNo>{pricing_no}</PricingNo>
    <UUID>{uuid_val}</UUID>
</ListStatusRequest>
"""
        return xml
    
    def parse_status_response(self, xml_response: str) -> Dict:
        """
        Parse ListStatus response XML.
        
        Returns:
            Dict with parsed order status information
        """
        try:
            root = ET.fromstring(xml_response)
            
            list_id = root.findtext(".//ListID") or "Unknown"
            list_status = root.findtext(".//ListOrderStatus") or "Unknown"
            basket_name = root.findtext(".//BasketName") or "Unknown"
            
            orders = []
            for order in root.findall(".//Order_List"):
                order_id = order.findtext("OrderID") or "Unknown"
                clordid = order.findtext("ClOrdID") or "Unknown"
                status = order.findtext("OrdStatus") or "Unknown"
                security = order.findtext(".//Instrument/SecurityID") or "Unknown"
                
                orders.append({
                    "order_id": order_id,
                    "clordid": clordid,
                    "status": status,
                    "security": security
                })
            
            return {
                "success": True,
                "list_id": list_id,
                "list_status": list_status,
                "basket_name": basket_name,
                "order_count": len(orders),
                "orders": orders,
                "raw_xml": xml_response
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_xml": xml_response
            }