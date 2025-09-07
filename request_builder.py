import yaml
from jinja2 import Template
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import date
import pandas as pd

from portfolio_configs import PORTFOLIO_CONFIGS, PortfolioConfigManager, PortfolioConfig
from matcher import SecurityReplacementMatcher
from constraint_builder import ReplacementConstraintBuilder


class PortfolioOptimizerRequestBuilder:
    def __init__(self, template_path: str, config_manager: PortfolioConfigManager):
        self.template_path = template_path
        self.config_manager = config_manager
        
    def build_request(self, portfolio_id: str, 
                     as_of_date: str = None,
                     reporting_currency: str = "USD",
                     cash_instrument_id: str = "IX244867-0",
                     max_cash_weight: float = 0.05) -> Dict[str, Any]:
        """Build the API request from template and portfolio config."""
        
        # Get portfolio-specific config
        portfolio_config = self.config_manager.get_config(portfolio_id)
        
        # Load template
        with open(self.template_path, 'r') as f:
            template_content = f.read()
        
        # Set default date if not provided
        if as_of_date is None:
            as_of_date = date.today().strftime("%Y-%m-%d")
        
        # Create mapping from config to template variables
        template_vars = self._map_config_to_template(
            portfolio_id, portfolio_config, as_of_date, 
            reporting_currency, cash_instrument_id, max_cash_weight
        )
        
        # Render template
        template = Template(template_content)
        rendered_yaml = template.render(**template_vars)
        
        # Convert to dict for API request
        request_dict = yaml.safe_load(rendered_yaml)

        # Convert string numbers to proper numeric types
        request_dict = self._convert_string_numbers_to_numeric(request_dict)
        
        # Apply dynamic constraints (restricted lists, no-trade lists)
        request_dict = self._apply_dynamic_constraints(request_dict, portfolio_config)
        
        return request_dict
    
    def _map_config_to_template(self, portfolio_id: str, 
                               config: PortfolioConfig,
                               as_of_date: str,
                               reporting_currency: str,
                               cash_instrument_id: str,
                               max_cash_weight: float) -> Dict[str, Any]:
        """Map configuration parameters to template variables."""
        return {
            'PORTFOLIO_ID': portfolio_id,
            'BENCHMARK_ID': config.benchmark,
            'MIN_LOTS': config.min_trade_size,
            'VALUE_LOTS': config.min_trade_value,
            'ROUND_LOTS': config.round_lot_size,
            'SECTOR_WEIGHT_MIN_THRESHOLD': -config.sector_weight_tolerance,
            'SECTOR_WEIGHT_MAX_THRESHOLD': config.sector_weight_tolerance,
            'COUNTRY_WEIGHT_MIN_THRESHOLD': -config.country_weight_tolerance,
            'COUNTRY_WEIGHT_MAX_THRESHOLD': config.country_weight_tolerance,
            'MAX_CASH_WEIGHT': max_cash_weight,
            'AS_OF_DATE': as_of_date,
            'REPORTING_CURRENCY': reporting_currency,
            'CASH_INSTRUMENT_ID': cash_instrument_id
        }
    
    def _convert_string_numbers_to_numeric(self, obj):
        """Recursively convert string numbers to proper numeric types."""
        if isinstance(obj, dict):
            return {key: self._convert_string_numbers_to_numeric(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_string_numbers_to_numeric(item) for item in obj]
        elif isinstance(obj, str):
            # Try to convert string to int or float
            try:
                # Check if it's an integer
                if '.' not in obj and obj.lstrip('-').isdigit():
                    return int(obj)
                # Check if it's a float
                elif obj.replace('.', '').replace('-', '').isdigit():
                    return float(obj)
                else:
                    return obj
            except ValueError:
                return obj
        else:
            return obj
    
    def _apply_dynamic_constraints(self, request: Dict[str, Any], 
                                  config: PortfolioConfig) -> Dict[str, Any]:
        """Apply restricted lists and no-trade constraints."""
        
        # Add restricted security constraints
        if config.restricted_securities:
            for security in config.restricted_securities:
                constraint = self._create_restricted_security_constraint(security)
                request['task']['instrumentConstraints'].append(constraint)
        
        # Add no-trade constraints
        if config.no_trade_securities:
            for security in config.no_trade_securities:
                constraint = self._create_no_trade_constraint(security)
                request['task']['instrumentConstraints'].append(constraint)
        
        return request
    
    def _create_restricted_security_constraint(self, security_id: str) -> Dict[str, Any]:
        """Create constraint to restrict a specific security."""
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
    
    def _create_no_trade_constraint(self, security_id: str) -> Dict[str, Any]:
        """Create constraint to prevent trading a specific security."""
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
    
    def build_request_with_security_constraints(self, portfolio_id: str,
                                            frame_clean: pd.DataFrame,
                                            restricted_securities: List[str],
                                            **kwargs) -> Dict[str, Any]:
        """Build optimization request with security-level constraints."""
        
        # Find replacements
        replacement_handler = SecurityReplacementMatcher(frame_clean)
        replacements = replacement_handler.find_replacement_securities(restricted_securities)
        
        # replacement_summary = replacement_handler.get_replacement_summary(replacements)
        # replacement_validation = replacement_handler.validate_replacements(replacements)
        # print(replacement_summary)
        # print(replacement_validation)

        # Create all instrument constraints
        all_constraints = self.create_all_instrument_constraints(
            frame_clean, restricted_securities, replacements
        )
        
        # Build base request
        request = self.build_request(portfolio_id, **kwargs)
        
        # Add all instrument constraints
        request['task']['instrumentConstraints'].extend(all_constraints)
        
        return request, replacements
    

    def create_all_instrument_constraints(self, frame_clean: pd.DataFrame, 
                                    restricted_securities: List[str],
                                    replacements: Dict[str, Dict],
                                    tolerance: float = 0.0005,
                                    identifier_column: str = 'ID059') -> List[Dict[str, Any]]:
        """
        Create all instrument-level constraints: replacements + benchmark tracking for others.
        
        Args:
            frame_clean: Clean holdings dataframe
            restricted_securities: List of restricted securities
            replacements: Output from SecurityReplacementMatcher
            tolerance: Weight tolerance for constraints
            identifier_column: Column for security identification
        
        Returns:
            Complete list of instrument constraints for optimizer
        """
        # Get replacement constraints
        constraint_builder = ReplacementConstraintBuilder()
        replacement_constraints = constraint_builder.create_constraints(replacements, tolerance)
        
        # Get all benchmark securities
        benchmark_securities = frame_clean[
            (frame_clean['POS_B'].notna()) & 
            (frame_clean['POS_B'] != 0)
        ].copy()
        
        # Extract benchmark weights for non-restricted securities
        benchmark_weights = {}
        replacement_securities = set(info['replacement_security'] for info in replacements.values())
        
        for _, row in benchmark_securities.iterrows():
            security_id = row[identifier_column]
            
            # Skip if this security is restricted or is a replacement security
            if security_id not in restricted_securities and security_id not in replacement_securities:
                weight_pct = row['PCT_WGT_B']
                if pd.notna(weight_pct):
                    # Convert percentage to decimal
                    benchmark_weights[security_id] = float(weight_pct) / 100
        
        # Create benchmark tracking constraints for non-restricted securities
        tracking_securities = list(benchmark_weights.keys())
        tracking_constraints = constraint_builder.create_benchmark_tracking_constraints(
            tracking_securities, 
            benchmark_weights, 
            tolerance
        )
        
        # Merge all constraints
        all_constraints = constraint_builder.merge_constraints([
            replacement_constraints,
            tracking_constraints
        ])
        
        return all_constraints