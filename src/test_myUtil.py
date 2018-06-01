# -*- coding: utf-8 -*-

from myUtil import Line


def test_notify_line():
    line = Line()
    http_status = line.notify_line("LINEメッセージテスト")
    assert http_status.status_code == 200

    http_status = line.notify_line_stamp("LINEスタンプテスト", "2", "179")
    assert http_status.status_code == 200
