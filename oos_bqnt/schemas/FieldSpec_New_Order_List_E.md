# New Order List (E)

| **FIX 4.4 Tag** | **XML Element** | **Required by Service** | **Description** |
|-----------------|-----------------|--------------------------|-----------------|
| **FIX Standard Header** | – | R | MsgType = E |
| **8** | BeginString | CR | Identifies the beginning of a new message and protocol version.<br>**Valid value:** FIX 4.4<br>This is required for FIX connectivity. |
| **49** | SenderCompID | R | Assigned value used to identify the firm sending the message. API users will use “BAS_UPD_TSORD” in this field. |
| **35** | MsgType | R | Defines message type. **Value:** E |
| **56** | TargetCompID | R | Assigned value used to identify the receiving firm. API users will use “BAS_INT_UPORD” in this field. |
| **34** | MsgSeqNum | CR | Integer message sequence number. Required for FIX, optional for MQ. |
| **52** | SendingTime | R | Time of message transmission, always expressed in UTC (Universal Time Coordinated, also known as GMT). |
| **7779** | RouteToSession | CR | Required for the MQ Interface. Pricing Number (PX) number values should be used. This will be used to form the reply to queue.<br>**For example:**<br>`<functionality>.<RouteToSession>`<br>`TSORD.REPLY.1234` |
| **66** | ListID | R | Must be unique, by client, for the day. |
| **6374** | BasketName | CR | Name of the basket being staged. It must be unique. Maximum length of 32 characters. |
| **5419** | BasketID | CR | Unique BasketID assigned by Bloomberg which is given to a basket order when the first order is added using BasketName.<br><br>**📝 Note:**<br>To add subsequent orders to existing baskets, clients must pass a unique BasketID returned by Bloomberg when the first order is added in Basket.<br><br>Basket ID to be provided in numerical values only. |
| **9896** | PricingNo | R | Bloomberg OMS Pricing Number (PX). This is the main client identifier. All processing is done within a context of a pricing number. |
| **68** | TotNoOrder | R | Total number of orders in the list. Up to 1,000 orders per basket for specific Asset Classes*. Refer to Appendix. |
| **893** | LastFragment | O | Indicates whether this is the last fragment in a sequence of message fragments. Only required when the message has been fragmented. |
| **21053** | TSOpenNoControlFlags | O | Total number of controls data sent in group. |
| **> 21054** | TSOpenControlFlagName | CR | Control Flag Name. For supported values see Appendices (Control Flow Flags and Values).<br>LIST_PROCESSING_LEVEL flag allows processing each order individually or as a basket (Message Type E). |
| **> 21055** | TSOpenControlFlagValue | CR | Specifies flag values. For LIST_PROCESSING_LEVEL:<br>**ORDER** – process individually (default).<br>**LIST** – process as a basket. |
| **9998** | UUID | R | UUID of user submitting this message. Used for auditing and found via `IAM <GO>` in Bloomberg Terminal. |
| **73** | NoOrders | R | Total number of orders in the list – up to 1,000. See *List Orders: Maximum Size*. |
| **> 11** | ClOrdID | O | First field in repeating group. Unique order identifier assigned by institution. (Max 30 chars.) |
| **> 54** | Side | R | **1 = Buy**, **2 = Sell**<br>Other values support cover/short scenarios using FIX Tags 77, 233, and 234. |
| **> 77** | PositionEffect | CR | Additional identifier for Buy-cover transaction.<br>**Valid value:**<br>• C = Close |
| **> 60** | TransactTime | R | Order creation time (AIM perspective) / execution time (FIX perspective). Expressed in UTC. |
| **> > 55** | Symbol | CR | Required if SecurityID (48) not present. Identifies security for staging and loading.<br><br>**📝 Note:**<br>FixedIncomeFlag (9894) must be provided if BLPYellowKey value is not supplied in this tag. |
| **> > 48** | SecurityID | CR | CUSIP, ISIN, or BBID of security traded. “When Issued” securities require Bloomberg ID (BBID). One of Symbol (55) or SecurityID (48) + SecurityIDSource (22) must be present. |
| **> > 22** | SecurityIDSource | CR | Identifies type of SecurityID.<br>**Valid values:**<br>• UNKNOWN<br>• 1 = CUSIP<br>• 2 = SEDOL1<br>• 4 = ISIN<br>• A = BLOOMBERG_SYMBOL<br>**Bloomberg-defined codes:**<br>• 103 = SEDOL2<br>• 111 = BLOOMBERG_UNIQUE_ID<br>• 112 = FIGI |
| **> > 207** | SecurityExchange | CR | Exchange code (for ISIN, CUSIP, SEDOL, Bloomberg Unique ID). Used for EMSX order creation. |
| **699** | BenchmarkSecurityID | O | Identifier of benchmark security (e.g. treasury vs corporate bond). |
| **761** | BenchmarkSecurityIDSource | CR | Source of BenchmarkSecurityID. Required if BenchmarkSecurityID present.<br>**Valid values:**<br>1 = CUSIP<br>2 = SEDOL1<br>4 = ISIN<br>A = BLOOMBERG_SYMBOL<br>**Bloomberg codes:**<br>111 = BLOOMBERG_UNIQUE_ID<br>S = FIGI |
| **423** | PriceType | O | Required when price (44) is yield, discount, or spread.<br>**Valid values:**<br>1 = Percentage<br>4 = Discount<br>6 = Spread<br>9 = Yield<br><br>**📝 Note:**<br>Not supported for swap orders (e.g., CDS Spread/Price cannot be overwritten from an ‘E’ message). |
| **> 453** | NoPartyIDs | O | Number of PartyID, PartyIDSource, and PartyRole. |
| **> > 448** | PartyID | CR | Identifier/code for each NoPartyID. Eligible platforms include MarketAxess, TradeWeb, FXGO, FXALL, and others.<br>**Valid values:**<br>1–23 covering major execution venues (see original doc for mapping). |
| **> > 447** | PartyIDSource | CR | Identifies class or source of PartyID. |
| **> > 452** | PartyRole | CR | Identifies type/role of PartyID.<br>**Valid values:**<br>1 = EXECUTING FIRM<br>2 = BROKER_OF_CREDIT<br>10 = SETTLEMENT LOCATION<br>102 = TRADERUUID<br>108 = TRADING_DESK<br>110 = PORTFOLIO_MANAGER<br>112 = EXECUTION_TARGET |
| **> 40** | OrdType | R | **Valid values:**<br>1 = MARKET<br>2 = LIMIT<br>3 = STOP<br>4 = STOP_LIMIT<br>5 = MARKET_ON_CLOSE |
| **> 120** | SettlCurrency | O | Currency code to settle trade (ISO code). |
| **> 155** | SettlCurrFxRate | CR | FX rate between default account currency and trade currency (FIX 120 / SettlCurrency). Optional if SettlCurrency provided. |
| **> 9894** | FixedIncomeFlag | CR | Specifies type of asset.<br>**Valid values:**<br>1 = Comdty<br>2 = Equity<br>3 = Muni<br>4 = Pfd<br>5 = Mmkt<br>6 = Govt<br>8 = Corp<br>9 = Index<br>10 = Curncy<br>11 = Mtge<br><br>**📝 Note:**<br>If Symbol (55) or SecurityID (48) cannot uniquely identify the security, FixedIncomeFlag (9894) must be provided.<br>FX Spot/Forward Baskets not supported. |
| **854** | QtyType | O | Quantity type.<br>**Valid values:**<br>0 = Units (Shares, par, currency)<br>1 = Contracts |
| **> > 38** | OrderQty | R | Quantity ordered (shares, face, or nominal). |
| **> 232** | NoStipulations | O | Number of stipulation types. |
| **> > 233** | StipulationType | CR | Defines stipulation types (e.g., PURPOSE, STRATEGY, USE_CASH_AT_SETTLEMENT_ONLY, AIM_TRANSACTION_CODE). |
| **> > 234** | StipulationValue | CR | Value for given stipulation type.<br>Examples:<br>A = Active<br>C = Cover<br>H = Hedge<br>USE_CASH_AT_SETTLEMENT_ONLY = true/false<br>NEAR/FAR for LEG_TYPE |
| **591** | PreAllocMethod | O | Defines preallocation method (e.g., user-specified quantity or equal split). |
| **> 78** | NoAllocs | CR | Number of pre-trade allocation repeating groups (up to 400). |
| **> > 79** | AllocAccount | CR | First field in repeating group; identifies account, group, or allocation method. |
| **> > 661** | AllocAcctIDSource | O | Type of allocation account ID.<br>**Valid values:**<br>100 = AccountType<br>101 = AccountGroupType<br>102 = AllocationMethodType |
| **> 539** | NoNestedPartyIDs | CR | Required if nested parties exist. |
| **> > 524** | NestedPartyID | R | Identifier or name of nested party. |
| **> > 538** | NestedPartyRole | R | Role of nested party (Clearing Broker, Prime Broker, Strategy, Decision Maker). |
| **> > 80** | AllocQty | CR | Allocation quantity (percent or unit). |
| **44** | Price | O | Unit price or all-in rate for FX securities. |
| **64** | SettlDate | CR | Settlement date for the transaction. |
| **9610** | NoNotes | O | Total number of notes sent in group. |
| **> 9611** | NoteType | CR | Type of note (LONG or SHORT). Notes customizable in `CUTS <GO>`. |
| **> 9612** | NoteId | CR | Represents which note field is being sent (1–8 for SHORT or LONG). |
| **> 9613** | NoteText | CR | Note text data.<br>Short note = 12 chars, Long note = 45 chars. |
| **75** | TradeDate | O | Date of trade execution. |
| **59** | TimeInForce | O | Specifies order duration.<br>**Valid values:**<br>0 = DAY<br>1 = GOOD_TILL_CANCEL<br>2 = AT_THE_OPENING<br>3 = IMMEDIATE_OR_CANCEL<br>4 = FILL_OR_KILL<br>6 = GOOD_TILL_DATE<br>7 = AT_THE_CLOSE |
| **432** | ExpireDate | CR | Required if TimeInForce = GOOD_TILL_DATE (format YYYY:MM:DD). |
| **126** | ExpireTime | CR | Required if TimeInForce = GOOD_TILL_DATE (format YYYY:MM:DD-HH:MM:SS). |
| **58** | Text | O | Freeform text string (up to 44 characters). Used for AIM Instructions. |
| **10** | Checksum | R | Integer checksum for message. |
