# -*- coding: utf-8 -*-

from technicalAnalysis import MacdCross, MyTechnicalAnalysisUtil
from bitbankAutoOrder import Bitbank


def test_get_macd_cross_status():
    mtau = MyTechnicalAnalysisUtil()
    macd_cross_status = mtau.get_macd_cross_status("1min")

    condition_1 = (macd_cross_status == MacdCross.GOLDEN)
    condition_2 = (macd_cross_status == MacdCross.DEAD)
    condition_3 = (macd_cross_status == MacdCross.OTHER)

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
    monkeypatch.setattr(Bitbank, 'get_xrp_jpy_value',
                        lambda x: (last, sell, buy))
    sut = Bitbank()
    last, sell, buy = sut.get_xrp_jpy_value()
    assert (last, sell, buy) == (50.1, 53.1, 49.2)


def test_get_rsi():
    mtau = MyTechnicalAnalysisUtil()
    rsi = mtau.get_rsi("1min")
    assert rsi >= 0
    assert rsi <= 100


def test_get_ema():
    n_short = 9
    n_long = 26
    mtau = MyTechnicalAnalysisUtil()
    ema = mtau.get_ema("1min", n_short, n_long)
    assert ema is not None


def test_get_candlestick_range():
    start = "20180608"
    end = "20180606"
    mtau = MyTechnicalAnalysisUtil()
    try:
        df = mtau.get_candlestick_range("1min", start, end)
    except ValueError:
        assert True

    start = "20180606"
    end = "20180608"
    mtau = MyTechnicalAnalysisUtil()
    df = mtau.get_candlestick_range("1min", start, end)
    print(df)


def test_get_rci():
    mtau = MyTechnicalAnalysisUtil()
    rci = mtau.get_rci("1min")
    print(rci)
    assert rci >= -100
    assert rci <= 100
