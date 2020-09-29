from google.cloud import bigquery
from urllib.error import HTTPError
import pickle
import pandas_market_calendars as pmc
from datetime import datetime
from polygon import RESTClient
import os
import requests
import pandas as pd

def call_historical(ticker, date, time=None, limit=50000):
    url = f'https://api.polygon.io/v2/ticks/stocks/trades/{ticker}/{date}'
    params = {
        'apiKey': '',
        'timestamp': time,
        'limit': limit,
    }

    try:
        res = requests.get(url, params)
    except HTTPError:
        return call_historical(ticker, data, time, limit)

    return res.json()


def load_from_csv(file_path, table_id):
    '''
    table_id = "your-project.your_dataset.your_table_name"
    '''
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1, autodetect=True,
    )

    with open(file_path, "rb") as source_file:
        job = client.load_table_from_file(source_file, table_id, job_config=job_config)

    job.result()  # Waits for the job to complete.

    table = client.get_table(table_id)  # Make an API request.
    print(
        "Loaded {} rows and {} columns to {}".format(
            table.num_rows, len(table.schema), table_id
        )
    )

def load_from_pandas(df, destination_table):
    '''
    Uses pandas-gbq client to load directly to bigquery, skipping the need to save csv's

    Specify a schema to ensure types read correctly

    destination_table: Name of table to be written, in the form dataset.tablename
    project_id: Google BigQuery Account project ID. Optional when available from the environment.
    '''
    # schema = [
    #     bigquery.SchemaField("sip_timestamp", "TIMESTAMP", mode="NULLABLE"),
    #     bigquery.SchemaField("participant_timestamp", "TIMESTAMP", mode="NULLABLE"),
    #     bigquery.SchemaField("sequence_number", "INT64", mode="NULLABLE"),
    #     bigquery.SchemaField("id", "INT64", mode="NULLABLE"),
    #     bigquery.SchemaField("exchange", "INT64", mode="NULLABLE"),
    #     bigquery.SchemaField("size", "INT64", mode="NULLABLE"),
    #     bigquery.SchemaField("price", "FLOAT64", mode="NULLABLE"),
    #     bigquery.SchemaField("tape", "INT64", mode="NULLABLE"),
    #     bigquery.SchemaField("symbol", "STRING", mode="NULLABLE"),
    # ]
    schema = [
        {'name': 'sip_timestamp', 'type': 'TIMESTAMP'},
        {'name': 'participant_timestamp', 'type': 'TIMESTAMP'},
        {'name': 'sequence_number', 'type': 'INTEGER'},
        {'name': 'id', 'type': 'INTEGER'},
        {'name': 'exchange', 'type': 'INTEGER'},
        {'name': 'size', 'type': 'INTEGER'},
        {'name': 'price', 'type': 'FLOAT'},
        {'name': 'tape', 'type': 'INTEGER'},
        {'name': 'symbol', 'type': 'STRING'},
    ]

    df.to_gbq(destination_table, table_schema=schema, if_exists='append')

def format_and_save(json, file_path=None):
    #print(json)
    df = pd.DataFrame(json['results'])

    # map the column names
    df = df.rename(key_map, axis=1)

    # add the ticker symbol
    df['symbol'] = stock

    # ensure correct types for each column
    df['sip_timestamp'] = pd.to_datetime(df['sip_timestamp'])
    df['participant_timestamp'] = pd.to_datetime(df['participant_timestamp'])
    df['id'] = df['id'].astype('int')
    df['sequence_number'] = df['sequence_number'].astype('int')
    df['exchange'] = df['exchange'].astype('int')
    df['size'] = df['size'].astype('int')
    df['price'] = df['price'].astype('float')
    df['tape'] = df['tape'].astype('int')
    df['symbol'] = df['symbol'].astype('O')

    # use only the cols as specified
    df = df[cols]
    if file_path:
        df.to_csv(file_path, index=False)
    elif file_path is None:
        return df


if __name__ == "__main__":

    client = bigquery.Client()
    key = '0URbzTqnNwTsHIe4UPz8AjazYT9vYFNq'

    limit = 50000
    cols = ['sip_timestamp', 'participant_timestamp', 'sequence_number', 'id', 'exchange', 'size', 'price', 'tape',
            'symbol']

    with open('stocks_tracker.pickle', 'rb') as f:
        stocks = pickle.load(f)

    with open('key_map.pickle', 'rb') as f:
        key_map = pickle.load(f)

    with open('days_tracker.pickle', 'rb') as f:
        day_tracker = pickle.load(f)

    for day in day_tracker['days']:
        if day in day_tracker['days_complete']:
            continue

        today = datetime.strptime(day, '%Y-%m-%d')
        for stock in stocks:
            ## complete the next block iteratively until all the data for that day is gathered
            ## complete = False
            ##
            if 'days_complete' in stocks[stock]:
                if day in stocks[stock]['days_complete']:
                    print(f'Already complete: {stock}')
                    continue

            while True:
                if 'namechange' in stocks[stock]:
                    if today < stocks[stock]['namechange']['date']:
                        stock_name = stocks[stock]['namechange']['beforename']
                    elif today >= stocks[stock]['namechange']['date']:
                        stock_name = stocks[stock]['namechange']['as_of_name']
                # grab the starttime if an end_timestamp exists, else set the starttime as None
                if stocks[stock]['timestamp_tracker']['end_timestamp'] is None:
                    starttime = None
                elif stocks[stock]['timestamp_tracker']['end_timestamp']:
                    starttime = stocks[stock]['timestamp_tracker']['end_timestamp']

                # get the json for the stock on the day with the correct symbol and starttime
                print(stock)
                print(today)
                print(starttime)
                print(limit)
                json = call_historical(stock, day, time=starttime, limit=limit)

                # format the json and save as csv
                df = format_and_save(json, file_path=None)

                # insert the json in the bigquery table

                load_from_pandas(df, 'sp500historical.csv_historic')
                # Abandoning loading from csv, keeping call for posterity
                # load_from_csv('historic_csv.csv', 'sp500historical.csv_historic')

                # set the end_timestamp as the last tick
                stocks[stock]['timestamp_tracker']['end_timestamp'] = json['results'][-1]['t']

                # if the start timestamp is None, create an entry for it
                if stocks[stock]['timestamp_tracker']['start_timestamp'] is None:
                    stocks[stock]['timestamp_tracker']['start_timestamp'] = json['results'][0]['t']


                if len(json['results']) < limit:
                    if 'days_complete' in stocks[stock]:
                        stocks[stock]['days_complete'].append(day)
                    elif 'days_complete' not in stocks[stock]:
                        stocks[stock]['days_complete'] = [day]
                    with open('stocks_tracker.pickle', 'wb') as f:
                        pickle.dump(stocks, f)
                    break

                with open('stocks_tracker.pickle', 'wb') as f:
                    pickle.dump(stocks, f)

        day_tracker['days_complete'].append(day)

        with open('day_tracker.pickle', 'wb') as f:
            pickle.dump(day_tracker, f)
