# Copyright (c) vnquant. All rights reserved.
import pandas as pd
import numpy as np
import requests
import random
from typing import Optional
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import sys
# sys.path.insert(0,'/Users/phamdinhkhanh/Documents/vnquant')
from vnquant import configs
from vnquant.data.loader.proto import DataLoadProto
from vnquant.log import logger
from vnquant.utils import utils

URL_VND = configs.URL_VND
API_VNDIRECT = configs.API_VNDIRECT
URL_CAFE = configs.URL_CAFE
HEADERS = configs.HEADERS
REGEX_PATTERN_PRICE_CHANGE_CAFE = configs.REGEX_PATTERN_PRICE_CHANGE_CAFE
STOCK_COLUMNS_CAFEF = configs.STOCK_COLUMNS_CAFEF
STOCK_COLUMNS_CAFEF_FINAL = configs.STOCK_COLUMNS_CAFEF_FINAL

_CAFE_FALLBACK_URLS = [
    "https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx",
    "https://s.cafef.vn/Lich-su-giao-dich/-1.chn",
    "https://finance.vietstock.vn/data/eventstypedata",
]

_CAFE_FIELD_MAP = {
    'code': ['code', 'Symbol', 'Ma', 'StockCode', 'MCK'],
    'date': ['Ngay', 'date', 'NgayGiaoDich', 'TradingDate', 'Date'],
    'close': ['GiaDongCua', 'close', 'ClosePrice', 'GiaDTCua', 'GiaDongCua2'],
    'open': ['GiaMoCua', 'open', 'OpenPrice', 'GiaMoCua2'],
    'high': ['GiaCaoNhat', 'high', 'HighPrice', 'GiaCaoNhat2'],
    'low': ['GiaThapNhat', 'low', 'LowPrice', 'GiaThapNhat2'],
    'adjust_price': ['GiaDieuChinh', 'adjust_price', 'AdjClose', 'GiaDieuChinh2', 'AdjPrice'],
    'change_str': ['ThayDoi', 'change_str', 'Change', 'ThayDoi2'],
    'volume_match': ['KhoiLuongKhopLenh', 'volume_match', 'Volume', 'KLGiaoDich', 'KLKhopLenh'],
    'value_match': ['GiaTriKhopLenh', 'value_match', 'Value', 'GTGiaoDich', 'GTKhopLenh'],
    'volume_reconcile': ['KLThoaThuan', 'volume_reconcile', 'PutthroughVolume', 'KLThoaThuan2'],
    'value_reconcile': ['GtThoaThuan', 'value_reconcile', 'PutthroughValue', 'GTThoaThuan2'],
}


def _cafe_robust_get(symbol: str, start_date: str, end_date: str,
                     max_retries: int = 3, timeout: int = 20) -> list:
    '''
    Robust CAFE data fetcher: tries multiple URL endpoints, handles 301 redirects,
    accepts flexible JSON shapes, and returns a list of raw data dicts (or empty list).
    '''
    urls_to_try = [URL_CAFE] + [u for u in _CAFE_FALLBACK_URLS if u != URL_CAFE]
    user_agent = random.choice(configs.USER_AGENTS)

    for url in urls_to_try:
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': 'https://s.cafef.vn/',
                }
                params = {
                    "Symbol": symbol,
                    "StartDate": start_date,
                    "EndDate": end_date,
                    "PageIndex": 1,
                    "PageSize": 9999,
                }
                res = requests.get(url, params=params, headers=headers,
                                   allow_redirects=True, timeout=timeout,
                                   verify=False)
                res.raise_for_status()
                try:
                    payload = res.json()
                except ValueError:
                    logger.warning(f"CAFE {url} returned non-JSON (status {res.status_code}), trying next.")
                    continue
                data_list = None
                if isinstance(payload, list):
                    data_list = payload
                elif isinstance(payload, dict):
                    for key in ['Data', 'data', 'DataList', 'items', 'result', 'records']:
                        val = payload.get(key)
                        if isinstance(val, list):
                            data_list = val
                            break
                        if isinstance(val, dict):
                            for sub_key in ['Data', 'data', 'items', 'records']:
                                sub_val = val.get(sub_key)
                                if isinstance(sub_val, list):
                                    data_list = sub_val
                                    break
                            if data_list:
                                break
                if data_list is None:
                    logger.warning(f"CAFE {url} JSON shape unrecognized, trying next.")
                    continue
                if not data_list:
                    logger.warning(f"CAFE {url}: empty data list for {symbol}")
                    continue
                logger.info(f"CAFE data fetched from {url} for {symbol}: {len(data_list)} records.")
                return data_list
            except requests.exceptions.RequestException as e:
                logger.warning(f"CAFE {url} request error (attempt {attempt+1}/{max_retries}): {e}")
                continue
            except Exception as e:
                logger.warning(f"CAFE {url} unexpected error (attempt {attempt+1}/{max_retries}): {e}")
                continue
    logger.error(f"CAFE all endpoints failed for symbol {symbol}")
    return []


def _normalize_cafe_data(raw_rows: list, symbol: str) -> Optional[pd.DataFrame]:
    '''
    Normalize raw CAFE data rows into a DataFrame with our standard column set.
    Uses flexible field mapping so minor JSON field renames don't break the pipeline.
    Returns None if normalization fails.
    '''
    if not raw_rows:
        return None
    try:
        df = pd.DataFrame(raw_rows)
    except Exception as e:
        logger.error(f"Failed to convert CAFE raw data to DataFrame: {e}")
        return None
    if df.empty:
        return None
    df['code'] = symbol
    out = pd.DataFrame()
    for std_col, candidate_keys in _CAFE_FIELD_MAP.items():
        found = None
        for ck in candidate_keys:
            if ck in df.columns:
                found = ck
                break
        if found is not None:
            out[std_col] = df[found]
        elif std_col == 'code':
            out[std_col] = symbol
        else:
            out[std_col] = None
    required = ['date', 'close', 'open', 'high', 'low']
    missing_required = [c for c in required if c not in out.columns or out[c].isna().all()]
    if missing_required:
        logger.error(f"CAFE data missing required fields after normalization: {missing_required}")
        return None
    out['change_str'] = out['change_str'].fillna('').astype(str)
    return out


class DataLoaderCAFE(DataLoadProto):
    def __init__(self, symbols, start, end, *arg, **karg):
        self.symbols = symbols
        self.start = start
        self.end = end
        super(DataLoaderCAFE, self).__init__(symbols, start, end)

    def download(self):
        stock_datas = []
        symbols = self.pre_process_symbols()
        logger.info('Start downloading data symbols {} from CAFEF, start: {}, end: {}!'.format(symbols, self.start, self.end))

        for symbol in symbols:
            one = self.download_one(symbol)
            if one is not None and not one.empty:
                stock_datas.append(one)
            else:
                logger.warning(f"Symbol {symbol} has no data, skipping.")

        if not stock_datas:
            logger.error("No data could be downloaded for any symbol from CAFE.")
            return pd.DataFrame()
        data = pd.concat(stock_datas, axis=1)
        data = data.sort_index(ascending=False)
        return data

    def download_one(self, symbol):
        try:
            start_date = utils.convert_text_dateformat(self.start, origin_type='%d/%m/%Y', new_type='%Y-%m-%d')
            end_date = utils.convert_text_dateformat(self.end, origin_type='%d/%m/%Y', new_type='%Y-%m-%d')
        except Exception as e:
            logger.error(f"Date parse error for {symbol}: {e}")
            return None
        raw = _cafe_robust_get(symbol, start_date, end_date)
        if not raw:
            logger.error(f"Data of the symbol {symbol} is not available")
            return None
        stock_data = _normalize_cafe_data(raw, symbol)
        if stock_data is None or stock_data.empty:
            logger.error(f"Normalized data empty for {symbol}")
            return None
        try:
            stock_change = stock_data['change_str'].str.extract(REGEX_PATTERN_PRICE_CHANGE_CAFE, expand=True)
            stock_change.columns = ['change', 'percent_change']
            stock_data = pd.concat([stock_data, stock_change], axis=1)
            final_cols = [c for c in STOCK_COLUMNS_CAFEF_FINAL if c != 'code']
            for c in final_cols:
                if c not in stock_data.columns:
                    stock_data[c] = np.nan
            stock_data = stock_data[STOCK_COLUMNS_CAFEF_FINAL]

            list_numeric_columns = [
                'close', 'open', 'high', 'low', 'adjust_price',
                'change', 'percent_change',
                'volume_match', 'value_match', 'volume_reconcile', 'value_reconcile'
            ]
            for c in list_numeric_columns:
                if c in stock_data.columns:
                    stock_data[c] = pd.to_numeric(stock_data[c], errors='coerce')

            stock_data = stock_data.set_index('date')
            try:
                stock_data.index = pd.to_datetime(stock_data.index, format='%d/%m/%Y', errors='coerce')
            except Exception:
                stock_data.index = pd.to_datetime(stock_data.index, errors='coerce')
            stock_data = stock_data.dropna(subset=['close'])
            stock_data.index.name = 'date'
            stock_data = stock_data.sort_index(ascending=False)
            stock_data = stock_data.ffill()
            stock_data['total_volume'] = stock_data.get('volume_match', 0).fillna(0) + \
                                         stock_data.get('volume_reconcile', 0).fillna(0)
            stock_data['total_value'] = stock_data.get('value_match', 0).fillna(0) + \
                                        stock_data.get('value_reconcile', 0).fillna(0)

            iterables = [stock_data.columns.tolist(), [symbol]]
            mulindex = pd.MultiIndex.from_product(iterables, names=['Attributes', 'Symbols'])
            stock_data.columns = mulindex

            logger.info('data {} from {} to {} have already cloned!' \
                         .format(symbol,
                                 utils.convert_text_dateformat(self.start, origin_type = '%d/%m/%Y', new_type = '%Y-%m-%d'),
                                 utils.convert_text_dateformat(self.end, origin_type='%d/%m/%Y', new_type='%Y-%m-%d')))
            return stock_data
        except Exception as e:
            logger.error(f"Error processing CAFE data for {symbol}: {e}")
            return None
    
# if __name__ == "__main__":  
#     loader2 = DataLoaderCAFE(symbols=["VND"], start="2017-01-10", end="2019-02-15")
#     print(loader2.download())
