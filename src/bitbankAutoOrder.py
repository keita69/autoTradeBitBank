# -*- coding: utf-8 -*-

import os
import time

import pandas as pd
import python_bitbankcc

from myUtil import MyLogger, MyUtil, Line
from technicalAnalysis import MacdCross, MyTechnicalAnalysisUtil


class Bitbank:
    def __init__(self):
        """ コンストラクタ """
        self.api_key = os.getenv("BITBANK_API_KEY")
        self.api_secret = os.getenv("BITBANK_API_SECRET")
        self.check_env()
        self.pubApi = python_bitbankcc.public()
        self.prvApi = python_bitbankcc.private(self.api_key, self.api_secret)
        self.myLogger = MyLogger(__name__)

    def check_env(self):
        """ 環境変数のチェック """
        if (self.api_key is None) or (self.api_secret is None):
            emsg = '''
            Please set BITBANK_API_KEY or BITBANK_API_SECRET in Environment !!
            ex) exoprt BITBANK_API_KEY=XXXXXXXXXXXXXXXXXX
            '''
            raise EnvironmentError(emsg)

    def get_balances(self):
        """ 現在のXRP資産の取得 """
        balances = self.prvApi.get_asset()
        for data in balances['assets']:
            if (data['asset'] == 'jpy') or (data['asset'] == 'xrp'):
                self.myLogger.info('●通貨：' + data['asset'])
                self.myLogger.info('保有量：' + data['onhand_amount'])

    def get_total_assets(self):
        """ 現在の総資産（円）の取得 """
        balances = self.prvApi.get_asset()
        total = 0.0
        for data in balances['assets']:
            if data['asset'] == 'jpy':
                total = total + float(data['onhand_amount'])
            elif data['asset'] == 'xrp':
                xrp_last, _, _ = self.get_xrp_jpy_value()
                xrp_assets = float(data['onhand_amount']) * float(xrp_last)
                total = total + xrp_assets
        return total

    def get_xrp_jpy_value(self):
        """ 現在のXRP価格を取得 """
        try:
            value = self.pubApi.get_ticker(
                'xrp_jpy'  # ペア
            )
        except BaseException as be:
            self.myLogger.exception("r現在のXRP価格取得失敗。リトライ", be)
            self.get_xrp_jpy_value()

        last = float(value['last'])  # 現在値
        sell = float(value['sell'])  # 現在の売り注文の最安値
        buy = float(value['buy'])    # 現在の買い注文の最高値

        return last, sell, buy

    def get_active_orders(self):
        """ 現在のアクティブ注文情報を取得 """
        return self.prvApi.get_active_orders('xrp_jpy')


class AutoTrader:
    """ 自動売買
    """

    def __init__(self, order):
        """ コンストラクタ """
        self.order = order
        self.LOOP_COUNT_MAIN = 10
        self.AMOUNT = "1"

        self.BENEFIT = 0.5  # 利益
        self.BUY_ORDER_RANGE = 0.0
        self.BUY_CANCEL_THRESHOLD = 0.5  # 再買い注文するための閾値
        self.SELL_ORDER_RANGE = 0.1
        self.POLLING_SEC_MAIN = 15
        self.POLLING_SEC_BUY = 0.1
        self.POLLING_SEC_SELL = 0.1

        self.myLogger = MyLogger(__name__)

        self.mu = MyUtil()
        self.mtau = MyTechnicalAnalysisUtil()
        self.line = Line()
        self.bitbank = Bitbank()

    def get_order_price(self, order):
        """ 価格または平均価格から価格を取得する """
        self.myLogger.debug("注文の価格を取得する {0}".format(order))
        if order.get("price") is not None:
            p = order["price"]
        elif order.get("average_price") is not None:
            p = order["average_price"]
        else:
            raise AttributeError

        f_price = float(p)
        return f_price

    def is_fully_filled(self, orderResult):
        """ 注文の約定を判定 """
        last, _, _ = self.bitbank.get_xrp_jpy_value()

        side = orderResult["side"]
        f_price = self.get_order_price(orderResult)
        status = orderResult["status"]
        f_remaining_amount = float(orderResult["remaining_amount"])  # 未約定の数量
        f_executed_amount = float(orderResult["executed_amount"])    # 約定済み数量
        pair = orderResult["pair"]
        f_last = float(last)
        order_id = orderResult["order_id"]

        # self.myLogger.debug("注文時の数量：{0:.0f}".format(f_start_amount))
        result = False
        if status == "FULLY_FILLED":
            msg_promise = ("{0} 注文 約定済 {6}：{1:.3f} 円 x {2:.0f}({3}) "
                           "[現在:{4:.3f}円] ID：{5}")
            self.myLogger.info(msg_promise.format(side,
                                                  f_price,
                                                  f_executed_amount,
                                                  pair,
                                                  f_last,
                                                  order_id,
                                                  status))
            result = True
        else:
            msg_wait = ("{0} 注文 約定待ち {6}：{1:.3f}円 x {2:.0f}({3}) "
                        "[現在:{4:.3f}円] ID：{5}")
            self.myLogger.info(msg_wait.format(side,
                                               f_price,
                                               f_remaining_amount,
                                               pair,
                                               f_last,
                                               order_id,
                                               status))
        return result

    def get_buy_order_info(self):
        """ 買い注文(成行)のリクエスト情報を取得 """
        buy_order_info = {"pair": "xrp_jpy",      # ペア
                          "amount": self.AMOUNT,  # 注文枚数
                          # "price": buyPrice,    # 注文価格
                          "price": 0.0,             # 注文価格
                          "orderSide": "buy",     # buy
                          "orderType": "market"   # 成行(market)
                          }
        return buy_order_info

    def get_sell_order_info(self):
        """ 売り注文のリクエスト情報を取得 """
        sell_order_info = {"pair": "xrp_jpy",      # ペア
                           "amount": self.AMOUNT,  # 注文枚数
                           "price": 0.0,           # 注文価格
                           "orderSide": "sell",    # buy or sell
                           "orderType": "market"   # 指値注文の場合はlimit
                           }
        return sell_order_info

    def is_stop_loss(self, sell_order_result):
        """ 売り注文(損切注文)の判定 下記、条件の場合は損切をする（True）
                条件(condition)：
            1. 含み損が損切価格より大きい　または
            2. RSIが閾値(RSI_THRESHOLD)より大きい　かつ　含み損が損切価格の(n*100)％より大きい
        """

        # 条件1
        last, _, _ = self.bitbank.get_xrp_jpy_value()
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

        if condition_1 or condition_2:
            msg_cond = ("【損切判定されました 現在値：{0:.3f} 損切値：{1:.3f}】C[{2}][{3}]"
                        .format(f_last, stop_loss_price,
                                condition_1, condition_2))
            self.myLogger.info(msg_cond)
            return True
        else:
            return False

    def get_stop_loss_price(self, sell_order_result):
        """ 損切価格の取得 """
        f_sell_order_price = self.get_order_price(sell_order_result)  # 売り指定価格

        THRESHOLD = 10  # 閾値
        return f_sell_order_price - (self.SELL_ORDER_RANGE * THRESHOLD)

    def get_stop_loss_price_n(self, sell_order_result, n):
        """ 損切価格(閾値にnをかける)の取得 """
        f_sell_order_price = self.get_order_price(sell_order_result)  # 売り指定価格

        THRESHOLD = 10 * n  # 閾値
        return f_sell_order_price - (self.SELL_ORDER_RANGE * THRESHOLD)

    def is_buy_order(self):
        """ 買い注文の判定
        条件(condition)：
            1. 1min MACDクロスがゴールデンクロスの場合　かつ
            2. (5min MACD - シグナル) が正の場合　かつ
               シグナルをMACDが下から上へ抜けた時＝上昇トレンドが始まるよーー！＝買いシグナル
            3. EMSクロスdiffの絶対値の総和がEMS_DIFF_THRESHOLD以上
        """

        last, _, _ = self.bitbank.get_xrp_jpy_value()
        f_last = float(last)  # 現在値

        # 条件1
        macd_status = self.mtau.get_macd_cross_status("1min")
        condition_1 = (macd_status == MacdCross.GOLDEN)

        # 条件2
        df_macd_5 = self.mtau.get_macd("5min")
        # self.myLogger.debug("5min macd {0}".format(df_macd_5))
        macd_5 = df_macd_5.iloc[-1]["macd"]
        sig_5 = df_macd_5.iloc[-1]["signal"]
        condition_2 = (macd_5 > sig_5)

        # 条件3
        n_short = 9
        n_long = 26
        EMS_DIFF_THRESHOLD = 0.1
        df_ema = self.mtau.get_ema("1min", n_short, n_long)
        df_ema_diff = pd.DataFrame(
            df_ema["ema_short"] - df_ema["ema_long"], columns=["diff"])
        df_ema_diff_short = df_ema_diff.tail(n_short)
        ema_abs_sum = df_ema_diff_short.abs().sum(axis=0).values[0]
        condition_3 = (ema_abs_sum > EMS_DIFF_THRESHOLD)

        msg_cond = ("買注文待 last:{0:.3f} {1}"
                    "EMS_SUM：{2:.3f}({3:.3f})"
                    "C[{4}][{5}][{6}]"
                    "macd_5:{7:.3f} sig_5:{8:.3f}")
        self.myLogger.debug(msg_cond.format(f_last, macd_status,
                                            ema_abs_sum, EMS_DIFF_THRESHOLD,
                                            condition_1,
                                            condition_2,
                                            condition_3,
                                            macd_5,
                                            sig_5))

        if condition_1 and condition_2 and condition_3:
            return True

        return False

    def is_buy_order_cancel(self, order_result):
        """ 買い注文のキャンセル判定 """
        last, _, _ = self.bitbank.get_xrp_jpy_value()
        f_last = float(last)  # 現在値

        f_order_price = self.get_order_price(order_result)
        f_last = float(last)
        f_cancel_price = float(self.get_buy_cancel_price(order_result))

        if f_last > f_cancel_price:
            msg_rebuy = ("last:{0:.3f} 買い注文価格:{1:.3f} 再注文価格:{2:.3f}"
                         .format(f_last, f_order_price, f_cancel_price))
            self.myLogger.debug(msg_rebuy)
            return True
        else:
            return False

    def get_buy_cancel_price(self, order_result):
        """ 買い注文 キャンセル 価格 取得
        買い注文価格からTHRESHOLD価格が高騰したら再度買い注文をする
        """
        f_order_price = self.get_order_price(order_result)
        return self.BUY_CANCEL_THRESHOLD + f_order_price

    def buy_order(self):
        """ 買い注文処理 """

        # 買うタイミングを待つ
        while True:
            time.sleep(self.POLLING_SEC_BUY)

            if self.is_buy_order():  # 買い注文判定
                break

        # 買い注文処理
        buy_order_info = self.get_buy_order_info()
        buy_value = self.bitbank.prvApi.order(
            buy_order_info["pair"],         # ペア
            buy_order_info["price"],        # 価格
            buy_order_info["amount"],       # 注文枚数
            buy_order_info["orderSide"],    # 注文サイド 買(buy)
            buy_order_info["orderType"]     # 注文タイプ 成行(market))
        )

        # 買い注文約定待ち
        while True:
            time.sleep(self.POLLING_SEC_BUY)

            # 買い注文結果を取得
            buy_order_result = self.bitbank.prvApi.get_order(
                buy_value["pair"],     # ペア
                buy_value["order_id"]  # 注文タイプ 成行(market)
            )
            self.order.buy_result = buy_order_result

            # 買い注文の約定判定
            if self.is_fully_filled(buy_order_result):
                self.notify_buy(self.order)
                break

        return buy_order_result  # 買い注文終了(売り注文へ)

    def is_waittig_sell_order(self, order):
        """ 売り注文（成行）できない（待ち状態）か判定する
        条件１：買い注文時の価格＋BENEFITが現在価格より小さい（まだ売れない）　または
        条件２：現在価格より損切価格（stop loss price）が小さい（まだ売れない）　または
        条件３：買い注文時の価格より前回のタイミングより増えている（まだ売れない）
        """
        last, _, _ = self.bitbank.get_xrp_jpy_value()

        # 条件１
        buy_price = self.get_order_price(order.buy_result)
        condition1 = (buy_price + self.BENEFIT < last)

        # 条件２
        stop_loss_price = self.get_stop_loss_price(order.buy_result)
        condition2 = last < stop_loss_price

        # 条件３
        condition3 = (order.pre_last > last)
        cond_msg = "売り注文判定 [{0}][{1}][{2}] pre_last:{3:.3f} last:{4:.3f}"
        self.myLogger.debug(cond_msg.format(
            condition1, condition2, condition3, order.pre_last, last))

        order.pre_last = last

        return condition1 or condition2 or condition3

    def notify_buy(self, order):
        buy_price = self.get_order_price(order.buy_result)
        buy_order_id = order.buy_result["order_id"]

        self.line.notify_line(("買い価格 {0:.3f}円 ID：{1}")
                              .format(buy_price, buy_order_id))

    def notify_sell(self, order):
        buy_price = self.get_order_price(order.buy_result)
        sell_price = self.get_order_price(order.sell_result)
        sell_order_id = order.sell_result["order_id"]
        benefit = sell_price - buy_price

        if benefit > 0:
            # 利益
            self.line.notify_line_stamp(("【利益】{0:.3f}円 売価格 {1:.3f}円 ID：{2}")
                                        .format(benefit,
                                                sell_price,
                                                sell_order_id), "1", "10")
        else:
            # 損切
            self.line.notify_line_stamp(("【損切】{0:.3f}円 売価格 {1:.3f}円 ID：{2}")
                                        .format(benefit,
                                                sell_price,
                                                sell_order_id), "1", "104")

    def sell_order(self, buy_order_result):
        """ 売り注文処理 """

        while self.is_waittig_sell_order(self.order):
            time.sleep(self.POLLING_SEC_SELL)
            break

        sell_order_info = self.get_sell_order_info()
        sell_order_value = self.bitbank.prvApi.order(
            sell_order_info["pair"],       # ペア
            sell_order_info["price"],      # 価格
            sell_order_info["amount"],     # 注文枚数
            sell_order_info["orderSide"],  # 注文サイド
            sell_order_info["orderType"]   # 注文タイプ
        )

        while True:
            time.sleep(self.POLLING_SEC_SELL)

            sell_order_result = self.bitbank.prvApi.get_order(
                sell_order_value["pair"],     # ペア
                sell_order_value["order_id"]  # 注文タイプ 指値 or 成行
            )

            if self.is_fully_filled(sell_order_result):
                self.order.sell_result = sell_order_result
                self.notify_sell(self.order)
                break


class Order:
    def __init__(self):
        self.buy_limit_ralue = 0.0    # buy指定価格
        self.sell_limit_value = 0.0   # sell指定価格

        self.pre_last = 0.0           # 前回処理時の現在価格
        self.buy_result = None        # buy約定結果情報
        self.sell_result = None       # sell約定結果情報
        self.stop_loss_price = 0.0    # 損切価格


# main
if __name__ == '__main__':
    od = Order()
    at = AutoTrader(od)
    line = Line()
    bitbank = Bitbank()
    count = 0

    try:
        for i in range(0, at.LOOP_COUNT_MAIN):
            count = count + 1
            total_assets = bitbank.get_total_assets()
            at.myLogger.info("#############################################")
            msg = "=== 処理開始[NO.{0}] 総資産:{1}円===".format(count, total_assets)
            at.myLogger.info(msg)
            line.notify_line(msg)
            buy_result = at.buy_order()        # 買い注文処理
            at.sell_order(buy_result)   # 売り注文処理

            activeOrders = bitbank.get_active_orders()["orders"]
            if activeOrders != []:
                at.myLogger.debug("デバッグ 注文一覧 {0}".format(activeOrders))
                time.sleep(60)
                at.myLogger.debug("デバッグ ６０秒後 注文一覧 {0}".format(activeOrders))
            if activeOrders != []:
                line.notify_line_stamp("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)), "1", "422")
                at.myLogger.debug("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)))
                for j, act_order in enumerate(activeOrders):
                    at.myLogger.debug(
                        "現在のオーダー一覧 :{0}:{1}".format(j, act_order))

                break  # Mainループブレイク

    except KeyboardInterrupt as ki:
        line.notify_line_stamp("自動売買が中断されました 詳細：{0}".format(ki), "1", "3")
    except BaseException as be:
        line.notify_line_stamp("システムエラーが発生しました！ 詳細：{0}".format(be), "1", "17")
        raise BaseException
    finally:
        line.notify_line_stamp("自動売買が終了！処理回数：{0}回".format(count), "2", "516")
