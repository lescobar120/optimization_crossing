import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class SecurityReplacementMatcher:
    """Handles the logic for finding replacement securities using hierarchical matching."""
    
    def __init__(self, clean_holdings_df: pd.DataFrame):
        """
        Initialize with clean holdings dataframe.
        
        Args:
            clean_holdings_df: DataFrame that has already been cleaned by HoldingsDataProcessor
        """
        self.holdings_df = clean_holdings_df
        self._validate_required_columns()
        
    def _validate_required_columns(self) -> None:
        """Validate that the dataframe has required columns for replacement logic."""
        required_columns = [
            'POS_B', 'PCT_WGT_B', 'CURRENT_MARKET_CAP', 
            'SECTOR', 'GROUP', 'SUBGROUP', 'TICKER'
        ]
        
        missing_columns = [col for col in required_columns if col not in self.holdings_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    def find_replacement_securities(self, restricted_securities: List[str], 
                                  identifier_column: str = 'ID059') -> Dict[str, Dict]:
        """
        Find replacement securities for restricted securities.
        
        Args:
            restricted_securities: List of restricted security identifiers
            identifier_column: Column to use for matching securities (TICKER, FIGI_B, etc.)
        
        Returns:
            Dictionary mapping restricted security -> replacement info
        """
        if identifier_column not in self.holdings_df.columns:
            raise ValueError(f"Identifier column '{identifier_column}' not found in dataframe")
            
        replacements = {}
        
        # Get benchmark securities only (have POS_B values)
        benchmark_securities = self._get_benchmark_securities()
        
        for restricted_security in restricted_securities:
            replacement = self._find_single_replacement(
                restricted_security, benchmark_securities, identifier_column
            )
            if replacement:
                replacements[restricted_security] = replacement
                
        return replacements
    
    def _get_benchmark_securities(self) -> pd.DataFrame:
        """Get only securities that are in the benchmark (have POS_B values)."""
        return self.holdings_df[
            (self.holdings_df['POS_B'].notna()) & 
            (self.holdings_df['POS_B'] != 0)
        ].copy()
    
    def _find_single_replacement(self, restricted_security: str, 
                               benchmark_df: pd.DataFrame,
                               identifier_column: str) -> Optional[Dict]:
        """
        Find a single replacement security using hierarchical matching.
        """
        # Get the restricted security's details
        restricted_row = benchmark_df[
            benchmark_df[identifier_column] == restricted_security
        ]
        
        if restricted_row.empty:
            print(f"Warning: {restricted_security} not found in benchmark")
            return None
            
        restricted_info = restricted_row.iloc[0]
        
        # Get potential replacements (exclude the restricted security itself)
        candidates = benchmark_df[
            benchmark_df[identifier_column] != restricted_security
        ].copy()
        
        # Hierarchical matching: SUBGROUP -> GROUP -> SECTOR
        replacement = None
        
        # Level 1: Same SUBGROUP
        if pd.notna(restricted_info['SUBGROUP']):
            subgroup_matches = candidates[
                candidates['SUBGROUP'] == restricted_info['SUBGROUP']
            ]
            if not subgroup_matches.empty:
                replacement = self._select_best_match_by_market_cap(
                    subgroup_matches, restricted_info['CURRENT_MARKET_CAP']
                )
        
        # Level 2: Same GROUP (if no SUBGROUP match)
        if replacement is None and pd.notna(restricted_info['GROUP']):
            group_matches = candidates[
                candidates['GROUP'] == restricted_info['GROUP']
            ]
            if not group_matches.empty:
                replacement = self._select_best_match_by_market_cap(
                    group_matches, restricted_info['CURRENT_MARKET_CAP']
                )
        
        # Level 3: Same SECTOR (if no GROUP match)
        if replacement is None and pd.notna(restricted_info['SECTOR']):
            sector_matches = candidates[
                candidates['SECTOR'] == restricted_info['SECTOR']
            ]
            if not sector_matches.empty:
                replacement = self._select_best_match_by_market_cap(
                    sector_matches, restricted_info['CURRENT_MARKET_CAP']
                )
        
        if replacement is not None:
            return {
                'replacement_security': replacement[identifier_column],
                'replacement_ticker': replacement['TICKER'],
                'restricted_weight': float(restricted_info['PCT_WGT_B']),
                'replacement_weight': float(replacement['PCT_WGT_B']),
                'combined_weight': float(restricted_info['PCT_WGT_B'] + replacement['PCT_WGT_B']),
                'match_level': self._get_match_level(restricted_info, replacement),
                'restricted_market_cap': float(restricted_info['CURRENT_MARKET_CAP']) if pd.notna(restricted_info['CURRENT_MARKET_CAP']) else None,
                'replacement_market_cap': float(replacement['CURRENT_MARKET_CAP']) if pd.notna(replacement['CURRENT_MARKET_CAP']) else None,
                'restricted_sector': restricted_info['SECTOR'],
                'replacement_sector': replacement['SECTOR']
            }
        
        print(f"Warning: No replacement found for {restricted_security}")
        return None
    
    def _select_best_match_by_market_cap(self, candidates: pd.DataFrame, 
                                       target_market_cap: float) -> pd.Series:
        """
        Select the candidate with the closest market cap to the target.
        """
        if pd.isna(target_market_cap):
            # If target market cap is NaN, just return the first candidate
            return candidates.iloc[0]
        
        # Calculate absolute difference in market cap
        candidates = candidates.copy()
        candidates['market_cap_diff'] = abs(
            candidates['CURRENT_MARKET_CAP'].fillna(0) - target_market_cap
        )
        
        # Return the candidate with smallest market cap difference
        return candidates.loc[candidates['market_cap_diff'].idxmin()]
    
    def _get_match_level(self, restricted_info: pd.Series, replacement_info: pd.Series) -> str:
        """
        Determine the level at which the match was found.
        """
        if (pd.notna(restricted_info['SUBGROUP']) and 
            restricted_info['SUBGROUP'] == replacement_info['SUBGROUP']):
            return 'SUBGROUP'
        elif (pd.notna(restricted_info['GROUP']) and 
              restricted_info['GROUP'] == replacement_info['GROUP']):
            return 'GROUP'
        elif (pd.notna(restricted_info['SECTOR']) and 
              restricted_info['SECTOR'] == replacement_info['SECTOR']):
            return 'SECTOR'
        else:
            return 'NO_MATCH'
    
    def get_replacement_summary(self, replacements: Dict[str, Dict]) -> Dict[str, int]:
        """
        Get a summary of replacement match levels.
        
        Args:
            replacements: Output from find_replacement_securities()
            
        Returns:
            Dictionary with count of matches at each level
        """
        summary = {'SUBGROUP': 0, 'GROUP': 0, 'SECTOR': 0, 'NO_MATCH': 0}
        
        for replacement_info in replacements.values():
            match_level = replacement_info.get('match_level', 'NO_MATCH')
            summary[match_level] += 1
            
        return summary
    
    def validate_replacements(self, replacements: Dict[str, Dict], 
                            max_combined_weight_pct: float = 10.0) -> Dict[str, List[str]]:
        """
        Validate replacement mappings for potential issues.
        
        Args:
            replacements: Output from find_replacement_securities()
            max_combined_weight_pct: Maximum allowed combined weight percentage
            
        Returns:
            Dictionary of validation issues
        """
        issues = {
            'high_concentration': [],
            'cross_sector': [],
            'no_match': []
        }
        
        for restricted_security, info in replacements.items():
            # Check for high concentration risk
            if info['combined_weight'] > max_combined_weight_pct:
                issues['high_concentration'].append({
                    'restricted': restricted_security,
                    'replacement': info['replacement_security'],
                    'combined_weight': info['combined_weight']
                })
            
            # Check for cross-sector replacements
            if info['restricted_sector'] != info['replacement_sector']:
                issues['cross_sector'].append({
                    'restricted': restricted_security,
                    'replacement': info['replacement_security'],
                    'restricted_sector': info['restricted_sector'],
                    'replacement_sector': info['replacement_sector']
                })
            
            # Check for poor matches
            if info['match_level'] == 'NO_MATCH':
                issues['no_match'].append(restricted_security)
        
        return issues


