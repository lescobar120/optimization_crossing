import pandas as pd
import requests
from requests.exceptions import ChunkedEncodingError
import time
import logging
import json
import datetime
import re
import codecs
from urllib.parse import urlencode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Any, Iterable, Mapping, Dict, List, Optional
from collections import defaultdict

from bloomberg.enterprise.oauth import (OAuthClient, EnvTier,
                                        OAuthDeviceModeConfig, OAuthServerModeConfig
                                        )
from bloomberg.enterprise.oauth.oauth_flows.oauth_user_mode import UserModeOauth
from bloomberg.enterprise.oauth.utils import _oauth_store

TOKEN_PATH = "https://bsso.blpprofessional.com/ext/api/as/token.oauth2"
CATALOG_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/info'
REPORT_PATH = 'https://api.bloomberg.com/enterprise/portfolio/report/data'


class ReportHandler:
    """
    Report handler with concurrent fetching capabilities and improved token management.
    """

    def __init__(self, config_path: str, token_margin: int = 60, timeout: int = 600, cache_only=False, cache_dir="../datasets"):
        """
        Initialize the enhanced report handler.
        
        Args:
            config_path: Path to configuration file
            token_margin: Seconds before token expiry to refresh
            timeout: Request timeout in seconds
        """
        self.config_path = config_path
        self.token_margin = token_margin
        self.timeout = timeout
        self.cache_only = cache_only
        self.cache_dir = Path(cache_dir)
        
        self._build_config()
        self._oauth_client = None
        self._access_token = None
        self._token_expiry = 0.0
        self._token_lock = threading.Lock()
        
        self.authenticate()

    ###########################  AUTHENTICATION  ###########################

    def _build_config(self):
        """Load configuration from file."""
        with open(self.config_path, "r") as config_file:
            raw_config = config_file.read()
        self.config = json.loads(raw_config)

    def authenticate(self):
        """Authenticate and get initial token."""
        if self.cache_only:
            print("[CACHE-ONLY] Authentication skipped.")
            return
    
        if not self._oauth_client:
            _oauth_store.purge_tokens(self.config['client_id'], EnvTier.PROD)
            self._oauth_client = OAuthClient(
                client_id=self.config['client_id'],
                #env=EnvTier.PROD,
                config=OAuthDeviceModeConfig(client_secret=self.config['client_secret'])
                # config=OAuthServerModeConfig(client_secret=self.config['client_secret'])
            )

        self._access_token = self._oauth_client.generate_or_refresh_token()
        self._token_expiry = time.time() + 3600  # Assume 1 hour expiry
        self.headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }

    def _maybe_refresh_token(self):
        """Refresh token if near expiry."""
        if time.time() > self._token_expiry - self.token_margin:
            with self._token_lock:
                # Double-check after acquiring lock
                if time.time() > self._token_expiry - self.token_margin:
                    self.authenticate()

    ###########################  REQUESTS  #################################

    def search_catalog(self, portfolio=None, report=None, benchmark=None):
        """Search catalog for available reports."""
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

        info_response = requests.get(
            CATALOG_PATH,
            headers=self.headers,
            params=urlencode(catalog_body),
            timeout=self.timeout
        )

        return info_response

    def get_report(self, portfolio: str, report: str, section: str=None, 
                          classification=None, classificationLevels=None, dates=None):
        """
        Get MAC HPA report data.
        
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

        res = requests.post(
            REPORT_PATH,
            headers=self.headers,
            data=json.dumps(body),
            timeout=self.timeout
        )
        
        return res

    def fetch_reports_concurrent(
        self,
        portfolio: str,
        report_configs: Mapping[str, List[Mapping[str, Any]]],
        *,
        max_workers: int = 3,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch multiple reports concurrently.
        
        Args:
            portfolio: Portfolio name
            report_configs: Dictionary mapping report names to list of configurations
                Example::
                    {
                        "REPORT_1": [
                            {"section": "FactorReturns", "dates": ["2025-01-01", "2025-01-02"]},
                            {"section": "Exposures"},
                            ],
                        "REPORT_2": [
                            {"dates": ["2025-05-30"]},
                            ],
                    }
            max_workers: Maximum number of concurrent workers
            
        Returns:
            Dictionary mapping keys to DataFrames
        """

        # =============================================================================
        # STEP 1: FLATTEN THE CONFIGURATION STRUCTURE
        # =============================================================================
        
        # Input might be: {"Report1": [config1, config2], "Report2": [config3]}
        # We need to flatten this to: [(Report1, config1), (Report1, config2), (Report2, config3)]
        
        if isinstance(report_configs, dict):
            flat_configs = [
                (rpt_name, cfg)                           # Create tuple of (report_name, config)
                for rpt_name, cfg_list in report_configs.items()  # For each report
                for cfg in (cfg_list if isinstance(cfg_list, list) else [cfg_list])  # For each config (handle single config)
            ]
        else:
            flat_configs = list(report_configs)  # Already flattened
        
        # EXAMPLE: 
        # Input:  {"Report1": [{"section": "A"}, {"section": "B"}]}
        # Output: [("Report1", {"section": "A"}), ("Report1", {"section": "B"})]
        
        # =============================================================================
        # STEP 2: SPLIT LARGE DATE RANGES TO AVOID API LIMITS
        # =============================================================================
        
        MAX_DATES = 100  # PEDL API can handle ~300 dates, but we're conservative
        expanded = []
        
        for rpt, cfg in flat_configs:
            dates = cfg.get("dates")  # Get dates from config
            
            # If dates list is too long, split it into chunks
            if dates and isinstance(dates, list) and len(dates) > MAX_DATES:
                for i in range(0, len(dates), MAX_DATES):      # Split into chunks of MAX_DATES
                    chunk = cfg.copy()
                    chunk["dates"] = dates[i : i + MAX_DATES]  # Replace dates with chunk
                    expanded.append((rpt, chunk))              # Add to expanded list
            else:
                expanded.append((rpt, cfg))  # No splitting needed
        
        flat_configs = expanded  # Replace original with expanded version
        
        # EXAMPLE:
        # If dates = ["2025-01-01", "2025-01-02", ..., "2025-06-30"] (150 dates)
        # This gets split into chunks of 100 dates each

        # =============================================================================
        # STEP 3: DEFINE THE WORKER FUNCTION
        # =============================================================================
        
        def _fetch_one(report_name: str, cfg: dict) -> tuple[str, dict, pd.DataFrame]:
            """
            This function runs in each thread to fetch one report configuration.
            Each thread will call this function with different parameters.
            """
            
            # THREAD SAFETY: Only one thread can refresh token at a time
            with self._token_lock:  # This is a threading.Lock()
                self._maybe_refresh_token()  # Refresh API token if needed
            
            try:
                response = self.get_mac_hpa_report(portfolio, report_name, **cfg)
                records = self.get_records_from_response(response)
                df = pd.DataFrame(records)
                return report_name, cfg, df
                
            except Exception as e:
                logging.error(f"Error fetching {report_name} with config {cfg}: {e}")
                return report_name, cfg, pd.DataFrame()  # Return empty DataFrame on error
        
        # =============================================================================
        # STEP 4: EXECUTE CONCURRENT FETCHES
        # =============================================================================
        
        results = []
        
        # ThreadPoolExecutor manages a pool of worker threads
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            
            # Submit all tasks to the thread pool
            # Each task is: pool.submit(function, arg1, arg2, ...)
            fut_map = {
                pool.submit(_fetch_one, rpt, cfg): (rpt, cfg)  # Map future -> original args
                for rpt, cfg in flat_configs  # For each report config
            }
            
            # Wait for tasks to complete and collect results
            for fut in as_completed(fut_map):  # as_completed yields futures as they finish
                try:
                    rpt, cfg, df = fut.result()  # Get the result from the completed task
                    results.append((rpt, cfg, df))  # Add to results list
                except Exception as e:
                    logging.error(f"Error in concurrent fetch: {e}")
        
        # AT THIS POINT: All API calls have completed (either successfully or with errors)
        # results = [(report1, config1, dataframe1), (report2, config2, dataframe2), ...]

        # =============================================================================
        # STEP 5: COMBINE RESULTS BY REPORT+SECTION
        # =============================================================================
        
        # Group results by report+section key
        out: Dict[str, List[pd.DataFrame]] = defaultdict(list)
        
        for rpt, cfg, df in results:
            section = cfg.get("section")  # Get section name from config
            
            # Create a unique key: either "ReportName" or "ReportName-SectionName"
            key = f"{rpt}-{section}" if section else rpt
            
            out[key].append(df)  # Add DataFrame to the list for this key
        
        # EXAMPLE:
        # out = {
        #     "RBC PEDL Attribution - 1D-Attribution Main View": [df1, df2],
        #     "RBC PEDL Attribution - 1D-Return Splits": [df3]
        # }
        
        # =============================================================================
        # STEP 6: CONCATENATE CHUNKS AND DEDUPLICATE
        # =============================================================================
        
        combined: Dict[str, pd.DataFrame] = {}
        
        for key, frames in out.items():
            if frames:  # If we have DataFrames for this key
                df_full = pd.concat(frames, ignore_index=True)  # Combine all chunks
                df_full.drop_duplicates(inplace=True)  # Remove any duplicate rows
                combined[key] = df_full
            else:
                combined[key] = pd.DataFrame()  # Empty DataFrame if no data

        return combined

    ###########################  RESPONSE PARSING  #########################

    def get_records_from_response(self, response):
        """
        Parse response content and extract JSON records.
        Uses improved JSON extraction with balanced brace tracking.
        """
        data = response.content.decode("utf-8", errors="ignore")

        json_objects: List[dict] = []
        depth = 0
        buf: List[str] = []

        for ch in data:
            if ch == "{":
                if depth == 0:
                    buf = []  # start a new object
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
                        # skip malformed fragment but keep going
                        pass

        if not json_objects:
            raise ValueError("No JSON objects found in PEDL multipart response")

        return self._convert_response_dict_into_records_dict(json_objects)

    def _convert_response_dict_into_records_dict(self, json_elements):
        """Convert response JSON elements to records."""
        assert isinstance(json_elements, list), 'A list of dicts is expected'
        all_records = []

        for response_dict in json_elements:
            # Some chunks are metadata only without dataColumns, then skip.
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

            # Zip all values into dicts
            records = [dict(zip(column_data.keys(), row)) for row in zip(*column_data.values())]
            all_records.extend(records)

        return all_records

