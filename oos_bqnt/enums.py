"""
Enumerations for OOS_BQNT integration layer.

All enums used for order creation, execution, and status tracking.
"""

from enum import Enum


class OrderType(Enum):
    """Order type"""
    MARKET = '1'
    LIMIT = '2'
    STOP = '3'
    STOP_LIMIT = '4'
    MARKET_ON_CLOSE = '5'
    ON_CLOSE = 'A'


class ReportType(Enum):
    """Report type"""
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
    """Time in force"""
    DAY = '0'
    GOOD_TILL_CANCEL = '1'
    AT_THE_OPENING = '2'
    IMMEDIATE_OR_CANCEL = '3'
    FILL_OR_KILL = '4'
    GOOD_TILL_DATE = '6'
    AT_THE_CLOSE = '7'


class ExecutionInstruction(Enum):
    """Execution instruction"""
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
    """Handling instruction"""
    AUTOMATED_ORDER_NO_BROKER_INTERVENTION = '1'
    AUTOMATED_ORDER_OK_BROKER_INTERVENTION = '2'
    MANUAL_ORDER = '3'


class ListProcessingLevel(Enum):
    """List processing level"""
    ORDER = 'ORDER'
    LIST = 'LIST'


class ListOrderStatus(Enum):
    """List order status"""
    REJECT = '7'
    ALL_DONE = '6'
    INBIDDINGPROCESS = '1'
    RECEIVEDFOREXECUTION = '2'
    EXECUTING = '3'
    CANCELING = '4'
    ALERT = '5'


class ListStatusType(Enum):
    """List status type"""
    ACK = '1'
    RESPONSE = '2'
    TIMED = '3'
    EXECSTARTED = '4'
    ALLDONE = '5'
    ALERT = '6'


class FlowControlTag(Enum):
    """Flow control tag"""
    ACTIVE_ORDER = '0'
    WHAT_IF_ORDER = '1'  # Validate order against compliance rule without generating order
    HELD_ORDER = '3'


class SecurityIdType(Enum):
    """Security identifier type"""
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
    """Compliance status"""
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
    """Order side"""
    BUY = '1'
    SELL = '2'


class QuantityType(Enum):
    """Quantity type"""
    UNITS = '0'  # shares, par, currency
    CONTRACTS = '1'


class CheckPretradeCompliance(Enum):
    """Check pre-trade compliance flag"""
    YES = 'Y'
    NO = 'N'


class OrderIdType(Enum):
    """Order ID type"""
    BLOOMBERG = '1'
    EXTERNAL_ID = '2'


class PartyRole(Enum):
    """Party role"""
    EXECUTING_FIRM = '1'
    BROKER_OF_CREDIT = '2'
    SETTLEMENT_LOCATION = '10'
    TRADERUUID = '102'
    TRADING_DESK = '108'
    PORTFOLIO_MANAGER = '110'
    EXECUTION_TARGET = '112'


class OrderStatus(Enum):
    """Order status"""
    NEW = '0'
    PARTIAL_FILLED = '1'
    FILLED = '2'
    DONE_FOR_DAY = '3'
    CANCELLED = '4'
    REPLACED = '5'
    REJECTED = '8'
    SUSPENDED = '9'
    PENDING_NEW = 'A'


