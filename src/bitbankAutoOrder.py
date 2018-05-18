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


class MyLogger:

    def getTimestamp(self):
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')

    # DEBUG	10	動作確認などデバッグの記録
    def debug(self, msg):
        print("{0}[DEBUG] {1}".format(self.getTimestamp(), msg))
    # INFO	20	正常動作の記録

    def info(self, msg):
        print("{0}[INFO] {1}".format(self.getTimestamp(), msg))
    # WARNING	30	ログの定義名

    def warning(self, msg):
        print("{0}[WARNING] {1}".format(self.getTimestamp(), msg))
    # ERROR	40	エラーなど重大な問題

    def error(self, msg):
        print("{0}[ERROR] {1}".format(self.getTimestamp(), msg))
    # CRITICAL	50	停止など致命的な問題

    def critical(self, msg):
        print("{0}[CRITICAL] {1}".format(self.getTimestamp(), msg))


class AutoOrder:
    def __init__(self):
        self.buyOrderRange = 0.0
        self.sellOrderRange = 0.1
        self.pollingSec = 0.1

        self.myLogger = MyLogger()
        self.api_key = os.getenv("BITBANK_API_KEY")
        self.api_secret = os.getenv("BITBANK_API_SECRET")
        self.line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")

        self.checkEnv()

        self.pubApi = python_bitbankcc.public()
        self.prvApi = python_bitbankcc.private(self.api_key, self.api_secret)

    def checkEnv(self):
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

    def getBalances(self):
        self.myLogger.info(self.api_key)
        self.myLogger.info(self.api_secret)
        balances = self.prvApi.get_asset()
        for data in balances['assets']:
            if((data['asset'] == 'jpy') or (data['asset'] == 'xrp')):
                self.myLogger.info('●通貨：' + data['asset'])
                self.myLogger.info('保有量：' + data['onhand_amount'])

    def getXrjpJpyValue(self):
        value = self.pubApi.get_ticker(
            'xrp_jpy'  # ペア
        )

        last = value['last']  # 現在値
        sell = value['sell']  # 現在の売り注文の最安値
        buy = value['buy']  # 現在の買い注文の最高値

        return last, sell, buy

    def getActiveOrders(self):
        activeOrders = self.prvApi.get_active_orders('xrp_jpy')
        return activeOrders

    # 注文
    def order(self):
        pass  # todo

    # 注文約定判定
    def isFULLY_FILLED(self, orderResult):
        if (orderResult["status"] == "FULLY_FILLED"):
            side = orderResult["side"]
            order_id = orderResult["order_id"]
            msg = (" ---> {0} 注文約定 ID{1}"
                   .format(side, order_id))
            self.myLogger.info(msg)
            return True
        else:
            return False

    # 買い注文情報取得
    def getBuyOrderInfo(self):
        _, _, buy = self.getXrjpJpyValue()
        # 買い注文アルゴリズム
        buyAmount = "1"
        buyPrice = str(float(buy) - self.buyOrderRange)

        buyOrderInfo = {"pair": "xrp_jpy",  # ペア
                        "amount": buyAmount,  # 注文枚数
                        "price": buyPrice,  # 注文価格
                        "orderSide": "buy",  # buy or sell
                        "orderType": "limit"  # 指値注文の場合はlimit
                        }
        return buyOrderInfo

    # 売り注文情報取得
    def getSellOrderInfo(self):
        _, sell, _ = self.getXrjpJpyValue()
        # 売り注文アルゴリズム
        sellAmount = "1"
        sellPrice = str(float(sell) + self.sellOrderRange)
        sellOrderInfo = {"pair": "xrp_jpy",  # ペア
                         "amount": sellAmount,  # 注文枚数
                         "price": sellPrice,  # 注文価格
                         "orderSide": "sell",  # buy or sell
                         "orderType": "limit"  # 指値注文の場合はlimit
                         }
        return sellOrderInfo

    # 売り注文(成行)情報取得
    def getSellOrderInfoByMarket(self, amount, price):
        sellOrderInfo = {"pair": "xrp_jpy",  # ペア
                         "amount": amount,  # 注文枚数
                         "price": price,  # 注文価格
                         "orderSide": "sell",  # buy or sell
                         "orderType": "market"  # 成行注文の場合はmarket
                         }
        return sellOrderInfo

    # 損切注文
    def isStopLoss(self, sellOrderResult):
        last, _, _ = self.getXrjpJpyValue()
        f_last = float(last)  # 現在値

        # 現在値が損切値を下回った場合、損切判定
        if(self.getStopLossPrice(sellOrderResult) > f_last):
            self.myLogger.info("【損切判定されました 現在値：{0} 損切値：{1} 】".format(
                f_last, self.getStopLossPrice(sellOrderResult)))
            return True
        return False

    # 損切価格（ポイント）取得
    def getStopLossPrice(self, sellOrderResult):
        f_sellOrderPrice = float(sellOrderResult["price"])  # 売り指定価格

        threshold = 10  # 閾値
        return f_sellOrderPrice - (self.sellOrderRange * threshold)

    # 買い注文キャンセル処理
    def isBuyOrderCancel(self, last, buyOrderStatus):
        f_buyOrderPrice = float(buyOrderStatus["price"])
        f_last = float(last)
        threshold = 0.5  # 再買い注文するための閾値
        if (f_last - f_buyOrderPrice > threshold):
            self.myLogger.debug("現在値：{0} 買い注文価格：{1} 再注文するための閾値：{2}".format(
                f_last, f_buyOrderPrice, threshold))
            return True
        else:
            return False

    # 買い注文処理
    def buyOrder(self):
        # Buy Order
        buyOrderInfo = self.getBuyOrderInfo()
        buyValue = self.prvApi.order(
            buyOrderInfo["pair"],  # ペア
            buyOrderInfo["price"],  # 価格
            buyOrderInfo["amount"],  # 注文枚数
            buyOrderInfo["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            buyOrderInfo["orderType"]  # 注文タイプ 指値 or 成行(limit or market))
        )

        while True:
            last, _, _ = self.getXrjpJpyValue()

            time.sleep(self.pollingSec)

            buyOrderResult = self.prvApi.get_order(
                buyValue["pair"],  # ペア
                buyValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )
            f_buyOrderPrice = float(buyOrderInfo["price"])
            f_buyOrderAmount = float(buyOrderInfo["amount"])
            f_last = float(last)
            msg = "買い注文[{0:.3f}円[now {2:.3f}円] x {1:.0f}XRP]の約定を待ち。[{3}]"
            self.myLogger.info(
                msg.format(f_buyOrderPrice,
                           f_buyOrderAmount,
                           f_last,
                           buyOrderResult["status"]))

            if(self.isFULLY_FILLED(buyOrderResult)):  # 買い注文約定判定
                break

            if (self.isBuyOrderCancel(last, buyOrderResult)):
                buyCanCelOrderResult = self.prvApi.cancel_order(
                    buyOrderResult["pair"],     # ペア
                    buyOrderResult["order_id"]  # 注文ID
                )
                msg = ("買い注文をキャンセル 注文ID:{0}"
                       .format(buyCanCelOrderResult["order_id"]))
                self.myLogger.info(msg)
                buyOrderResult = buyCanCelOrderResult

            return buyOrderResult

    # 売り注文
    def sellOrder(self, buyOrderResult):
        sellOrderInfo = self.getSellOrderInfo()
        sellValue = self.prvApi.order(
            sellOrderInfo["pair"],  # ペア
            sellOrderInfo["price"],  # 価格
            sellOrderInfo["amount"],  # 注文枚数
            sellOrderInfo["orderSide"],  # 注文サイド 売 or 買(buy or sell)
            sellOrderInfo["orderType"]  # 注文タイプ 指値 or 成行(limit or market))
        )

        while True:
            last, _, _ = self.getXrjpJpyValue()
            sellOrderResult = self.prvApi.get_order(
                sellValue["pair"],  # ペア
                sellValue["order_id"]  # 注文タイプ 指値 or 成行(limit or market))
            )

            f_sellOrderPrice = float(sellOrderInfo["price"])
            f_sellOrderAmount = float(sellOrderInfo["amount"])
            f_last = float(last)
            f_stopLossPrice = float(self.getStopLossPrice(sellOrderResult))
            msg = "売り注文[{0}円[now {2}円] x {1}XRP]の約定を待ち。[損切：{3}円] "
            self.myLogger.info(msg.format(
                f_sellOrderPrice, f_sellOrderAmount, f_last, f_stopLossPrice))

            time.sleep(self.pollingSec)

            if (self.isStopLoss(sellOrderResult)):

                # cancel sellOrder
                cancelValue = self.prvApi.cancel_order(
                    sellOrderResult["pair"],  # ペア
                    sellOrderResult["order_id"]  # 注文ID
                )

                self.myLogger.info(
                    "【損切】売り注文をキャンセル 注文ID:{0}".format(cancelValue["order_id"]))

                # order sellOrder by market
                amount = sellOrderResult["start_amount"]
                price = sellOrderResult["price"]
                sellOrderInfoByMarket = self.getSellOrderInfoByMarket(
                    amount, price)

                sellByMarketValue = self.prvApi.order(
                    sellOrderInfoByMarket["pair"],  # ペア
                    sellOrderInfoByMarket["price"],  # 価格
                    sellOrderInfoByMarket["amount"],  # 注文枚数
                    # 注文サイド 売 or 買(buy or sell)
                    sellOrderInfoByMarket["orderSide"],
                    # 注文タイプ 指値 or 成行(limit or market))
                    sellOrderInfoByMarket["orderType"]
                )

                f_sell = float(sellByMarketValue["price"])
                f_buy = float(buyOrderResult["price"])
                f_buyAmount = float(buyOrderResult["executed_amount"])
                f_sellStartAmount = float(sellByMarketValue["start_amount"])
                f_loss = (f_sell - f_buy) * f_buyAmount
                f_last = last
                msg = ("【損切】売り注文 (ID:{0})"
                       " [{1:.3f}円 x {2:.0f}XRP]を行いました。[現在値：{3:.3f}円] ")
                self.myLogger.info(msg.format(
                    sellByMarketValue["order_id"],
                    f_loss,
                    f_sellStartAmount,
                    f_last))

                msg = ("【損切】売り注文[成行] (ID:{0})"
                       " [{1:.3f}円 x {2:.0f}XRP]を行いました。[現在値：{3:.3f}円] ")
                self.notifyLineStamp(msg.format(
                    sellByMarketValue["order_id"],
                    f_sell,
                    f_sellStartAmount,
                    f_last), "1", "104")
                # 損切オーダーは約定を待たない。

            # 売り注文約定判定
            if (self.isFULLY_FILLED(sellOrderResult)):
                f_amount = float(sellOrderResult["executed_amount"])
                f_sell = float(sellOrderResult["price"])
                f_buy = float(buyOrderResult["price"])
                f_benefit = (f_sell - f_buy) * f_amount

                lineMsg = ("売り注文が約定！ 利益：{0:.3f}円 x {1:.0f}XRP "
                           .format(f_benefit, f_amount))
                self.notifyLine(lineMsg)
                break

        return buyOrderResult, sellValue

    # 注文処理
    def orderBuySell(self):
        buyOrderResult = self.buyOrder()
        buyOrderResult, _ = self.sellOrder(buyOrderResult)

    # LINE通知（messageのみ）
    def notifyLine(self, message):
        self.notifyLineStamp(message, "", "")

    # LINE通知（スタンプ付き）
    # https://devdocs.line.me/files/sticker_list.pdf
    def notifyLineStamp(self, message, stickerPackageId, stickerId):
        line_notify_api = 'https://notify-api.line.me/api/notify'
        JST = timezone(timedelta(hours=+9), 'JST')
        message = "{0}  {1}".format(str(datetime.now(JST)), message)

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
    # ao.getBalances()

    # 実験
    try:
        loop_cnt = 10

        for i in range(0, loop_cnt):
            ao.myLogger.info("#############################################")
            ao.myLogger.info("=== 実験[NO.{0}] ===".format(i))
            ao.orderBuySell()
            time.sleep(15)

            activeOrders = ao.getActiveOrders()["orders"]
            if(len(activeOrders) != 2):
                ao.notifyLineStamp("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)), "1", "422")
                ao.myLogger.debug("売買数が合いません！！！ 注文数：{0}".format(
                    len(activeOrders)))
                for i in range(len(activeOrders)):
                    ao.myLogger.debug(
                        "現在のオーダー一覧 :{0}".format(activeOrders[i]))
                break

        ao.notifyLineStamp("自動売買が終了！処理回数：{0}回".format(i), "2", "516")

    except KeyboardInterrupt as ki:
        ao.notifyLineStamp("自動売買が中断されました 詳細：{0}".format(ki), "1", "3")
    except BaseException as e:
        ao.notifyLineStamp("システムエラーが発生しました！ 詳細：{0}".format(e), "1", "17")
        raise e

    sys.exit()
