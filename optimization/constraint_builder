from typing import Dict, List, Any, Optional

class ReplacementConstraintBuilder:
    """Converts replacement mappings to optimizer constraints."""
    
    @staticmethod
    def create_constraints(replacements: Dict[str, Dict], 
                         tolerance: float = 0.0005,
                         use_percentage: bool = True) -> List[Dict[str, Any]]:
        """
        Generate API constraints from replacement mappings.
        
        Args:
            replacements: Output from SecurityReplacementMatcher.find_replacement_securities()
            tolerance: Small tolerance around target weights to allow optimizer flexibility
            use_percentage: If True, weights are in percentage; if False, in decimal
            
        Returns:
            List of constraint dictionaries for the optimizer API
        """
        constraints = []
        
        for restricted_security, replacement_info in replacements.items():
            replacement_security = replacement_info['replacement_security']
            
            # Convert weights to decimal if they're in percentage
            if use_percentage:
                restricted_weight = replacement_info['restricted_weight'] / 100
                replacement_weight = replacement_info['replacement_weight'] / 100
                combined_weight = replacement_info['combined_weight'] / 100
            else:
                restricted_weight = replacement_info['restricted_weight']
                replacement_weight = replacement_info['replacement_weight']
                combined_weight = replacement_info['combined_weight']
            
            # Create constraints
            restricted_constraint = ReplacementConstraintBuilder.create_zero_weight_constraint(
                restricted_security
            )
            replacement_constraint = ReplacementConstraintBuilder.create_target_weight_constraint(
                replacement_security, combined_weight, tolerance
            )
            
            constraints.extend([restricted_constraint, replacement_constraint])
        
        return constraints
    
    @staticmethod
    def create_zero_weight_constraint(security_id: str) -> Dict[str, Any]:
        """
        Create constraint to zero out a security.
        
        Args:
            security_id: Security identifier to restrict
            
        Returns:
            Constraint dictionary for optimizer API
        """
        return {
            "scope": {
                "instrumentUniqueId": security_id
            },
            "units": "PERCENT",
            "relativeTo": "NONE",
            "fields": [
                {
                    "fieldCode": "MAX_WEIGHT",
                    "valueOrField": {"value": 0.0}
                }
            ]
        }
    
    @staticmethod
    def create_target_weight_constraint(security_id: str, 
                                      target_weight: float,
                                      tolerance: float = 0.0001) -> Dict[str, Any]:
        """
        Create constraint to set a security to a target weight with tolerance.
        
        Args:
            security_id: Security identifier
            target_weight: Target weight in decimal format (e.g., 0.05 for 5%)
            tolerance: Allowed deviation from target weight
            
        Returns:
            Constraint dictionary for optimizer API
        """
        min_weight = max(0.0, target_weight - tolerance)
        max_weight = target_weight + tolerance
        
        return {
            "scope": {
                "instrumentUniqueId": security_id
            },
            "units": "PERCENT",
            "relativeTo": "NONE",
            "fields": [
                {
                    "fieldCode": "MIN_WEIGHT",
                    "valueOrField": {"value": min_weight}
                },
                {
                    "fieldCode": "MAX_WEIGHT",
                    "valueOrField": {"value": max_weight}
                }
            ]
        }
    
    @staticmethod
    def create_no_trade_constraint(security_id: str) -> Dict[str, Any]:
        """
        Create constraint to prevent trading a specific security.
        
        Args:
            security_id: Security identifier
            
        Returns:
            Constraint dictionary for optimizer API
        """
        return {
            "scope": {
                "instrumentUniqueId": security_id
            },
            "units": "POSITIONS",
            "relativeTo": "NONE",
            "fields": [
                {
                    "fieldCode": "MAX_TRADE",
                    "valueOrField": {"value": 0.0}
                },
                {
                    "fieldCode": "MIN_TRADE",
                    "valueOrField": {"value": 0.0}
                }
            ]
        }
    
    @staticmethod
    def create_benchmark_tracking_constraints(securities_to_track: List[str],
                                            benchmark_weights: Dict[str, float],
                                            tolerance: float = 0.0005) -> List[Dict[str, Any]]:
        """
        Create constraints to track benchmark weights for specified securities.
        
        Args:
            securities_to_track: List of security identifiers to track benchmark
            benchmark_weights: Dictionary mapping security_id -> benchmark weight (decimal)
            tolerance: Allowed deviation from benchmark weight
            
        Returns:
            List of constraint dictionaries for optimizer API
        """
        constraints = []
        
        for security_id in securities_to_track:
            if security_id in benchmark_weights:
                benchmark_weight = benchmark_weights[security_id]
                constraint = ReplacementConstraintBuilder.create_target_weight_constraint(
                    security_id, benchmark_weight, tolerance
                )
                constraints.append(constraint)
        
        return constraints
    
    @staticmethod
    def validate_constraints(constraints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate constraint structure and identify potential issues.
        
        Args:
            constraints: List of constraint dictionaries
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'statistics': {
                'total_constraints': len(constraints),
                'zero_weight_constraints': 0,
                'target_weight_constraints': 0,
                'no_trade_constraints': 0
            }
        }
        
        required_fields = ['scope', 'units', 'relativeTo', 'fields']
        
        for i, constraint in enumerate(constraints):
            # Check required fields
            missing_fields = [field for field in required_fields if field not in constraint]
            if missing_fields:
                validation_results['errors'].append(
                    f"Constraint {i}: Missing required fields: {missing_fields}"
                )
                validation_results['is_valid'] = False
            
            # Classify constraint type
            if 'fields' in constraint:
                for field in constraint['fields']:
                    field_code = field.get('fieldCode', '')
                    value = field.get('valueOrField', {}).get('value', None)
                    
                    if field_code == 'MAX_WEIGHT' and value == 0.0:
                        validation_results['statistics']['zero_weight_constraints'] += 1
                    elif field_code in ['MIN_WEIGHT', 'MAX_WEIGHT'] and value != 0.0:
                        validation_results['statistics']['target_weight_constraints'] += 1
                    elif field_code in ['MIN_TRADE', 'MAX_TRADE'] and value == 0.0:
                        validation_results['statistics']['no_trade_constraints'] += 1
            
            # Check for potential issues
            if constraint.get('units') == 'PERCENT':
                for field in constraint.get('fields', []):
                    value = field.get('valueOrField', {}).get('value', None)
                    if value is not None and (value < 0 or value > 1):
                        validation_results['warnings'].append(
                            f"Constraint {i}: Weight value {value} outside normal range [0,1]"
                        )
        
        return validation_results
    
    @staticmethod
    def merge_constraints(constraint_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Merge multiple constraint lists, removing duplicates and conflicts.
        
        Args:
            constraint_lists: List of constraint lists to merge
            
        Returns:
            Merged constraint list
        """
        merged_constraints = []
        seen_securities = set()
        
        for constraint_list in constraint_lists:
            for constraint in constraint_list:
                security_id = constraint.get('scope', {}).get('instrumentUniqueId')
                
                if security_id and security_id not in seen_securities:
                    merged_constraints.append(constraint)
                    seen_securities.add(security_id)
                elif security_id:
                    # Handle conflict - could implement more sophisticated logic here
                    print(f"Warning: Duplicate constraint for {security_id}, using first occurrence")
        
        return merged_constraints
    
