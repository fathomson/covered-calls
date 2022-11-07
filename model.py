import pandas as pd


class Data:
    def __init__(self):
        self.df= pd.DataFrame()


    def add(self, _df):
        self.df = pd.concat([self.df, _df], ignore_index=True)


class Text:
    def __init__(self):
        self.status = ''

    def set_status(self, new_status):
        self.status = new_status