"""
Configuration for OOS_BQNT integration layer.

Loads environment variables and sets up connection parameters.
"""

import os

# Required environment variables
required_env_variables = {
    'USING_IBM_MQ',
    'BBG_UUID',
    'PX_NUM',
    'USE_NEW_CMGR_XML'
}

# Validate all required variables are set
for req_var in required_env_variables:
    assert req_var in os.environ, f'Required variable {req_var} not in the list of environment variables'

# Load environment variables
USING_IBM_MQ = os.environ.get('USING_IBM_MQ')
BBG_UUID = os.environ.get('BBG_UUID')
PX_NUM = os.environ.get('PX_NUM')

# Boolean string values
BOOL_STRINGS = {'1', 'TRUE', 'Y', 'YES', 'T'}

# Parse boolean flags
USE_NEW_CMGR_XML = os.environ.get('USE_NEW_CMGR_XML').upper() in BOOL_STRINGS

# Set SENDER_ID and TARGET_ID based on IBM MQ usage
if USING_IBM_MQ.upper() in BOOL_STRINGS:
    SENDER_ID = 'MQ_UPL_TSORD'
    TARGET_ID = 'MQ_INT_TSORD'
else:
    SENDER_ID = 'BAS_UPL_TSORD'
    TARGET_ID = 'BAS_INT_TSORD'