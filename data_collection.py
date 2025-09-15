import asyncio
import os
import pandas as pd
import datetime
from dotenv import load_dotenv
import aiohttp
import json

# Windows asyncio 修正
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
API_KEY = os.getenv('ETHERSCAN_API_KEY')  # Etherscan API Key

async def get_transactions(session, contract_address, api_key):
    url = f'https://api.etherscan.io/api?module=account&action=tokentx&contractaddress={contract_address}&startblock=0&endblock=999999999&sort=asc&apikey={api_key}'
    async with session.get(url) as response:
        try:
            data = await response.json()
            print(f"DEBUG: API response for {contract_address}: {data}")  # 印出 API 回傳
            result = data.get('result', [])
            # 如果 result 是字串，嘗試轉成 list
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except Exception as e:
                    print(f"Failed to parse 'result' as JSON list: {e}")
                    result = []
            return result
        except Exception as e:
            print(f"Error in getting transactions for contract {contract_address}: {e}")
            return []

def convert_timestamp_to_readable(time_stamp):
    dt_object = datetime.datetime.utcfromtimestamp(int(time_stamp))
    return dt_object.strftime('%Y-%m-%d %H:%M:%S')

def save_to_csv(data, filename='result.csv'):
    os.makedirs('data', exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(os.path.join('data', filename), index=False)
    print(f'CSV file {filename} has been saved.')

async def main():
    async with aiohttp.ClientSession() as session:
        collected_data = []
        contract_address = '0xfbe6f37d3db3fc939f665cfe21238c11a5447831'
        transactions = await get_transactions(session, contract_address, API_KEY)
        print(f"{contract_address} → {len(transactions)} tx found")

        for tx in transactions:
            try:
                # tx 可能還是不是 dict，要先檢查
                if not isinstance(tx, dict):
                    print(f"Skipping invalid transaction data: {repr(tx)}")
                    continue

                if tx.get('to') == "0x0000000000000000000000000000000000000000":
                    continue
                token_decimal = int(tx.get('tokenDecimal', 0)) if tx.get('tokenDecimal') else 0
                amount = int(tx.get('value', 0)) / (10 ** token_decimal)
                readable_time = convert_timestamp_to_readable(tx.get('timeStamp', '0'))

                event_data = {
                    'BlockNumber': tx.get('blockNumber'),
                    'TimeStamp': readable_time,
                    'Hash': tx.get('hash'),
                    'From': tx.get('from'),
                    'To': tx.get('to'),
                    'Value': amount,
                    'TokenName': tx.get('tokenName'),
                    'TokenSymbol': tx.get('tokenSymbol')
                }

                collected_data.append(event_data)
                print("event_data:", event_data)

            except Exception as e:
                print(f"Error in transaction {repr(tx)}: {e}")
                continue

        save_to_csv(collected_data)

if __name__ == "__main__":
    asyncio.run(main())