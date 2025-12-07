"""
Compliance Module

Reads compliance details from Bloomberg AIM XML responses and structures them
into Python objects for easy processing.
"""

from collections import namedtuple
import json
import logging
import lxml.etree as ET

from .enums import ComplianceStatus  # Import from enums.py instead of base

logger = logging.getLogger(__name__)


class ComplianceViolation:
    """
    Represents a single compliance violation.
    
    Attributes:
        account_name: Name of the account with violation
        severity: Severity level of the violation
        rule_name: Name of the compliance rule violated
        violation_type: Type of violation (default: 'UNKNOWN')
        restricted_broker: Broker that is restricted (if applicable)
    """
    
    def __init__(self,
                 account_name: str,
                 severity: str,
                 rule_name: str,
                 violation_type: str = 'UNKNOWN',
                 restricted_broker: str = None):
        self.account_name = account_name
        self.severity = severity
        self.rule_name = rule_name
        self.violation_type = violation_type
        self.restricted_broker = restricted_broker

    def __repr__(self):
        s = [f'{k}:{v}' for k, v in self.__dict__.items()]
        return 'VIOLATION_DETAILS: ' + ' | '.join(s)
    
    def to_dict(self):
        """Convert violation to dictionary"""
        return self.__dict__


class ComplianceResponse:
    """
    Represents the overall compliance response from Bloomberg.
    
    Attributes:
        compliance_status: Overall compliance status (ComplianceStatus enum)
        compliance_violations: List of ComplianceViolation objects
    """
    
    def __init__(self,
                 compliance_status: ComplianceStatus,
                 compliance_violations: list = None):
        if compliance_violations is None:
            compliance_violations = []
            
        if compliance_violations:
            assert all(isinstance(x, ComplianceViolation) for x in compliance_violations), \
                f'Only ComplianceViolations are accepted in {self.__class__.__name__}'
                
        self.compliance_status = compliance_status
        self.compliance_violations = compliance_violations

    def __repr__(self):
        details = [str(v) for v in self.compliance_violations]
        details_str = f" || {details}" if len(self.compliance_violations) > 0 else ""
        return (f'Compliance Status = {self.compliance_status.name} || '
                f'Num Violations {len(self.compliance_violations)}{details_str}')
    
    def to_dict(self):
        """Convert compliance response to dictionary"""
        return {
            'Status': self.compliance_status.name if self.compliance_status else 'NONE',
            'NumViolations': len(self.compliance_violations),
            'Violation Details': [obj.to_dict() for obj in self.compliance_violations]
        }
    
    def get_structured_summary(self):
        """
        Get a structured summary of the compliance response for easier processing.
    
        Returns:
            dict: Structured compliance information with the following keys:
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


def get_compliance_response_new_version(xml_obj: ET.Element) -> ComplianceResponse:
    """
    Parse compliance response from Bloomberg AIM XML (new version format).
    
    This is the current/recommended version for parsing compliance responses.
    
    Args:
        xml_obj: lxml Element containing the XML response
        
    Returns:
        ComplianceResponse object with parsed compliance data
        
    Raises:
        AssertionError: If xml_obj doesn't have iter method
    """
    assert hasattr(xml_obj, 'iter'), 'xml object with iter method should be passed to this function'
    
    # Find control flags section
    control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
    if len(control_flags_group_elements) == 0:
        return ComplianceResponse(
            compliance_status=ComplianceStatus(None),
            compliance_violations=[]
        )

    control_flags_elements = control_flags_group_elements.pop().getchildren()
    compliance_violations = []
    compliance_status = None
    
    # Parse each control flag
    for el in control_flags_elements:
        flag_name = el.find('TSOpenControlFlagName').text
        flag_value = el.find('TSOpenControlFlagValue').text
        
        if flag_name == 'COMPLIANCE_STATUS':
            compliance_status = flag_value
            
        if flag_name == 'COMPLIANCE_VIOLATION_DETAIL':
            try:
                # Parse violation XML
                compliance_violation_obj = ET.fromstring(flag_value.encode('utf8'))
                ET.indent(compliance_violation_obj, space="   ")
                xml_string = ET.tostring(compliance_violation_obj, pretty_print=True, 
                                        encoding='utf8').decode('utf8')
                logger.debug(f'Compliance Violation XML Raw\n{xml_string}')
                
                # Extract account violations
                account_violation_groups = compliance_violation_obj.iter('AccountDet')
                for account_el in account_violation_groups:
                    account_name = account_el.attrib['AccountName']
                    violation_elements = account_el.iter('Rule')
                    
                    for vio_el in violation_elements:
                        severity = vio_el.find('Severity').text
                        rule_name = vio_el.find('RuleName').text
                        compliance_violations.append(
                            ComplianceViolation(
                                account_name=account_name,
                                severity=severity,
                                rule_name=rule_name
                            )
                        )
            except Exception as e:
                logger.warning(f'Error parsing the compliance violation details. {e}')
                compliance_violations = [
                    ComplianceViolation(
                        account_name='UNKNOWN',
                        severity='UNKNOWN',
                        rule_name='Error Parsing the compliance details'
                    )
                ]
            
    return ComplianceResponse(
        compliance_status=ComplianceStatus(compliance_status),
        compliance_violations=compliance_violations
    )


def get_compliance_response_old_version(xml_obj: ET.Element) -> ComplianceResponse:
    """
    Parse compliance response from Bloomberg AIM XML (old version format).
    
    This is maintained for backward compatibility with older XML formats.
    Use get_compliance_response_new_version() for new implementations.
    
    Args:
        xml_obj: lxml Element containing the XML response
        
    Returns:
        ComplianceResponse object with parsed compliance data
        
    Raises:
        AssertionError: If xml_obj doesn't have iter method
    """
    assert hasattr(xml_obj, 'iter'), 'xml object with iter method should be passed to this function'
    
    control_flags_group_elements = [*xml_obj.iter('TSOpenNoControlFlags')]
    if len(control_flags_group_elements) == 0:
        return ComplianceResponse(
            compliance_status=ComplianceStatus(None),
            compliance_violations=[]
        )
    
    control_flags_elements = control_flags_group_elements.pop().getchildren()
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
                logger.debug(f'Compliance Violation Details')
                logger.debug(f'''
{ET.tostring(compliance_violation_obj, pretty_print=True, encoding='utf8').decode('utf8')}
                ''')
                
                violation_elements = compliance_violation_obj.findall('violation')

                for vio_el in violation_elements:
                    vio_el_details = vio_el.attrib
                    severity = vio_el_details.get('Severity', None)
                    rule_name = vio_el_details.get('Rulelong', None)
                    
                    compliance_violations.append(
                        ComplianceViolation(
                            account_name='UNKNOWN',  # Old format doesn't have account info
                            severity=severity,
                            rule_name=rule_name
                        )
                    )
            except Exception as e:
                logger.warning(f'Error parsing the compliance violation details. {e}')
                compliance_violations = [
                    ComplianceViolation(
                        account_name='UNKNOWN',
                        severity='UNKNOWN',
                        rule_name='Error Parsing the compliance details'
                    )
                ]
            
    return ComplianceResponse(
        compliance_status=ComplianceStatus(compliance_status),
        compliance_violations=compliance_violations
    )