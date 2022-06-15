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


def filter_derivatives(df):
    """
    :param df: DataFrame containing all actual derivatives contracts.
    :return: A dataframe with active monthly derivatives contracts
    """
    df.drop(df.index[df['Location'] != 'Amsterdam'], inplace=True)
    df.drop(df.index[df['Product family'] != 'Stock options'], inplace=True)
    df = df[~df['Instrument name'].str.contains('OLD', na=False)]
    df = df[~df['Instrument name'].str.contains('Week', na=False)].reset_index(drop=True)
    return df

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

    df = pd.DataFrame(json_data['extended'][0]['rowc'])
    df['strike']=  df[['strike']].applymap(lambda text: BeautifulSoup(text, 'html.parser').get_text())
    df.drop(df.index[df['best_bid'] == '-'], inplace=True)

    if len(df)<1:
        return None

    cols = ['strike', 'best_bid', 'best_ask']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce', axis=1)

    df['name'] = stock['Instrument name']
    df['code'] = stock['Code']
    df['matures'] = json_data['extended'][0]['maturityDate']

    # determine share price,
    df.reset_index(inplace=True, drop=True)
    stock_price=round(df['strike'][0] + (df['best_bid'][0]+ df['best_ask'][0])/2,2)

    # determine amount invested and interest earned
    df['profit'] = df.apply(lambda x: (x['strike']+x['best_bid'] - stock_price) if x['strike'] < stock_price else (x['best_bid']), axis=1)
    df['invested'] = df.apply( lambda x: (stock_price - x['best_bid']) , axis=1)
    df['interest'] = df['profit']/df['invested']

    # 1 option is for 100 stocks
    df['invested'] = df['invested'] * 100

    return df[['name','code','matures','strike','best_bid','best_ask', 'invested','interest']]

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
        url = 'https://live.euronext.com/nl/ajax/getPricesOptionsAjax/stock-options/{}/DAMS'.format(stock['Code'])
        page = requests.post(url).json()
        with open(out_fp, 'w') as file:
            file.write(json.dumps(page))

    df = parse_stock_option(page,stock)

    return df


def get_df():
    all_derivatives = get_derivatives('https://live.euronext.com/derivatives_contracts/getFullDownloadAjax')
    return filter_derivatives(all_derivatives)


def queue_handler(q, n,data, text):
    while q.qsize() > 0:
        row = q.get()
        result = get_stock_options(row)
        data.add(result)
        text.set_status('Refreshing {} option prices  ({}/{} | {:.0%})'.format(row['Instrument name'], n - q.qsize(), n,1 - (q.qsize()/n) ))
        q.task_done()
    text.set_status('')
