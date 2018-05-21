# -*- coding: utf-8 -*-

import os
import sys
import traceback
import time
import datetime
import requests
import logging
from logging import getLogger, StreamHandler, DEBUG


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
        # 参考：http://joemphilips.com/post/python_logging/
        self.logger = getLogger(__name__)
        self.handler = StreamHandler()
        self.handler.setLevel(DEBUG)
        self.logger.setLevel(DEBUG)
        self.logger.addHandler(self.handler)
        formatter = logging.Formatter(
            '%(asctime)s - %(name) - %(Levelname)s - %(message)s')
        self.handler.setFormatter(formatter)

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
    def __init__(self):
        """ コンストラクタ """
        self.LOOP_COUNT_MAIN = 10
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
        last, _, _ = self.get_xrp_jpy_value()

        side = orderResult["side"]
        order_id = orderResult["order_id"]
        pair = orderResult["pair"]
        f_price = float(orderResult["price"])
        # f_start_amount = float(orderResult["remaining_amount"])      # 注文時の数量
        f_remaining_amount = float(orderResult["remaining_amount"])  # 未約定の数量
        f_executed_amount = float(orderResult["executed_amount"])   # 約定済み数量
        f_last = float(last)

        # self.myLogger.debug("注文時の数量：{0:.0f}".format(f_start_amount))
        result = False
        if (orderResult["status"] == "FULLY_FILLED"):
            msg = ("{0} 注文 約定済：{1:.3f} 円 x {2:.0f}({3}) "
                   "[現在:{4:.3f}円] ID：{5}")
            self.myLogger.info(msg.format(side,
                                          f_price,
                                          f_executed_amount,
                                          pair,
                                          f_last,
                                          order_id))
            result = True
        else:
            msg = ("{0} 注文 約定待ち：{1:.3f}円 x {2:.0f}({3}) "
                   "[現在:{4:.3f}円] ID：{5} ")
            self.myLogger.info(msg.format(side,
                                          f_price,
                                          f_remaining_amount,
                                          pair,
                                          f_last,
                                          order_id))
        return result

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
            time.sleep(self.POLLING_SEC_BUY)

            last, _, _ = self.get_xrp_jpy_value()

            # 買い注文結果を取得
            buy_orderResult = self.prvApi.get_order(
                buyValue["pair"],     # ペア
                buyValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )

            # 買い注文の約定判定
            if(self.is_fully_filled(buy_orderResult)):
                break

            if (self.is_buy_order_cancel(last, buy_orderResult)):
                buyCanCelOrderResult = self.prvApi.cancel_order(
                    buy_orderResult["pair"],     # ペア
                    buy_orderResult["order_id"]  # 注文ID
                )

                while True:
                    time.sleep(self.POLLING_SEC_BUY)
                    if(self.is_fully_filled(buyCanCelOrderResult)):
                        msg = ("買い注文をキャンセル 注文ID:{0}"
                               .format(buy_orderResult["order_id"]))
                        self.myLogger.info(msg)
                        break

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
            time.sleep(self.POLLING_SEC_SELL)

            last, _, _ = self.get_xrp_jpy_value()

            sell_order_result = self.prvApi.get_order(
                sellValue["pair"],     # ペア
                sellValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )

            # 売り注文約定判定
            if (self.is_fully_filled(sell_order_result)):
                f_amount = float(sell_order_result["executed_amount"])
                f_sell = float(sell_order_result["price"])
                f_buy = float(buy_orderResult["price"])
                f_benefit = (f_sell - f_buy) * f_amount

                line_msg = ("売り注文が約定！ 利益：{0:.3f}円 x {1:.0f}XRP "
                            .format(f_benefit, f_amount))
                self.notify_line(line_msg)
                self.myLogger.debug(line_msg)
                break

            if (self.is_stop_loss(sell_order_result)):  # 損切する場合
                # 約定前の売り注文キャンセル
                cancel_result = self.prvApi.cancel_order(
                    sell_order_result["pair"],     # ペア
                    sell_order_result["order_id"]  # 注文ID
                )

                while True:
                    time.sleep(self.POLLING_SEC_SELL)
                    if(self.is_fully_filled(cancel_result)):
                        msg = ("売り注文をキャンセル 注文ID:{0}"
                               .format(sell_order_result["order_id"]))
                        self.myLogger.info(msg)
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

                while True:
                    time.sleep(self.POLLING_SEC_SELL)
                    if(self.is_fully_filled(sell_by_market_result)):
                        msg = ("【損切】売り注文 (ID:{0})"
                               " [{1:.3f}円 x {2:.0f}XRP]を行いました。"
                               "[現在値：{3:.3f}円] ")
                        self.myLogger.info(msg.format(
                            sell_by_market_result["order_id"],
                            f_loss,
                            f_sell_start_amount,
                            f_last))
                        break

                line_msg = ("【損切】売り注文[成行] (ID:{0})"
                            " [{1:.3f}円 x {2:.0f}XRP]を行いました。[現在値：{3:.3f}円] ")
                self.notify_line_stamp(line_msg.format(
                    sell_by_market_result["order_id"],
                    f_sell,
                    f_sell_start_amount,
                    f_last), "1", "104")

        return buy_orderResult, sellValue

    def order_buy_sell(self):
        """ 注文処理メイン（買い注文 → 売り注文） """
        buy_orderResult = self.buy_order()
        buy_orderResult, _ = self.sell_order(buy_orderResult)

    def notify_line(self, message):
        """ LINE通知（messageのみ） """
        return self.notify_line_stamp(message, "", "")

    def notify_line_stamp(self, message, stickerPackageId, stickerId):
        """ LINE通知（スタンプ付き）
        LINEスタンプの種類は下記URL参照
        https://devdocs.line.me/files/sticker_list.pdf
        """
        line_notify_api = 'https://notify-api.line.me/api/notify'

        message = "{0}  {1}".format(self.mu.get_timestamp(), message)

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
