# -*- coding: utf-8 -*-

import bitbankAutoOrder


def test_1():
    ao = bitbankAutoOrder.AutoOrder()
    ao.notify_line("LINEメッセージテスト")
    ao.notify_line_stamp("LINEメッセージテスト", "2", "179")
