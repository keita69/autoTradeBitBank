#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
import time
import bitbankAutoOrder


@pytest.fixture(scope="module", autouse=True)
def before_after():
    # 前処理
    ao = bitbankAutoOrder.AutoOrder()
    yield ao
    # 後処理
    # nop


def test_1(before_after):
    before_after.notify_line("LINEメッセージテスト")
    before_after.notify_line("LINEメッセージテスト", "2", "179")
