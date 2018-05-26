# -*- coding: utf-8 -*-

import pytest
import python_bitbankcc
from bitbankAutoOrder import MyTechnicalAnalysisUtil
from bitbankAutoOrder import AutoOrder
from bitbankAutoOrder import EmaCross


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


def test_ems_cross():
    n_short = 9
    n_long = 26
    mtau = MyTechnicalAnalysisUtil()
    ema_cross_status = mtau.get_ema_cross_status(
        "1min", n_short, n_long)
    assert ema_cross_status == (
        EmaCross.GOLDEN_CROSS or EmaCross.DEAD_CROSS or EmaCross.OTHER_CROSS)
