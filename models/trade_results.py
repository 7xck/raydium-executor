import pandas as pd


class TradeResults:
    def __init__(self, pool_id):
        self.pool_id = pool_id
        self.time = pd.Timestamp.now()  # utc
        self.s_tx_two = ""

    def class_attrs_to_dict(self):
        return self.__dict__

    def save(self, engine):
        # save to db
        # turn to dict
        dict_to_save = self.class_attrs_to_dict()
        df = pd.DataFrame([dict_to_save])
        df.to_sql("trade_results", engine, if_exists="append", index=False)
