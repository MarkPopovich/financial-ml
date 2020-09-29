import pandas as pd
from polygon import RESTClient
import datetime
from functools import reduce
import pandas_market_calendars as pmc
from google.cloud import storage
import os
import sys
import time

def set_environment():
    key = '0URbzTqnNwTsHIe4UPz8AjazYT9vYFNq'
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './secrets/tpu-training-289520-f7727af0669b.json'
    storage_client = storage.Client()
    return key, storage_client

def get_sp():
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    spdf = table[0]

    spdf.loc[spdf[spdf['Symbol'] == 'LUMN'].index[0], 'Symbol'] = 'CTL'
    return spdf


def get_keymap():
    with RESTClient('0URbzTqnNwTsHIe4UPz8AjazYT9vYFNq') as client:
        resp = client.historic_trades_v2("BRK.B", "2018-03-02")

    key_map = {key: resp.map[key]['name'] for key in resp.map}
    return key_map

def get_calendar():
    nyse = pmc.get_calendar('NYSE')
    days = nyse.schedule(start_date='2020-06-23', end_date='2020-09-17').index
    return days


def recursive_ask(stock, strdate, limit, timestamp):
    try:
        current_ticks = client.historic_trades_v2(stock,
                                                  strdate,
                                                  limit=limit,
                                                  timestamp=timestamp
                                                  ).results
    except HTTPError as error:
        print(error)
        print('Asking recursively')
        time.sleep(1)
        currrent_ticks = recursive_ask(stock, strdate, limit, timestamp)

    return currrent_ticks

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
        print('Iteration start {}'.format(time.strftime('%c', time.localtime())))
    return now_time

def polygon_pull():
    stocks = get_sp()['Symbol']
    key_map = get_keymap()
    days = get_calendar()
    key, client = set_environment()
    data_path = 'gs://fin-aml/data/agg_data_pulls/'
    agg_data_path = data_path + 'gg_1mm_bars_'
    ticks_data_path = data_path + 'ticks_df.csv'


    ticks_df = pd.DataFrame()
    increment = 1000000000
    sp500 = stocks
    limit_size = 50000
    start = None
    # timer = timing()
    date_tracker = pd.DataFrame()

    # Should I just start over then?
    for date in days:
        start = timing(start)

        pd.DataFrame({'day': [date]}).to_csv(data_path + 'tracker.csv')
        # timer.iterate()

        ## TO DO
        ## Ensure that the loop gathers all the data for each day before moving on to the next day
        stock_tracker = {stock: {'laststamp': None, 'complete': False} for stock in sp500}

        strdate = date.date().strftime('%Y-%m-%d')
        laststamps = {stock: None for stock in sp500}
        print(strdate)

        for stock in sp500:
            print(stock)
            # download a batch of data and add it to the list
            while stock_tracker[stock]['complete'] == False:
                with RESTClient(key) as client:
                    try:
                        current_ticks = client.historic_trades_v2(stock,
                                                                  strdate,
                                                                  limit=limit_size,
                                                                  timestamp=stock_tracker[stock]['laststamp']
                                                                  ).results
                    except HTTPError as error:
                        print(error)
                        print('Asking recursively')
                        time.sleep(1)
                        current_ticks = recursive_ask(stock,
                                                      strdate,
                                                      limit=limit_size,
                                                      timestamp=stock_tracker[stock]['laststamp'])

                    try:
                        print(current_ticks[-1])
                    except:
                        missing_stocks.append(stock)
                        print(f'exception {stock}')
                        stock_tracker[stock]['complete'] = True
                        continue

                    stock_tracker[stock]['laststamp'] = current_ticks[-1]['t']
                    current_df = pd.DataFrame(current_ticks)
                    current_df.rename(key_map, axis=1, inplace=True)
                    current_df['sip_timestamp'] = pd.to_datetime(current_df['sip_timestamp'])
                    current_df['participant_timestamp'] = pd.to_datetime(current_df['participant_timestamp'])
                    current_df['SYMBOL'] = stock

                    ticks_df = pd.concat([ticks_df, current_df], axis=0)

                    if len(current_ticks) < limit_size:
                        stock_tracker[stock]['complete'] = True

        ticks_df.sort_values(by='sip_timestamp', ascending=True, inplace=True)
        ticks_df.drop_duplicates(subset=list(ticks_df.columns.drop('conditions')), inplace=True)
        ticks_df['dollar_volume'] = ticks_df['size'] * ticks_df['price']

        if 'dv_cumsum' in ticks_df.columns:
            cumsum_start = ticks_df['dv_cumsum'].iloc[0]
        else:
            cumsum_start = 0

        ticks_df['dv_cumsum'] = ticks_df['dollar_volume'].cumsum() + cumsum_start

        start_increment = ticks_df['dv_cumsum'].min() // increment * increment
        end_increment = ticks_df['dv_cumsum'].max() // increment * increment + increment
        int_val = pd.interval_range(start_increment, end_increment, freq=increment)
        ticks_df['interval_range'] = pd.cut(ticks_df['dv_cumsum'], int_val)

        last_interval_ticks = ticks_df['interval_range'].max()
        #     if 'interval_range' in agg_df.columns:
        #         last_interval_agg = agg_df['interval_range'].iloc[-1] + 2 * increment
        #     else:
        #         last_interval_agg = ticks_df['interval_range'].min() + 2 * increment
        last_interval_agg = ticks_df['interval_range'].min() + 2 * increment

        if last_interval_ticks > last_interval_agg:
            ## aggregate the data, insert it into agg_df, and then drop what has been aggregated from ticks_df
            mask = ticks_df['interval_range'] < ticks_df['interval_range'].max()
            agged = reduce(lambda left, right: pd.merge(left, right, how='outer', left_index=True, right_index=True), [
                ticks_df.groupby(['interval_range', 'SYMBOL'])['sip_timestamp'].first().rename('open_timestamp'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['sip_timestamp'].last().rename('close_timestamp'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['size'].sum(),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['price'].first().rename('open'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['price'].min().rename('low'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['price'].max().rename('high'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['price'].last().rename('close'),
                ticks_df.groupby(['interval_range', 'SYMBOL'])['dollar_volume'].sum()
            ])
            agged = agged[agged.index.get_level_values(0) != agged.index.get_level_values(0)[-1]]
            agged = agged.reset_index()

            agged_path = agg_data_path + strdate + '.csv'
            agged.to_csv(agged_path)
            # agg_df = pd.concat([agg_df, agged], axis=0)
            ticks_df = ticks_df[~mask]
        ticks_df.to_csv(ticks_data_path)
        # agg_df.to_csv('../data/sp500/aggregated_1mm_bars.csv')


if __name__ == '__main__':
    globals()[sys.argv[1]]()
