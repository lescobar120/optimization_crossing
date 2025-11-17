"""
XML Response Parser for Basket Orders

Parses XML responses from Bloomberg AIM basket order submissions.
"""

import logging
import lxml.etree as ET

from enums import ListOrderStatus, ListProcessingLevel
from compliance import get_compliance_response_new_version as get_compliance_response

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Basket Order Creation Response
# ----------------------------------------------------------------------

class BasketOrderCreationResponse:
    """
    Response object for basket order creation.
    
    Attributes:
        order_id: List ID from Bloomberg
        order_status: Overall list order status
        compliance_response: Compliance check results
        error_message: Error message if any
        individual_responses: List of individual order responses
    """
    
    def __init__(
        self,
        list_id: int | str,
        list_status: ListOrderStatus,
        compliance_response,
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
        """Convert response to dictionary"""
        return {
            "list_id": self.order_id,
            "list_status": self.order_status.value,
            "error": self.error_message,
            "compliance": str(self.compliance_response),
            "individual_responses": [
                r.to_dict() if hasattr(r, 'to_dict') else r 
                for r in self.individual_responses
            ],
        }


# ----------------------------------------------------------------------
# XML Response Parser
# ----------------------------------------------------------------------

class BasketOrderXMLParser:
    """Parser for Bloomberg AIM basket order XML responses"""

    @staticmethod
    def get_response_from_xml(
        xml_string, 
        list_processing_level: ListProcessingLevel
    ) -> BasketOrderCreationResponse:
        """
        Parse XML response from Bloomberg AIM.

        Args:
            xml_string: XML response as string or bytes
            list_processing_level: Processing level (ORDER or LIST)

        Returns:
            BasketOrderCreationResponse object with parsed data

        Raises:
            ValueError: If XML is invalid format
        """
        # Convert to XML object
        if isinstance(xml_string, str):
            xml_obj = ET.XML(xml_string.encode("utf8"))
        elif isinstance(xml_string, (bytes, bytearray)):
            xml_obj = ET.XML(xml_string)
        else:
            raise ValueError("XML must be string or bytes")

        # Extract list-level information
        list_id_el = xml_obj.find("ListID")
        list_status_el = xml_obj.find("ListOrderStatus")
        list_id = list_id_el.text if list_id_el is not None else "UNKNOWN"
        list_status = ListOrderStatus(
            list_status_el.text if list_status_el is not None else "7"
        )

        list_error_text_el = xml_obj.find("ListStatusText")
        list_error_text = list_error_text_el.text if list_error_text_el is not None else ""

        # Extract individual order responses
        order_elements = xml_obj.findall("./NoOrders/Order")
        single_order_responses = []
        for o in order_elements:
            order_status_el = o.find("OrdStatus")
            order_status = order_status_el.text if order_status_el is not None else "8"
            single_order_responses.append(
                dict(
                    order_status=order_status,
                    xml=ET.tostring(o, pretty_print=True).decode()
                )
            )

        # Get compliance response
        comp_resp = get_compliance_response(xml_obj)

        return BasketOrderCreationResponse(
            list_id=list_id,
            list_status=list_status,
            compliance_response=comp_resp,
            error_message=list_error_text,
            individual_responses=single_order_responses,
        )


