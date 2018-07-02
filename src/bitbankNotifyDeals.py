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
            pair_dic = {"btc_jpy": 514, "xrp_jpy": 166}
            # RSI が 20 % 以下の場合にLINE通知する
            candle_type_list = ("5min", "15min")

            for pair in pair_dic:
                for candle_type in candle_type_list:
                    rsi = mtau.get_rsi(candle_type, pair)
                    rci = mtau.get_rci(candle_type, pair)
                    msg_rxi = "【{0} {1} 買い時】RSI= {2:.1f} ％ RCI= {3:.1f} ％"

                    if rsi < 20:
                        self.line.notify_line_stamp(
                            msg_rxi.format(
                                pair,
                                candle_type,
                                rsi,
                                rci), "2", pair_dic[pair])

                    print(msg_rxi.format(pair, candle_type, rsi, rci))
                    time.sleep(1)


# main
if __name__ == '__main__':
    line = Line()
    retry = 0
    while True:
        print("===== RSI通知処理開始 ======")

        try:
            Advisor().notify_rsi_under_20()
        except BaseException as be:
            msg = "RSI通知でエラーが発生しました！ 詳細：{0}".format(be)
            print(be)
            line.notify_line_stamp(msg, "1", "17")
            raise BaseException

        retry = retry + 1
