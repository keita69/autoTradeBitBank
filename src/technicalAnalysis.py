import time
from enum import Enum
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import python_bitbankcc
from myUtil import MyLogger


class EmaCross(Enum):
    """ EMSのクロス状態を定義 """
    GOLDEN = 1
    DEAD = 0
    OTHER = -1


class MacdCross(Enum):
    """ MACDのクロス状態を定義 """
    GOLDEN = 1
    DEAD = 0
    OTHER = -1


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
        self.myLogger = MyLogger("MyTechnicalAnalysisUtil")
        self.RSI_N = 14

    def get_candlestick_range(self, candle_type, s_yyyymmdd, e_yyyymmdd):
        """ チャート情報（ロウソク）をstart(yyyymmdd)-end(yyyymmdd)期間分取得する
        """
        start_ymd = datetime.strptime(s_yyyymmdd, '%Y%m%d')
        end_ymd = datetime.strptime(e_yyyymmdd, '%Y%m%d')

        if start_ymd > end_ymd:
            raise ValueError

        crnt_ymd = end_ymd

        df = pd.DataFrame()

        while True:
            str_crnt_ymd = crnt_ymd.strftime('%Y%m%d')
            candlestick = self.pubApi.get_candlestick(
                "xrp_jpy", candle_type, str_crnt_ymd)
            ohlcv = candlestick["candlestick"][0]["ohlcv"]
            df_ohlcv = pd.DataFrame(ohlcv,
                                    columns=["open",   # 始値
                                             "hight",   # 高値
                                             "low",     # 安値
                                             "close",   # 終値
                                             "amount",  # 出来高
                                             "time"])   # UnixTime
            df = df.append(df_ohlcv, ignore_index=True)
            if str_crnt_ymd == s_yyyymmdd:
                break

            crnt_ymd = crnt_ymd - timedelta(days=1)

        return df

    def get_candlestick(self, candle_type):
        """ 最新のチャート情報（ロウソク）を今日と昨日の２日分取得する。
        ・サンプル
                   open   hight     low   close      amount           time
            221  65.372  65.401  65.351  65.400  39242.7256  1527738060000
            222  65.401  65.420  65.334  65.368  35837.8861  1527738120000
            223  65.368  65.368  65.208  65.272  70144.5507  1527738180000
        """
        now = time.time()
        now_utc = datetime.utcfromtimestamp(now)

        yyyymmdd = now_utc.strftime('%Y%m%d')
        # self.myLogger.debug(
        #    "yyyymmdd={0} candle_type={1}".format(yyyymmdd, candle_type))
        try:
            candlestick = self.pubApi.get_candlestick(
                "xrp_jpy", candle_type, yyyymmdd)
        except ConnectionResetError as cre:
            self.myLogger.exception("get_canlestickでエラー。再実行します", cre)
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

        yesterday = now_utc - timedelta(days=1)
        str_yesterday = yesterday.strftime('%Y%m%d')
        try:
            yday_candlestick = self.pubApi.get_candlestick(
                "xrp_jpy", candle_type, str_yesterday)
        except ConnectionResetError as cre:
            self.myLogger.exception(
                "get_canlestick(yesterday)でエラー。再実行します", cre)
            candlestick = self.pubApi.get_candlestick(
                "xrp_jpy", candle_type, str_yesterday)

        yday_ohlcv = yday_candlestick["candlestick"][0]["ohlcv"]
        df_yday_ohlcv = pd.DataFrame(yday_ohlcv,
                                     columns=["open",      # 始値
                                              "hight",     # 高値
                                              "low",       # 安値
                                              "close",     # 終値
                                              "amount",    # 出来高
                                              "time"])     # UnixTime
        df_yday_ohlcv.append(df_ohlcv, ignore_index=True)  # 前日分追加

        # self.myLogger.debug("ohlcv:\n{0}".format(df_ohlcv))
        return df_ohlcv

    def get_ema(self, candle_type, n_short, n_long):
        """ EMA(指数平滑移動平均)を返却する
        計算式：EMA ＝ 1分前のEMA+α(現在の終値－1分前のEMA)
            *移動平均の期間をn
            *α=2÷(n+1)
        参考
        http://www.algo-fx-blog.com/ema-how-to-do-with-python-pandas/
        """

        df_ema = self.get_candlestick(candle_type)
        df_ema['ema_long'] = df_ema['close'].ewm(span=int(n_long)).mean()
        df_ema['ema_short'] = df_ema['close'].ewm(span=int(n_short)).mean()

        # self.myLogger.debug("ema:\n{0}".format(df_ema))

        return df_ema

    def get_macd_cross_status(self, candle_type):
        """
        ・シグナルをMACDが下から上へ抜けた時＝上昇トレンド(＝買いシグナル)
        ・シグナルをMACDが上から下へ抜けた時＝下降トレンド(＝売りシグナル)
        """
        macd = self.get_macd(candle_type)
        mhd_org = macd.tail(2)
        mhd = mhd_org.copy()
        mhd["diff"] = mhd_org["macd"] - mhd_org["signal"]

        # self.myLogger.debug(
        #    "\n======== macd_head =======\n\n {0}".format(mhd))
        condition_1 = (mhd["diff"].values[0] <= -0.01) and (
            mhd["diff"].values[1] > -0.01)  # 買いシグナル
        condition_2 = (mhd["diff"].values[0] >= 0.01) and (
            mhd["diff"].values[1] < 0.01)  # 売りシグナル

        status = MacdCross.OTHER
        if condition_1:
            # golden cross
            status = MacdCross.GOLDEN
        elif condition_2:
            # dead cross
            status = MacdCross.DEAD

        # self.myLogger.debug("MACD Status:{0}".format(status))
        return status

    def get_macd(self, candle_type):
        """ MACD:MACDはEMA（指数平滑移動平均）の長期と短期の値を用いており、主にトレンドの方向性や転換期を見極める指標
        計算式
            MACD = 短期EMA（12） – 長期EMA（26）
            シグナル = MACDの指数平滑移動平均（9）
        参考
        http://www.algo-fx-blog.com/macd-python-technical-indicators/
        """
        n_short = 12
        n_long = 26
        n_signal = 9
        df_ema = self.get_ema(candle_type, n_short, n_long)
        df_ema["macd"] = df_ema["ema_short"] - df_ema["ema_long"]
        df_ema["signal"] = df_ema["macd"].ewm(span=n_signal).mean()
        # self.myLogger.debug(
        #     "\n======== df_ema {1} \n\n {0}".format(df_ema, candle_type))

        return df_ema

    def get_rsi(self, n: int, candle_type):
        """ RSI：50%を中心にして上下に警戒区域を設け、70%以上を買われすぎ、30%以下を売られすぎと判断します。
        計算式：RSI＝直近N日間の上げ幅合計の絶対値/（直近N日間の上げ幅合計の絶対値＋下げ幅合計の絶対値）×100
        参考
        http://www.algo-fx-blog.com/rsi-python-ml-features/
        """
        df_ohlcv = self.get_candlestick(candle_type)
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

    def get_rci(self, candle_type):
        """ RCI：RCIとは“Rank Correlation Index”の略です。日本語でいうと「順位相関係数」となります。
            日付（時間）と価格それぞれに順位をつけることによって、両者にどれだけの相関関係があるのかを計算し、
            相場のトレンドとその勢い、過熱感を知ることができます。
            ピーク値で反転しやすい。± 90 % を超えると売りトレンドになりやすい(自論)。
        計算式：RCI = ( 1 – 6y / ( n × ( n**2 – 1 ) ) ) × 100   ※ -100 < RCI < 100
                a = 時間の順位
                b = レートの順位
                y = (a-b)**2 の合計
                n : 基本は 9
        参考
        https://kabu.com/investment/guide/technical/14.html
        """
        n = 9

        now = time.time()
        now_utc = datetime.utcfromtimestamp(now)
        today = now_utc.strftime('%Y%m%d')

        yesterday_utc = now_utc - timedelta(days=n)
        yesterday = yesterday_utc.strftime('%Y%m%d')

        df = self.get_candlestick_range(candle_type, yesterday, today).tail(n)

        df = df.sort_values("time", ascending=False)  # 降順
        df["a"] = np.arange(1, len(df)+1)

        df = df.sort_values("close", ascending=False)  # 降順
        df["b"] = np.arange(1, len(df)+1)

        df["a-b"] = df["a"] - df["b"]
        df["(a-b)**2"] = df["a-b"]**2

        y = df["(a-b)**2"].sum()

        rci = (1 - 6*y / (n * (n**2 - 1))) * 100

        self.myLogger.debug("df_rci:{0}　y:{1}".format(df, y))
        return rci
