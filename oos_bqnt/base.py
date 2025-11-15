from enum import Enum
from collections import namedtuple
import os
from typing import NamedTuple

required_env_variables = {'USING_IBM_MQ',
                          'BBG_UUID',
                          'PX_NUM',
                          'USE_NEW_CMGR_XML'
                          }

for req_var in required_env_variables:
    assert req_var in os.environ, f'Required variable {req_var} not in the list of environment variables'

USING_IBM_MQ = os.environ.get('USING_IBM_MQ')
BOOL_STRINGS = {'1','TRUE','Y','YES','T'}


if USING_IBM_MQ.upper() in BOOL_STRINGS:
    SENDER_ID = 'MQ_UPL_TSORD'
    TARGET_ID = 'MQ_INT_TSORD'
else:
    SENDER_ID = 'BAS_UPL_TSORD'
    TARGET_ID = 'BAS_INT_TSORD'

BBG_UUID = os.environ.get('BBG_UUID')
PX_NUM = os.environ.get('PX_NUM')
USE_NEW_CMGR_XML = os.environ.get('USE_NEW_CMGR_XML').upper() in BOOL_STRINGS

class OrderType(Enum):
    MARKET = '1'
    LIMIT = '2'
    STOP = '3'
    STOP_LIMIT = '4'
    MARKET_ON_CLOSE = '5'
    ON_CLOSE = 'A'

class ReportType(Enum):
    NEW = '0'
    DONE_FOR_DAY = '3'
    CANCELLED = '3'
    REPLACED = '5'
    REJECTED = '8'
    SUSPENDED = '9'
    TRADE_FILL = 'F'
    TRADE_FILL_CORRECTION = 'G'
    TRADE_FILL_CANCEL = 'H'
    ASSIGN_UNASSIGN_TRADER = 'I'
    VMGR_STATUS = 'V'

class TimeInForce(Enum):
     DAY = '0'
     GOOD_TILL_CANCEL = '1'
     AT_THE_OPENING = '2'
     IMMEDIATE_OR_CANCEL = '3'
     FILL_OR_KILL = '4'
     GOOD_TILL_DATE = '6'
     AT_THE_CLOSE = '7'

class ExecutionInstruction(Enum):
    STAY_ON_OFFER_SIDE = '0'
    NOT_HELD = '1'
    WORK = '2'
    GO_ALONG = '3'
    OVER_THE_DAY = '4'
    HELD = '5'
    PARTICIPATE_DO_NOT_INITIATE = '6'
    STRICT_SCALE = '7'
    TRY_TO_SCALE = '8'
    STAY_ON_BID_SIDE = '9'
    NO_CROSS = 'A'
    OK_TO_CROSS = 'B'
    CALL_FIRST = 'C'
    PERCENT_OF_VOLUME = 'D'
    DO_NOT_INCREASE = 'E'
    DO_NOT_REDUCE = 'F'
    ALL_OR_NONE = 'G'
    INSTITUTIONS_ONLY = 'I'
    NON_NEGOTIABLE = 'N'
    SUSPEND = 'S'
    CUSTOMER_DISPLAY_INSTRUCTION = 'U'

class HandlingInstruction(Enum):
    AUTOMATED_ORDER_NO_BROKER_INTERVENTION = '1'
    AUTOMATED_ORDER_OK_BROKER_INTERVENTION = '2'
    MANUAL_ORDER = '3'

class ListProcessingLevel(Enum):
    ORDER = 'ORDER'
    LIST = 'LIST'

class ListOrderStatus(Enum):
    REJECT = '7'
    ALL_DONE = '6'
    INBIDDINGPROCESS = '1'
    RECEIVEDFOREXECUTION = '2'
    EXECUTING = '3'
    CANCELING = '4'
    ALERT = '5'

class ListStatusType(Enum):
    ACK = '1'
    RESPONSE = '2'
    TIMED = '3'
    EXECSTARTED = '4'
    ALLDONE = '5'
    ALERT ='6'

class FlowControlTag(Enum):
    ACTIVE_ORDER = '0'
    WHAT_IF_ORDER = '1' # what if wil; validate order against compliance rule and send back
        #compliance result without generating order in Bloomberg system
    HELD_ORDER = '3'

class SecurityIdType(Enum):
    UNKNOWN = 'UNKNOWN'
    CUSIP = '1'
    SEDOL1 = '2'
    ISIN = '4'
    BLOOMBERG_SYMBOL = 'A'
    SEDOL2 = '103'
    EQUITY_TICKER = '108'
    BLOOMBERG_UNIQUE_ID = '111'
    FIGI = '112'

class ComplianceStatus(Enum):
    COMPLIANCE_PASSED = '0'
    WARNING = '1'
    NEED_APPROVAL = '2'
    ORDER_REJECTED = '3'
    TRADE_OVERRIDE = '4'
    COMPLIANCE_BYPASSED_BY_USER = '5'
    COMPLIANCE_BYPASSED_BY_CONFIGURATION = '6'
    COMPLIANCE_DISABLED = '7'
    NONE = None

class Side(Enum):
    BUY = '1'
    SELL = '2'

AllocationGroupMethod = namedtuple('AllocationGroupMethod',field_names = ['AccountGroup','MethodName'])
SingleAllocation = namedtuple('SingleAllocation',field_names = ['Account','Quantity'])

class QuantityType(Enum):
    UNITS = '0'# shares, par , currency
    CONTRACTS = '1'


class CheckPretradeCompliance(Enum):
    YES = 'Y'
    NO = 'N'

class OrderIdType(Enum):
    BLOOMBERG = '1'
    EXTERNAL_ID = '2'

class PartyRole(Enum):
    EXECUTING_FIRM = '1'
    BROKER_OF_CREDIT = '2'
    SETTLEMENT_LOCATION = '10'
    TRADERUUID = '102'
    TRADING_DESK = '108'
    PORTFOLIO_MANAGER = '110'
    EXECUTION_TARGET = '112'

class PartyDetails(NamedTuple):
    PartyID : str
    PartyRole: PartyRole


class OrderStatus(Enum):
    NEW = '0'
    PARIAL_FILLED = '1'
    FILLED = '2'
    DONE_FOR_DAY = '3'
    CANCELLED = '4'
    REPLACED = '5'
    REJECTED = '8'
    SUSPENDED = '9'
    PENDING_NEW = 'A'

class iXMLHandler(object):
    'Interface class'

    @staticmethod
    def get_request_xml_string(**kwargs):
        ...

    @staticmethod
    def get_response_from_xml(xml_str:str):
        ...
    

