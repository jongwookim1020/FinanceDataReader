import sys
sys.path.insert(0, 'd:\\dev\\FinanceDataReader-dev\\FinanceDataReader\\src')
import FinanceDataReader as fdr

df = fdr.StockListing('KRX-DELISTING')
print(len(df))
print(df.head(2))
