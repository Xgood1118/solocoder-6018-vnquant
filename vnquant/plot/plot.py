from vnquant.data.dataloader import DataLoader
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import vnquant.utils.utils as utils
import pandas as pd
import numpy as np


def compute_bollinger_bands(data: pd.DataFrame, window: int = 20, num_std: float = 2.0,
                            price_col: str = 'close') -> pd.DataFrame:
    '''
    Compute Bollinger Bands for price data.
    Compatible with multi-period data returned by DataLoader.download_panel().

    Args:
        data: DataFrame containing price data (must have price_col).
              Works with plain DataFrames and with MultiIndex columns.
        window: rolling window size (default 20).
        num_std: number of standard deviations for upper/lower bands (default 2.0).
        price_col: which price column to use (default 'close').

    Returns:
        DataFrame with columns bb_mid, bb_upper, bb_lower. Index aligned with input.
    '''
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        attrs = df.columns.get_level_values('Attributes')
        if price_col not in attrs.values:
            for cand in ['close', 'adjust', 'adjust_close', 'adjust_price']:
                if cand in attrs.values:
                    price_col = cand
                    break
        price = df.xs(price_col, level='Attributes', axis=1)
        if isinstance(price, pd.DataFrame) and price.shape[1] == 1:
            price = price.iloc[:, 0]
        elif isinstance(price, pd.DataFrame) and price.shape[1] > 1:
            price = price.iloc[:, 0]
    else:
        if price_col not in df.columns:
            for cand in ['close', 'adjust', 'adjust_close', 'adjust_price']:
                if cand in df.columns:
                    price_col = cand
                    break
        price = df[price_col]

    mid = price.rolling(window=window, min_periods=1).mean()
    std = price.rolling(window=window, min_periods=1).std()
    upper = mid + num_std * std
    lower = mid - num_std * std

    result = pd.DataFrame({
        'bb_mid': mid,
        'bb_upper': upper,
        'bb_lower': lower
    }, index=df.index)
    return result

def _vnquant_candle_stick_source(symbol,
                                 start_date, end_date,
                                 colors=['blue', 'red'],
                                 width=800, height=600,
                                 show_vol=True,
                                 data_source='VND',
                                 bollinger: bool = False,
                                 bb_window: int = 20,
                                 bb_std: float = 2.0,
                                 **kargs):
    loader = DataLoader(symbol, start_date, end_date, minimal=True, data_source=data_source)
    data = loader.download()
    symbol = list(data.columns.levels[1])[0]
    data.columns = ['high', 'low', 'open', 'close', 'adjust', 'volume']
    title = '{} stock price & volume from {} to {}'.format(symbol, start_date, end_date)
    rows = 2 if show_vol else 1
    row_heights = [0.6, 0.4] if show_vol else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        row_heights=row_heights)

    fig.append_trace(go.Candlestick(
        x=data.index,
        open=data['open'], high=data['high'],
        low=data['low'], close=data['close'],
        increasing_line_color=colors[0],
        decreasing_line_color=colors[1],
        name='price'),
        row=1, col=1)

    if bollinger:
        bb = compute_bollinger_bands(data, window=bb_window, num_std=bb_std, price_col='close')
        touch_upper = (data['high'] >= bb['bb_upper'])
        touch_lower = (data['low'] <= bb['bb_lower'])
        fig.append_trace(go.Scatter(
            x=data.index, y=bb['bb_upper'],
            mode='lines', line=dict(color='rgba(180, 0, 0, 0.8)', width=1.2),
            name=f'BB Upper ({bb_window},{bb_std})',
            legendgroup='bollinger'),
            row=1, col=1)
        fig.append_trace(go.Scatter(
            x=data.index, y=bb['bb_mid'],
            mode='lines', line=dict(color='rgba(80, 80, 80, 0.8)', width=1.0, dash='dash'),
            name=f'BB Mid SMA{bb_window}',
            legendgroup='bollinger'),
            row=1, col=1)
        fig.append_trace(go.Scatter(
            x=data.index, y=bb['bb_lower'],
            mode='lines', line=dict(color='rgba(0, 120, 0, 0.8)', width=1.2),
            fill='tonexty', fillcolor='rgba(180, 180, 255, 0.08)',
            name=f'BB Lower ({bb_window},{bb_std})',
            legendgroup='bollinger'),
            row=1, col=1)
        if touch_upper.any():
            fig.append_trace(go.Scatter(
                x=data.index[touch_upper],
                y=data['high'][touch_upper],
                mode='markers',
                marker=dict(color='red', size=8, symbol='circle-open', line_width=2),
                name='Touch Upper Band',
                showlegend=True,
                legendgroup='bollinger'),
                row=1, col=1)
        if touch_lower.any():
            fig.append_trace(go.Scatter(
                x=data.index[touch_lower],
                y=data['low'][touch_lower],
                mode='markers',
                marker=dict(color='green', size=8, symbol='circle-open', line_width=2),
                name='Touch Lower Band',
                showlegend=True,
                legendgroup='bollinger'),
                row=1, col=1)

    if show_vol:
        fig.append_trace(go.Bar(
            x=data.index,
            y=data['volume'],
            name='Volume'),
            row=2, col=1)

    fig.update_layout(
        title=title,
        yaxis_title='Price',
        xaxis_title='Date',
        width=width,
        height=height,
        showlegend=True
    )

    fig.show()

def vnquant_candle_stick_source(
        symbol,
        start_date, end_date,
        colors=['blue', 'red'],
        width=800, height=600,
        data_source='VND',
        show_advanced = ['volume', 'macd', 'rsi'],
        bollinger: bool = False,
        bb_window: int = 20,
        bb_std: float = 2.0,
        **kargs
    ):
    '''
    This function is to visualize a candle stick stock index with advanced metrics
    Args:
        symbol (string): stock index
        start_date (string: 'yyyy-mm-dd'): start date
        end_date (string: 'yyyy-mm-dd'): end date
        colors (list: ['blue', 'red']): list colors of up and down candle
        width (int: 800): width of graph figure
        height (int: 600): height of graph figure
        data_source (string: 'VND'): data source to get stock price
        show_advanced (list: ['volume', 'macd', 'rsi']): list of advanced stock index to show up.
        bollinger (bool: False): whether to overlay Bollinger Bands on the main price chart.
        bb_window (int: 20): Bollinger Bands rolling window size.
        bb_std (float: 2.0): Bollinger Bands number of standard deviations.
        
    Example:
        from vnquant import plot as pl
        pl.vnquant_candle_stick_source(
            symbol='TCB',
            title='TCB symbol from 2022-01-01 to 2022-10-01',
            xlab='Date', ylab='Price',
            start_date='2022-01-01',
            end_date='2022-10-01',
            data_source='CAFE',
            show_advanced = ['volume', 'macd', 'rsi'],
            bollinger=True, bb_window=20, bb_std=2.0
        )
    '''
    
    loader = DataLoader(symbols=symbol, 
                        start=start_date, 
                        end=end_date, minimal=True, 
                        data_source=data_source, table_style='levels')

    data = loader.download()
    data = data[['high', 'low', 'open', 'close', 'adjust', 'volume_match']]
    data.columns = ['high', 'low', 'open', 'close', 'adjust', 'volume']
    title = '{} stock price & volume from {} to {}'.format(symbol, start_date, end_date)

    num_indices = len(show_advanced)
    row_heights = [round(1/(num_indices+1), 1)]*(num_indices)+[1-round(1/(num_indices+1), 1)*num_indices]
    r_price = 1
    r_volume = 2
    r_rsi = 3
    w_rsi = 1

    if num_indices == 3:
        r_price = 1
        r_volume = 2
        r_macd = 3
        r_rsi = 4
        w_macd = 1
        w_rsi = 1
        row_heights = [0.3, 0.3, 0.15, 0.15]

    if show_advanced==['rsi', 'volume']:
        r_price = 1
        r_volume = 2
        r_rsi = 3
        w_rsi = 1
        row_heights = [0.5, 0.3, 0.2]

    if show_advanced==['volume', 'macd']:
        r_price = 1
        r_volume = 2
        r_macd = 3
        w_macd = 1
        row_heights = [0.5, 0.3, 0.2]

    if show_advanced==['macd', 'rsi']:
        r_price = 1
        r_macd = 3
        w_macd = 1
        r_rsi = 3
        w_rsi = 1
        row_heights = [0.5, 0.3, 0.2]
    
    if show_advanced==['volume']:
        r_price = 1
        r_volume = 2
        row_heights = [0.6, 0.4]

    if show_advanced==['macd']:
        r_price = 1
        r_macd = 2
        w_macd = 1
        row_heights = [0.6, 0.4]

    if show_advanced==['rsi']:
        r_price = 1
        r_rsi = 2
        w_rsi = 1
        row_heights = [0.6, 0.4]

    fig = make_subplots(rows=num_indices + 1, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        # subplot_titles=('Price', 'Volume'),
                        row_heights=row_heights)

    fig.append_trace(
        go.Candlestick(
            x=data.index,
            open=data['open'], high=data['high'],
            low=data['low'], close=data['close'],
            increasing_line_color=colors[0],
            decreasing_line_color=colors[1],
            name='price'
        ),
        row=r_price, col=1
    )

    # Compute & plot Bollinger Bands
    if bollinger:
        bb = compute_bollinger_bands(data, window=bb_window, num_std=bb_std, price_col='close')
        touch_upper = (data['high'] >= bb['bb_upper'])
        touch_lower = (data['low'] <= bb['bb_lower'])
        fig.append_trace(
            go.Scatter(
                x=data.index, y=bb['bb_upper'],
                mode='lines', line=dict(color='rgba(180, 0, 0, 0.8)', width=1.2),
                name=f'BB Upper ({bb_window},{bb_std})',
                legendgroup='bollinger'
            ), row=r_price, col=1)
        fig.append_trace(
            go.Scatter(
                x=data.index, y=bb['bb_mid'],
                mode='lines', line=dict(color='rgba(80, 80, 80, 0.8)', width=1.0, dash='dash'),
                name=f'BB Mid SMA{bb_window}',
                legendgroup='bollinger'
            ), row=r_price, col=1)
        fig.append_trace(
            go.Scatter(
                x=data.index, y=bb['bb_lower'],
                mode='lines', line=dict(color='rgba(0, 120, 0, 0.8)', width=1.2),
                fill='tonexty', fillcolor='rgba(180, 180, 255, 0.08)',
                name=f'BB Lower ({bb_window},{bb_std})',
                legendgroup='bollinger'
            ), row=r_price, col=1)
        if touch_upper.any():
            fig.append_trace(
                go.Scatter(
                    x=data.index[touch_upper],
                    y=data['high'][touch_upper],
                    mode='markers',
                    marker=dict(color='red', size=8, symbol='circle-open', line_width=2),
                    name='Touch Upper Band', showlegend=True, legendgroup='bollinger'
                ), row=r_price, col=1)
        if touch_lower.any():
            fig.append_trace(
                go.Scatter(
                    x=data.index[touch_lower],
                    y=data['low'][touch_lower],
                    mode='markers',
                    marker=dict(color='green', size=8, symbol='circle-open', line_width=2),
                    name='Touch Lower Band', showlegend=True, legendgroup='bollinger'
                ), row=r_price, col=1)

    # Compute MACD:
    if 'macd' in show_advanced:
        # refers to: https://www.alpharithms.com/calculate-macd-python-272222/
        # Get the 26-day EMA of the closing price
        k = data['close'].ewm(span=12, adjust=False, min_periods=12).mean()
        # Get the 12-day EMA of the closing price
        d = data['close'].ewm(span=26, adjust=False, min_periods=26).mean()
        # Subtract the 26-day EMA from the 12-Day EMA to get the MACD
        macd = k - d
        # Get the 9-Day EMA of the MACD for the Trigger line
        macd_s = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        # Calculate the difference between the MACD - Trigger for the Convergence/Divergence value
        macd_h = macd - macd_s
        # Add all of our new values for the MACD to the dataframe
        data['macd'] = data.index.map(macd)
        data['macd_h'] = data.index.map(macd_h)
        data['macd_s'] = data.index.map(macd_s)
        # Fast Signal (%k)
        fig.append_trace(
            go.Scatter(
                x=data.index,
                y=data['macd'],
                line=dict(color='#ff9900', width=w_macd),
                name='macd',
                showlegend=True,
                legendgroup='2',
            ), row=r_macd, col=1
        )
        # Slow signal (%d)
        fig.append_trace(
            go.Scatter(
                x=data.index,
                y=data['macd_s'],
                line=dict(color='#000000', width=w_macd),
                showlegend=True,
                legendgroup='2',
                name='signal'
            ), row=r_macd, col=1
        )
        # Colorize the histogram values
        colors = np.where(data['macd_h'] < 0, '#000', '#ff9900')
        # Plot the histogram
        fig.append_trace(
            go.Bar(
                x=data.index,
                y=data['macd_h'],
                name='histogram',
                marker_color=colors,
            ), row=r_macd, col=1
        )

    # Compute RSI:
    if 'rsi' in show_advanced:
        delta = data['close'].diff()
        up = delta.clip(lower=0)
        down = -1*delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up/ema_down
        data['RSI'] = 100 - (100/(1+rs))

        fig.append_trace(
            go.Scatter(
                x=data.index, 
                y=data['RSI'], 
                name='RSI', 
                line=dict(width=w_rsi)
              ),
            row=r_rsi,
            col=1
        )

        fig.add_hline(y=70, line_dash="dot", row=r_rsi, col="all",
                  annotation_text="70%", 
                  annotation_position="bottom right")

        fig.add_hline(y=30, line_dash="dot", row=r_rsi, col="all",
                  annotation_text="30%", 
                  annotation_position="bottom right")

    # show volume    
    if 'volume' in show_advanced:
        fig.append_trace(
            go.Bar(
                x=data.index,
                y=data['volume'],
                marker=dict(color='red'),
                name='Volume'
            ),
        row=r_volume, col=1)

    fig.update_layout(
        title=title,
        yaxis_title='Price',
        xaxis_title='Date',
        width=width,
        height=height,
        showlegend=True
    )

    fig.show()

def vnquant_candle_stick(data,
                        title=None,
                        xlab='Date', ylab='Price',
                        start_date=None, end_date=None,
                        colors=['blue', 'red'],
                        width=800, height=600,
                        data_source='VND',
                        show_advanced=['volume', 'macd', 'rsi'],
                        bollinger: bool = False,
                        bb_window: int = 20,
                        bb_std: float = 2.0,
                        **kargs):
    '''
    This function is to visualize a candle stick stock index with advanced metrics
    Args:
        data (string or pandas DataFrame): stock data
        title (string: None): title of figure plot
        xlab (string: 'Date'): x label
        ylab (string: 'Price'): y label
        start_date (string: 'yyyy-mm-dd'): start date
        end_date (string: 'yyyy-mm-dd'): end date
        colors (list: ['blue', 'red']): list colors of up and down candle
        width (int: 800): width of graph figure
        height (int: 600): height of graph figure
        data_source (string: 'VND'): data source to get stock price belonging to ['VND', 'CAFE']
        show_advanced (list: ['volume', 'macd', 'rsi']): list of advanced stock index to show up. Each element belongs to ['volume', 'macd', 'rsi'] 
        bollinger (bool: False): whether to overlay Bollinger Bands.
        bb_window (int: 20): Bollinger Bands rolling window size.
        bb_std (float: 2.0): Bollinger Bands number of standard deviations.
        
    Example:
        from vnquant import plot as pl
        pl.vnquant_candle_stick(
            data='TCB',
            title='TCB symbol from 2022-01-01 to 2022-10-01',
            xlab='Date', ylab='Price',
            start_date='2022-01-01',
            end_date='2022-10-01',
            data_source='CAFE',
            show_advanced = ['volume', 'macd', 'rsi'],
            bollinger=True, bb_window=20, bb_std=2.0
        )
    '''
    # Download data from source
    if isinstance(data, str):
        vnquant_candle_stick_source(symbol=data, start_date=start_date, end_date=end_date,
                                     colors=colors, width=width,
                                     height=height, show_advanced=show_advanced,
                                     data_source=data_source,
                                     bollinger=bollinger, bb_window=bb_window, bb_std=bb_std)
    else:
        if 'volume' in show_advanced:
            assert utils._isOHLCV(data)
            defau_cols = ['high', 'low', 'open', 'close', 'volume_match']
            avail_cols = [c for c in defau_cols if c in data.columns]
            data = data[avail_cols].copy()
            data.columns = avail_cols
            col_map = {c: c for c in avail_cols}
            col_map['volume_match'] = 'volume' if 'volume_match' in avail_cols else None
            rename_map = {k: v for k, v in col_map.items() if v and k != v}
            if rename_map:
                data = data.rename(columns=rename_map)
        else:
            assert utils._isOHLC(data)
            defau_cols = ['high', 'low', 'open', 'close']
            avail_cols = [c for c in defau_cols if c in data.columns]
            data = data[avail_cols].copy()
            data.columns = avail_cols

        x = data.index

        try:
            data.index = pd.DatetimeIndex(x)
            x = data.index
        except (IndexError, TypeError):
            raise IndexError('index of dataframe must be DatetimeIndex!')
        
        if not isinstance(data.index, pd.core.indexes.datetimes.DatetimeIndex):
            raise IndexError('index of dataframe must be DatetimeIndex!')

        if start_date is None:
            start_date = max(data.index)
        if end_date is None:
            end_date = max(data.index)

        has_vol = 'volume' in show_advanced and (('volume' in data.columns) or ('volume_match' in data.columns))
        rows = 2 if has_vol else 1
        row_heights = [0.6, 0.4] if has_vol else [1.0]

        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                            row_heights=row_heights)

        fig.append_trace(go.Candlestick(
            x=x,
            open=data['open'], high=data['high'],
            low=data['low'], close=data['close'],
            increasing_line_color=colors[0],
            decreasing_line_color=colors[1],
            name='price'),
            row=1, col=1)

        if bollinger:
            bb = compute_bollinger_bands(data, window=bb_window, num_std=bb_std, price_col='close')
            touch_upper = (data['high'] >= bb['bb_upper'])
            touch_lower = (data['low'] <= bb['bb_lower'])
            fig.append_trace(
                go.Scatter(
                    x=x, y=bb['bb_upper'],
                    mode='lines', line=dict(color='rgba(180, 0, 0, 0.8)', width=1.2),
                    name=f'BB Upper ({bb_window},{bb_std})',
                    legendgroup='bollinger'
                ), row=1, col=1)
            fig.append_trace(
                go.Scatter(
                    x=x, y=bb['bb_mid'],
                    mode='lines', line=dict(color='rgba(80, 80, 80, 0.8)', width=1.0, dash='dash'),
                    name=f'BB Mid SMA{bb_window}',
                    legendgroup='bollinger'
                ), row=1, col=1)
            fig.append_trace(
                go.Scatter(
                    x=x, y=bb['bb_lower'],
                    mode='lines', line=dict(color='rgba(0, 120, 0, 0.8)', width=1.2),
                    fill='tonexty', fillcolor='rgba(180, 180, 255, 0.08)',
                    name=f'BB Lower ({bb_window},{bb_std})',
                    legendgroup='bollinger'
                ), row=1, col=1)
            if touch_upper.any():
                fig.append_trace(
                    go.Scatter(
                        x=x[touch_upper],
                        y=data['high'][touch_upper],
                        mode='markers',
                        marker=dict(color='red', size=8, symbol='circle-open', line_width=2),
                        name='Touch Upper Band', showlegend=True, legendgroup='bollinger'
                    ), row=1, col=1)
            if touch_lower.any():
                fig.append_trace(
                    go.Scatter(
                        x=x[touch_lower],
                        y=data['low'][touch_lower],
                        mode='markers',
                        marker=dict(color='green', size=8, symbol='circle-open', line_width=2),
                        name='Touch Lower Band', showlegend=True, legendgroup='bollinger'
                    ), row=1, col=1)

        if has_vol:
            volume = data['volume'] if 'volume' in data.columns else data.get('volume_match', None)
            if volume is not None:
                fig.append_trace(go.Bar(
                    x=x,
                    y=volume,
                    name='Volume'),
                    row=2, col=1)

        fig.update_layout(
            title=title,
            yaxis_title=ylab,
            xaxis_title=xlab,
            showlegend=True
        )

        fig.show()
