import re
from datetime import datetime
import pandas as pd

def _convert_letter_to_num(str_num):
    powers = {'B': 10 ** 9, 'M': 10 ** 6, 'K': 10 ** 3, '': 1}
    m = re.search(r"([0-9\.]+)(M|B|K|)", str_num)
    if m:
        val = m.group(1)
        mag = m.group(2)
        return float(val) * powers[mag]
    return 0.0

def _validate_dates(start, end):
    start = pd.to_datetime(start) if start else datetime(1980, 1, 1)
    end = pd.to_datetime(end) if end else datetime.today()
    return start, end

def _convert_kletter_to_num(value):
    """ Convert Korean market cap format (e.g., '5,212조 1,826억') to a numeric value. """
    powers = {'조': 10**12, '억': 10**8, '': 1}  # Korean number units
    value = value.replace(',', '')  # Remove commas for easier processing
    
    total = 0
    # Match numbers and corresponding units (조, 억)
    matches = re.findall(r'(\d+)(조|억)?', value)
    
    for match in matches:
        num = int(match[0])  # Number part
        unit = match[1] if match[1] else ''  # Unit part, default to empty if not found
        total += num * powers[unit]  # Multiply by corresponding unit power

    return total