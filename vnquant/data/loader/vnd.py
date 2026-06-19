# Copyright (c) vnquant. All rights reserved.
from typing import Union, Optional
import pandas as pd
import numpy as np
import requests
import random
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import sys
# sys.path.insert(0,'/Users/phamdinhkhanh/Documents/vnquant')
from vnquant import utils
from vnquant import configs
from vnquant.log import logger
from vnquant.data.loader.proto import DataLoadProto

API_VNDIRECT = configs.API_VNDIRECT
HEADERS = configs.HEADERS


_VND_FALLBACK_URLS = [
    "https://finfo-api.vndirect.com.vn/v4/stock_prices/",
    "https://api-finfo.vndirect.com.vn/v4/stock_prices/",
]


class DataLoaderVND(DataLoadProto):
    def __init__(self, 
        symbols: list, 
        start: Optional[Union[str, datetime]], 
        end: Optional[Union[str, datetime]], *arg, **karg):
        self.symbols = symbols
        self.start = start
        self.end = end
        super().__init__(symbols, start, end)

    def download(self):
        stock_datas = []
        symbols = self.pre_process_symbols()
        logger.info('Start downloading data symbols {} from VNDIRECT, start: {}, end: {}!'.format(symbols, self.start, self.end))
        for symbol in symbols:
            one = self.download_one(symbol)
            if one is not None and not one.empty:
                stock_datas.append(one)
            else:
                logger.warning(f"Symbol {symbol} has no data from VND, skipping.")
        if not stock_datas:
            logger.error("No data could be downloaded for any symbol from VND.")
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
        query = 'code:' + symbol + '~date:gte:' + start_date + '~date:lte:' + end_date
        try:
            delta = datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')
            size = max(delta.days + 1, 100)
        except Exception:
            size = 1000
        params = {
            "sort": "date",
            "size": size,
            "page": 1,
            "q": query
        }
        user_agent = random.choice(configs.USER_AGENTS)
        headers = dict(HEADERS)
        headers['User-Agent'] = user_agent

        data_list = None
        last_err = None
        for url in _VND_FALLBACK_URLS:
            try:
                res = requests.get(url, params=params, headers=headers,
                                   allow_redirects=True, timeout=20, verify=False)
                res.raise_for_status()
                try:
                    payload = res.json()
                except ValueError:
                    logger.warning(f"VND {url} returned non-JSON, trying next.")
                    continue
                if isinstance(payload, dict):
                    for key in ['data', 'Data', 'items', 'records', 'result']:
                        v = payload.get(key)
                        if isinstance(v, list):
                            data_list = v
                            break
                    if data_list is None and 'data' not in payload:
                        data_list = None
                elif isinstance(payload, list):
                    data_list = payload
                if data_list is not None:
                    logger.info(f"VND data fetched from {url} for {symbol}: {len(data_list)} records.")
                    break
            except requests.exceptions.RequestException as e:
                last_err = e
                logger.warning(f"VND {url} request error: {e}")
                continue
            except Exception as e:
                last_err = e
                logger.warning(f"VND {url} unexpected error: {e}")
                continue

        if data_list is None or not data_list:
            if last_err:
                logger.error(f"Data of the symbol {symbol} is not available: {last_err}")
            else:
                logger.error(f"Data of the symbol {symbol} is not available")
            return None

        try:
            data = pd.DataFrame(data_list)
            columns_lower = {c.lower(): c for c in data.columns}
            def col(*names):
                for n in names:
                    if n in data.columns:
                        return n
                    if n.lower() in columns_lower:
                        return columns_lower[n.lower()]
                return None

            code_col = col('code', 'Code', 'ticker', 'symbol') or 'code'
            date_col = col('date', 'Date', 'tradingDate', 'ngay') or 'date'
            floor_col = col('floor', 'Floor', 'san')
            basic_col = col('basicPrice', 'basic_price', 'BasicPrice')
            ceiling_col = col('ceilingPrice', 'ceiling_price')
            floor_price_col = col('floorPrice', 'floor_price')
            close_col = col('close', 'Close', 'closePrice', 'giaDongCua')
            open_col = col('open', 'Open', 'openPrice', 'giaMoCua')
            high_col = col('high', 'High', 'highPrice', 'giaCaoNhat')
            low_col = col('low', 'Low', 'lowPrice', 'giaThapNhat')
            avg_col = col('average', 'Average', 'avgPrice')
            ad_close_col = col('adClose', 'adjust', 'adjust_close', 'adClose')
            ad_open_col = col('adOpen', 'adjust_open', 'adOpen')
            ad_high_col = col('adHigh', 'adjust_high', 'adHigh')
            ad_low_col = col('adLow', 'adjust_low', 'adLow')
            ad_avg_col = col('adAverage', 'adjust_average', 'adAverage')
            change_col = col('change', 'Change', 'thayDoi')
            ad_change_col = col('adChange', 'adjust_change', 'adChange')
            pct_col = col('pctChange', 'percent_change', 'pctChange')
            nm_vol_col = col('nmVolume', 'volume_match', 'nmVolume')
            nm_val_col = col('nmValue', 'value_match', 'nmValue')
            pt_vol_col = col('ptVolume', 'volume_reconcile', 'ptVolume')
            pt_val_col = col('ptValue', 'value_reconcile', 'ptValue')

            stock_data = pd.DataFrame()
            stock_data['code'] = data[code_col] if code_col and code_col in data.columns else symbol
            stock_data['date'] = data[date_col] if date_col and date_col in data.columns else None
            stock_data['floor'] = data[floor_col] if floor_col and floor_col in data.columns else ''
            stock_data['basic_price'] = data[basic_col] if basic_col and basic_col in data.columns else np.nan
            stock_data['ceiling_price'] = data[ceiling_col] if ceiling_col and ceiling_col in data.columns else np.nan
            stock_data['floor_price'] = data[floor_price_col] if floor_price_col and floor_price_col in data.columns else np.nan
            stock_data['close'] = data[close_col] if close_col and close_col in data.columns else np.nan
            stock_data['open'] = data[open_col] if open_col and open_col in data.columns else np.nan
            stock_data['high'] = data[high_col] if high_col and high_col in data.columns else np.nan
            stock_data['low'] = data[low_col] if low_col and low_col in data.columns else np.nan
            stock_data['average'] = data[avg_col] if avg_col and avg_col in data.columns else np.nan
            stock_data['adjust_close'] = data[ad_close_col] if ad_close_col and ad_close_col in data.columns else np.nan
            stock_data['adjust_open'] = data[ad_open_col] if ad_open_col and ad_open_col in data.columns else np.nan
            stock_data['adjust_high'] = data[ad_high_col] if ad_high_col and ad_high_col in data.columns else np.nan
            stock_data['adjust_low'] = data[ad_low_col] if ad_low_col and ad_low_col in data.columns else np.nan
            stock_data['adjust_average'] = data[ad_avg_col] if ad_avg_col and ad_avg_col in data.columns else np.nan
            stock_data['change'] = data[change_col] if change_col and change_col in data.columns else np.nan
            stock_data['adjust_change'] = data[ad_change_col] if ad_change_col and ad_change_col in data.columns else np.nan
            stock_data['percent_change'] = data[pct_col] if pct_col and pct_col in data.columns else np.nan
            stock_data['volume_match'] = data[nm_vol_col] if nm_vol_col and nm_vol_col in data.columns else 0
            stock_data['value_match'] = data[nm_val_col] if nm_val_col and nm_val_col in data.columns else 0
            stock_data['volume_reconcile'] = data[pt_vol_col] if pt_vol_col and pt_vol_col in data.columns else 0
            stock_data['value_reconcile'] = data[pt_val_col] if pt_val_col and pt_val_col in data.columns else 0

            numeric_cols = [
                'basic_price', 'ceiling_price', 'floor_price',
                'close', 'open', 'high', 'low', 'average',
                'adjust_close', 'adjust_open', 'adjust_high', 'adjust_low', 'adjust_average',
                'change', 'adjust_change', 'percent_change',
                'volume_match', 'value_match', 'volume_reconcile', 'value_reconcile'
            ]
            for c in numeric_cols:
                stock_data[c] = pd.to_numeric(stock_data[c], errors='coerce')

            stock_data = stock_data.set_index('date')
            stock_data.index = pd.to_datetime(stock_data.index, errors='coerce')
            stock_data = stock_data.dropna(subset=['close'])
            stock_data.index.name = 'date'
            stock_data = stock_data.sort_index(ascending=False)
            stock_data = stock_data.ffill()
            stock_data['total_volume'] = stock_data['volume_match'].fillna(0) + stock_data['volume_reconcile'].fillna(0)
            stock_data['total_value'] = stock_data['value_match'].fillna(0) + stock_data['value_reconcile'].fillna(0)

            iterables = [stock_data.columns.tolist(), [symbol]]
            mulindex = pd.MultiIndex.from_product(iterables, names=['Attributes', 'Symbols'])
            stock_data.columns = mulindex

            logger.info('data {} from {} to {} have already cloned!' \
                         .format(symbol,
                                 utils.convert_text_dateformat(self.start, origin_type = '%d/%m/%Y', new_type = '%Y-%m-%d'),
                                 utils.convert_text_dateformat(self.end, origin_type='%d/%m/%Y', new_type='%Y-%m-%d')))
            return stock_data
        except Exception as e:
            logger.error(f"Error processing VND data for {symbol}: {e}")
            return None

# if __name__ == "__main__":  
#     loader1 = DataLoaderVND(symbols=["VND"], start="2017-01-10", end="2019-02-15")
#     print(loader1.download())
