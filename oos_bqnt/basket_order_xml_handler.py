import uuid as _uuid
import datetime
import logging
import lxml.etree as ET

from base import (
    iXMLHandler,
    FlowControlTag,
    ListProcessingLevel,
    CheckPretradeCompliance,
    SecurityIdType,
    OrderType,
    Side,
    ListOrderStatus,
    OrderStatus,
    SingleAllocation,
)
from compliance import get_compliance_response_new_version as get_compliance_response
from compliance import ComplianceResponse

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------

def _require(cond, msg):
    if not cond:
        raise ValueError(msg)

def _text(parent, tag, value):
    el = ET.SubElement(parent, tag)
    el.text = str(value)
    return el

def _ymdhms(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).strftime("%Y%m%d-%H:%M:%S")

def _rand6():
    return _uuid.uuid4().hex[:6].upper()

def _basket_name(prefix: str = "BQuantDemo") -> str:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{today}{_uuid.uuid4().hex[:1].upper()}"

# ----------------------------------------------------------------------
# Basket Order Creation Response
# ----------------------------------------------------------------------

class BasketOrderCreationResponse:
    def __init__(
        self,
        list_id: int | str,
        list_status: ListOrderStatus,
        compliance_response: ComplianceResponse,
        error_message: str = "",
        individual_responses: list | None = None,
    ):
        self.order_id = list_id
        self.order_status = list_status
        self.compliance_response = compliance_response
        self.error_message = error_message
        self.individual_responses = individual_responses or []

    def __repr__(self):
        s = [f"{k}:{v}" for k, v in self.__dict__.items()]
        return " | ".join(s)

    def to_dict(self):
        return {
            "list_id": self.order_id,
            "list_status": self.order_status.value,
            "error": self.error_message,
            "compliance": str(self.compliance_response),
            "individual_responses": [
                r.to_dict() for r in self.individual_responses
            ],
        }

# ----------------------------------------------------------------------
# BasketOrderXMLHanlder (with CROSS broker)
# ----------------------------------------------------------------------

class BasketOrderXMLHanlder(iXMLHandler):
    """XML builder for equity-only basket orders, includes broker Parties for crossed trades."""

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

        now = datetime.datetime.now(datetime.timezone.utc)
        _require(all(isinstance(x, dict) for x in list_of_orders), "list_of_orders must be a list of dicts")

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

        _text(root, "BasketName", basket_name)
        _text(root, "TotNoOrders", len(list_of_orders))

        no_orders_el = ET.SubElement(root, "NoOrders", count=str(len(list_of_orders)))

        for order_ in list_of_orders:
            order_el = BasketOrderXMLHanlder.__build_order_element(
                now=now,
                basket_name_prefix=basket_name_prefix,
                uuid_val=uuid_val,
                **order_,
            )
            no_orders_el.append(order_el)

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

    # ---------------------- Order Builder ----------------------
    @staticmethod
    def __build_order_element(
        *,
        security_id: str,
        security_id_type: SecurityIdType | str,
        side: Side,
        order_type: OrderType,
        limit_price: float,
        quantity: int,
        settl_currency: str,
        crossed: bool = False,   # <-- this line MUST be here
        allocation_instruction=None,
        alloc_acct_id_source: str = "100",
        individual_alloc_id: str = "TEST",
        now: datetime.datetime,
        basket_name_prefix: str = "BQuantDemo",
        clord_id: str | None = None,
        uuid_val: str = "26656679",
    ):
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

        _text(order, "Side", side.value)
        _text(order, "Price", limit_price)
        _text(order, "TransactTime", _ymdhms(now))

        oqd = ET.SubElement(order, "OrderQtyData")
        _text(oqd, "OrderQty", quantity)
        _text(order, "OrdType", order_type.value)
        _text(order, "SettlCurrency", settl_currency)

        # Parties
        parties = ET.SubElement(order, "Parties")
        if crossed:
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
            npids = ET.SubElement(parties, "NoPartyIDs", count="2")
            p2 = ET.SubElement(npids, "Party")
            _text(p2, "PartyID", uuid_val)
            _text(p2, "PartyRole", "110")
            p3 = ET.SubElement(npids, "Party")
            _text(p3, "PartyID", uuid_val)
            _text(p3, "PartyRole", "102")

        # Allocations – use actual account from SingleAllocation
        na = ET.SubElement(order, "NoAllocs", count=str(len(allocation_instruction)))
        for alloc in allocation_instruction:
            acct = getattr(alloc, "Account", None) or "UNKNOWN"
            qty  = getattr(alloc, "Quantity", 0)
            _text(na, "AllocAccount", acct)
            _text(na, "AllocAcctIDSource", alloc_acct_id_source)
            _text(na, "IndividualAllocID", acct)   # use same portfolio ID for alloc ID
            _text(na, "AllocQty", qty)


        ET.SubElement(order, "BBNotes")
        return order

    # ---------------------- Response Parser ----------------------
    @staticmethod
    def get_response_from_xml(xml_string, list_processing_level: ListProcessingLevel):
        if isinstance(xml_string, str):
            xml_obj = ET.XML(xml_string.encode("utf8"))
        elif isinstance(xml_string, (bytes, bytearray)):
            xml_obj = ET.XML(xml_string)
        else:
            raise ValueError("XML must be string or bytes")

        list_id_el = xml_obj.find("ListID")
        list_status_el = xml_obj.find("ListOrderStatus")
        list_id = list_id_el.text if list_id_el is not None else "UNKNOWN"
        list_status = ListOrderStatus(list_status_el.text if list_status_el is not None else "7")

        list_error_text_el = xml_obj.find("ListStatusText")
        list_error_text = list_error_text_el.text if list_error_text_el is not None else ""

        order_elements = xml_obj.findall("./NoOrders/Order")
        single_order_responses = []
        for o in order_elements:
            order_status_el = o.find("OrdStatus")
            order_status = order_status_el.text if order_status_el is not None else "8"
            single_order_responses.append(
                dict(order_status=order_status, xml=ET.tostring(o, pretty_print=True).decode())
            )

        comp_resp = get_compliance_response(xml_obj)

        return BasketOrderCreationResponse(
            list_id=list_id,
            list_status=list_status,
            compliance_response=comp_resp,
            error_message=list_error_text,
            individual_responses=single_order_responses,
        )
