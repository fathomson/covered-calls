import json
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

def get_derivatives(url, out_fp='data/derivatives.csv'):
    """
    :param url: The url containing all derivatives contracts
    :param out_fp: Out file name for storing all derivatives contracts
    :return: A dataframe containing all derivatives contract
    """
    if not os.path.exists(os.path.dirname(out_fp)):
        os.makedirs(os.path.dirname(out_fp))
    if not os.path.isfile(out_fp):
        page = requests.get(url)
        with open(out_fp, 'w', encoding="utf-8") as file:
            file.write(page.text)
    return pd.read_csv(out_fp, skiprows=1, sep=';', header=0)

def week_or_month(x):
    if 'Week' in x:
        return 'Week'
    else:
        return 'Month'

def filter_derivatives(df):
    """
    :param df: DataFrame containing all actual derivatives contracts.
    :return: A dataframe with active monthly derivatives contracts
    """
    df.drop(df.index[df['Location'] != 'Amsterdam'], inplace=True)
    df.drop(df.index[df['Product family'] != 'Stock options'], inplace=True)
    df = df[~df['Instrument name'].str.contains('OLD', na=False)]
    return df

def get_latest_price(stock):
    url = 'https://live.euronext.com/intraday_chart/getChartData/{}-XAMS/intraday'.format(stock['Underlying ISIN'])
    try:
        return requests.post(url).json()[-1]['price']
    except:
        return


def parse_stock_option(json_data, stock):
    """
    :param json_data: List of all contracts ang their price
    :param stock: The stock row to get options for, 'Code'
    :return: A dataframe containing code, strike price, bid, ask, invested and interest
    """
    if json_data is None:
        return

    if json_data['extended'][0] is None:
        return

    if len(json_data['extended'][0]['rowc']) <2:
        return
    if len(json_data['extended'][0]['rowp']) <2:
        return

    df_c = pd.DataFrame(json_data['extended'][0]['rowc'])
    df_c['option'] = 'call'
    df_p = pd.DataFrame(json_data['extended'][0]['rowp'])
    df_p['option'] = 'put'

    df = pd.concat([df_c, df_p], ignore_index=True)

    df['strike'] = df[['strike']].applymap(lambda text: BeautifulSoup(text, 'html.parser').get_text())
    df.drop(df.index[df['best_bid'] == '-'], inplace=True)

    if len(df)<1:
        return

    cols = ['strike', 'best_bid', 'best_ask']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

    stock_price = get_latest_price(stock)
    if not stock_price:
        return

    df['name'] = stock['Instrument name']
    df['name_short'] = '{} ({})'.format(stock['Instrument name'].split(' ')[0], stock['Code'])
    df['latest_price'] = stock_price
    df['code'] = stock['Code']
    df['matures'] = json_data['extended'][0]['maturityDate']
    df.loc[:, 'period'] = df['name'].apply(week_or_month)

    # determine share price,
    df.reset_index(inplace=True, drop=True)

    # CALL
    df['tv_call'] = df.apply(lambda x: x['best_bid'] if (stock_price < x['strike']) else (x['best_bid'] - (stock_price - x['strike'])) , axis=1)
    df['tvspc'] = df.apply(lambda x: x['tv_call']/stock_price, axis=1)
    #PUT
    df['tv_put'] = df.apply(lambda x: x['best_bid'] if (stock_price > x['strike']) else (x['best_bid'] - (x['strike'] - stock_price))  , axis=1)
    df['tvspp'] = df.apply(lambda x: x['tv_put']/stock_price, axis=1)

    return df[['name_short','matures','period','latest_price', 'strike','best_bid','best_ask','option', 'tvspc', 'tvspp']]

def get_stock_options(stock, use_existing=False):
    """
    :param stock: The stock row to get options for, 'Code'
    :param use_existing: Save data for later use? (prices might have changed)
    :return: A json file containing a list of the stock option
    """

    out_fp = 'data/{}.json'.format(stock['Code'])
    if not os.path.exists(os.path.dirname(out_fp)):
        os.makedirs(os.path.dirname(out_fp))
    if use_existing and os.path.isfile(out_fp):
        with open(out_fp) as fp:
            page = json.load(fp)
    else:
        url = 'https://live.euronext.com/en/ajax/getPricesOptionsAjax/stock-options/{}/DAMS'.format(stock['Code'])
        page = requests.post(url).json()
        with open(out_fp, 'w') as file:
            file.write(json.dumps(page))

    df = parse_stock_option(page,stock)

    return df


def get_df():
    all_derivatives = get_derivatives('https://live.euronext.com/derivatives_contracts/getFullDownloadAjax')
    return filter_derivatives(all_derivatives)


def queue_handler(q, n, data, text):
    while q.qsize() > 0:
        row = q.get()
        result = get_stock_options(row)
        if result is not None:
            data.add(result)
        else:
            a=1
            #print(row)
        text.set_status('Refreshing {} option prices  ({}/{} | {:.0%})'.format(row['Instrument name'], n - q.qsize(), n,1 - (q.qsize()/n) ))
        q.task_done()
    text.set_status('')
