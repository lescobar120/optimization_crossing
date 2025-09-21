# optimization_workflow.py


"""
This file contains low-level functions that handle specific optimization tasks:

API Communication

send_optimization_request(): Sends requests to the Bloomberg API
poll_optimization_result(): Polls for results until completion
get_optimization_response(): Combines the above functions


Task Management

build_optimization_request(): Formats tasks for the API
register_optimization_tasks(): Creates and registers optimization tasks
build_task(): Builds optimization tasks from parameters
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import time
from datetime import datetime


from config.updated_api_config import (
    OPTIMIZATION_TRIGGER_ENDPOINT, 
    RESULTS_RETRIEVAL_ENDPOINT,
    WAIT_TIME_SECONDS,
    get_authorization_headers
)


def send_optimization_request(optimization_request: dict, task_optimization_id: str=None, auth_headers={}, tracker=None):
    """
    Sends the initial POST request to start the optimization.
    
    Parameters:
    - optimization_request: The optimization request payload
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - tracker: Optional tracker object to update optimization status
    
    Returns:
    - api_optimization_id: The ID returned by the API for polling
    - initial_response_json: The full response data
    
    Raises exceptions if the request fails
    """
    auth_headers = auth_headers or {}
    
    try:
        initial_response = requests.post(
            OPTIMIZATION_TRIGGER_ENDPOINT,
            data=json.dumps(optimization_request),
            headers={'Content-Type': 'application/json', **auth_headers}
        )
        
        initial_response.raise_for_status()
        initial_response_json = initial_response.json()
        api_optimization_id = initial_response_json['optimizationId']
        
        # Update tracker using our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, api_generated_id=api_optimization_id, status="RUNNING")
            
        return api_optimization_id, initial_response_json
        
    except requests.exceptions.RequestException as e:
        error_message = f"Failed to start optimization: {str(e)}"
        
        # Additional error details if available
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_message += f" - Details: {error_details}"
            except:
                error_message += f" - Status code: {e.response.status_code}"
        
        # Update tracker with our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
            
        raise RuntimeError(error_message)


def poll_optimization_result(api_optimization_id: str, task_optimization_id: str=None, 
                            auth_headers={}, max_retries=30, 
                            initial_wait=WAIT_TIME_SECONDS, tracker=None):
    """
    Polls the optimization result endpoint until completion or failure.
    
    Parameters:
    - api_optimization_id: The ID returned by the API for polling
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - max_retries: Maximum number of retry attempts
    - initial_wait: Initial wait time between retries (in seconds)
    - tracker: Optional tracker object to update status
    
    Returns:
    - The final optimization result
    
    Raises exceptions if polling fails
    """
    auth_headers = auth_headers or {}
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            opt_response = requests.get(
                RESULTS_RETRIEVAL_ENDPOINT + api_optimization_id,
                headers=auth_headers
            )
            
            # Success case - optimization completed
            if opt_response.status_code == 200:
                result = opt_response.json()
                    
                return result
                
            # Still processing - continue polling
            elif opt_response.status_code == 202:
                wait_time = initial_wait * (1.1 ** retry_count)  # Exponential backoff
                time.sleep(wait_time)
                retry_count += 1
                
            # Error case - unexpected status code
            else:
                error_data = opt_response.json() if opt_response.text else {"message": "Unknown error"}
                error_message = f"Error retrieving optimization results: {opt_response.status_code} - {error_data}"
                
                # Update tracker using our task optimization ID
                if tracker:
                    tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
                    
                return error_data
                
        except requests.exceptions.RequestException as e:
            error_message = f"Error polling optimization results: {str(e)}"
            
            # Update tracker using our task optimization ID
            if tracker:
                tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
                
            raise RuntimeError(error_message)
    
    # Handle case where max retries exceeded
    timeout_message = f"Optimization polling timed out after {max_retries} attempts"
    
    # Update tracker using our task optimization ID
    if tracker:
        tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=timeout_message)
        
    raise TimeoutError(timeout_message)


def get_optimization_response(optimization_request: dict, task_optimization_id: str=None, auth_headers={}, tracker=None):
    """
    Sends the optimization request and polls until the results are ready.
    
    Parameters:
    - optimization_request: The optimization request payload
    - task_optimization_id: Our internally generated optimization ID (for tracker)
    - auth_headers: Authentication headers
    - tracker: Optional tracker object to update optimization status
    
    Returns:
    - The optimization result
    """

    auth_headers = auth_headers or get_authorization_headers()
    
    try:
        # Start the optimization
        api_optimization_id, _ = send_optimization_request(
            optimization_request, 
            task_optimization_id,
            auth_headers=auth_headers,
            tracker=tracker
        )
        
        # Poll for the result
        return poll_optimization_result(
            api_optimization_id,
            task_optimization_id,
            auth_headers=auth_headers,
            tracker=tracker
        )
        
    except Exception as e:
        # Handle any unexpected exceptions
        error_message = f"Optimization failed: {str(e)}"
        
        # Update tracker using our task optimization ID
        if tracker:
            tracker.update_optimization_status(task_optimization_id, status="FAILED", error_message=error_message)
            
        # Re-raise the exception for the caller to handle
        raise


def build_optimization_request(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build full optimization request from task.
    
    Args:
        task: Optimization task dictionary
    
    Returns:
        Complete optimization request for API
    """
    
    return {
        ## PORTFOLIO ##
        "portfolio": {
            "id": task['portfolioId'],
            "type": "PORTFOLIO_NAME"
        },
        ## BENCHMARK ##
        "benchmark": {
            "id": task['benchmarkId'],
            "type": task["benchmark_type"]
        },
        ## TRADE UNIVERSES ##
        #"tradeUniverse": trade_univ,
        "tradeUniverse": task['tradeUniverse'],
        ## OPTIMIZATION TASK ##
        "task": {
            "goals": task['goals'],
            "portfolioConstraints": task['portfolioConstraints'],
            "instrumentConstraints": task['instrumentConstraints'],
            "riskOptions": task['riskOptions'],
            "options": task['options']
        },
        
        ## ADDITIONAL ##
        "asOfDate": task['asOfDate'],
        "reportingCurrency": "USD",
        "saveTo": task['saveTo'] if 'saveTo' in task else "NONE",
        "enableLookThrough": task['enableLookThrough'] if 'enableLookThrough' in task else False,
        "infusedCashAmount": task['infusedCashAmount'] if 'infusedCashAmount' in task else 0
    }



