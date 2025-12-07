"""
XML Builder for Basket Orders

Builds XML requests for AIM basket orders.
Handles crossed orders (with CROSS broker) and standard orders.
"""

import uuid as _uuid
import datetime
import logging
import lxml.etree as ET

from .enums import (
    FlowControlTag,
    ListProcessingLevel,
    CheckPretradeCompliance,
    SecurityIdType,
    OrderType,
    Side,
    TimeInForce,
)
from .order_types import SingleAllocation

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------

def _require(cond, msg):
    """Raise ValueError if condition is False"""
    if not cond:
        raise ValueError(msg)


def _text(parent, tag, value):
    """Create XML element with text value"""
    el = ET.SubElement(parent, tag)
    el.text = str(value)
    return el


def _ymdhms(dt: datetime.datetime) -> str:
    """Format datetime as YYYYMMDD-HH:MM:SS in UTC"""
    return dt.astimezone(datetime.timezone.utc).strftime("%Y%m%d-%H:%M:%S")


def _rand6():
    """Generate random 6-character hex string"""
    return _uuid.uuid4().hex[:6].upper()


def _basket_name(prefix: str = "BQuantDemo") -> str:
    """Generate unique basket name with date and random suffix"""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{today}{_uuid.uuid4().hex[:1].upper()}"


# ----------------------------------------------------------------------
# BasketOrderXMLBuilder
# ----------------------------------------------------------------------

class BasketOrderXMLBuilder:
    """
    XML builder for equity-only basket orders.
    Includes broker Parties for crossed trades.
    """

    @staticmethod
    def get_request_xml_string(
        *,
        custom_list_id: str | int | None = None,
        list_of_orders: list,
        basket_name: str | None = None,
        basket_name_prefix: str = "BQuantDemo",
        sender_id: str = "MQ_UPL_TSORD",
        target_id: str = "MQ_INT_TSORD",
        route_to_session: str = "4571.DRAY.BQNT",
        pricing_no: str = "4571",
        uuid_val: str = "26656679",
        flow_control_flag: FlowControlTag = FlowControlTag.ACTIVE_ORDER,
        list_processing_level: ListProcessingLevel = ListProcessingLevel.LIST,
        check_pretrade_compliance: CheckPretradeCompliance = CheckPretradeCompliance.NO,
        compliance_override_text: str = "TestOverride",
    ) -> str:
        """
        Build XML request string for basket order submission.

        Args:
            custom_list_id: Optional custom list ID
            list_of_orders: List of order dicts with required fields:
                - security_id: str
                - security_id_type: SecurityIdType
                - side: Side (BUY/SELL)
                - order_type: OrderType
                - limit_price: float
                - quantity: int
                - settl_currency: str
                - crossed: bool (True to include CROSS broker)
                - allocation_instruction: list[SingleAllocation]
            basket_name: Optional basket name (auto-generated if None)
            basket_name_prefix: Prefix for auto-generated basket name
            sender_id: FIX sender ID
            target_id: FIX target ID
            route_to_session: Bloomberg routing session
            pricing_no: Bloomberg pricing number
            uuid_val: Bloomberg UUID
            flow_control_flag: Order flow control flag
            list_processing_level: Processing level (ORDER or LIST)
            check_pretrade_compliance: Enable compliance checking
            compliance_override_text: Compliance override text

        Returns:
            XML string ready for API submission

        Raises:
            ValueError: If list_of_orders is invalid
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        _require(all(isinstance(x, dict) for x in list_of_orders), 
                "list_of_orders must be a list of dicts")

        # Auto-generate basket name if not provided
        if not basket_name:
            basket_name = _basket_name(basket_name_prefix)

        root = ET.Element("NewOrderList")

        # FIX header
        hdr = ET.SubElement(root, "FIXMessageHeader")
        _text(hdr, "MsgType", "E")
        _text(hdr, "SenderCompID", sender_id)
        _text(hdr, "TargetCompID", target_id)
        _text(hdr, "SendingTime", _ymdhms(now))
        _text(hdr, "RouteToSession", route_to_session)
        
        # Add ListID if provided (otherwise Bloomberg auto-generates)
        if custom_list_id:
            _text(root, "ListID", str(custom_list_id))
        
        _text(root, "BasketName", basket_name)
        _text(root, "TotNoOrders", len(list_of_orders))

        no_orders_el = ET.SubElement(root, "NoOrders", count=str(len(list_of_orders)))

        for order_ in list_of_orders:
            order_el = BasketOrderXMLBuilder.__build_order_element(
                now=now,
                basket_name_prefix=basket_name_prefix,
                uuid_val=uuid_val,
                **order_,
            )
            no_orders_el.append(order_el)

        _text(root, "ListProcessingLevel", list_processing_level.value)
        _text(root, "PricingNo", pricing_no)
        _text(root, "UUID", uuid_val)

        # TSOpenControlFlags
        tscf = ET.SubElement(root, "TSOpenControlFlags")
        group = ET.SubElement(tscf, "TSOpenNoControlFlags")
        items = []

        def _flag(name, value):
            item = ET.SubElement(group, "aTSOpenControlFlag")
            _text(item, "TSOpenControlFlagName", name)
            _text(item, "TSOpenControlFlagValue", value)
            items.append(item)

        _flag("CHECK_PRETRADE_COMPLIANCE", check_pretrade_compliance.value)
        _flag("COMPLIANCE_OVERRIDE", compliance_override_text)
        _flag("FLOW_CONTROL_FLAG", flow_control_flag.value)
        group.set("count", str(len(items)))

        xml_string = ET.tostring(root, pretty_print=True, encoding="utf8").decode("utf8")
        logger.debug("Final Basket Order Request XML:\n%s", xml_string)
        return xml_string

    @staticmethod
    def __build_order_element(
        *,
        security_id: str,
        security_id_type: SecurityIdType | str,
        side: Side,
        order_type: OrderType,
        quantity: int,
        settl_currency: str,
        settl_date: str | None = None,
        security_exchange: str | None = None,
        crossed: bool = False,
        limit_price: float | None = None,
        stop_price: float | None = None,
        allocation_instruction=None,
        alloc_acct_id_source: str = "100",
        individual_alloc_id: str = "TEST",
        now: datetime.datetime,
        basket_name_prefix: str = "BQuantDemo",
        clord_id: str | None = None,
        uuid_val: str = "26656679",
        time_in_force: TimeInForce | None = None,
        instructions: str | None = None,
        long_notes: str | None = None, 
        broker: str | None = None,
    ):
        """
        Build individual order element.

        Args:
            security_id: Security identifier
            security_id_type: Type of security ID
            side: BUY or SELL
            order_type: Order type (LIMIT, MARKET, etc.)
            limit_price: Limit price
            quantity: Order quantity
            settl_currency: Settlement currency
            crossed: If True, adds CROSS broker to Parties
            allocation_instruction: List of SingleAllocation namedtuples
            alloc_acct_id_source: Allocation account ID source
            individual_alloc_id: Individual allocation ID
            now: Current datetime
            basket_name_prefix: Basket name prefix for ClOrdID
            clord_id: Optional custom ClOrdID
            uuid_val: Bloomberg UUID

        Returns:
            lxml.etree.Element: Order element
        """
        allocation_instruction = allocation_instruction or []
        order = ET.Element("Order")

        # ClOrdID
        _text(order, "ClOrdID", clord_id or f"{basket_name_prefix}_{_rand6()}")

        # Instrument
        instr = ET.SubElement(order, "Instrument")
        _text(instr, "SecurityID", security_id)
        val = security_id_type.value if isinstance(security_id_type, SecurityIdType) else str(security_id_type)
        _text(instr, "SecurityIDSource", val)
        _text(instr, "FixedIncomeFlag", 2)  # equities only

        # Add exchange if provided
        if security_exchange:
            _text(instr, "SecurityExchange", security_exchange)
        
        _text(order, "Side", side.value)
        _text(order, "HandlInst", "1")  # Automated execution, private, no broker intervention
        
        # Only add price for LIMIT and STOP_LIMIT orders
        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if limit_price is not None:
                _text(order, "Price", limit_price)
        
        # Add stop price for STOP and STOP_LIMIT orders
        if order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
            if stop_price is not None:
                _text(order, "StopPx", stop_price)
        
        _text(order, "TransactTime", _ymdhms(now))

        oqd = ET.SubElement(order, "OrderQtyData")
        _text(oqd, "OrderQty", quantity)
        _text(order, "OrdType", order_type.value)
        
        # Always add TimeInForce (default to DAY if not specified)
        if time_in_force is not None:
            _text(order, "TimeInForce", time_in_force.value)
        else:
            _text(order, "TimeInForce", TimeInForce.DAY.value)
        
        _text(order, "SettlCurrency", settl_currency)
        # Add settlement date if provided
        if settl_date:
            _text(order, "SettlDate", settl_date)

        # Parties
        parties = ET.SubElement(order, "Parties")
        if crossed:
            # Crossed order: includes CROSS broker
            npids = ET.SubElement(parties, "NoPartyIDs", count="3")
            # Broker CROSS
            p1 = ET.SubElement(npids, "Party")
            _text(p1, "PartyID", "CROSS")
            _text(p1, "PartyRole", "2")
            # Portfolio manager
            p2 = ET.SubElement(npids, "Party")
            _text(p2, "PartyID", uuid_val)
            _text(p2, "PartyRole", "110")
            # Trader
            p3 = ET.SubElement(npids, "Party")
            _text(p3, "PartyID", uuid_val)
            _text(p3, "PartyRole", "102")
        else:
            # Standard order: no broker (unless specified)
            if broker:
                npids = ET.SubElement(parties, "NoPartyIDs", count="3")
                # External broker
                p1 = ET.SubElement(npids, "Party")
                _text(p1, "PartyID", broker)
                _text(p1, "PartyRole", "1")  # EXECUTING_FIRM
            else:
                npids = ET.SubElement(parties, "NoPartyIDs", count="2")
            
            # Portfolio manager (always)
            p2 = ET.SubElement(npids, "Party")
            _text(p2, "PartyID", uuid_val)
            _text(p2, "PartyRole", "110")
            
            # Trader (always)
            p3 = ET.SubElement(npids, "Party")
            _text(p3, "PartyID", uuid_val)
            _text(p3, "PartyRole", "102")
        
        # Pre-allocation method: user-specified quantities
        _text(order, "PreAllocMethod", "0")  # 0 = user-specified, 1 = proportional
        
        # Allocations
        na = ET.SubElement(order, "NoAllocs", count=str(len(allocation_instruction)))
        for alloc in allocation_instruction:
            acct = getattr(alloc, "Account", None) or "UNKNOWN"
            qty = getattr(alloc, "Quantity", 0)
            
            _text(na, "AllocAccount", acct)
            _text(na, "AllocAcctIDSource", alloc_acct_id_source)
            _text(na, "IndividualAllocID", acct)  # use same portfolio ID for alloc ID
            _text(na, "AllocQty", qty)

        # Add instructions
        notes = ET.SubElement(order, "BBNotes")
        if instructions:
            _text(notes, "Text", instructions)
        
        if long_notes:
            _text(order, "Txt", long_notes)
        
        return order


