# -*- coding: utf-8 -*-

import os
import sys
import traceback
import time
import requests
import pandas as pd
import numpy as np
import logging
from logging import getLogger, StreamHandler, DEBUG
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timezone, timedelta
from sklearn import linear_model
from enum import Enum
import python_bitbankcc

from datetime import datetime, timedelta, timezone


class MyUtil:
    """ 処理に依存しない自分専用のユーティリティクラス """

    def get_timestamp(self):
        """ JSTのタイムスタンプを取得する """
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')


class EmaCross(Enum):
    """ EMSのクロス状態を定義 """
    GOLDEN_CROSS = 1
    DEAD_CROSS = 0
    OTHER_CROSS = -1


class MyTechnicalAnalysisUtil:
    """ テクニカル分析のユーティリティクラス
    https://www.rakuten-sec.co.jp/MarketSpeed/onLineHelp/msman2_5_1_2.html

    PRAM:
        n: 対象データ数(5とか14くらいが良いとされる)
        cadle_type: "1min","5min","15min","30min","1hour"のいづれか。
    """

    def __init__(self):
        """ コンストラクタ """
        self.pubApi = python_bitbankcc.public()
        self.myLogger = MyLogger()
        self.RSI_N = 14

    def get_candlestick(self, n: int, candle_type):
        now = time.time()
        now_utc = datetime.utcfromtimestamp(now)

        yyyymmdd = now_utc.strftime('%Y%m%d')
        self.myLogger.debug(
            "yyyymmdd={0} candle_type={1}".format(yyyymmdd, candle_type))
        candlestick = self.pubApi.get_candlestick(
            "xrp_jpy", candle_type, yyyymmdd)

        ohlcv = candlestick["candlestick"][0]["ohlcv"]
        df_ohlcv = pd.DataFrame(ohlcv,
                                columns=["open",    # 始値
                                         "hight",   # 高値
                                         "low",     # 安値
                                         "close",   # 終値
                                         "amount",  # 出来高
                                         "time"])   # UnixTime

        if(len(ohlcv) <= n):  # データが不足している場合
            yesterday = now_utc - timedelta(days=1)
            str_yesterday = yesterday.strftime('%Y%m%d')
            yday_candlestick = self.pubApi.get_candlestick(
                "xrp_jpy", candle_type, str_yesterday)
            yday_ohlcv = yday_candlestick["candlestick"][0]["ohlcv"]
            df_yday_ohlcv = pd.DataFrame(yday_ohlcv,
                                         columns=["open",      # 始値
                                                  "hight",     # 高値
                                                  "low",       # 安値
                                                  "close",     # 終値
                                                  "amount",    # 出来高
                                                  "time"])     # UnixTime
            df_ohlcv.append(df_yday_ohlcv, ignore_index=True)  # 前日分追加

        return df_ohlcv

    def get_ema(self, candle_type, n_short, n_long):
        """ EMA(指数平滑移動平均)を返却する
        計算式：EMA ＝ 1分前のEMA+α(現在の終値－1分前のEMA)
            *移動平均の期間をn
            *α=2÷(n+1)
        参考
        http://www.algo-fx-blog.com/ema-how-to-do-with-python-pandas/
        """
        df_ema = self.get_candlestick(n_long, candle_type)

        df_ema['ema_short'] = df_ema['close'].ewm(span=int(n_short)).mean()
        df_ema['ema_long'] = df_ema['close'].ewm(span=int(n_long)).mean()

        tail_index = (n_short) * -1
        return df_ema[tail_index:]

    def get_ema_cross_status(self, candle_type, n_short, n_long):
        """ EMAからゴールデンクロス、デットクロス、その他 状態 を返却する
        https://pythondatascience.plavox.info/scikit-learn/%E7%B7%9A%E5%BD%A2%E5%9B%9E%E5%B8%B0
        EMA(diff) = EMA(Short) - EMA(Long)
        過去N分のEMA(diff)から回帰直線の傾きを求め、その傾き(a)で ゴールデンクロス、デットクロス、その他 を
        判定する。
        １．ゴールデンクロス判定
            a(傾き) >= +γ(+閾値) かつ {EMA(diff)[last-1] > 0 かつ EMA(diff)[last] <= 0}
            →　EMA(diff)が正から負に反転した場合
        ２．デットクロス判定
            {(EMA(diff)[last-2] < 0 または EMA(diff)[last-1] < 0) かつ
              EMA(diff)[last] >= 0}
            →　EMA(diff)が負から正に反転した場合(最後の２つが同時にマイナスになることもある)

            最後の２つが同時にマイナスになるパターン
            2018-05-28 07:31:57,910 %(levelname)s EMA:
                open   hight     low    ...     ema_short   ema_long      diff
            443  64.220  64.239  64.220  ...     64.188285  64.165461  0.022825
            444  64.230  64.230  64.199  ...     64.196428  64.170167  0.026261
            445  64.229  64.230  64.173  ...     64.192343  64.170599  0.021743
            446  64.179  64.217  64.173  ...     64.197274  64.174037  0.023238
            447  64.211  64.217  64.181  ...     64.199619  64.176626  0.022993
            448  64.217  64.217  64.200  ...     64.201495  64.179024  0.022471
            449  64.209  64.251  64.209  ...     64.211396  64.184356  0.027040
            450  64.251  64.251  64.191  ...     64.209117  64.185515  0.023602
            451  64.191  64.200  64.080  ...     64.187094  64.179106  0.007987

            2018-05-28 07:32:01,031 %(levelname)s EMA:
                open   hight     low    ...     ema_short   ema_long      diff
            444  64.230  64.230  64.199  ...     64.196428  64.170167  0.026261
            445  64.229  64.230  64.173  ...     64.192343  64.170599  0.021743
            446  64.179  64.217  64.173  ...     64.197274  64.174037  0.023238
            447  64.211  64.217  64.181  ...     64.199619  64.176626  0.022993
            448  64.217  64.217  64.200  ...     64.201495  64.179024  0.022471
            449  64.209  64.251  64.209  ...     64.211396  64.184356  0.027040
            450  64.251  64.251  64.191  ...     64.209117  64.185515  0.023602
            451  64.191  64.200  64.002  ...     64.167694  64.171921 -0.004227
            452  64.098  64.098  64.098  ...     64.153755  64.166445 -0.012691

        ３．その他判定（何もしない）
            -γ(-閾値) < a(傾き) < +γ(+閾値)
        """

        df_ema = self.get_ema(candle_type, n_short, n_long)

        df_ema_x = pd.DataFrame(df_ema["time"], columns=["time"])
        df_ema_y = pd.DataFrame(
            df_ema["ema_short"] - df_ema["ema_long"], columns=["diff"])

        clf = linear_model.LinearRegression()
        x = df_ema_x.values.tolist()
        y = df_ema_y.values.tolist()

        clf.fit(x, y)        # 予測モデルを作成
        a = clf.coef_        # 回帰係数（傾き）
        b = clf.intercept_   # 切片 (誤差)
        c = clf.score(x, y)  # 決定係数

        THRESHOLD = 0.0
        last3_value = df_ema_y["diff"][-3:-2].values[0]
        last2_value = df_ema_y["diff"][-2:-1].values[0]
        last_value = df_ema_y["diff"][-1:].values[0]

        df_ema_debug = pd.concat([df_ema, df_ema_y], axis=1)
        self.myLogger.debug("EMA:\n{0}".format(df_ema_debug))

        msg = "予想モデル：y = {0}x + {1} 決定係数：{2} Booby：{3} Last：{4}"
        self.myLogger.debug(msg.format(a, b, c, last2_value, last_value))

        if((a >= THRESHOLD) and (last2_value < 0) and (last_value > 0)):
            # golden cross
            return EmaCross.GOLDEN_CROSS
        elif(((last3_value > 0) or (last2_value > 0)) and (last_value <= 0)):
            # dead cross
            return EmaCross.DEAD_CROSS

        # other cross
        return EmaCross.OTHER_CROSS

    def get_rsi(self, n: int, candle_type):
        """ RSI：50%を中心にして上下に警戒区域を設け、70%以上を買われすぎ、30%以下を売られすぎと判断します。
        計算式：RSI＝直近N日間の上げ幅合計の絶対値/（直近N日間の上げ幅合計の絶対値＋下げ幅合計の絶対値）×100
        参考
        http://www.algo-fx-blog.com/rsi-python-ml-features/
        """
        df_ohlcv = self.get_candlestick(n, candle_type)
        df_close = df_ohlcv["close"].astype('float')
        df_diff = df_close.diff()

        # 値上がり幅、値下がり幅をシリーズへ切り分け
        up, down = df_diff.copy(), df_diff.copy()
        up[up < 0] = 0
        down[down > 0] = 0

        up_sma_n = up.rolling(window=n, center=False).mean()  # mean:平均を計算
        down_sma_n = down.abs().rolling(window=n, center=False).mean()

        df_rs = up_sma_n / down_sma_n
        df_rsi = 100.0 - (100.0 / (1.0 + df_rs))

        return df_rsi[-1:].values.tolist()[0]  # 最新のRSIを返却（最終行）


class MyLogger:
    """ ログの出力表現を集中的に管理する自分専用クラス """

    def __init__(self):
        """ コンストラクタ """
        # 参考：http://joemphilips.com/post/python_logging/
        self.logger = getLogger(__name__)
        self.logger.setLevel(DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s %(name) %(levelname)s %(message)s")
        sh = StreamHandler()
        sh.setLevel(DEBUG)
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

        rfh = TimedRotatingFileHandler(
            './log.txt', when="d", interval=1, backupCount=20)
        rfh.setLevel(DEBUG)
        rfh.setFormatter(formatter)
        self.logger.addHandler(rfh)

    def debug(self, msg):
        """ DEBUG	10	動作確認などデバッグの記録 """
        self.logger.debug(msg)

    def info(self, msg):
        """ INFO	20	正常動作の記録 """
        self.logger.info(msg)

    def warning(self, msg):
        """ WARNING	30	ログの定義名 """
        self.logger.warning(msg)

    def error(self, msg):
        """ ERROR	40	エラーなど重大な問題 """
        self.logger.error(msg)

    def critical(self, msg):
        """ CRITICAL	50	停止など致命的な問題 """
        self.logger.critical(msg)


class AutoOrder:
    """ 自動売買
    ■ 制御フロー
        全体処理 LOOP
            買い注文処理
                買い注文判定 LOOP
                買い注文約定待ち LOOP
                    買い注文約定判定
                        買い注文約定 BREAK
                    買い注文キャンセル判定
                        買い注文キャンセル注文
                        買い注文(成行)
                        CONTINUE(買い注文約定待ち LOOPへ)

            売り注文処理
                売り注文処理
                売り注文約定待ち LOOP
                    売り注文約定判定
                        売り注文約定 BREAK
                    損切処理判定
                        売り注文キャンセル注文
                        売り注文(成行)
                        売り注文(成行)約定待ち LOOP
    """

    def __init__(self):
        """ コンストラクタ """
        self.LOOP_COUNT_MAIN = 10
        self.AMOUNT = "1"

        self.BUY_ORDER_RANGE = 0.0
        self.SELL_ORDER_RANGE = 0.1
        self.POLLING_SEC_MAIN = 15
        self.POLLING_SEC_BUY = 0.1
        self.POLLING_SEC_SELL = 0.1

        self.myLogger = MyLogger()
        self.api_key = os.getenv("BITBANK_API_KEY")
        self.api_secret = os.getenv("BITBANK_API_SECRET")
        self.line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")

        self.check_env()

        self.mu = MyUtil()
        self.mtau = MyTechnicalAnalysisUtil()

        self.pubApi = python_bitbankcc.public()
        self.prvApi = python_bitbankcc.private(self.api_key, self.api_secret)

    def check_env(self):
        """ 環境変数のチェック """
        if ((self.api_key is None) or (self.api_secret is None)):
            emsg = '''
            Please set BITBANK_API_KEY or BITBANK_API_SECRET in Environment !!
            ex) exoprt BITBANK_API_KEY=XXXXXXXXXXXXXXXXXX
            '''
            raise EnvironmentError(emsg)

        if (self.api_key is None):
            emsg = '''
            Please set LINE_NOTIFY_TOKEN in OS environment !!
            ex) exoprt LINE_NOTIFY_TOKEN=XXXXXXXXXXXXXXXXXX"
            '''
            raise EnvironmentError(emsg)

    def get_balances(self):
        """ 現在のXRP資産の取得 """
        balances = self.prvApi.get_asset()
        for data in balances['assets']:
            if((data['asset'] == 'jpy') or (data['asset'] == 'xrp')):
                self.myLogger.info('●通貨：' + data['asset'])
                self.myLogger.info('保有量：' + data['onhand_amount'])

    def get_total_assets(self):
        """ 現在の総資産（円）の取得 """
        balances = self.prvApi.get_asset()
        total_assets = 0.0
        for data in balances['assets']:
            if (data['asset'] == 'jpy'):
                total_assets = total_assets + float(data['onhand_amount'])
            elif (data['asset'] == 'xrp'):
                xrp_last, _, _ = self.get_xrp_jpy_value()
                xrp_assets = float(data['onhand_amount']) * float(xrp_last)
                total_assets = total_assets + xrp_assets
        return total_assets

    def get_xrp_jpy_value(self):
        """ 現在のXRP価格を取得 """
        value = self.pubApi.get_ticker(
            'xrp_jpy'  # ペア
        )

        last = value['last']  # 現在値
        sell = value['sell']  # 現在の売り注文の最安値
        buy = value['buy']    # 現在の買い注文の最高値

        return last, sell, buy

    def get_active_orders(self):
        """ 現在のアクティブ注文情報を取得 """
        activeOrders = self.prvApi.get_active_orders('xrp_jpy')
        return activeOrders

    def is_fully_filled(self, orderResult, threshold_price):
        """ 注文の約定を判定 """
        last, _, _ = self.get_xrp_jpy_value()

        side = orderResult["side"]
        order_id = orderResult["order_id"]
        pair = orderResult["pair"]
        status = orderResult["status"]
        f_price = float(orderResult["price"])
        # f_start_amount = float(orderResult["remaining_amount"])    # 注文時の数量
        f_remaining_amount = float(orderResult["remaining_amount"])  # 未約定の数量
        f_executed_amount = float(orderResult["executed_amount"])    # 約定済み数量
        f_threshold_price = float(threshold_price)  # buy:買直し sell:損切 価格
        f_last = float(last)

        # self.myLogger.debug("注文時の数量：{0:.0f}".format(f_start_amount))
        result = False
        if (status == "FULLY_FILLED"):
            msg = ("{0} 注文 約定済 {7}：{1:.3f} 円 x {2:.0f}({3}) "
                   "[現在:{4:.3f}円] [閾値]：{5:.3f} ID：{6}")
            self.myLogger.info(msg.format(side,
                                          f_price,
                                          f_executed_amount,
                                          pair,
                                          f_last,
                                          f_threshold_price,
                                          order_id,
                                          status))
            result = True
        elif (status == "CANCELED_UNFILLED"):
            msg = ("{0} 注文 キャンセル済 {7}：{1:.3f} 円 x {2:.0f}({3}) "
                   "[現在:{4:.3f}円] [閾値]：{5:.3f} ID：{6}")
            self.myLogger.info(msg.format(side,
                                          f_price,
                                          f_executed_amount,
                                          pair,
                                          f_last,
                                          f_threshold_price,
                                          order_id,
                                          status))
            result = True
        else:
            msg = ("{0} 注文 約定待ち {7}：{1:.3f}円 x {2:.0f}({3}) "
                   "[現在:{4:.3f}円] [閾値]：{5:.3f} ID：{6}")
            self.myLogger.info(msg.format(side,
                                          f_price,
                                          f_remaining_amount,
                                          pair,
                                          f_last,
                                          f_threshold_price,
                                          order_id,
                                          status))
        return result

    def get_buy_order_info(self):
        """ 買い注文のリクエスト情報を取得 """
        _, _, buy = self.get_xrp_jpy_value()
        # 買い注文アルゴリズム
        buyPrice = str(float(buy) - self.BUY_ORDER_RANGE)

        buy_order_info = {"pair": "xrp_jpy",    # ペア
                          "amount": self.AMOUNT,  # 注文枚数
                          "price": buyPrice,    # 注文価格
                          "orderSide": "buy",   # buy or sell
                          "orderType": "limit"  # 指値注文の場合はlimit TODO 成行にする？
                          }
        return buy_order_info

    def get_sell_order_info(self):
        """ 売り注文のリクエスト情報を取得 """
        _, sell, _ = self.get_xrp_jpy_value()
        # 売り注文アルゴリズム
        sellPrice = str(float(sell) + self.SELL_ORDER_RANGE)
        sell_order_info = {"pair": "xrp_jpy",      # ペア
                           "amount": self.AMOUNT,  # 注文枚数
                           "price": sellPrice,     # 注文価格
                           "orderSide": "sell",    # buy or sell
                           "orderType": "limit"    # 指値注文の場合はlimit
                           }
        return sell_order_info

    def get_sell_order_info_by_barket(self, amount, price):
        """ 売り注文(成行)のリクエスト情報を取得 """
        sell_order_info = {"pair": "xrp_jpy",      # ペア
                           "amount": amount,       # 注文枚数
                           "price": price,         # 注文価格
                           "orderSide": "sell",    # buy or sell
                           "orderType": "market"   # 成行注文の場合はmarket
                           }
        return sell_order_info

    def is_stop_loss(self, sell_order_result):
        """ 売り注文(損切注文)の判定
                条件(condition)：
            1. 含み損が損切価格より大きい　または
            2. RSIが閾値(RSI_THRESHOLD)より大きい　かつ　含み損が損切価格の(n*100)％より大きい　または
            3. EMSクロスがデッドクロスの場合
        """

        # 条件1
        last, _, _ = self.get_xrp_jpy_value()
        f_last = float(last)  # 現在値
        stop_loss_price = self.get_stop_loss_price(sell_order_result)
        condition_1 = (stop_loss_price > f_last)

        # 条件2
        RSI_THRESHOLD = 60
        f_rsi = float(self.mtau.get_rsi(9, "1min"))
        over_rsi = (f_rsi > RSI_THRESHOLD)
        n = 0.30
        f_stop_loss_price_n = float(
            self.get_stop_loss_price_n(sell_order_result, n))
        over_stop_loss_n = (f_stop_loss_price_n > f_last)
        condition_2 = over_rsi and over_stop_loss_n

        # 条件3
        n_short = 9
        n_long = 26
        status = self.mtau.get_ema_cross_status("1min", n_short, n_long)
        dead_cross = (status == EmaCross.DEAD_CROSS)
        condition_3 = dead_cross

        if(condition_1 or condition_2 or condition_3):
            msg = ("【損切判定されました 現在値：{0} 損切値：{1} 】"
                   .format(f_last, stop_loss_price))
            self.myLogger.info(msg)
            return True
        else:
            return False

    def get_stop_loss_price(self, sell_order_result):
        """ 損切価格の取得 """
        f_sell_order_price = float(sell_order_result["price"])  # 売り指定価格

        THRESHOLD = 10  # 閾値
        return f_sell_order_price - (self.SELL_ORDER_RANGE * THRESHOLD)

    def get_stop_loss_price_n(self, sell_order_result, n):
        """ 損切価格(閾値にnをかける)の取得 """
        f_sell_order_price = float(sell_order_result["price"])  # 売り指定価格

        THRESHOLD = 10 * n  # 閾値
        return f_sell_order_price - (self.SELL_ORDER_RANGE * THRESHOLD)

    def is_buy_order(self):
        """ 買い注文の判定
        条件(condition)：
            1. RSIが閾値(RSI_THRESHOLD)より小さい　かつ
            2. EMSクロスがゴールデンクロスの場合
        """

        # 条件1
        f_rsi = float(self.mtau.get_rsi(self.mtau.RSI_N, "1min"))
        last, _, _ = self.get_xrp_jpy_value()
        f_last = float(last)  # 現在値
        RSI_THRESHOLD = 60
        condition_1 = (f_rsi < RSI_THRESHOLD)

        # 条件2
        n_short = 9
        n_long = 26
        ema_cross_status = self.mtau.get_ema_cross_status(
            "1min", n_short, n_long)
        condition_2 = (ema_cross_status == EmaCross.GOLDEN_CROSS)

        msg = ("買い注文待ち 現在値：{0:.3f} RSI：{1:.3f} RSI閾値：{2} EMSクロス：{3}"
               .format(f_last, f_rsi, RSI_THRESHOLD, ema_cross_status))
        self.myLogger.debug(msg)

        if(condition_1 and condition_2):
            return True

        return False

    def is_buy_order_cancel(self, buy_order_result):
        """ 買い注文のキャンセル判定 """
        last, _, _ = self.get_xrp_jpy_value()
        f_last = float(last)  # 現在値

        f_buy_order_price = float(buy_order_result["price"])
        f_last = float(last)
        f_buy_cancel_price = float(self.get_buy_cancel_price(buy_order_result))

        if (f_last > f_buy_cancel_price):
            msg = ("現在値：{0:.3f} 買い注文価格：{1:.3f} 再注文価格：{2:.3f}"
                   .format(f_last, f_buy_order_price, f_buy_cancel_price))
            self.myLogger.debug(msg)
            return True
        else:
            return False

    def get_buy_cancel_price(self, buy_order_result):
        """ 買い注文 キャンセル 価格 """
        f_buy_order_price = float(buy_order_result["price"])
        THRESHOLD = 0.5  # 再買い注文するための閾値
        return THRESHOLD + f_buy_order_price

    def buy_order(self):
        """ 買い注文処理 """

        # 買うタイミングを待つ
        while True:
            time.sleep(self.POLLING_SEC_BUY)

            if(self.is_buy_order()):
                break

        # 買い注文処理
        buy_order_info = self.get_buy_order_info()
        buy_value = self.prvApi.order(
            buy_order_info["pair"],  # ペア
            buy_order_info["price"],  # 価格
            buy_order_info["amount"],  # 注文枚数
            buy_order_info["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            # 注文タイプ 指値 or 成行(limit or market))
            buy_order_info["orderType"]
        )

        self.notify_line(("買い注文発生 {0}円 ID：{1}")
                         .format(buy_order_info["price"],
                                 buy_value["order_id"]))

        # 買い注文約定待ち
        while True:
            time.sleep(self.POLLING_SEC_BUY)

            # 買い注文結果を取得
            buy_order_result = self.prvApi.get_order(
                buy_value["pair"],     # ペア
                buy_value["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )
            buy_cancel_price = self.get_buy_cancel_price(buy_order_result)

            # 買い注文の約定判定
            if(self.is_fully_filled(buy_order_result, buy_cancel_price)):
                break

            # 買い注文のキャンセル判定
            if (self.is_buy_order_cancel(buy_order_result)):
                # 買い注文(成行)
                buy_cancel_order_result = self.prvApi.cancel_order(
                    buy_order_result["pair"],     # ペア
                    buy_order_result["order_id"]  # 注文ID
                )

                self.notify_line(("買い注文キャンセル処理発生！！ ID：{0}")
                                 .format(buy_value["order_id"]))

                buy_cancel_price = self.get_buy_cancel_price(
                    buy_cancel_order_result)
                buy_order_result = buy_cancel_order_result
                continue  # 買い注文約定待ちループへ

        return buy_order_result  # 買い注文終了(売り注文へ)

    def sell_order(self, buy_order_result):
        """ 売り注文処理 """
        sell_order_info = self.get_sell_order_info()
        sell_order_result = self.prvApi.order(
            sell_order_info["pair"],       # ペア
            sell_order_info["price"],      # 価格
            sell_order_info["amount"],     # 注文枚数
            sell_order_info["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            sell_order_info["orderType"]   # 注文タイプ 指値 or 成行(limit or market))
        )

        self.notify_line(("売り注文発生 {0}円 ID：{1}")
                         .format(sell_order_info["price"],
                                 sell_order_result["order_id"]))

        while True:
            time.sleep(self.POLLING_SEC_SELL)

            sell_order_status = self.prvApi.get_order(
                sell_order_result["pair"],     # ペア
                sell_order_result["order_id"]  # 注文タイプ 指値 or 成行
            )

            stop_loss_price = self.get_stop_loss_price(sell_order_status)
            if (self.is_fully_filled(sell_order_status,
                                     stop_loss_price)):  # 売り注文約定判定
                order_id = sell_order_status["order_id"]
                f_amount = float(sell_order_status["executed_amount"])
                f_sell = float(sell_order_status["price"])
                f_buy = float(buy_order_result["price"])
                f_benefit = (f_sell - f_buy) * f_amount

                line_msg = "売り注文約定 利益：{0:.3f}円 x {1:.0f}XRP ID：{2}"
                self.notify_line_stamp(line_msg.format(
                    f_benefit, f_amount, order_id), "1", "10")
                self.myLogger.debug(line_msg.format(
                    f_benefit, f_amount, order_id))

                break

            stop_loss_price = self.get_stop_loss_price(sell_order_status)
            if (self.is_stop_loss(sell_order_status)):  # 損切する場合
                # 約定前の売り注文キャンセル(結果のステータスはチェックしない)
                cancel_result = self.prvApi.cancel_order(
                    sell_order_status["pair"],     # ペア
                    sell_order_status["order_id"]  # 注文ID
                )

                order_id = cancel_result["order_id"]
                self.myLogger.debug("売りキャンセル注文ID：{0}".format(order_id))

                # 売り注文（成行）で損切
                amount = buy_order_result["start_amount"]
                price = buy_order_result["price"]  # 成行なので指定しても意味なし？
                sell_order_info_by_market = self.get_sell_order_info_by_barket(
                    amount, price)

                sell_market_result = self.prvApi.order(
                    sell_order_info_by_market["pair"],       # ペア
                    sell_order_info_by_market["price"],      # 価格
                    sell_order_info_by_market["amount"],     # 注文枚数
                    sell_order_info_by_market["orderSide"],
                    sell_order_info_by_market["orderType"]
                )

                while(self.is_fully_filled(
                        sell_market_result, stop_loss_price)):
                    break

                order_id = sell_market_result["order_id"]
                self.myLogger.debug("売り注文（成行）ID：{0}".format(order_id))

                order_id = sell_market_result["order_id"]
                f_amount = float(sell_market_result["executed_amount"])
                f_sell = float(sell_market_result["price"])
                f_buy = float(buy_order_result["price"])
                f_benefit = (f_sell - f_buy) * f_amount

                msg = ("デバッグ 売り注文(損切)！ 損失：{0:.3f}円 x {1:.0f}XRP"
                       "ID：{2} f_sell={3} f_buy={4}")
                self.myLogger.debug(msg.format(
                    f_benefit, f_amount, order_id, f_sell, f_buy))

                line_msg = "売り注文(損切)！ 損失：{0:.3f}円 x {1:.0f}XRP ID：{2}"
                self.notify_line_stamp(line_msg.format(
                    f_benefit, f_amount, order_id), "1", "104")
                self.myLogger.debug(line_msg.format(
                    f_benefit, f_amount, order_id))

                sell_order_result = sell_market_result
                break

        return buy_order_result, sell_order_result

    def order_buy_sell(self):
        """ 注文処理メイン（買い注文 → 売り注文） """
        buy_order_result = self.buy_order()
        buy_order_result, _ = self.sell_order(buy_order_result)

    def notify_line(self, message):
        """ LINE通知（messageのみ） """
        return self.notify_line_stamp(message, "", "")

    def notify_line_stamp(self, message, stickerPackageId, stickerId):
        """ LINE通知（スタンプ付き）
        LINEスタンプの種類は下記URL参照
        https://devdocs.line.me/files/sticker_list.pdf
        """
        line_notify_api = 'https://notify-api.line.me/api/notify'

        total_assets = self.get_total_assets()
        message = "{0}  {1} 総資産：{2}円".format(
            self.mu.get_timestamp(), message, total_assets)

        if(stickerPackageId == "" or stickerId == ""):
            payload = {'message': message}
        else:
            payload = {'message': message,
                       'stickerPackageId': stickerPackageId,
                       'stickerId': stickerId}

        headers = {'Authorization': 'Bearer ' +
                   self.line_notify_token}  # 発行したトークン
        return requests.post(line_notify_api, data=payload, headers=headers)


# main
if __name__ == '__main__':
    ao = AutoOrder()

    try:
        for i in range(0, ao.LOOP_COUNT_MAIN):
            ao.myLogger.info("#############################################")
            ao.myLogger.info("=== 実験[NO.{0}] ===".format(i))
            ao.order_buy_sell()
            time.sleep(ao.POLLING_SEC_MAIN)

            activeOrders = ao.get_active_orders()["orders"]
            if(len(activeOrders) != 0):
                ao.notify_line_stamp("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)), "1", "422")
                ao.myLogger.debug("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)))
                for i in range(len(activeOrders)):
                    ao.myLogger.debug(
                        "現在のオーダー一覧 :{0}".format(activeOrders[i]))

                break  # Mainループブレイク

        ao.get_balances()
        ao.notify_line_stamp("自動売買が終了！処理回数：{0}回".format(i + 1), "2", "516")

    except KeyboardInterrupt as ki:
        ao.notify_line_stamp("自動売買が中断されました 詳細：{0}".format(ki), "1", "3")
    except BaseException as be:
        ao.notify_line_stamp("システムエラーが発生しました！ 詳細：{0}".format(be), "1", "17")
        raise BaseException

    sys.exit()
