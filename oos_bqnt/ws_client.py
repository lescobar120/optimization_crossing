"""
Helper methods to support testing server mode auth services.
"""

import base64
import binascii
import hashlib
import hmac
import json
import time
import urllib
import uuid
import urllib.parse as urlencodelib


def generate_url(path, method, credentials, uri, jwt_params = {}, header_params = {}, query_params = {}):
    client_id = credentials["clientId"]
    client_secret = credentials["clientSecret"]
    query_params['jwt'] = generate_jwt(client_id, binascii.unhexlify(client_secret), path, uri, method, jwt_params, header_params)
    return uri + path + '?' + urlencodelib.urlencode(query_params)


def decode_base64(data):
    """Decode base64, padding being optional.

    :param data: Base64 data as an ASCII byte string
    :returns: The decoded byte string.

    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += b'='* (4 - missing_padding)
    return base64.decodestring(data)

def generate_websocket_url(path, method, credentials, uri, jwt_params = {}, header_params = {}, query_params = {}):
    websocket_uri = uri
   # websocket_uri = uri.replace('http', 'ws', 1)
    
    websocket_jwt_params = dict({
        'connection_expiry': int(round(time.time())) + 500
    }.items() | jwt_params.items())

    return generate_url(path, method, credentials, websocket_uri, websocket_jwt_params, header_params, query_params)

def generate_jwt(key_id, key_secret, path, uri, method, jwt_params = {}, header_params = {}):
    header = generate_header(header_params)
    payload = generate_payload(key_id, path, uri, method, jwt_params)
    jwt_header = header + "." + payload
    signature = generate_signature(jwt_header, key_secret)
    return jwt_header + "." + signature

def b64encode(string):
    if type(string) != type(b''):
        string = string.encode()
    return base64.urlsafe_b64encode(string).replace("=".encode(), "".encode()).decode()

def generate_header(params):
    algo = {
        "alg": "HS256",
        "typ": "JWT"
    }
    headers = dict(algo.items() | params.items())
    print(json.dumps(headers))
    return b64encode(json.dumps(headers))
    #return base64.urlsafe_b64encode(json.dumps(headers)).replace("=", "")

def generate_payload(key_id, path, uri, method, payload_params = {}):
    current_time = int(round(time.time()))
    jwt_payload = {
        "iss": key_id,
        "kid" : key_id,
        "exp": current_time + 300,
        "nbf": current_time - 60,
        "iat": current_time - 60,
        "region": "ny",
        "method": method,
        "path": path,
        "host": uri,
        "client_id": key_id,
        "nonce": str(uuid.uuid4())
    }
    payload = dict(jwt_payload.items() | payload_params.items())
    return b64encode(json.dumps(payload))
    #return base64.urlsafe_b64encode(json.dumps(payload)).replace("=", "")

def generate_signature(payload, key_secret):
    hs256 = hmac.new(key_secret, payload.encode(), hashlib.sha256)
    digest = hs256.digest()
    return b64encode(digest)
    