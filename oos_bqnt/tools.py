#from client import generate_url, generate_jwt, BLOOMBERG_URI, TESTING_URI, API_HOST
from local_secrets import clientId, clientSecret
import asyncio
import websockets
print(websockets.__version__)
from websockets import client
from ws_client import generate_websocket_url
import nest_asyncio
nest_asyncio.apply()
import uuid
import logging
import sys
import datetime
#import xmltodict
#from dict2xml import dict2xml
import numpy as np
import pandas as pd
import bql
from ws_utils import hello
    
class TradingSystem:
        
    def __init__(self, trades):
        self.trade = trades
        self.payload = None
        with open('request_basket_1.xml') as fd:
            self.payload = xmltodict.parse(fd.read())
      
    def create_basket(self,basketname):
        self.payload['NewOrderList']['BasketName'] = basketname
        self.payload['NewOrderList']['FIXMessageHeader']['SendingTime'] = datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")
        self.payload['NewOrderList']['NoOrders'] = { 'Count' : 0, 'Order' : []}

    def add_order(self,order):
        neworder={'ClOrdID' : order['ClOrdID'],
              'Instrument' : {'SecurityID': order['SecurityID'], 'SecurityIDSource' : order['SecurityIDSource'], 'FixedIncomeFlag' : order['FixedIncomeFlag']},
              'Side' : order['Side'],
              'Price' : order['Price'],
              'TransactTime' : order['TransactTime'],
              'OrderQtyData' : {'OrderQty': order['OrderQty']},
              'OrdType' : order['OrdType'],
              'SettlCurrency' : order['SettlCurrency'],
              'BBNotes' : order['BBNotes']
              }
        self.payload['NewOrderList']['NoOrders']['Order'].append(neworder)
        self.payload['NewOrderList']['NoOrders']['Count']+=1
    
    
    def execute(self, moke=True):
        print("Creating AIM basket order ... and sending to AIM.")
        
        if moke:
            with open('request_basket_1.xml', 'r') as f:
                request_data1 = f.read()
            with open('request_basket_2.xml', 'r') as f:
                request_data2 = f.read()
            request_data = request_data1 + request_data2
        else:
            request_data = '<?xml version=\"1.0\" encoding= "UTF-8 "?>\n' + dict2xml(self.payload, indent= " ")

        print(request_data)
                
        API_HOST = "wss://api.bloomberg.com"
        API_URI = "/integration/ws/bquant/aim/orders" #4160
        #API_URI = "/integration/ws/bqnt/aim/oos" #4571
        credentials = {
            'clientId': clientId,
            'clientSecret': clientSecret
        }
        url = generate_websocket_url(API_URI, 'GET', credentials, API_HOST)
        
        asyncio.get_event_loop().run_until_complete(hello(url, request_data))                 
    
    
class Portfolio:
    
    def __init__(self, signal, GMV):
        self.signal = signal
        self.target_positions = np.round(signal['combined_signal']*GMV)
        self.target_positions = self.target_positions.rename('positions')
                
    def get_target_positions(self):        
        return self.target_positions
    
    def get_share_target_positions(self, prices=100):
        self.share_target_positions = np.round(self.target_positions/prices)
        return self.share_target_positions
        
    def get_latest_share_target_positions(self):
        return self.share_target_positions['2022-02-25']           
        
    def get_current_holdings(self):
        
        # Get a service
        bq = bql.Service()
                
        # Get universe members (id), and their names (id_name) for each day
        request = "get(TS_POSITION())for(members(type=AIM,ACCOUNTS=['GM-0001'],pxnum=4160))"
        response = bq.execute(request) 
        df_resp = bql.combined_df(response) 
        df_resp = df_resp[~df_resp.index.str.contains('Curncy')]['TS_POSITION()'].sort_values()
        
        self.holdings = df_resp
        
        return df_resp      
    
    def get_trades(self):
        return self.target_positions.join(self.holdings)
    
    

def logger_setup():

    #Creating and Configuring Logger

    Log_Format = "%(levelname)s %(asctime)s - %(message)s"

    logging.basicConfig(stream = sys.stdout, 
                        filemode = "w",
                        format = Log_Format, 
                        level = logging.ERROR)

    mlogger = logging.getLogger()
    return mlogger

    
def load_request_basket():
    with open('request_basket_1.xml', 'r') as f:
        request_data1 = f.read()
    with open('request_basket_2.xml', 'r') as f:
        request_data2 = f.read()
    request_data = request_data1 + request_data2
    return request_data

              
def run_request_from_file(filename, url):
    """
    Send XML request from file and return Bloomberg's response.
    
    Args:
        filename: Path to XML file
        url: WebSocket URL
        
    Returns:
        str: XML response from Bloomberg, or None if failed
    """
    with open(filename, 'r') as f:
        request_data = f.read()

    # Optional: extract and print order IDs
    import xml.etree.ElementTree as ET
    root = ET.fromstring(request_data)
    OrderID = root.findall('.//ClOrdID')
    OrderIDs = [elem.text for elem in OrderID if elem.text is not None]
    ListOrders = ', '.join(OrderIDs).strip()
    print("Connecting to url= " + url + "\n\nSending request of each order(s) below:\n" + ListOrders + "\n")

    # CAPTURE and RETURN the response
    response = asyncio.run(hello(url, request_data))
    return response