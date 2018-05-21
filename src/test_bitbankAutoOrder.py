# -*- coding: utf-8 -*-

import pytest
import bitbankAutoOrder


def test_notify_line():
    ao = bitbankAutoOrder.AutoOrder()
    http_status = ao.notify_line("LINEメッセージテスト")
    assert http_status.status_code == "200"

    http_status = ao.notify_line_stamp("LINEスタンプテスト", "2", "179")
    assert http_status.status_code == "200"
