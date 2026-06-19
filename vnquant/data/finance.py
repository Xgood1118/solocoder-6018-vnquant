# Copyright (c) vnquant. All rights reserved.
from bs4 import BeautifulSoup
import requests
import vnquant.utils.utils as utils
import pandas as pd
import logging as logging
import re
import requests
import time
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


_FINANCE_RATIO_ITEM_CODES = {
    'roe': '53030',
    'gross_margin': '52005',
    'net_margin': '51050',
    'debt_to_asset': '53021',
}

_FINANCE_RATIO_ITEM_NAMES_VI = {
    'roe': ['ROE', 'Tỷ suất lợi nhuận trên vốn chủ sở hữu', 'Return on equity'],
    'gross_margin': ['Biên lợi nhuận gộp', 'Gross profit margin', ' Gross margin'],
    'net_margin': ['Biên lợi nhuận ròng', 'Net profit margin', 'Net margin'],
    'debt_to_asset': ['Tỷ lệ Nợ/Tổng tài sản', 'Debt to asset', 'Total debt to total assets'],
}

class FinanceLoader():
    def __init__(self, symbol, start, end, *arg, **karg):
        self.symbol = symbol
        self.start = start
        self.end = end

    def get_finan_report(self):
        start_time = time.time()
        page = requests.get("https://finfo-api.vndirect.com.vn/v3/stocks/financialStatement?secCodes={}&reportTypes=QUARTER&modelTypes=1,89,101,411&fromDate={}&toDate={}".format(self.symbol, self.start, self.end))
        data = page.json()
        end_time = time.time()
        data_dates = {}
        #print('request time: ', end_time-start_time)
        start_time = time.time()
        for item in data['data']['hits']:
            item = item['_source']
            date = item['fiscalDate']
            itemName = item['itemName']
            itemCode = item['itemCode']
            numericValue = item['numericValue']
            if date not in data_dates:
                data_dates[date] = [[], []]
            else:
                if itemName not in data_dates[date][0]:
                    data_dates[date][0].append(itemName)
                    data_dates[date][1].append(numericValue)
        end_time = time.time()
        #print('access data time: ', end_time-start_time)
        start_time = time.time()
        for i, (date, item) in enumerate(data_dates.items()):
            df_date = pd.DataFrame(data={'index':item[0], date[:7]:item[1]})
            if i == 0:
                df = df_date
            else:
                df = pd.merge(df, df_date, how='inner')
        df.set_index('index', inplace=True)
        end_time = time.time()
        #print('merge time: ', end_time-start_time)
        return df

    def get_business_report(self):
        start_time = time.time()
        page = requests.get("https://finfo-api.vndirect.com.vn/v3/stocks/financialStatement?secCodes={}&reportTypes=QUARTER&modelTypes=2,90,102,412&fromDate={}&toDate={}".format(self.symbol, self.start, self.end))
        data = page.json()
        end_time = time.time()
        data_dates = {}
        #print('request time: ', end_time-start_time)
        start_time = time.time()
        for item in data['data']['hits']:
            item = item['_source']
            date = item['fiscalDate']
            itemName = item['itemName']
            itemCode = item['itemCode']
            numericValue = item['numericValue']
            if date not in data_dates:
                data_dates[date] = [[], []]
            else:
                if itemName not in data_dates[date][0]:
                    data_dates[date][0].append(itemName)
                    data_dates[date][1].append(numericValue)
        end_time = time.time()
        #print('access data time: ', end_time-start_time)
        start_time = time.time()
        for i, (date, item) in enumerate(data_dates.items()):
            df_date = pd.DataFrame(data={'index':item[0], date[:7]:item[1]})
            if i == 0:
                df = df_date
            else:
                df = pd.merge(df, df_date, how='inner')
        df.set_index('index', inplace=True)
        end_time = time.time()
        #print('merge time: ', end_time-start_time)
        return df

    def get_cashflow_report(self):
        start_time = time.time()
        page = requests.get("https://finfo-api.vndirect.com.vn/v3/stocks/financialStatement?secCodes={}&reportTypes=QUARTER&modelTypes=3,91,103,413&fromDate={}&toDate={}".format(self.symbol, self.start, self.end))
        data = page.json()
        end_time = time.time()
        data_dates = {}
        #print('request time: ', end_time-start_time)
        start_time = time.time()
        for item in data['data']['hits']:
            item = item['_source']
            date = item['fiscalDate']
            itemName = item['itemName']
            itemCode = item['itemCode']
            numericValue = item['numericValue']
            if date not in data_dates:
                data_dates[date] = [[], []]
            else:
                if itemName not in data_dates[date][0]:
                    data_dates[date][0].append(itemName)
                    data_dates[date][1].append(numericValue)
        end_time = time.time()
        #print('access data time: ', end_time-start_time)
        start_time = time.time()
        for i, (date, item) in enumerate(data_dates.items()):
            df_date = pd.DataFrame(data={'index':item[0], date[:7]:item[1]})
            if i == 0:
                df = df_date
            else:
                df = pd.merge(df, df_date, how='inner')
        df.set_index('index', inplace=True)
        end_time = time.time()
        #print('merge time: ', end_time-start_time)
        return df

    def get_basic_index(self):
        start_year = int(self.start[:4])
        end_year = int(self.end[:4])
        years = np.arange(start_year, end_year+1, 1)[::-1]
        years = ['{}-12-31'.format(year) for year in years]
        data_dates = {}
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
        headers = {'User-Agent': user_agent}
        for year in years:
            page = requests.get("https://finfo-api.vndirect.com.vn/v4/ratios?q=code:{}~itemCode:53030,52005,51050,53021,52001,52002,54018,712010,712020,712030,712040~reportDate:{}".format(self.symbol, year), headers=headers)
            data = page.json()
            
            for item in data['data']:
                date = item['reportDate']
                itemName = item['itemName']
                itemCode = item['itemCode']
                value = item['value']
                if date not in data_dates:
                    data_dates[date] = [[], []]
                else:
                    if itemName not in data_dates[date][0] and itemName != "":
                        data_dates[date][0].append(itemName)
                        data_dates[date][1].append(value)

        for i, (date, item) in enumerate(data_dates.items()):
            df_date = pd.DataFrame(data={'index':item[0], date[:7]:item[1]})
            if i == 0:
                df = df_date
            else:
                df = pd.merge(df, df_date, how='inner')

        df.set_index('index', inplace=True)
        return df

    def get_ratio_quarterly(self, item_codes: Optional[List[str]] = None) -> pd.DataFrame:
        '''
        Fetch quarterly financial ratios from finfo v4/ratios API.
        Returns DataFrame with index=quarter ('YYYY-Qn') and columns=metrics.
        Missing values are kept as NaN (not 0).
        '''
        if item_codes is None:
            item_codes = list(_FINANCE_RATIO_ITEM_CODES.values())
        start_year = int(self.start[:4])
        end_year = int(self.end[:4])
        years = np.arange(start_year, end_year + 1, 1)
        data_records = []
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
        headers = {'User-Agent': user_agent}
        for year in years:
            for q in range(1, 5):
                # construct a canonical fiscal end date for this quarter
                month_end = 3 * q
                report_date = f"{year}-{str(month_end).zfill(2)}-{pd.Timestamp(year, month_end, 1).days_in_month:02d}"
                url = "https://finfo-api.vndirect.com.vn/v4/ratios"
                payload_str = (
                    f"q=code:{self.symbol}~itemCode:{','.join(item_codes)}~reportDate:{report_date}"
                )
                params = {'q': payload_str.split('q=')[1], 'size': 50}
                try:
                    page = requests.get(url, params=params, headers=headers, timeout=15)
                    data = page.json()
                except Exception:
                    continue
                for item in data.get('data', []):
                    data_records.append({
                        'quarter': f"{year}-Q{q}",
                        'reportDate': item.get('reportDate'),
                        'itemCode': item.get('itemCode'),
                        'itemName': item.get('itemName'),
                        'value': item.get('value'),
                    })
        if not data_records:
            return pd.DataFrame()
        raw = pd.DataFrame(data_records)
        item_code_to_key = {v: k for k, v in _FINANCE_RATIO_ITEM_CODES.items()}
        raw['metric'] = raw['itemCode'].map(item_code_to_key).fillna(raw['itemCode'])
        pivoted = raw.pivot_table(index='quarter', columns='metric', values='value', aggfunc='last')
        def _match_metric_from_name(df: pd.DataFrame) -> pd.DataFrame:
            for metric, names in _FINANCE_RATIO_ITEM_NAMES_VI.items():
                if metric in df.columns:
                    continue
                for nm in names:
                    for col in df.columns:
                        if isinstance(col, str) and (nm.lower() in str(col).lower() or str(col).lower() in nm.lower()):
                            df = df.rename(columns={col: metric})
                            break
                    if metric in df.columns:
                        break
            return df
        pivoted = _match_metric_from_name(pivoted)
        for k in _FINANCE_RATIO_ITEM_CODES:
            if k not in pivoted.columns:
                pivoted[k] = np.nan
        pivoted = pivoted[sorted(pivoted.columns)]
        pivoted = pivoted.sort_index()
        return pivoted


def _fetch_quarterly_ratios_for_symbol(symbol: str, start: str, end: str,
                                       item_codes: List[str]) -> pd.DataFrame:
    loader = FinanceLoader(symbol, start, end)
    df = loader.get_ratio_quarterly(item_codes=item_codes)
    df.insert(0, 'symbol', symbol)
    return df


def industry_ratio_comparison(symbols: List[str],
                              start: str, end: str,
                              metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    '''
    Perform cross-sectional peer analysis: fetch quarterly ratios for each symbol,
    classify by industry via utils.symbols_to_industry (wraps utils.get_ind_class),
    then for each quarter compute the difference from the industry mean and a ranking.

    Args:
        symbols: list of tickers to compare.
        start: start date string 'YYYY-MM-DD'.
        end: end date string 'YYYY-MM-DD'.
        metrics: subset of ['roe', 'gross_margin', 'net_margin', 'debt_to_asset'].
                 Defaults to all four.

    Returns:
        dict with keys:
            - 'industry_map': {symbol: industry_info}
            - 'raw_panel': long-format DataFrame [symbol, quarter] x metrics
            - 'diffs': DataFrame, per (symbol, quarter, metric): value - industry_mean
            - 'rankings': dict quarter -> DataFrame [symbol x metric] with ranks.
                           Symbols missing data for a given metric/quarter are ranked at
                           the bottom with an explicit note in column
                           `{metric}_note` = '数据不足' and their rank is NaN.
    '''
    if metrics is None:
        metrics = ['roe', 'gross_margin', 'net_margin', 'debt_to_asset']
    item_codes = [_FINANCE_RATIO_ITEM_CODES[m] for m in metrics if m in _FINANCE_RATIO_ITEM_CODES]
    industry_map = utils.symbols_to_industry(symbols)
    all_frames = []
    for sym in symbols:
        try:
            df = _fetch_quarterly_ratios_for_symbol(sym, start, end, item_codes)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to fetch ratios for {sym}: {e}")
            df = pd.DataFrame(columns=['symbol', 'quarter'] + metrics)
        all_frames.append(df)
    panel = pd.concat(all_frames, ignore_index=True)
    for m in metrics:
        if m not in panel.columns:
            panel[m] = np.nan
    panel['industry'] = panel['symbol'].map(
        lambda s: (industry_map.get(s, {}) or {}).get('industryName', 'Unknown')
    )
    panel['industryCode'] = panel['symbol'].map(
        lambda s: (industry_map.get(s, {}) or {}).get('industryCode', None)
    )
    group_keys = ['industry'] if panel['industry'].notna().any() and (panel['industry'] != 'Unknown').any() \
        else ['__all__']
    if group_keys == ['__all__']:
        panel['__all__'] = '__all__'
    long_melt = panel.melt(id_vars=['symbol', 'quarter', 'industry', 'industryCode'],
                           value_vars=metrics, var_name='metric', value_name='value')
    if '__all__' in long_melt.columns:
        group_col = '__all__'
    else:
        group_col = 'industry'
    industry_mean = long_melt.groupby([group_col, 'quarter', 'metric'])['value'].transform('mean')
    long_melt['diff_vs_industry_mean'] = long_melt['value'] - industry_mean
    diffs_wide = long_melt.pivot_table(
        index=['symbol', 'quarter', 'industry', 'industryCode'],
        columns='metric', values='diff_vs_industry_mean', aggfunc='last'
    ).reset_index()
    rankings = {}
    quarters_sorted = sorted([q for q in long_melt['quarter'].dropna().unique()])
    higher_is_better = {'roe', 'gross_margin', 'net_margin'}
    for q in quarters_sorted:
        sub = long_melt[long_melt['quarter'] == q].copy()
        rows = []
        for sym in symbols:
            sym_row = {'symbol': sym}
            sym_industry = (industry_map.get(sym, {}) or {}).get('industryName', 'Unknown')
            sym_row['industry'] = sym_industry
            for m in metrics:
                mask = (sub['symbol'] == sym) & (sub['metric'] == m)
                val_series = sub.loc[mask, 'value']
                has_data = not val_series.empty and pd.notna(val_series.values[0])
                if has_data:
                    sym_row[m] = float(val_series.values[0])
                    sym_row[f'{m}_diff_vs_mean'] = float(
                        sub.loc[mask, 'diff_vs_industry_mean'].values[0]
                    )
                    sym_row[f'{m}_note'] = ''
                else:
                    sym_row[m] = np.nan
                    sym_row[f'{m}_diff_vs_mean'] = np.nan
                    sym_row[f'{m}_note'] = '数据不足'
            rows.append(sym_row)
        qdf = pd.DataFrame(rows)
        for m in metrics:
            order_group = qdf.copy()
            valid = order_group[order_group[f'{m}_note'] == ''].copy()
            if m in higher_is_better:
                valid = valid.sort_values(m, ascending=False, na_position='last')
            else:
                valid = valid.sort_values(m, ascending=True, na_position='last')
            rank_map = {s: i + 1 for i, s in enumerate(valid['symbol'])}
            qdf.insert(qdf.columns.get_loc(f'{m}_note') + 1, f'{m}_rank',
                       qdf['symbol'].map(rank_map))
        qdf = qdf.set_index('symbol')
        rankings[q] = qdf
    return {
        'industry_map': industry_map,
        'raw_panel': panel,
        'diffs': diffs_wide,
        'rankings': rankings,
    }


if __name__ == "__main__":
    loader = FinanceLoader('VNM', '2018-01-01', '2019-01-01')
    # index = loader.get_basic_index()
    report = loader.get_finan_report()
    # business = loader.get_business_report()
    # cashflow = loader.get_cashflow_report()
    # print(index)
    print(report)
    # print(business)
    # print(cashflow)
