#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
import time
import bitbankAutoOrder

@pytest.fixture(scope="module", autouse=True)
def before_after():
    # 前処理
    print "created!"
    ao = bitbankAutoOrder.AutoOrder()
    yield ao

    # 後処理
    print "closed!"

def test_1(before_after):
    ao.notify_line("LINEメッセージテスト")
    ao.notify_line("LINEメッセージテスト", "2", "179")
