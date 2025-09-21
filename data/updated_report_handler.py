# updated_report_handler.py
"""
Updated ReportHandler that uses shared authentication to avoid redundant authentication.
This should replace your enhanced_report_handler.py
"""

import pandas as pd
import requests
import time
import logging
import json
import datetime
from urllib.parse import urlencode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Any, Iterable, Mapping, Dict, List, Optional
from collections import defaultdict

from auth.shared_auth_manager import get_shared_auth_manager


class UpdatedReportHandler:
    """
    Updated ReportHandler that uses shared authentication manager.
    
    This eliminates redundant authentication by using a shared authentication state
    across all workflow components.
    """

    def __init__(self, config_path: str, token_margin: int = 60, timeout: int = 600, cache_only=False, cache_dir="../datasets"):
        """
        Initialize the updated report handler.
        
        Args:
            config_path: Path to Bloomberg configuration file
            token_margin: Seconds before token expiry to refresh (unused with shared auth)
            timeout: Request timeout in seconds
            cache_only: If True, skip authentication (for testing)
            cache_dir: Directory for caching data
        """
        self.config_path = config_path
        self.token_margin = token_margin
        self.timeout = timeout
        self.cache_only = cache_only
        self.cache_dir = Path(cache_dir)
        
        # Use shared authentication manager instead of individual auth
        self.shared_auth = get_shared_auth_manager(config_path)
        self._token_lock = threading.Lock()
        
        # Only authenticate if not cache-only mode
        if not self.cache_only:
            print("[AUTH] Using shared authentication manager...")
            # The shared manager will handle authentication as needed
        else:
            print("[CACHE-ONLY] Authentication skipped.")

    def authenticate(self):
        """
        Authenticate using shared authentication manager.
        This method is kept for compatibility but now uses shared auth.
        """
        if self.cache_only:
            return
            
        print("[AUTH] Checking shared authentication state...")
        
        if self.shared_auth.is_ready():
            print("[AUTH] Already authenticated via shared manager!")
            return
        
        print("[AUTH] Starting Bloomberg authentication via shared manager...")
        success = self.shared_auth.authenticate_if_needed()
        
        if not success:
            error_msg = self.shared_auth.auth_error or "Authentication failed"
            raise RuntimeError(f"Bloomberg authentication failed: {error_msg}")
        
        print("[AUTH] Bloomberg authentication completed successfully!")

    def _maybe_refresh_token(self):
        """Ensure token is valid using shared authentication manager."""
        if self.cache_only:
            return
            
        # The shared manager handles token refresh automatically
        # Just verify we're still authenticated
        if not self.shared_auth.is_ready():
            self.shared_auth.authenticate_if_needed()

    def get_authorization_headers(self) -> Dict[str, str]:
        """
        Get authorization headers using shared authentication manager.
        
        Returns:
            Dictionary containing authorization headers
        """
        if self.cache_only:
            return {}
            
        return self.shared_auth.get_auth_headers()

    ###########################  REQUESTS - EXACT COMPATIBILITY  ###########################

    def search_catalog(self, portfolio=None, report=None, benchmark=None):
        """Search catalog for available reports - EXACT COMPATIBILITY."""
        if self.cache_only:
            # Return mock response for cache-only mode
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
                def json(self):
                    return {"reportInformation": "mock"}
            return MockResponse()
            
        self._maybe_refresh_token()
        
        if not (portfolio and report):
            return
        
        catalog_body = {}
        if portfolio:
            catalog_body['portfolio'] = portfolio
        if report:
            catalog_body['reportName'] = report
        if benchmark:
            catalog_body['benchmark'] = benchmark

        # Get headers from shared auth manager
        headers = self.get_authorization_headers()

        # Use requests for compatibility with existing code
        info_response = requests.get(
            'https://api.bloomberg.com/enterprise/portfolio/report/info',
            headers=headers,
            params=urlencode(catalog_body),
            timeout=self.timeout
        )

        return info_response

    def get_report(self, portfolio: str, report: str, section: str = None, 
                   classification=None, classificationLevels=None, dates=None):
        """
        Get MAC HPA report data - EXACT COMPATIBILITY.
        
        Args:
            portfolio: Portfolio name
            report: Report name
            section: Report section
            classification: Classification filter
            classificationLevels: Classification levels
            dates: List of dates
            
        Returns:
            Response object
        """
        if self.cache_only:
            # Return mock response for cache-only mode
            class MockResponse:
                def __init__(self):
                    self.status_code = 200
                    self.content = b'{"mock": "data"}'
            return MockResponse()
            
        self._maybe_refresh_token()

        # Confirm report data exists in datalake
        info_response = self.search_catalog(portfolio=portfolio, report=report)

        if 'reportInformation' not in info_response.json():
            print(f"Data does not exist in the BQL Datalake for {portfolio} and {report} combination")
            return info_response

        body = {
            "reportInformation": {
                "reportName": report,
                "portfolio": portfolio,
            },
        }

        if section:
            body["reportInformation"]["section"] = section
        
        if classification:
            body["reportInformation"]["classification"] = classification
        if classificationLevels:
            body["classificationLevels"] = classificationLevels
        if dates:
            body["dates"] = dates

        # Get headers from shared auth manager
        headers = self.get_authorization_headers()

        res = requests.post(
            'https://api.bloomberg.com/enterprise/portfolio/report/data',
            headers=headers,
            data=json.dumps(body),
            timeout=self.timeout
        )
        
        return res

    def get_mac_hpa_report(self, portfolio: str, report: str, **kwargs):
        """
        Alias for get_report to maintain compatibility.
        
        This method name appears in your fetch_reports_concurrent method.
        """
        return self.get_report(portfolio, report, **kwargs)

    def fetch_reports_concurrent(self, portfolio: str, report_configs: Mapping[str, List[Mapping[str, Any]]], 
                                *, max_workers: int = 3) -> Dict[str, pd.DataFrame]:
        """
        Fetch multiple reports concurrently - EXACT COMPATIBILITY.
        
        This method maintains exact compatibility with your existing ReportHandler.
        """
        if self.cache_only:
            print("[CACHE-ONLY] Concurrent fetch skipped - returning empty DataFrames.")
            return {f"mock_{i}": pd.DataFrame() for i in range(len(report_configs))}

        # Flatten configuration structure
        if isinstance(report_configs, dict):
            flat_configs = [
                (rpt_name, cfg)
                for rpt_name, cfg_list in report_configs.items()
                for cfg in (cfg_list if isinstance(cfg_list, list) else [cfg_list])
            ]
        else:
            flat_configs = list(report_configs)

        # Split large date ranges
        MAX_DATES = 100
        expanded = []
        
        for rpt, cfg in flat_configs:
            dates = cfg.get("dates")
            
            if dates and isinstance(dates, list) and len(dates) > MAX_DATES:
                for i in range(0, len(dates), MAX_DATES):
                    chunk = cfg.copy()
                    chunk["dates"] = dates[i : i + MAX_DATES]
                    expanded.append((rpt, chunk))
            else:
                expanded.append((rpt, cfg))
        
        flat_configs = expanded

        # Define worker function
        def _fetch_one(report_name: str, cfg: dict) -> tuple[str, dict, pd.DataFrame]:
            # No need for token lock with shared auth - it handles thread safety
            try:
                response = self.get_mac_hpa_report(portfolio, report_name, **cfg)
                records = self.get_records_from_response(response)
                df = pd.DataFrame(records)
                return report_name, cfg, df
                
            except Exception as e:
                logging.error(f"Error fetching {report_name} with config {cfg}: {e}")
                return report_name, cfg, pd.DataFrame()

        # Execute concurrent fetches
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_map = {
                pool.submit(_fetch_one, rpt, cfg): (rpt, cfg)
                for rpt, cfg in flat_configs
            }
            
            for fut in as_completed(fut_map):
                try:
                    rpt, cfg, df = fut.result()
                    results.append((rpt, cfg, df))
                except Exception as e:
                    logging.error(f"Error in concurrent fetch: {e}")

        # Combine results by report+section
        out: Dict[str, List[pd.DataFrame]] = defaultdict(list)
        
        for rpt, cfg, df in results:
            section = cfg.get("section")
            key = f"{rpt}-{section}" if section else rpt
            out[key].append(df)

        # Concatenate chunks and deduplicate
        combined: Dict[str, pd.DataFrame] = {}
        
        for key, frames in out.items():
            if frames:
                df_full = pd.concat(frames, ignore_index=True)
                df_full.drop_duplicates(inplace=True)
                combined[key] = df_full
            else:
                combined[key] = pd.DataFrame()

        return combined

    ###########################  RESPONSE PARSING - EXACT COMPATIBILITY  #########################

    def get_records_from_response(self, response):
        """
        Parse response content and extract JSON records - EXACT COMPATIBILITY.
        """
        data = response.content.decode("utf-8", errors="ignore")

        json_objects: List[dict] = []
        depth = 0
        buf: List[str] = []

        for ch in data:
            if ch == "{":
                if depth == 0:
                    buf = []
                depth += 1
            if depth > 0:
                buf.append(ch)
            if ch == "}":
                depth -= 1
                if depth == 0 and buf:
                    obj_str = "".join(buf)
                    try:
                        json_objects.append(json.loads(obj_str))
                    except json.JSONDecodeError:
                        pass

        if not json_objects:
            raise ValueError("No JSON objects found in PEDL multipart response")

        return self._convert_response_dict_into_records_dict(json_objects)

    def _convert_response_dict_into_records_dict(self, json_elements):
        """Convert response JSON elements to records - EXACT COMPATIBILITY."""
        assert isinstance(json_elements, list), 'A list of dicts is expected'
        all_records = []

        for response_dict in json_elements:
            if "dataColumns" not in response_dict:
                continue
            
            columns = response_dict["dataColumns"]
            column_data = {}

            for element in columns:
                name = element["name"]
                dtype = element["type"] + "s"
                data = element.get(dtype)
                if dtype == "dates":
                    data = pd.to_datetime(data)
                column_data[name] = data

            records = [dict(zip(column_data.keys(), row)) for row in zip(*column_data.values())]
            all_records.extend(records)

        return all_records


# For complete compatibility, create an alias
ReportHandler = UpdatedReportHandler
EnhancedReportHandler = UpdatedReportHandler  # For migration compatibility