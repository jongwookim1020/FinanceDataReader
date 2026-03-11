import requests
import json
import pandas as pd
from datetime import datetime

url = 'http://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd?baseName=krx.mdc.i18n.component&key=B128.bld'
headers = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://data.krx.co.kr/'
}
j = json.loads(requests.get(url, headers=headers).text)
date_str = j['result']['output'][0]['max_work_dt']
formatted_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
csv_url = f'https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/refs/heads/master/data/listing/delisting/{formatted_date}.csv'
print('csv_url:', csv_url)
try:
    df = pd.read_csv(csv_url)
    print("Cols:", df.columns)
    print("Len:", len(df))
    print(df.head(2))
    print(df.tail(2))
except Exception as e:
    print(e)
