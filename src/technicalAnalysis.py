import time
from enum import Enum
from datetime import datetime, timedelta

import pandas as pd
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
        self.myLogger = MyLogger(__name__)
        self.RSI_N = 14

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
        condition_1 = (mhd["diff"].values[0] <= 0) and (
            mhd["diff"].values[1] > 0)  # 買いシグナル
        condition_2 = (mhd["diff"].values[0] >= 0) and (
            mhd["diff"].values[1] < 0)  # 売りシグナル

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
        self.myLogger.debug(
            "\n======== df_ema {1} =======\n\n {0}".format(df_ema, candle_type))

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
