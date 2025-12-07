"""
Type definitions for OOS_BQNT integration layer.

Named tuples and data structures used throughout the system.
"""

from collections import namedtuple
from typing import NamedTuple
from .enums import PartyRole


# Named tuples for allocation and party details
AllocationGroupMethod = namedtuple(
    'AllocationGroupMethod',
    field_names=['AccountGroup', 'MethodName']
)

SingleAllocation = namedtuple(
    'SingleAllocation',
    field_names=['Account', 'Quantity']
)


class PartyDetails(NamedTuple):
    """Party details for order parties"""
    PartyID: str
    PartyRole: PartyRole


# Interface class for XML handlers
class iXMLHandler(object):
    """Interface class for XML handlers"""
    
    @staticmethod
    def get_request_xml_string(**kwargs):
        """Generate XML request string"""
        ...
    
    @staticmethod
    def get_response_from_xml(xml_str: str):
        """Parse XML response string"""
        ...