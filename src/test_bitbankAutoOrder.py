# -*- coding: utf-8 -*-

from bitbankAutoOrder import Bitbank, AutoOrder


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


def test_get_xrp_jpy_value():
    bb = Bitbank()
    last, sell, buy = bb.get_xrp_jpy_value()
    f_last = float(last)
    f_sell = float(sell)
    f_buy = float(buy)
    assert (f_last, f_sell, f_buy) > (0.0, 0.0, 0.0)


def test_get_total_assets():
    bb = Bitbank()
    total_assets = bb.get_total_assets()
    assert total_assets > 0.0


def test_get_buy_cancel_price():
    ao = AutoOrder()
    buy_order_result = {
        "order_id": 43763954,
        "pair": "xrp_jpy",
        "side": "buy",
        "type": "market",
        "start_amount": "1.000000",
        "remaining_amount": "0.000000",
        "executed_amount": "1.000000",
        "average_price": "67.1270",
        "ordered_at": 1527856987081,
        "executed_at": 1527856988273,
        "status": "FULLY_FILLED"
    }
    price = ao.get_buy_cancel_price(buy_order_result)
    assert price == 67.1270 + ao.BUY_CANCEL_THRESHOLD


def test_get_balances():
    bb = Bitbank()
    bb.get_balances()


def test_get_active_orders():
    bb = Bitbank()
    bb.get_active_orders()


def test_is_buy_order():
    ao = AutoOrder()
    ao.is_buy_order()


def test_is_buy_order_cancel():
    buy_order_result = {
        "order_id": 43763954,
        "pair": "xrp_jpy",
        "side": "buy",
        "type": "market",
        "start_amount": "1.000000",
        "remaining_amount": "0.000000",
        "executed_amount": "1.000000",
        "average_price": "99967.1270",
        "ordered_at": 1527856987081,
        "executed_at": 1527856988273,
        "status": "FULLY_FILLED"
    }
    ao = AutoOrder()
    assert ao.is_buy_order_cancel(buy_order_result) is False


def test_is_fully_filled():
    threshold_price = 100000000
    buy_order_result = {
        "order_id": 43763954,
        "pair": "xrp_jpy",
        "side": "buy",
        "type": "market",
        "start_amount": "1.000000",
        "remaining_amount": "0.000000",
        "executed_amount": "1.000000",
        "average_price": "99967.1270",
        "ordered_at": 1527856987081,
        "executed_at": 1527856988273,
        "status": "FULLY_FILLED"
    }
    ao = AutoOrder()
    assert ao.is_fully_filled(buy_order_result, threshold_price) is True

    buy_order_result["status"] = "CANCELED_UNFILLED"
    assert ao.is_fully_filled(buy_order_result, threshold_price) is True

    buy_order_result["status"] = "UNFILLED"
    assert ao.is_fully_filled(buy_order_result, threshold_price) is False


def test_get_buy_order_info():
    ao = AutoOrder()
    buy_order_info = ao.get_buy_order_info()
    assert buy_order_info["amount"] == ao.AMOUNT
    assert buy_order_info["orderSide"] == "buy"
    assert buy_order_info["orderType"] == "market"


def test_get_sell_order_info():
    ao = AutoOrder()
    sell_order_info = ao.get_sell_order_info()
    assert sell_order_info["amount"] == ao.AMOUNT
    assert sell_order_info["orderSide"] == "sell"
    assert sell_order_info["orderType"] == "limit"


def test_get_sell_order_info_by_barket():
    ao = AutoOrder()
    amount = ao.AMOUNT
    price = "10000"
    sell_order_info = ao.get_sell_order_info_by_barket(amount, price)
    assert sell_order_info["amount"] == ao.AMOUNT
    assert sell_order_info["orderSide"] == "sell"
    assert sell_order_info["orderType"] == "market"


def test_is_stop_loss():
    sell_order_result = {
        "order_id": 43763954,
        "pair": "xrp_jpy",
        "side": "sell",
        "type": "limit",
        "start_amount": "1.000000",
        "remaining_amount": "0.000000",
        "executed_amount": "1.000000",
        "average_price": "0.1270",
        "ordered_at": 1527856987081,
        "executed_at": 1527856988273,
        "status": "FULLY_FILLED"
    }
    ao = AutoOrder()
    assert ao.is_stop_loss(sell_order_result) is False
