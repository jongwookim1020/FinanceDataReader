import requests
import json
import pandas as pd
from datetime import datetime

url = 'http://data.krx.co.kr/comm/bldAttendant/executeForResourceBundle.cmd?baseName=krx.mdc.i18n.component&key=B128.bld'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd'
}
j = json.loads(requests.get(url, headers=headers).text)
date_str = j['result']['output'][0]['max_work_dt']
print("max_work_dt:", date_str)

formatted_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
print("formatted_date:", formatted_date)

csv_url = f'https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/refs/heads/master/data/listing/krx/{formatted_date}.csv'
print("csv_url:", csv_url)
try:
    df = pd.read_csv(csv_url)
    print("Columns:", df.columns)
    print("Len:", len(df))
except Exception as e:
    print(e)
