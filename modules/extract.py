'''
py file for functions interacting with TD Ameritrade API and extracting information
'''
import sys
sys.path.append('/home/jovyan/work/modules/')

import requests
import datetime
import pandas as pd
from modules.transform import format_date, base_returns
import time
import os 
import config
import time 
    
client_id = config.TDAMERITRADE

def load_set(stock, data_dir, tail):
    df = pd.read_pickle('{}{}{}.pickle'.format(data_dir, stock, tail))
    return df

def unix_time_millis(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return int((dt - epoch).total_seconds() * 1000.0)


def get_history(stock, 
                periodType='year', 
                frequencyType='daily', 
                frequency='1', 
                periods=1, 
                startDate=None,
                endDate=None,
                extended='true'):
    
    endpoint = r"https://api.tdameritrade.com/v1/marketdata/{}/pricehistory".format(stock)
    
    payload = {'apikey':client_id,
                  'periodType':periodType,
                  'frequencyType':frequencyType,
                  'frequency': frequency,
                  'period':periods,
                  'needExtendedHoursData':extended,
                  'startDate':startDate,
                  'endDate':endDate
                  }
    
    content = requests.get(url= endpoint, params = payload)
    data = content.json()
    
    return data

def format_date(data, drop=True):
    df = pd.DataFrame(data['candles'])
    
    df['datetime'] = df['datetime'].apply(lambda x: datetime.datetime.fromtimestamp(x/1000))
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    df['minute'] = df['datetime'].dt.minute
    df['min_num'] = df['hour'] * 60 + df['minute']
    
    #if drop == True:
    #    df.drop('datetime', axis = 1, inplace = True)
    
    return df

def extract_stock(stock, data_dir=None, suffix='', 
                  periodType='year', 
                  frequencyType='daily', 
                  frequency='1', 
                  periods=1, 
                  return_df=False, 
                  extended='true',
                  endDate=None,
                  startDate=None,
                  reverse=False):
    
    stock_data = get_history(stock, 
                             periodType=periodType, 
                             frequencyType=frequencyType, 
                             frequency=frequency, 
                             periods=periods,
                             endDate=endDate,
                             startDate=startDate
                            )
    
    stock_df = format_date(stock_data)
    stock_df['SYMBOL'] = stock
    stock_df = base_returns(stock_df)
    if reverse == True:
        stock_df = stock_df.iloc[::-1]
    # save as pickle
    if data_dir:
        stock_df.to_pickle('{}{}{}.pickle'.format(data_dir, stock, suffix))
    
    if return_df:
        return stock_df
    
def extract_multi_periods(stock, data_dir=None, suffix='', 
                          periodType='day', 
                          frequencyType='minute', 
                          frequency='1', 
                          periods=10,
                          return_df=True, 
                          extended='true',
                          num_extracts=3):
    
    dt_end = datetime.datetime.now()
    endDate = unix_time_millis(dt_end)
    
    dt_start = dt_end - datetime.timedelta(days=periods)
    startDate = unix_time_millis(dt_start)
    
    df = extract_stock(stock,
                  return_df=True,
                  periodType=periodType, 
                  frequencyType=frequencyType, 
                  frequency='1',  
                  extended='true',
                  endDate=endDate,
                  startDate=startDate)
    time.sleep(.5)
    
    for i in range(1,num_extracts):
        dt_end = dt_start
        endDate = unix_time_millis(dt_end)
        dt_start = dt_end - datetime.timedelta(days=periods)
        startDate = unix_time_millis(dt_start)
        
        df = pd.concat([df, extract_stock(stock,
                  return_df=True,
                  periodType=periodType, 
                  frequencyType=frequencyType, 
                  frequency='1',  
                  extended='true',
                  endDate=endDate,
                  startDate=startDate)])
        time.sleep(.5)
        
    df.drop_duplicates(subset='datetime', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    if data_dir:
        df.to_pickle('{}{}{}.pickle'.format(data_dir, stock, suffix))
        
    return df



def timing(start=None):
    if start == None:
        now_time = time.time()
        print('Start time {}'.format(time.strftime('%c', time.localtime(now_time))))
    else:
        now_time = time.time()
        elapsed = now_time - start
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        print(f'Time elapsed {hours} hours, {mins} minues, {secs} seconds')
        print('Iteration start elapsed {}'.format(time.strftime('%c', time.localtime())))
    return now_time
    