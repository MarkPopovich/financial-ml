import config
import asyncio
import json
from tda.auth import easy_client
from tda.client import Client
from tda.streaming import StreamClient


client = easy_client(
        api_key=config.TDAMERITRADE,
        redirect_uri='https://127.0.0.1',
        token_path='./tmp_token/token.pickle')
stream_client = StreamClient(client, account_id=None)

### TO DO
### write a function or class that inserts the msg into a SQL table on gc

async def read_stream():
    await stream_client.login()
    await stream_client.quality_of_service(StreamClient.QOSLevel.EXPRESS)
    await stream_client.nasdaq_book_subs(['GOOG'])
    await stream_client.level_one_equity_subs(['GOOG'])

    stream_client.add_level_one_equity_handler(
        lambda msg: print(json.dumps(msg, indent=4)))

    stream_client.add_timesale_options_handler(
            lambda msg: print(json.dumps(msg, indent=4)))

    while True:
        await stream_client.handle_message()

asyncio.get_event_loop().run_until_complete(read_stream())