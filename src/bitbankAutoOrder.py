# -*- coding: utf-8 -*-

import os
import sys
import traceback
import time
import datetime
import requests
import logging


import python_bitbankcc

from datetime import datetime, timedelta, timezone


class MyUtility:
    """ 処理に依存しない自分専用のユーティリティクラス """

    def get_timestamp(self):
        """ JSTのタイムスタンプを取得する """
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')


class MyLogger:
    """ ログの出力表現を集中的に管理する自分専用クラス """

    def __init__(self):
        """ コンストラクタ """
        self.mu = MyUtility()

    def debug(self, msg):
        """ DEBUG	10	動作確認などデバッグの記録 """
        print("{0}[DEBUG] {1}".format(self.mu.get_timestamp(), msg))

    def info(self, msg):
        """ INFO	20	正常動作の記録 """
        print("{0}[INFO] {1}".format(self.mu.get_timestamp(), msg))

    def warning(self, msg):
        """ WARNING	30	ログの定義名 """
        print("{0}[WARNING] {1}".format(self.mu.get_timestamp(), msg))

    def error(self, msg):
        """ ERROR	40	エラーなど重大な問題 """
        print("{0}[ERROR] {1}".format(self.mu.get_timestamp(), msg))

    def critical(self, msg):
        """ CRITICAL	50	停止など致命的な問題 """
        print("{0}[CRITICAL] {1}".format(self.mu.get_timestamp(), msg))


class AutoOrder:
    def __init__(self):
        """ コンストラクタ """
        self.BUY_ORDER_RANGE = 0.0
        self.SELL_ORDER_RANGE = 0.1
        self.POLLING_SEC = 0.1

        self.myLogger = MyLogger()
        self.api_key = os.getenv("BITBANK_API_KEY")
        self.api_secret = os.getenv("BITBANK_API_SECRET")
        self.line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")

        self.check_env()

        self.mu = MyUtility()

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
        self.myLogger.info(self.api_key)
        self.myLogger.info(self.api_secret)
        balances = self.prvApi.get_asset()
        for data in balances['assets']:
            if((data['asset'] == 'jpy') or (data['asset'] == 'xrp')):
                self.myLogger.info('●通貨：' + data['asset'])
                self.myLogger.info('保有量：' + data['onhand_amount'])

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

    def is_fully_filled(self, orderResult):
        """ 注文の約定を判定 """
        if (orderResult["status"] == "FULLY_FILLED"):
            side = orderResult["side"]
            order_id = orderResult["order_id"]
            msg = (" ---> {0} 注文約定判定 ID{1}"
                   .format(side, order_id))
            self.myLogger.info(msg)
            return True
        else:
            return False

    def get_buy_order_info(self):
        """ 買い注文のリクエスト情報を取得 """
        _, _, buy = self.get_xrp_jpy_value()
        # 買い注文アルゴリズム
        BUY_AMOUNT = "1"
        buyPrice = str(float(buy) - self.BUY_ORDER_RANGE)

        buy_order_info = {"pair": "xrp_jpy",    # ペア
                          "amount": BUY_AMOUNT,  # 注文枚数
                          "price": buyPrice,    # 注文価格
                          "orderSide": "buy",   # buy or sell
                          "orderType": "limit"  # 指値注文の場合はlimit
                          }
        return buy_order_info

    def get_sell_order_info(self):
        """ 売り注文のリクエスト情報を取得 """
        _, sell, _ = self.get_xrp_jpy_value()
        # 売り注文アルゴリズム
        SELL_AMOUNT = "1"
        sellPrice = str(float(sell) + self.SELL_ORDER_RANGE)
        sell_order_info = {"pair": "xrp_jpy",      # ペア
                           "amount": SELL_AMOUNT,  # 注文枚数
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
        """ 売り注文(損切注文)の判定 """
        last, _, _ = self.get_xrp_jpy_value()
        f_last = float(last)  # 現在値

        stop_loss_price = self.get_stop_loss_price(sell_order_result)
        if(stop_loss_price > f_last):
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

    def is_buy_order_cancel(self, last, buy_orderStatus):
        """ 買い注文のキャンセル判定 """
        f_buy_order_price = float(buy_orderStatus["price"])
        f_last = float(last)
        THRESHOLD = 0.5  # 再買い注文するための閾値

        if (f_last - f_buy_order_price > THRESHOLD):
            msg = ("現在値：{0} 買い注文価格：{1} 再注文するための閾値：{2}"
                   .format(f_last, f_buy_order_price, THRESHOLD))
            self.myLogger.debug(msg)
            return True
        else:
            return False

    def buy_order(self):
        """ 買い注文処理 """
        buy_order_info = self.get_buy_order_info()
        buyValue = self.prvApi.order(
            buy_order_info["pair"],  # ペア
            buy_order_info["price"],  # 価格
            buy_order_info["amount"],  # 注文枚数
            buy_order_info["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            buy_order_info["orderType"]  # 注文タイプ 指値 or 成行(limit or market))
        )

        while True:
            time.sleep(self.POLLING_SEC)

            last, _, _ = self.get_xrp_jpy_value()

            buy_orderResult = self.prvApi.get_order(
                buyValue["pair"],  # ペア
                buyValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )
            f_buy_order_price = float(buy_order_info["price"])
            f_buy_orderAmount = float(buy_order_info["amount"])
            f_last = float(last)
            msg = "買い注文[{0:.3f}円[now {2:.3f}円] x {1:.0f}XRP]の約定を待ち。[{3}]"
            self.myLogger.info(
                msg.format(f_buy_order_price,
                           f_buy_orderAmount,
                           f_last,
                           buy_orderResult["status"]))

            if(self.is_fully_filled(buy_orderResult)):  # 買い注文約定判定
                break

            if (self.is_buy_order_cancel(last, buy_orderResult)):
                buyCanCelOrderResult = self.prvApi.cancel_order(
                    buy_orderResult["pair"],     # ペア
                    buy_orderResult["order_id"]  # 注文ID
                )
                msg = ("買い注文をキャンセル 注文ID:{0}"
                       .format(buyCanCelOrderResult["order_id"]))
                self.myLogger.info(msg)
                buy_orderResult = buyCanCelOrderResult

            return buy_orderResult

    def sell_order(self, buy_orderResult):
        """ 売り注文処理 """
        sell_order_info = self.get_sell_order_info()
        sellValue = self.prvApi.order(
            sell_order_info["pair"],       # ペア
            sell_order_info["price"],      # 価格
            sell_order_info["amount"],     # 注文枚数
            sell_order_info["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            sell_order_info["orderType"]   # 注文タイプ 指値 or 成行(limit or market))
        )

        while True:
            time.sleep(self.POLLING_SEC)

            last, _, _ = self.get_xrp_jpy_value()

            sell_order_result = self.prvApi.get_order(
                sellValue["pair"],     # ペア
                sellValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )

            f_sell_order_price = float(sell_order_info["price"])
            f_sell_orderAmount = float(sell_order_info["amount"])
            f_last = float(last)
            stop_loss_price = self.get_stop_loss_price(sell_order_result)
            f_stop_loss_price = float(stop_loss_price)
            msg = "売り注文[{0}円[now {2}円] x {1}XRP]の約定を待ち。[損切：{3}円] "
            self.myLogger.info(
                msg.format(
                    f_sell_order_price,
                    f_sell_orderAmount,
                    f_last,
                    f_stop_loss_price))

            if (self.is_stop_loss(sell_order_result)):  # 損切する場合
                # 約定前の売り注文キャンセル
                cancel_result = self.prvApi.cancel_order(
                    sell_order_result["pair"],     # ペア
                    sell_order_result["order_id"]  # 注文ID
                )

                while True:
                    if(self.is_fully_filled(cancel_result)):
                        break

                msg = ("【損切】売り注文をキャンセル 注文ID:{0}"
                       .format(cancel_result["order_id"]))
                self.myLogger.info(msg)

                # 売り注文（成行）で損切
                amount = sell_order_result["start_amount"]
                price = sell_order_result["price"]
                sell_order_info_by_market = self.get_sell_order_info_by_barket(
                    amount, price)

                sell_by_market_result = self.prvApi.order(
                    sell_order_info_by_market["pair"],       # ペア
                    sell_order_info_by_market["price"],      # 価格
                    sell_order_info_by_market["amount"],     # 注文枚数
                    sell_order_info_by_market["orderSide"],
                    sell_order_info_by_market["orderType"]
                )

                f_sell = float(sell_by_market_result["price"])
                f_buy = float(buy_orderResult["price"])
                f_buy_amount = float(buy_orderResult["executed_amount"])
                sell_amount = sell_by_market_result["start_amount"]
                f_sell_start_amount = float(sell_amount)
                f_loss = (f_sell - f_buy) * f_buy_amount
                f_last = last
                msg = ("【損切】売り注文 (ID:{0})"
                       " [{1:.3f}円 x {2:.0f}XRP]を行いました。[現在値：{3:.3f}円] ")
                self.myLogger.info(msg.format(
                    sell_by_market_result["order_id"],
                    f_loss,
                    f_sell_start_amount,
                    f_last))

                while True:
                    if(self.is_fully_filled(sell_by_market_result)):
                        break

                msg = ("【損切】売り注文[成行] (ID:{0})"
                       " [{1:.3f}円 x {2:.0f}XRP]を行いました。[現在値：{3:.3f}円] ")
                self.notify_line_stamp(msg.format(
                    sell_by_market_result["order_id"],
                    f_sell,
                    f_sell_start_amount,
                    f_last), "1", "104")

            # 売り注文約定判定
            if (self.is_fully_filled(sell_order_result)):
                f_amount = float(sell_order_result["executed_amount"])
                f_sell = float(sell_order_result["price"])
                f_buy = float(buy_orderResult["price"])
                f_benefit = (f_sell - f_buy) * f_amount

                lineMsg = ("売り注文が約定！ 利益：{0:.3f}円 x {1:.0f}XRP "
                           .format(f_benefit, f_amount))
                self.notify_line(lineMsg)
                break

        return buy_orderResult, sellValue

    def order_buy_sell(self):
        """ 注文処理 """
        buy_orderResult = self.buy_order()
        buy_orderResult, _ = self.sell_order(buy_orderResult)

    def notify_line(self, message):
        """ LINE通知（messageのみ） """
        self.notify_line_stamp(message, "", "")

    def notify_line_stamp(self, message, stickerPackageId, stickerId):
        """ LINE通知（スタンプ付き）
        LINEスタンプの種類は下記URL参照
        https://devdocs.line.me/files/sticker_list.pdf
        """
        line_notify_api = 'https://notify-api.line.me/api/notify'

        message = "{0}  {1}".format(self.mu.get_timestamp(), message)

        if((stickerPackageId == "") or (stickerId == "")):
            payload = {'message': message}
        else:
            payload = {'message': message,
                       'stickerPackageId': stickerPackageId,
                       'stickerId': stickerId}
            headers = {'Authorization': 'Bearer ' +
                       self.line_notify_token}  # 発行したトークン
            _ = requests.post(line_notify_api, data=payload, headers=headers)


# main
if __name__ == '__main__':
    ao = AutoOrder()

    # ao.get_balances()

    try:
        loop_cnt = 10

        for i in range(0, loop_cnt):
            ao.myLogger.info("#############################################")
            ao.myLogger.info("=== 実験[NO.{0}] ===".format(i))
            ao.order_buy_sell()
            time.sleep(15)

            activeOrders = ao.get_active_orders()["orders"]
            if(len(activeOrders) != 2):
                ao.notify_line_stamp("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)), "1", "422")
                ao.myLogger.debug("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)))
                for i in range(len(activeOrders)):
                    ao.myLogger.debug(
                        "現在のオーダー一覧 :{0}".format(activeOrders[i]))
                break

        ao.notify_line_stamp("自動売買が終了！処理回数：{0}回".format(i), "2", "516")

    except KeyboardInterrupt as ki:
        ao.notify_line_stamp("自動売買が中断されました 詳細：{0}".format(ki), "1", "3")
    except BaseException as e:
        ao.notify_line_stamp("システムエラーが発生しました！ 詳細：{0}".format(e), "1", "17")
        raise e

    sys.exit()
