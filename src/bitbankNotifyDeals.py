# -*- coding: utf-8 -*-
import time

from myUtil import Line
from technicalAnalysis import MyTechnicalAnalysisUtil

# main
if __name__ == '__main__':
    line = Line()
    mtau = MyTechnicalAnalysisUtil()

    try:
        while True:
            # RSI が 20 % 以下の場合にLINE通知する
            candle_type_list = ("1min", "5min", "15min", "60min")

            for candle_type in candle_type_list:
                rsi = mtau.get_rsi(9, candle_type)
                if rsi < 20:
                    msg_rsi = "【買い時】RSIが {0} で {1} ％です"
                    line.notify_line_stamp(
                        msg_rsi.format(candle_type, rsi), "1", "3")

            time.sleep(1)
    except BaseException as be:
        line.notify_line_stamp(
            "RSI通知でエラーが発生しました！ 詳細：{0}".format(be), "1", "17")
        raise BaseException
