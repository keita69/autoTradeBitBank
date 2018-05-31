# -*- coding: utf-8 -*-

import pytest
import python_bitbankcc
from bitbankAutoOrder import MyTechnicalAnalysisUtil
from bitbankAutoOrder import AutoOrder
from bitbankAutoOrder import EmaCross
from sklearn import linear_model


def test_get_macd():
    mtau = MyTechnicalAnalysisUtil()
    df_macd = mtau.get_macd("1min")
    print("MACD test \n{0}".format(df_macd))


def test_ems_cross():
    n_short = 9
    n_long = 26
    mtau = MyTechnicalAnalysisUtil()
    ema_cross_status = mtau.get_ema_cross_status(
        "1min", n_short, n_long)

    condition_1 = (ema_cross_status == EmaCross.GOLDEN_CROSS)
    condition_2 = (ema_cross_status == EmaCross.DEAD_CROSS)
    condition_3 = (ema_cross_status == EmaCross.OTHER_CROSS)

    assert (condition_1 or condition_2 or condition_3)


def test_is_stop_loss():
    """ テスト実行時の現在価格、EMS、RSIによって結果がことなる """
    sell_order_result = {
        "success": 1,
        "data": {
            "order_id": 41765227,
            "pair": "xrp_jpy",
            "side": "sell",
            "type": "limit",
            "start_amount": "1.000000",
            "remaining_amount": "0.000000",
            "executed_amount": "1.000000",
            "price": "67.4130",
            "average_price": "67.4130",
            "ordered_at": 1527257113483,
            "executed_at": 1527257770061,
            "status": "FULLY_FILLED"
        }
    }["data"]
    ao = AutoOrder()
    ao.is_stop_loss(sell_order_result)


def test_patch_get_xrp_jpy_value(monkeypatch):
    """ [Mock Patch]
    参考：http://thinkami.hatenablog.com/entry/2017/03/07/065903
    """
    last = 50.1
    sell = 53.1
    buy = 49.2
    monkeypatch.setattr(AutoOrder, 'get_xrp_jpy_value',
                        lambda x: (last, sell, buy))
    sut = AutoOrder()
    last, sell, buy = sut.get_xrp_jpy_value()
    assert (last, sell, buy) == (50.1, 53.1, 49.2)


def test_notify_line():
    ao = AutoOrder()
    http_status = ao.notify_line("LINEメッセージテスト")
    assert http_status.status_code == 200

    http_status = ao.notify_line_stamp("LINEスタンプテスト", "2", "179")
    assert http_status.status_code == 200


def test_get_rsi():
    mtau = MyTechnicalAnalysisUtil()
    rsi = mtau.get_rsi(mtau.RSI_N, "1min")
    assert rsi >= 0
    assert rsi <= 100


def test_get_ema():
    n_short = 9
    n_long = 26
    mtau = MyTechnicalAnalysisUtil()
    ema = mtau.get_ema("1min", n_short, n_long)
    assert len(ema) == n_short


def test_get_xrp_jpy_value():
    ao = AutoOrder()
    last, sell, buy = ao.get_xrp_jpy_value()
    f_last = float(last)
    f_sell = float(sell)
    f_buy = float(buy)
    assert (f_last, f_sell, f_buy) > (0.0, 0.0, 0.0)


def test_get_total_assets():
    ao = AutoOrder()
    total_assets = ao.get_total_assets()
    assert total_assets > 0.0
