# Copyright (c) vnquant. All rights reserved.
from typing import Union, Optional, List
import requests
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# import sys
# sys.path.insert(0, '/Users/phamdinhkhanh/Documents/vnquant')
import pandas as pd
import numpy as np
import pytz
from vnquant import configs
from vnquant.data.loader import DataLoaderVND, DataLoaderCAFE
from vnquant.log import logger


URL_VND = configs.URL_VND
API_VNDIRECT = configs.API_VNDIRECT
URL_CAFE = configs.URL_CAFE
HEADERS = configs.HEADERS
UTC7 = pytz.timezone('Asia/Bangkok')
VALID_PERIODS = ['D', 'W', 'M']
PERIOD_NAMES = {'D': 'daily', 'W': 'weekly', 'M': 'monthly'}

class DataLoader():
    '''
    The DataLoader class is designed to facilitate the downloading and structuring of stock data from different data sources. 
    It supports customization in terms of data sources, time frames, and data formatting.
    '''
    def __init__(self, 
        symbols: Union[str, list], 
        start: Optional[Union[str, datetime]]=None,
        end: Optional[Union[str, datetime]]=None, 
        data_source: str='CAFE', 
        minimal: bool=True,
        table_style: str='levels',
        *arg, **karg):
        '''
        Args:
            - symbols (Union[str, list]): A single stock symbol as a string or multiple stock symbols as a list of strings.
            - start (Optional[Union[str, datetime]], default=None): The start date for the data. Can be a string in the format 'YYYY-MM-DD' or a datetime object.
            - end (Optional[Union[str, datetime]], default=None): The end date for the data. Can be a string in the format 'YYYY-MM-DD' or a datetime object.
            - data_source (str, default='CAFE'): The data source to be used for downloading stock data. Currently supports 'CAFE' and 'VND'.
            - minimal (bool, default=True): If True, returns a minimal set of columns which are important. If False, returns all available columns.
            - table_style (str, default='levels'): The style of the returned table. Options are 'levels', 'prefix', and 'stack'.
        Return:
            - DataFrame: A pandas DataFrame containing the stock data with columns formatted according to the specified table_style.
        '''
        self.symbols = symbols
        self.start = start
        self.end = end
        self.data_source = data_source
        self.minimal = minimal
        self.table_style = table_style
    
    def download(self):
        if str.lower(self.data_source) == 'vnd':
            loader = DataLoaderVND(self.symbols, self.start, self.end)
            stock_data = loader.download()
        else:
            loader = DataLoaderCAFE(self.symbols, self.start, self.end)
            stock_data = loader.download()
        
        if self.minimal:
            if str.lower(self.data_source) == 'vnd':
                stock_data = stock_data[['code', 'high', 'low', 'open', 'close', 'adjust_close', 'volume_match', 'value_match']]
            else:
                stock_data = stock_data[['code', 'high', 'low', 'open', 'close', 'adjust_price', 'volume_match', 'value_match']]
            # Rename columns adjust_close or adjust_price to adjust
            list_columns_names = stock_data.columns.names
            list_tupple_names = stock_data.columns.values
            
            for i, (metric, symbol) in enumerate(list_tupple_names):
                if metric in ['adjust_price', 'adjust_close']:
                    list_tupple_names[i] = ('adjust', symbol)

            stock_data.columns = pd.MultiIndex.from_tuples(
                list_tupple_names,
                names=list_columns_names
            )
        if self.table_style == 'levels':
            return stock_data

        if self.table_style == 'prefix':
            new_column_names = [f'{symbol}_{attribute}' for attribute, symbol in stock_data.columns]
            stock_data.columns = new_column_names
            return stock_data

        if self.table_style == 'stack':
            stock_data = stock_data.stack('Symbols').reset_index().set_index('date')
            stock_data.pop('Symbols')
            new_columns = [col if col!='Symbols' else 'code' for col in list(stock_data.columns)]
            stock_data.columns = new_columns
            return stock_data

    def _convert_to_utc7(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize(UTC7)
        else:
            df.index = df.index.tz_convert(UTC7)
        return df.sort_index()

    def _resample_daily_to_period(self, df_daily: pd.DataFrame, period: str) -> pd.DataFrame:
        if period not in VALID_PERIODS:
            raise ValueError(f"Invalid period: {period}. Must be one of {VALID_PERIODS}")
        if period == 'D':
            return df_daily.copy()
        df = df_daily.copy()
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'adjust': 'last',
            'adjust_close': 'last',
            'adjust_price': 'last',
            'volume_match': 'sum',
            'value_match': 'sum',
            'volume_reconcile': 'sum',
            'value_reconcile': 'sum',
            'total_volume': 'sum',
            'total_value': 'sum',
            'change': 'last',
            'adjust_change': 'last',
            'percent_change': 'last',
            'basic_price': 'last',
            'ceiling_price': 'last',
            'floor_price': 'last',
            'average': 'last',
            'adjust_open': 'last',
            'adjust_high': 'last',
            'adjust_low': 'last',
            'adjust_average': 'last',
            'floor': 'last',
            'code': 'last',
        }
        attrs_in_df = set(df.columns.get_level_values('Attributes').unique())
        agg_dict = {}
        for attr, sym in df.columns:
            if attr in ohlc_dict and attr in attrs_in_df:
                agg_dict[(attr, sym)] = ohlc_dict[attr]
        if period == 'W':
            rule = 'W-FRI'
            label = 'right'
        elif period == 'M':
            rule = 'ME'
            label = 'right'
        else:
            rule = 'D'
            label = 'right'
        resampled = df.resample(rule=rule, label=label).agg(agg_dict)
        resampled = resampled.dropna(how='all')
        return resampled

    def _align_and_impute(self, df: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
        df = df.copy()
        df = df.sort_index()
        full_idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq, tz=df.index.tz)
        original_idx_set = set(df.index)
        df = df.reindex(full_idx)
        is_imputed = ~df.index.isin(original_idx_set)
        ohlc_cols = [c for c in df.columns.get_level_values('Attributes').unique() 
                     if c in ['open', 'high', 'low', 'close', 'adjust', 'adjust_close', 'adjust_price']]
        for attr in ohlc_cols:
            cols = [(attr, s) for s in df.columns.get_level_values('Symbols').unique() 
                    if (attr, s) in df.columns]
            if cols:
                df[cols] = df[cols].ffill()
        symbols = df.columns.get_level_values('Symbols').unique()
        impute_cols = pd.MultiIndex.from_tuples(
            [('is_imputed', s) for s in symbols], names=['Attributes', 'Symbols']
        )
        impute_arr = np.tile(np.asarray(is_imputed).reshape(-1, 1), (1, len(symbols)))
        impute_df = pd.DataFrame(impute_arr, index=df.index, columns=impute_cols)
        result = pd.concat([df, impute_df], axis=1)
        return result

    def download_single_source_periods(self, source: str, periods: List[str]) -> dict:
        loader_cls = DataLoaderVND if source.upper() == 'VND' else DataLoaderCAFE
        loader = loader_cls(self.symbols, self.start, self.end)
        df_daily = loader.download()
        df_daily = self._convert_to_utc7(df_daily)
        df_daily = df_daily.sort_index()
        result = {}
        for p in periods:
            if p not in VALID_PERIODS:
                raise ValueError(f"Invalid period '{p}', must be one of {VALID_PERIODS}")
            df_p = self._resample_daily_to_period(df_daily, p)
            freq_map = {'D': 'D', 'W': 'W-FRI', 'M': 'ME'}
            freq = freq_map[p]
            df_p = self._align_and_impute(df_p, freq=freq)
            result[p] = df_p
        return result

    def download_panel(self, periods: Optional[List[str]] = None,
                       data_sources: Optional[List[str]] = None) -> dict:
        '''
        Download multi-period aligned panel data from multiple sources.
        
        Args:
            periods: List of periods, e.g. ['D', 'W', 'M'] for daily/weekly/monthly.
                     Defaults to ['D', 'W', 'M'].
            data_sources: List of data sources, e.g. ['VND', 'CAFE']. Defaults to both.
        
        Returns:
            dict: Nested dict:
                {
                    'VND': {'D': DataFrame, 'W': DataFrame, 'M': DataFrame},
                    'CAFE': {'D': DataFrame, 'W': DataFrame, 'M': DataFrame}
                }
                Each DataFrame contains OHLCV per symbol plus is_imputed flag per symbol,
                index is UTC+7 DatetimeIndex, aligned per period with forward-filled gaps
                and skip-holiday empty segments (non-trading gaps are not filled with 0s
                but the price/volume attributes are forward-filled where possible).
        '''
        if periods is None:
            periods = ['D', 'W', 'M']
        if data_sources is None:
            data_sources = ['VND', 'CAFE']
        for p in periods:
            if p not in VALID_PERIODS:
                raise ValueError(f"Invalid period '{p}': valid are {VALID_PERIODS}")
        panel = {}
        for src in data_sources:
            src_upper = src.upper()
            if src_upper not in ['VND', 'CAFE']:
                raise ValueError(f"Invalid data source '{src}': valid are VND, CAFE")
            panel[src_upper] = self.download_single_source_periods(src_upper, periods)
        return panel

    def download_aligned_panel(self, periods: Optional[List[str]] = None,
                               data_sources: Optional[List[str]] = None) -> dict:
        '''
        Convenience alias for download_panel.
        Returns the same nested dict structure with is_imputed flags per symbol.
        '''
        return self.download_panel(periods=periods, data_sources=data_sources)

