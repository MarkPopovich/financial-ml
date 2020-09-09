'''
py file for transforming data extracted from TD Ameritrade API
'''
import numpy as np
import pandas as pd
from datetime import datetime

def format_date(data):
    df = pd.DataFrame(data['candles'])
    
    df['datetime'] = df['datetime'].apply(lambda x: datetime.fromtimestamp(x/1000))
    df['date'] = df['datetime'].dt.date
    df.drop('datetime', axis = 1, inplace = True)
    
    return df

def base_returns(stock_df):
    stock_df['prev_close'] = stock_df['close'].shift(1)
    stock_df['diff_1'] = stock_df['close'].diff(1)

    stock_df['pct_change'] = stock_df['diff_1'] / stock_df['prev_close']

    log_close = stock_df['close'] / stock_df['prev_close']
    stock_df['log_return'] = log_close.apply(np.log)
    
    return stock_df

def reverse_index(stock_df):
    stock_df = stock_df.reindex(index=stock_df.index[::-1])
    stock_df.reset_index(drop=True, inplace=True)
    
    return stock_df

def month_returns(stock_df, drop_pct = False):
    for i in range(0,31):
        stock_df['pct_return_'+str(i)] = stock_df['pct_change'].shift(-i)
        
    if drop_pct == True:
        stock_df.drop('pct_change', axis=1, inplace=True)
     
    return stock_df
        

def insert_stats(stock_df):
    stock_df = base_returns(stock_df)
    stock_df = reverse_index(stock_df)
    stock_df = month_returns(stock_df)
    
    return stock_df

def set_intervals(stock_df):
    '''
    sets the interval range and intervals column 
    '''
    pass

def distribution_mapper():
    pass

def interval_iterator():
    '''
    iterates over each interval, calling distribution_mapper and adding the column to the dataframe
    '''    
    pass

