import re
import requests
import pandas as pd
from io import StringIO
from FinanceDataReader._utils import (_convert_letter_to_num, _validate_dates)
import time

def _naver_data_reader(symbol, start, end):
    url = 'https://fchart.stock.naver.com/sise.nhn?timeframe=day&count=6000&requestType=0&symbol='
    r = requests.get(url + symbol)

    data_list = re.findall(r'<item data=\"(.*?)\" />', r.text, re.DOTALL)
    if len(data_list) == 0:
        print(f'"{symbol}" invalid symbol or has no data')
        return pd.DataFrame()
    data = '\n'.join(data_list)
    df = pd.read_csv(StringIO(data), delimiter='|', header=None, dtype={0:str})
    df.columns  = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')
    df.set_index('Date', inplace=True)
    df.sort_index(inplace=True)
    df['Change'] = df['Close'].pct_change()
    return df.loc[start:end]

class NaverDailyReader:
    def __init__(self, symbol, start=None, end=None):
        self.symbol = symbol
        self.source, self.code = symbol.split(':') if ':' in symbol else (None, symbol)
        self.start, self.end = _validate_dates(start, end)

    def read(self):
        # single code
        if ',' not in self.code: 
            return _naver_data_reader(self.code, self.start, self.end)
        
        # multiple codes, merge close price data as columns
        code_list = [s.strip() for s in self.code.split(',') if s]
        df_list = []
        for sym in code_list:
            try:
                df = _naver_data_reader(sym, self.start, self.end)
            except Exception as e:
                print(e, f' - "{sym}" not found or invalid periods')
            df_list.append(df.loc[self.start:self.end])
        merged = pd.concat([x['Close'] for x in df_list], axis=1)
        merged.columns = code_list
        merged.attrs = {'exchange':'KRX', 'source':'NAVER', 'data':'PRICE'}
        return merged

def _naver_crypto_data_reader(symbol, start, end, exchange="UPBIT", market_type="KRW"):
    """
    Read crypto daily OHLCV data from Naver Stock (UPBIT Market).
    """
    start_str = start.strftime('%Y-%m-%dT00:00:00')
    end_str = end.strftime('%Y-%m-%dT23:59:59')
    
    url = (
        f"https://m.stock.naver.com/front-api/chart/cryptoChartData"
        f"?exchangeType={exchange}&nfTicker={symbol}&marketType={market_type}&type=days&interval=1"
        f"&from={start_str}&to={end_str}"
    )
    
    max_retries = 5
    request_timeout = 10
    pause_seconds = 1  # How long to pause between retries
    
    for attempt in range(max_retries):
        try:
            time.sleep(pause_seconds)
            r = requests.get(url, headers={'user-agent': 'Mozilla/5.0 AppleWebKit/537.36'}, timeout=request_timeout)
            r.raise_for_status()
            break
        except requests.exceptions.Timeout:
            print(f"Timeout occurred for {symbol}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {symbol}: {e}")
    else:
        print(f"Failed to fetch data for {symbol} after {max_retries} attempts.")
        return None

    jo = r.json()
    if not jo.get('isSuccess', False):
        print(f"Failed to get valid data for {symbol}.")
        return None

    raw_data = jo.get('result', [])
    if not raw_data:
        print(f"No data found for {symbol}.")
        return None

    records = []
    for item in raw_data:
        records.append({
            # "Date": pd.to_datetime(item['tradeBaseAt']).normalize(),
            "Date": pd.to_datetime(item['tradeBaseAt']).tz_convert(None).normalize(),
            "Open": item['openPrice'],
            "High": item['highPrice'],
            "Low": item['lowPrice'],
            "Close": item['closePrice'],
            "Volume": item['accumulatedTradingVolume']
        })

    df = pd.DataFrame(records)
    df = df.set_index('Date')
    return df

class NaverCryptoDailyReader:
    def __init__(self, symbol, start=None, end=None, exchange="UPBIT", market_type="KRW"):
        start, end = _validate_dates(start, end)
        self.start = start
        self.end = end
        self.symbol = symbol.upper()
        self.exchange = exchange.upper()
        self.market_type = market_type.upper()

    def read(self):
        if ',' not in self.symbol:
            return _naver_crypto_data_reader(self.symbol, self.start, self.end, self.exchange, self.market_type)

        # multiple symbols
        df_list = []
        sym_list = [s.strip() for s in self.symbol.split(',') if s]
        for sym in sym_list:
            df = _naver_crypto_data_reader(sym, self.start, self.end, self.exchange, self.market_type)
            if df is not None:
                df = df[['Close']]  # Only Close price
                df = df.rename(columns={'Close': sym})
                df_list.append(df)
        merged = pd.concat(df_list, axis=1)
        merged.attrs = {'exchange': self.exchange, 'source': 'NAVER', 'data': 'CRYPTO'}
        return merged