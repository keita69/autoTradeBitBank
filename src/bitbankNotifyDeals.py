# -*- coding: utf-8 -*-
import os
import time

from myUtil import Line
from technicalAnalysis import MyTechnicalAnalysisUtil


class Advisor:
    def __init__(self):
        """ コンストラクタ """
        self.api_key = os.getenv("BITBANK_API_KEY")
        self.api_secret = os.getenv("BITBANK_API_SECRET")
        self.check_env()
        self.line = Line()

    def check_env(self):
        """ 環境変数のチェック """
        if (self.api_key is None) or (self.api_secret is None):
            emsg = '''
            Please set BITBANK_API_KEY or BITBANK_API_SECRET in Environment !!
            ex) exoprt BITBANK_API_KEY=XXXXXXXXXXXXXXXXXX
            '''
            raise EnvironmentError(emsg)

    def notify_rsi_under_20(self):
        mtau = MyTechnicalAnalysisUtil()

        while True:
            # RSI が 20 % 以下の場合にLINE通知する
            candle_type_list = ("1min", "5min", "15min", "30min", "1hour")

            for candle_type in candle_type_list:
                rsi = mtau.get_rsi(candle_type)
                if rsi < 20:
                    msg_rsi = "【買い時】RSIが {0} で {1} ％です"
                    self.line.notify_line_stamp(
                        msg_rsi.format(candle_type, rsi), "2", "514")

            time.sleep(1)


# main
if __name__ == '__main__':
    line = Line()

    try:
        Advisor().notify_rsi_under_20()
    except BaseException as be:
        line.notify_line_stamp(
            "RSI通知でエラーが発生しました！ 詳細：{0}".format(be), "1", "17")
        raise BaseException
