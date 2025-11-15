'Module to read compliance details from XML response'
from collections import namedtuple
import json
import lxml.etree as ET
import os
import logging
from base import *

logger = logging.getLogger(__name__)

class ComplianceViolation:
    def __init__(self,
                 account_name: str,
                 severity: str,
                 rule_name : str,
                 violation_type: str = 'UNKNOWN',
                 restricted_broker: str = None):
        self.account_name = account_name
        self.severity = severity
        self.rule_name = rule_name
        self.violation_type = violation_type
        self.restricted_broker = restricted_broker

    def __repr__(self):
        s = []
        for k,v in self.__dict__.items():
            s.append(f'{k}:{v}')
        return 'VIOLATION_DETAILS: ' + ' | '.join(s)
    
    def to_dict(self):
        return self.__dict__

# class ComplianceViolationPreJune2024(ComplianceViolation):
#     def __init__(self,
#                  compliance_status: ComplianceStatus,
#                  compliance_violation : None | ComplianceViolation = None):
#         self.compliance_status = compliance_status
#         self.compliance_violation = compliance_violation

#     def __repr__(self):
#         s = []
#         for k,v in self.__dict__.items():
#             s.append(f'{k}:{v}')
#         return f'Compliance Status: {self.compliance_status.name} | '
    
#     def to_dict(self):
#         return {'Status':self.compliance_status,'Violation Details': self.compliance_violation.to_dict()}

class ComplianceResponse:
    def __init__(self,
                 compliance_status: ComplianceStatus,
                 compliance_violations : list = []):
        if compliance_violations:
            assert all(map(lambda x: isinstance(x,ComplianceViolation),compliance_violations)), f'Only ComplianceViolations are accepted in {self.__class__.__name__}'
        self.compliance_status = compliance_status
        self.compliance_violations = compliance_violations

    def __repr__(self):
        details = [str(v) for v in self.compliance_violations]
        details_str = f" || {details}" if len(self.compliance_violations)>0 else ""
        return f'Compliance Status = {self.compliance_status.name} || Num Violations {len(self.compliance_violations)}{details_str}'
    
    def to_dict(self):
        return {'Status':self.compliance_status,
                'NumViolations':len(self.compliance_violations),
                'Violation Details': [obj.to_dict() for obj in self.compliance_violation.to_dict()]}
    
    def get_structured_summary(self):
        """
        Get a structured summary of the compliance response for easier processing.
    
        Returns:
        --------
        dict
            Structured compliance information with the following keys:
            - status: 'PASSED', 'REJECTED', 'WARNING', etc.
            - passed: boolean indicating if compliance passed
            - violations: list of violation details
            - broker_restrictions: dict mapping account -> list of restricted brokers
            - violations_by_type: dict grouping violations by type
        """
        # Initialize result structure
        result = {
            'status': self.compliance_status.name if self.compliance_status else 'UNKNOWN',
            'passed': False,
            'violations': [],
            'broker_restrictions': {},
            'violations_by_type': {
                'BROKER_RESTRICTION': [],
                'POSITION_LIMIT': [],
                'EXPOSURE_LIMIT': [],
                'CONCENTRATION_LIMIT': [],
                'LIQUIDITY_RESTRICTION': [],
                'RATING_RESTRICTION': [],
                'OTHER': []
            }
        }
    
        # Determine if compliance passed
        if self.compliance_status:
            result['passed'] = self.compliance_status.name in [
                'COMPLIANCE_PASSED',
                'COMPLIANCE_BYPASSED_BY_USER',
                'COMPLIANCE_BYPASSED_BY_CONFIGURATION'
            ]
    
        # Process each violation
        for violation in self.compliance_violations:
            violation_dict = violation.to_dict()
            result['violations'].append(violation_dict)
        
            # Categorize by type
            violation_type = violation_dict.get('violation_type', 'OTHER')
            if violation_type in result['violations_by_type']:
                result['violations_by_type'][violation_type].append(violation_dict)
            else:
                result['violations_by_type']['OTHER'].append(violation_dict)
        
            # Track broker restrictions
            if violation.violation_type == 'BROKER_RESTRICTION' and violation.restricted_broker:
                account = violation.account_name
                broker = violation.restricted_broker
            
                if account not in result['broker_restrictions']:
                    result['broker_restrictions'][account] = []
                if broker not in result['broker_restrictions'][account]:
                    result['broker_restrictions'][account].append(broker)
    
        return result
    
    

def get_compliance_response_new_version(xml_obj: ET.Element)->ComplianceResponse:
    assert hasattr(xml_obj,'iter'), 'xml object with iter method should be passed to this function'
    
    control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
    if len(control_flags_group_elements) == 0:
        return ComplianceResponse(compliance_status=ComplianceStatus(None),
                                  compliance_violations=[])

    control_flags_elements = control_flags_group_elements.pop().getchildren()
    # assert len(control_flags_elements)>=2, 'There should be at least 2 elements in the control flags element of XML'
    compliance_violations = []
    compliance_status = None
    
    for el in control_flags_elements:
        flag_name = el.find('TSOpenControlFlagName').text
        flag_value = el.find('TSOpenControlFlagValue').text
        if flag_name == 'COMPLIANCE_STATUS':
            compliance_status = flag_value
        if flag_name == 'COMPLIANCE_VIOLATION_DETAIL':
            try:
                compliance_violation_obj = ET.fromstring(flag_value.encode('utf8'))
                ET.indent(compliance_violation_obj,space="   ")
                xml_string = ET.tostring(compliance_violation_obj,pretty_print=True,encoding='utf8').decode('utf8')
                logger.debug(f'Compliance Violation XML Raw')
                logger.debug(f'''
{xml_string}
                             ''')
                
                account_violation_groups = compliance_violation_obj.iter('AccountDet')
                for account_el in account_violation_groups:
                    account_name = account_el.attrib['AccountName']
                    violation_elements = account_el.iter('Rule')
                    for vio_el in violation_elements:
                        severity = vio_el.find('Severity').text
                        rule_name = vio_el.find('RuleName').text
                        compliance_violations.append(ComplianceViolation(account_name=account_name,
                                                                         severity=severity,
                                                                         rule_name=rule_name))
            except Exception as e:
                logger.warning(f'Error parsing the complaince violation details. {e}')
                compliance_violations = [ComplianceViolation(severity='UNKNOWN',rule_name='Error Parsing the complaince details')]
            
    return ComplianceResponse(compliance_status=ComplianceStatus(compliance_status),
                                  compliance_violations=compliance_violations)





# def get_compliance_response_old_version(xml_obj: ET.Element)->ComplianceResponse:
#     assert hasattr(xml_obj,'iter'), 'xml object with iter method should be passed to this function'
    
#     control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
#     if len(control_flags_group_elements) == 0:
#         return ComplianceResponse(compliance_status=ComplianceStatus(None),
#                                   compliance_violations=[])
    

#     # Get account information from PreAllocGrp section
#     account_names = []
#     alloc_accounts = xml_obj.findall('.//AllocAccount')
#     for alloc_account in alloc_accounts:
#         if alloc_account.text:
#             account_names.append(alloc_account.text)
    
#     # If no accounts found in PreAllocGrp, try to get from other locations
#     if not account_names:
#         # Could also check for single account scenarios or other structures
#         account_names = ['UNKNOWN_ACCOUNT']


#     control_flags_elements = control_flags_group_elements.pop().getchildren()
#     # assert len(control_flags_elements)>=2, 'There should be at least 2 elements in the control flags element of XML'
#     compliance_violations = []
#     compliance_status = None
    
#     for el in control_flags_elements:
#         flag_name = el.find('TSOpenControlFlagName').text
#         flag_value = el.find('TSOpenControlFlagValue').text
#         print(flag_name, flag_value)
#         if flag_name == 'COMPLIANCE_STATUS':
#             compliance_status = flag_value
#         if flag_name == 'COMPLIANCE_VIOLATION_DETAIL':
#             try:
#                 compliance_violation_obj = ET.fromstring(flag_value.encode('utf8'))
#                 logger.debug(f'Compliance Violation Details')
#                 logger.debug(f'''
                             
#     {ET.tostring(compliance_violation_obj,pretty_print=True,encoding='utf8').decode('utf8')}
                             
#                              ''')
#                 violation_elements = compliance_violation_obj.findall('violation')

#                 for vio_el in violation_elements:
#                     vio_el_details = vio_el.attrib
#                     severity = vio_el_details.get('Severity',None)
#                     rule_name = vio_el_details.get('Rulelong',None)

#                     # Use the first account name, or cycle through them if multiple
#                     # You might need to adjust this logic based on your specific requirements
#                     account_name = account_names[0] if account_names else 'UNKNOWN_ACCOUNT'

#                     compliance_violations.append(ComplianceViolation(
#                         account_name=account_name,
#                         severity=severity,
#                         rule_name=rule_name
#                     ))
#             except Exception as e:
#                 logger.warning(f'Error parsing the complaince violation details. {e}')
#                 # Use the first account name from the allocation section
#                 account_name = account_names[0] if account_names else 'UNKNOWN_ACCOUNT'
#                 compliance_violations = [
#                     ComplianceViolation(
#                         account_name=account_name,
#                         severity='UNKNOWN',
#                         rule_name='Error Parsing the compliance details'
#                     )
#                 ]
            
#     return ComplianceResponse(compliance_status=ComplianceStatus(compliance_status),
#                                   compliance_violations=compliance_violations)


# def get_compliance_response_old_version(xml_obj: ET.Element)->ComplianceResponse:
#     assert hasattr(xml_obj,'iter'), 'xml object with iter method should be passed to this function'
    
#     # DEBUG: Print the entire XML structure
#     print("=== FULL XML RESPONSE ===")
#     if hasattr(xml_obj, 'tag'):
#         xml_string = ET.tostring(xml_obj, pretty_print=True, encoding='utf8').decode('utf8')
#         print(xml_string)
#     print("========================")
    
#     control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
#     if len(control_flags_group_elements) == 0:
#         print("DEBUG: No control flags found in XML")
#         return ComplianceResponse(compliance_status=ComplianceStatus(None),
#                                   compliance_violations=[])
    
#     # DEBUG: Check for account information in various locations
#     print("\n=== DEBUGGING ACCOUNT SEARCH ===")
    
#     # Method 1: Look for AllocAccount elements anywhere in the XML
#     alloc_accounts = xml_obj.findall('.//AllocAccount')
#     print(f"Method 1 - Found AllocAccount elements: {len(alloc_accounts)}")
#     for i, acc in enumerate(alloc_accounts):
#         print(f"  AllocAccount[{i}]: {acc.text}")
    
#     # Method 2: Look specifically in PreAllocGrp section
#     prealloc_groups = xml_obj.findall('.//PreAllocGrp')
#     print(f"Method 2 - Found PreAllocGrp elements: {len(prealloc_groups)}")
#     for i, group in enumerate(prealloc_groups):
#         print(f"  PreAllocGrp[{i}] contents:")
#         for child in group:
#             print(f"    {child.tag}: {child.text if child.text else 'No text'}")
#             for grandchild in child:
#                 print(f"      {grandchild.tag}: {grandchild.text if grandchild.text else 'No text'}")
    
#     # Method 3: Look for NoAllocs sections
#     no_allocs = xml_obj.findall('.//NoAllocs')
#     print(f"Method 3 - Found NoAllocs elements: {len(no_allocs)}")
#     for i, allocs in enumerate(no_allocs):
#         print(f"  NoAllocs[{i}] count: {allocs.get('count', 'No count')}")
#         for child in allocs:
#             print(f"    {child.tag}: {child.text if child.text else 'No text'}")
    
#     # Method 4: Look for any element with 'Alloc' in the name
#     all_alloc_elements = [elem for elem in xml_obj.iter() if 'Alloc' in elem.tag]
#     print(f"Method 4 - Found elements with 'Alloc' in tag: {len(all_alloc_elements)}")
#     for elem in all_alloc_elements:
#         print(f"  {elem.tag}: {elem.text if elem.text else 'No text'}")
#         if elem.attrib:
#             print(f"    Attributes: {elem.attrib}")
    
#     # Method 5: Check if it's in the original request structure (shouldn't be in response, but let's check)
#     print("\n=== CHECKING FOR OTHER ACCOUNT INDICATORS ===")
    
#     # Look for Account in any form
#     account_elements = [elem for elem in xml_obj.iter() if 'Account' in elem.tag]
#     print(f"Found elements with 'Account' in tag: {len(account_elements)}")
#     for elem in account_elements:
#         print(f"  {elem.tag}: {elem.text if elem.text else 'No text'}")
    
#     # Look for Party information (might contain broker/account info)
#     party_elements = xml_obj.findall('.//NoPartyIDs')
#     print(f"Found NoPartyIDs elements: {len(party_elements)}")
#     for party_group in party_elements:
#         print(f"  PartyIDs count: {party_group.get('count', 'No count')}")
#         for child in party_group:
#             print(f"    {child.tag}: {child.text if child.text else 'No text'}")
    
#     print("================================\n")
    
#     # Try to extract account names using multiple methods
#     account_names = []
    
#     # Try method 1: Direct AllocAccount search
#     for alloc_account in alloc_accounts:
#         if alloc_account.text:
#             account_names.append(alloc_account.text)
    
#     # If no accounts found, try looking in different places
#     if not account_names:
#         print("DEBUG: No accounts found via AllocAccount, trying alternative methods...")
        
#         # Try looking in the original order structure (though this might not be in response)
#         # Sometimes the response might echo back some original order info
#         clord_id = xml_obj.find('.//ClOrdID')
#         if clord_id is not None:
#             print(f"DEBUG: Found ClOrdID: {clord_id.text}")
        
#         # Check for any text that might be an account identifier
#         # This is a more desperate measure
#         all_text_elements = [elem for elem in xml_obj.iter() if elem.text and len(elem.text.strip()) > 0]
#         print("DEBUG: All text elements in XML:")
#         for elem in all_text_elements:
#             print(f"  {elem.tag}: '{elem.text.strip()}'")
    
#     print(f"DEBUG: Final account_names list: {account_names}")
    
#     # If still no accounts, use fallback
#     if not account_names:
#         account_names = ['UNKNOWN_ACCOUNT']
#         print("DEBUG: Using fallback account name")
    
#     control_flags_elements = control_flags_group_elements.pop().getchildren()
#     compliance_violations = []
#     compliance_status = None
    
#     for el in control_flags_elements:
#         flag_name = el.find('TSOpenControlFlagName').text
#         flag_value = el.find('TSOpenControlFlagValue').text
#         print(f"DEBUG: Processing flag - {flag_name}: {flag_value}")
        
#         if flag_name == 'COMPLIANCE_STATUS':
#             compliance_status = flag_value
#         if flag_name == 'COMPLIANCE_VIOLATION_DETAIL':
#             try:
#                 compliance_violation_obj = ET.fromstring(flag_value.encode('utf8'))
#                 logger.debug(f'Compliance Violation Details')
#                 violation_xml_str = ET.tostring(compliance_violation_obj,pretty_print=True,encoding='utf8').decode('utf8')
#                 print(f"DEBUG: Compliance violation XML structure:\n{violation_xml_str}")
                
#                 violation_elements = compliance_violation_obj.findall('violation')
#                 print(f"DEBUG: Found {len(violation_elements)} violation elements")

#                 for i, vio_el in enumerate(violation_elements):
#                     vio_el_details = vio_el.attrib
#                     print(f"DEBUG: Violation {i} attributes: {vio_el_details}")
#                     severity = vio_el_details.get('Severity', None)
#                     rule_name = vio_el_details.get('Rulelong', None)
                    
#                     # Use the first account name
#                     account_name = account_names[0] if account_names else 'UNKNOWN_ACCOUNT'
#                     print(f"DEBUG: Creating violation for account: {account_name}")
                    
#                     compliance_violations.append(ComplianceViolation(
#                         account_name=account_name,
#                         severity=severity,
#                         rule_name=rule_name
#                     ))
#             except Exception as e:
#                 logger.warning(f'Error parsing the compliance violation details. {e}')
#                 print(f"DEBUG: Exception during violation parsing: {e}")
#                 account_name = account_names[0] if account_names else 'UNKNOWN_ACCOUNT'
#                 compliance_violations = [
#                     ComplianceViolation(
#                         account_name=account_name,
#                         severity='UNKNOWN',
#                         rule_name='Error Parsing the compliance details'
#                     )
#                 ]
    
#     print(f"DEBUG: Final compliance_status: {compliance_status}")
#     print(f"DEBUG: Final compliance_violations count: {len(compliance_violations)}")
    
#     return ComplianceResponse(compliance_status=ComplianceStatus(compliance_status),
#                               compliance_violations=compliance_violations)




def get_compliance_response_old_version(xml_obj: ET.Element)->ComplianceResponse:
    assert hasattr(xml_obj,'iter'), 'xml object with iter method should be passed to this function'
    
    control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
    if len(control_flags_group_elements) == 0:
        return ComplianceResponse(compliance_status=ComplianceStatus(None),
                                  compliance_violations=[])
    
    control_flags_elements = control_flags_group_elements.pop().getchildren()
    compliance_violations = []
    compliance_status = None
    
    for el in control_flags_elements:
        flag_name = el.find('TSOpenControlFlagName').text
        flag_value = el.find('TSOpenControlFlagValue').text
        
        if flag_name == 'COMPLIANCE_STATUS':
            compliance_status = flag_value
        if flag_name == 'COMPLIANCE_VIOLATION_DETAIL':
            print(flag_name, flag_value)
            try:
                compliance_violation_obj = ET.fromstring(flag_value.encode('utf8'))
                logger.debug(f'Compliance Violation Details')
                logger.debug(f'''
                             
    {ET.tostring(compliance_violation_obj,pretty_print=True,encoding='utf8').decode('utf8')}
                             
                             ''')
                violation_elements = compliance_violation_obj.findall('violation')

                for vio_el in violation_elements:
                    vio_el_details = vio_el.attrib
                    severity = vio_el_details.get('Severity', None)
                    #rule_name = vio_el_details.get('Ruleshort', None)
                    rule_name = vio_el_details.get('Rulelong', None)
                    
                    # Extract the account name from the violation attributes
                    # The account is stored as 'Violator' in the violation attributes
                    account_name = vio_el_details.get('Violator', 'UNKNOWN_ACCOUNT')
                    
                    # Categorize the violation
                    violation_type, restricted_broker = categorize_violation(rule_name, account_name)
                    
                    compliance_violations.append(ComplianceViolation(
                        account_name=account_name,
                        severity=severity,
                        rule_name=rule_name,
                        violation_type=violation_type,
                        restricted_broker=restricted_broker
                    ))
            except Exception as e:
                logger.warning(f'Error parsing the compliance violation details. {e}')
                compliance_violations = [
                    ComplianceViolation(
                        account_name='UNKNOWN_ACCOUNT',
                        severity='UNKNOWN',
                        rule_name='Error Parsing the compliance details'
                    )
                ]
            
    return ComplianceResponse(compliance_status=ComplianceStatus(compliance_status),
                              compliance_violations=compliance_violations)



BROKER_COMPLIANCE_RULES = [
    'XBARX',
    'XBB',
    'XGS',
    'XBMO',
    'XBNP',
]

def categorize_violation(rule_name: str, account_name: str) -> tuple:
    """
    Categorize a compliance violation based on the rule name.
   
    Parameters:
    -----------
    rule_name : str
        The compliance rule name
    account_name : str
        The account name involved in the violation
       
    Returns:
    --------
    tuple
        (violation_type, restricted_broker) where:
        - violation_type: str categorizing the violation
        - restricted_broker: str or None if not a broker restriction
    """
    if not rule_name:
        return 'UNKNOWN', None
   
    rule_name_lower = rule_name.lower()
   
    # Broker restriction patterns
    #if 'broker' in rule_name_lower and 'restrict' in rule_name_lower:
    if rule_name in BROKER_COMPLIANCE_RULES:
        # Try to extract broker name
        # Handle formats like "Restricted Broker CITI" or "Broker Restriction: BARX"
        restricted_broker = None
       
        if 'Restricted Broker' in rule_name:
            restricted_broker = rule_name.split('Restricted Broker')[-1].strip()
        elif 'Broker Restriction:' in rule_name:
            restricted_broker = rule_name.split('Broker Restriction:')[-1].strip()
        elif 'restricted' in rule_name_lower:
            # Try to find the broker name in the rule
            # This is a more generic approach
            words = rule_name.split()
            broker_keywords = ['CITI', 'BARX', 'BB', 'GS', 'MS', 'JPM', 'BAML', 'UBS', 'DB', 'CS']
            for word in words:
                if word.upper() in broker_keywords:
                    restricted_broker = word.upper()
                    break
        elif rule_name in BROKER_COMPLIANCE_RULES:
            restricted_broker = rule_name[1:]
       
        return 'BROKER_RESTRICTION', restricted_broker
   
    # Position limit patterns
    elif any(keyword in rule_name_lower for keyword in ['position limit', 'max position', 'position size']):
        return 'POSITION_LIMIT', None
   
    # Exposure limit patterns
    elif any(keyword in rule_name_lower for keyword in ['exposure', 'max exposure', 'sector exposure']):
        return 'EXPOSURE_LIMIT', None
   
    # Concentration limit patterns
    elif any(keyword in rule_name_lower for keyword in ['concentration', 'issuer concentration', 'single name']):
        return 'CONCENTRATION_LIMIT', None
   
    # Liquidity patterns
    elif any(keyword in rule_name_lower for keyword in ['liquidity', 'liquid', 'illiquid']):
        return 'LIQUIDITY_RESTRICTION', None
   
    # Rating patterns
    elif any(keyword in rule_name_lower for keyword in ['rating', 'credit rating', 'investment grade']):
        return 'RATING_RESTRICTION', None
   
    # Default case
    else:
        return 'OTHER', None