import requests
import json
from json.decoder import JSONDecodeError
import pandas as pd
from bs4 import BeautifulSoup

from FinanceDataReader._utils import (_convert_letter_to_num, _validate_dates, _convert_kletter_to_num)

__tqdm_msg = '''
tqdm not installed. please install as follows

pip install tqdm
'''

class NaverStockListing:
    def __init__(self, market):
        self.market = market.upper()
        
    def read(self):
        verbose, raw = 1, False
        # verbose: 0=미표시, 1=진행막대와 진척율 표시, 2=진행상태 최소표시
        # raw: 원본 데이터를 반환
        exchange_map = {
            'NYSE':'NYSE', 
            'NASDAQ':'NASDAQ', 
            'AMEX':'AMEX',
            'SSE':'SHANGHAI',
            'SZSE':'SHENZHEN',
            'HKEX':'HONG_KONG',
            'TSE':'TOKYO',
            'HOSE':'HOCHIMINH', 
            'KRX':'all', 
            'KOSPI':'KOSPI', 
            'KOSDAQ':'KOSDAQ', 
        }
        try:
            exchange = exchange_map[self.market]
        except KeyError as e:
            raise ValueError(f'exchange "{self.market}" does not support')

        try:
            from tqdm import tqdm
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(__tqdm_msg)
                
        # phase 1 : http://api.stock.naver.com/stock/exchange/KOSPI/marketValue?page=1&pageSize=3
        #           http://api.stock.naver.com/stock/exchange/NASDAQ/marketValue?page=1&pageSize=3
        # phase 2 : https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category=all&pageSize=3&domesticStockExchangeType=KRX&page=1
        #           https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category=KOSPI&pageSize=50&domesticStockExchangeType=KRX&page=1
        #           https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category=KOSDAQ&pageSize=50&domesticStockExchangeType=KRX&page=1
        #           https://m.stock.naver.com/front-api/worldstock/exchange/stock/list?stockExchangeType=NASDAQ&stockPriceSortType=marketValue&page=1&pageSize=3
        # phase 3 : https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=ALL&orderType=marketSum&startIdx=0&pageSize=3
        #           https://stock.naver.com/api/foreign/market/stock/global?nation=USA&tradeType=NSQ&orderType=marketValue&startIdx=0&pageSize=3
        if exchange.upper() == 'ALL':
            url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page=1'
        elif exchange.upper() == 'KOSPI':
            url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page=1'
        elif exchange.upper() == 'KOSDAQ':
            url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page=1'
        else:
            url = f'http://api.stock.naver.com/stock/exchange/{exchange}/marketValue?page=1&pageSize=60'
        headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        try:
            r = requests.get(url, headers=headers)
            jo = json.loads(r.text)
            soup = BeautifulSoup(r.text, 'html.parser')
        except JSONDecodeError as e:
            print(soup.text)
            raise Exception(f'{r.status_code} "{r.reason}" Server response delayed. Retry later.')
            
        if verbose == 1:
            total = jo.get('totalCount') or jo.get('result', {}).get('totalCount', 0)
            t = tqdm(total=total)

        df_list = []
        for page in range(100): 
            if exchange.upper() == 'ALL':
                url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page={page+1}'
            elif exchange.upper() == 'KOSPI':
                url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page={page+1}'
            elif exchange.upper() == 'KOSDAQ':
                url = f'https://m.stock.naver.com/front-api/stock/domestic/stockList?sortType=marketValue&category={exchange}&pageSize=50&domesticStockExchangeType=KRX&page={page+1}'
            else:
                url = f'http://api.stock.naver.com/stock/exchange/{exchange}/marketValue?page={page+1}&pageSize=60'
            try:
                r = requests.get(url, headers=headers)
                jo = json.loads(r.text)
            except JSONDecodeError as e:
                print(r.text)
                raise Exception(f'{r.status_code} "{r.reason}" Server response delayed. Retry later.')

            df = pd.DataFrame(jo.get('stocks') or jo.get('result', {}).get('stocks', []))
            if 'stockEndType' in df.columns:
                df = df[df['stockEndType'] == 'stock']
            if not len(df):
                break
            if verbose == 1:
                t.update(len(df))
            elif verbose == 2:
                print('.', end='')
            df_list.append(df)
        if verbose == 1:
            t.close()
            t.clear()
        elif verbose == 2:
            print()
        merged = pd.concat(df_list)
        if raw:
            return merged 
        
        # merged['_code'] = merged['industryCodeType'].apply(lambda x: x['code'] if x else '')
        # merged['_industryGroupKor'] = merged['industryCodeType'].apply(lambda x: x['industryGroupKor'] if x else '')
        # ren_cols = {'symbolCode':'Symbol', 
        #             'stockNameEng':'Name', 
        #             '_code': 'IndustryCode',
        #             '_industryGroupKor':'Industry',
        # }

        if 'marketValueKrwHangeul' in merged.columns:
            merged['marketValueKrwHangeul'] = merged['marketValueKrwHangeul'].apply(_convert_kletter_to_num)
            ren_cols = {'symbolCode': 'Code', 
                        'stockNameEng': 'Name', 
                        'marketValueKrwHangeul': 'Marcap'}
        elif 'marketValueHangeul' in merged.columns:
            merged['marketValueHangeul'] = merged['marketValueHangeul'].apply(_convert_kletter_to_num)
            ren_cols = {'itemCode': 'Code', 
                        'stockName': 'Name', 
                        'marketValueHangeul': 'Marcap'}
        else:
            raise ValueError('Neither "marketValueKrwHangeul" nor "marketValueHangeul" found in data.')

        merged = merged[ren_cols.keys()]
        merged.rename(columns=ren_cols, inplace=True)
        merged.reset_index(drop=True, inplace=True)
        merged.attrs = {'exchange':'KRX', 'source':'NAVER', 'data':'LISTINGS'}
        return merged

class NaverEtfListing:
    def __init__(self, country):
        self.country = country.upper()
        
    def read(self):
        if self.country == "KR": return self.read_kr()
        elif self.country == "US": return self.read_us()
        else: raise ValueError(f'country "{self.country}" does not support')

    def read_kr(self):
        url = 'https://finance.naver.com/api/sise/etfItemList.nhn'
        r = requests.get(url)
        df = pd.DataFrame(r.json()['result']['etfItemList'])
        rename_cols = {
            'amonut':'Amount', 'changeRate':'ChangeRate', 'changeVal':'Change', 
            'etfTabCode':'Category', 'itemcode':'Symbol', 'itemname':'Name', 
            'marketSum':'MarCap', 'nav':'NAV', 'nowVal':'Price', 
            'quant':'Volume', 'risefall':'RiseFall', 'threeMonthEarnRate':'EarningRate'
        }
        # 'Symbol', 'Name', 'Price', 'NAV', 'EarningRate', 'Volume', 
        # 'Change', 'ChangeRate', 'Amount', 'MarCap', 'EarningRate'
        df = df.rename(columns=rename_cols)
        df.attrs = {'exchange':'KRX', 'source':'NAVER', 'data':'LISTINGS'}
        return df

    # 해외 ETF 수집 업데이트 건의 #198
    def read_us(self):
        verbose, raw = 1, False
        # verbose: 0=미표시, 1=진행막대와 진척율 표시, 2=진행상태 최소표시
        # raw: 원본 데이터를 반환
        try:
            from tqdm import tqdm
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(__tqdm_msg)
                
        url = f'https://api.stock.naver.com/etf/priceTop?page=1&pageSize=60'
        headers={'user-agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers)
            jo = json.loads(r.text)
        except JSONDecodeError as e:
            print(r.text)
            raise Exception(f'{r.status_code} "{r.reason}" Server response delayed. Retry later.')
            
        if verbose == 1:
            t = tqdm(total=jo['totalCount'])

        df_list = []
        for page in range(100): 
            url = f'https://api.stock.naver.com/etf/priceTop?page={page+1}&pageSize=60'
            try:
                r = requests.get(url, headers=headers)
                jo = json.loads(r.text)
            except JSONDecodeError as e:
                print(r.text)
                raise Exception(f'{r.status_code} "{r.reason}" Server response delayed. Retry later.')

            df = pd.DataFrame(jo['etfs'])
            if not len(df):
                break
            if verbose == 1:
                t.update(len(df))
            elif verbose == 2:
                print('.', end='')
            df_list.append(df)
        if verbose == 1:
            t.close()
            t.clear()
        elif verbose == 2:
            print()
        merged = pd.concat(df_list)
        if raw:
            return merged 
        
        ren_cols = {'symbolCode':'Symbol', 
                    'stockNameEng':'Name', 
        }
        merged = merged[ren_cols.keys()]
        merged.rename(columns=ren_cols, inplace=True)
        merged.reset_index(drop=True, inplace=True)
        merged.attrs = {'exchange':'KRX', 'source':'NAVER', 'data':'LISTINGS'}
        return merged
    
class NaverCryptoListing:
    def __init__(self, exchange='UPBIT'):
        self.exchange = exchange.upper()

    def read(self):
        verbose, raw = 1, False
        try:
            from tqdm import tqdm
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(__tqdm_msg)

        url = f'https://m.stock.naver.com/front-api/crypto/top?exchangeType={self.exchange}&sortType=marketValue&pageSize=60'
        headers = {'user-agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()  # Raise an exception for HTTP errors
            jo = r.json()
            if not jo['isSuccess']:
                raise Exception(f"API request failed: {jo['message']}")
        except JSONDecodeError as e:
            print(r.text)
            raise Exception(f'Failed to decode JSON: {e}')
        except requests.exceptions.RequestException as e:
            raise Exception(f'Request failed: {e}')

        total_count = 1000 # 실제 totalCount는 API 응답에 없으므로, 충분히 큰 값으로 설정
        if verbose == 1:
            t = tqdm(total=total_count)

        df_list = []
        page = 0
        while True:
            current_url = f'https://m.stock.naver.com/front-api/crypto/top?exchangeType={self.exchange}&sortType=marketValue&pageSize=60&page={page + 1}'
            try:
                r = requests.get(current_url, headers=headers)
                r.raise_for_status()
                jo = r.json()
                if not jo['isSuccess']:
                    raise Exception(f"API request failed on page {page + 1}: {jo['message']}")
                contents = jo['result']['contents']
            except (JSONDecodeError, requests.exceptions.RequestException) as e:
                print(f"Error fetching page {page + 1}: {e}")
                break

            df = pd.DataFrame(contents)
            if not len(df):
                break
            if verbose == 1:
                t.update(len(df))
            elif verbose == 2:
                print('.', end='')
            df_list.append(df)
            page += 1
            if page * 60 >= total_count: # 안전 장치
                break

        if verbose == 1:
            t.close()
            t.clear()
        elif verbose == 2:
            print()

        merged = pd.concat(df_list)
        if raw:
            return merged

        ren_cols = {
            'exchangeTicker': 'Symbol',
            # 'nfTicker': 'Symbol',
            'enName': 'Name',
            'tradePrice': 'Price',
            'marketCap': 'Marcap',
            'changeRate': 'ChangeRate',
            'changeValue': 'Change',
            'accumulatedTradingVolume': 'Volume',
            'accumulatedTradingValue': 'Amount',
        }
        merged = merged[ren_cols.keys()]
        merged.rename(columns=ren_cols, inplace=True)
        merged.reset_index(drop=True, inplace=True)
        merged.attrs = {'exchange': self.exchange, 'source': 'NAVER', 'data': 'CRYPTO_LISTINGS'}
        return merged