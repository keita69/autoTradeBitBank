# -*- coding: utf-8 -*-

from myUtil import Line, MyLogger


def test_notify_line():
    line = Line()
    http_status = line.notify_line("LINEメッセージテスト")
    assert http_status.status_code == 200

    http_status = line.notify_line_stamp("LINEスタンプテスト", "2", "179")
    assert http_status.status_code == 200


def test_logger():
    ml = MyLogger("Logger")
    ml.critical("CRITICAL")
    ml.error("ERROR")
    ml.warning("WARNING")
    ml.info("INFO")
    ml.debug("DEBUG")
