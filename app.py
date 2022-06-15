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


# classes holding ui data
data = Data()
text = Text()

st.set_page_config(
    page_title="Covered call strategy dutch stocks",
    page_icon="➰",
)


def _max_width_():
    max_width_str = f"max-width: 1400px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )


_max_width_()

# ui objects
st.title("➰ Covered call strategy dutch stocks")
st.write(
    """     
Selling calls for a stock that one owns can be a way to earn some extra income. In the table below an overview of stock / option combination and it\'s interest rates.
\n Note: Not financial advice.
  """
)
status = st.empty()
main_df = st.empty()

# load derivative df and add to queue
df = get_df()
q = Queue()
for _, row in df.iterrows():
    q.put(row)

# start parser threads
for i in range(4):
    threading.Thread(target=queue_handler, args=(q,len(df), data, text, ),   daemon=True).start()

# update views
def update_views():
    status.text(text.status)
    main_df.dataframe(data=data.df.style.format({'strike':'€{:.2f}','best_bid':'€{:.2f}','best_ask':'€{:.2f}','invested':'€{:.2f}','interest':'{:.2%}'}))

while q.qsize() > 0:
    update_views()
    time.sleep(1)

update_views()




