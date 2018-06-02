import requests
import json
import pandas as pd 
import numpy as np 
from pandas.io.json import json_normalize
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
import time




#Authorisation
req_token="bearer 8aaecdbf20139b5ecdfc004435616c80-8bc288f120974d820ad37eb99ec67e3c"
req_url="https://api-fxpractice.oanda.com/v3/instruments/EUR_AUD/candles"
headers_get={"Authorization":req_token}
headers={"Content-Type":"application/json", "Authorization":req_token}

########## API Function ###########
#Get Candle Data
def get_candles(headers,instrument="AUD_USD",count=500,granularity="M5"):
	get_candles_url="https://api-fxpractice.oanda.com/v3/instruments/"+instrument+"/candles"
	get_candles_params={"count":count,"granularity":granularity}
	get_candles_req= requests.get(get_candles_url,headers=headers,params=get_candles_params)
	get_candles_response=json.loads(get_candles_req.text)
	get_candles_df= json_normalize(get_candles_response["candles"])
	get_candles_df["close"]=get_candles_df["mid.c"].astype("float")
	get_candles_df["open"]=get_candles_df["mid.o"].astype("float")
	get_candles_df["high"]=get_candles_df["mid.h"].astype("float")
	get_candles_df["low"]=get_candles_df["mid.l"].astype("float")
	get_candles_df["date"]=pd.to_datetime(get_candles_df["time"])
	candles_df=pd.DataFrame()
	candles_df["date"]=get_candles_df["date"]
	candles_df["open"]=get_candles_df["open"]
	candles_df["high"]=get_candles_df["high"]
	candles_df["low"]=get_candles_df["low"]
	candles_df["close"]=get_candles_df["close"]
	candles_df["volume"]=get_candles_df["volume"]
	return candles_df


## Get Current Price
def get_pricing(headers,account_id="101-011-6420983-005",instrument="AUD_USD"):
	pricing_body={"instruments":instrument}
	pricing_url="https://api-fxpractice.oanda.com/v3/accounts/"+account_id+"/pricing"
	r = requests.get(pricing_url,headers=headers,params=pricing_body)
	pricing_response={}
	pricing_response["date"]=pd.to_datetime(json.loads(r.text)["time"]).to_pydatetime()
	pricing_response["bid"]=float(json.loads(r.text)["prices"][0]["bids"][0]["price"])
	pricing_response["ask"]=float(json.loads(r.text)["prices"][0]["asks"][0]["price"])
	pricing_response["mid"]=(pricing_response["ask"]+pricing_response["bid"])/2
	pricing_response["spread"]=pricing_response["ask"]-pricing_response["bid"]
	return pricing_response



####Place Order
def place_order(headers,account_id="101-011-6420983-005",units=100000,instrument="AUD_USD"):
	order_url="https://api-fxpractice.oanda.com/v3/accounts/"+account_id+"/orders"
	order= {"order":{
			"units": units,
		    "instrument": instrument,
		    "timeInForce": "FOK",
		    "type": "MARKET",
		    "positionFill": "DEFAULT"}
		  }
	req= requests.post(order_url,headers=headers,data=json.dumps(order))
	place_order_response=json.loads(req.text)
	#print json.loads(req.text)
	return req.status_code





## Close Open Trade by ID
def close_trade(headers,trade_id,account_id="101-011-6420983-005"):
	close_trade_url="https://api-fxpractice.oanda.com/v3/accounts/"+account_id+"/trades/"+str(trade_id)+"/close"
	close_trade_req = requests.put(close_trade_url,headers=headers)
	close_trade_response = close_trade_req.status_code
	return close_trade_response


## Batch Close Trades by Long or Short - Done
def close_position(headers,account_id="101-011-6420983-005",order_type="long",instrument="AUD_USD"):
	if order_type=="long":
		close_body={"longUnits":"ALL"}
	if order_type=="short":
		close_body={"shortUnits":"ALL"}
	close_position_url= "https://api-fxpractice.oanda.com/v3/accounts/"+account_id+"/positions/"+instrument+"/close"
	req = requests.put(close_position_url,headers=headers,data=json.dumps(close_body))
	close_position_response=json.loads(req.text)
	if req.status_code==200:
		if order_type=="long":
			return json_normalize(close_position_response["longOrderFillTransaction"]["tradesClosed"])
		if order_type=="short":
			return json_normalize(close_position_response["shortOrderFillTransaction"]["tradesClosed"])
	else:
		return req.status_code

## Get List of Trades - Done
def get_trades(headers,account_id="101-011-6420983-005",instrument="",state="OPEN"):
	get_trades_url="https://api-fxpractice.oanda.com/v3/accounts/"+account_id+"/trades"
	get_trades_body={"instruments":instrument,"state":state.upper()}
	get_trades_req=requests.get(get_trades_url,headers=headers,params=get_trades_body)
	if get_trades_req.status_code==200:
		get_trades_data=json.loads(get_trades_req.text)
		get_trades_data=json_normalize(get_trades_data["trades"])
		return get_trades_data
	else:
		return get_trades_req.status_code



############ Trading Strategy ##############

### Signal Analysis
candles_df=get_candles(headers=headers,instrument="AUD_USD")
candles_df["return"]=np.log(candles_df["close"]/candles_df["close"].shift(1))*100
candles_df=candles_df[1:]
candles_df["MA-120"] = candles_df["close"].rolling(120).mean()
candles_df["MA-60"] = candles_df["close"].rolling(60).mean()
candles_df["MA-30"] = candles_df["close"].rolling(30).mean()
candles_df["MA-15"] = candles_df["close"].rolling(15).mean()
candles_df=candles_df[120:]
candles_df["Buy_Signal"] = (candles_df["close"]>candles_df["MA-120"]) & (candles_df["close"]>candles_df["MA-60"])  & (candles_df["close"]>candles_df["MA-30"])
candles_df["Long_Close"] = (candles_df["close"]<candles_df["MA-15"])
candles_df["Sell_Signal"] = (candles_df["close"]<candles_df["MA-120"]) & (candles_df["close"]<candles_df["MA-60"])  & (candles_df["close"]<candles_df["MA-30"])
candles_df["Short_Close"] = (candles_df["close"]>candles_df["MA-30"])

###Get Current Price
current_price = get_pricing(headers=headers)

#Position Confirmation
open_trades_df=get_trades(headers=headers)
if len(open_trades_df)>0:

	#Position Management
	if (current_price["mid"]<(candles_df["low"][-5:].min())) or (candles_df["Long_Close"][-2:].values[0] and candles_df["Long_Close"][-2:].values[1]) == True:
		close_all_long_orders =close_position(headers=headers,order_type="long")
		print close_all_long_orders[["tradeID","realizedPL"]]
	if (current_price["mid"]>(candles_df["high"][-5:].max())) or (candles_df["Short_Close"][-2:].values[0] and candles_df["Short_Close"][-2:].values[1]) == True:
		close_all_short_orders =close_position(headers=headers,order_type="short")
		print close_all_short_orders[["tradeID","realizedPL"]]
else:
	#print "Seek Signal"
	#Seek Buy/Sell Signal
	if (candles_df["Buy_Signal"][-3:].values[0] and candles_df["Buy_Signal"][-3:].values[1] and candles_df["Buy_Signal"][-3:].values[2])== True:
		buy_order = place_order(headers=headers,units=100000)
		print "BUY:",buy_order
	if (candles_df["Sell_Signal"][-3:].values[0] and candles_df["Sell_Signal"][-3:].values[1] and candles_df["Sell_Signal"][-3:].values[2])== True:	
		buy_order = place_order(headers=headers,units=-100000)
		print "SELL:",buy_order

 