# -*- coding: utf-8 -*-

from technicalAnalysis import MacdCross, MyTechnicalAnalysisUtil
from bitbankAutoOrder import AutoOrder


def test_get_macd_cross_status():
    mtau = MyTechnicalAnalysisUtil()
    macd_cross_status = mtau.get_macd_cross_status("1min")

    condition_1 = (macd_cross_status == MacdCross.GOLDEN_CROSS)
    condition_2 = (macd_cross_status == MacdCross.DEAD_CROSS)
    condition_3 = (macd_cross_status == MacdCross.OTHER_CROSS)

    assert (condition_1 or condition_2 or condition_3)


def test_get_macd():
    mtau = MyTechnicalAnalysisUtil()
    df_macd = mtau.get_macd("1min")
    assert df_macd.values is not None


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
    assert ema is not None
