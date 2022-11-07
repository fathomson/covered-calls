###################################
# Covered call: Selling call options while also owning the equivalent amount of the underlying stock.
#
# This app gives a near real time overview of which stock and accompanying options give the highest ROI.
# Currently supported: AEX
#
# Note: This tool is not financial advice.  A higher ROI usually means higher risk.
# By applying this strategy one assumes that the market does not does it's job and the options is not priced fairly.
#
###################################
import time
from queue import Queue
import threading
import streamlit as st

from utils import get_df, queue_handler
from model import Data, Text


#
# Main
#
st.set_page_config(layout="wide",page_title="Sell puts, buy covered calls strategy dutch stocks",page_icon="➰", initial_sidebar_state="collapsed")
st.title("➰ Covered call strategy dutch stocks")
st.write(
    """     
Selling puts to get a stock (or option price) and then sell covered calls (for strike or option price) In the table below an overview of stock / option combination and it\'s interest rates.
\n Note: Not financial advice.
  """
)
status = st.empty()
call_df = st.empty()
put_df = st.empty()
text = Text()

#
# Sidebar
#

filter_option_period = st.sidebar.multiselect(
         'Select option period',
         ['Week', 'Month'],
         ['Week', 'Month'], key="periods")



def update_views():
    status.text(text.status)
    if 'option' not in st.session_state.data.df:
        return

    call_data_filtered = st.session_state.data.df[st.session_state.data.df['option']=='call']
    put_data_filtered = st.session_state.data.df[st.session_state.data.df['option']=='put']
    if 'period' in st.session_state.data.df:
        call_data_filtered = st.session_state.data.df[(st.session_state.data.df['option']=='call') & (st.session_state.data.df.period.isin(filter_option_period))]
        put_data_filtered = st.session_state.data.df[(st.session_state.data.df['option']=='put') & (st.session_state.data.df.period.isin(filter_option_period))]

    call_data_filtered.drop(columns=['option', 'tvspp'], inplace=True)
    put_data_filtered.drop(columns=['option', 'tvspc'], inplace=True)

    call_df.dataframe(data=call_data_filtered.style.format({'latest_price':'€{:.2f}','strike':'€{:.2f}','best_bid':'€{:.2f}','best_ask':'€{:.2f}','tvspc':'{:.2%}'}))
    put_df.dataframe(data=put_data_filtered.style.format({'latest_price':'€{:.2f}','strike':'€{:.2f}','best_bid':'€{:.2f}','best_ask':'€{:.2f}','tvspp':'{:.2%}'}))

def update_data():
    df = get_df()
    q = Queue()
    for _, row in df.iterrows():
        q.put(row)

    # start parser threads
    for i in range(10):
        threading.Thread(target=queue_handler, args=(q, len(df), st.session_state.data, text,), daemon=True).start()

    while q.qsize() > 0:
        update_views()
        time.sleep(1)

    update_views()
    st.session_state.updated = int(time.time())

#
# Data
#
if 'updated' not in st.session_state:
    st.session_state.data = Data()
    st.session_state.updated = 0

def button_refresh_click():
    st.session_state.data = Data()
    st.session_state.updated = 0
    load()

def load():
    # when update is longer then 1 hour ago update data
    if st.session_state.updated < (int(time.time()) - 60 * 60):
        update_data();
    else:
        update_views();


st.sidebar.button('Refresh data', on_click=button_refresh_click())












