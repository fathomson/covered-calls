import pandas as pd
import requests
from bs4 import BeautifulSoup

from utils import get_derivatives, filter_derivatives


def get_last_price(stock_code):
    url = 'https://live.euronext.com/en/ajax/getUnderlying/{}/DAMS/options'.format(stock_code)
    try:
        page = requests.get(url)
        if page.status_code != 200:
            return None
        soup = BeautifulSoup(page.content, 'html.parser')
        html_table = soup.find_all(class_='data-13')
        return float(html_table[7].text.lstrip().rstrip())
    except Exception as e:
        return None

def get_options(stock_code, last_price):
    url = 'https://live.euronext.com/en/ajax/submitOptionsForm/stock-options/{}/DAMS'.format(stock_code)
    page = requests.post(url)
    if page.status_code != 200:
        return None

    soup = BeautifulSoup(page.content, 'html.parser')
    html_table = soup.find("table",{"id":"prices_tables_0"})
    df = pd.read_html(str(html_table))[0]

    # Reformat table concat.
    df_c = df.iloc[:,[2,5,6]]
    df_c.columns = ['last','cp','strike']
    df_p = df.iloc[:,[6,7,10]]
    df_p.columns = ['strike','cp','last']
    df = pd.concat([df_c, df_p], ignore_index=True, sort=True)

    # cleanup and calculate delta
    df.drop(df.index[df['last'] == '-'], inplace=True)
    df['stock_price'] = last_price



# code = '4mt'
# p =get_last_price(code)
# o = get_options(code, p)
# a=1;


all_derivatives = get_derivatives('https://live.euronext.com/derivatives_contracts/getFullDownloadAjax')
df =  filter_derivatives(all_derivatives)
a=1;