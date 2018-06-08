import os
import logging
from logging import getLogger, StreamHandler, DEBUG
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timezone, timedelta

import requests


class MyUtil:
    """ 処理に依存しない自分専用のユーティリティクラス """

    def get_timestamp(self):
        """ JSTのタイムスタンプを取得する """
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S')


class MyLogger:
    """ ログの出力表現を集中的に管理する自分専用クラス """

    def __init__(self, name):
        """ コンストラクタ """
        # 参考：http://joemphilips.com/post/python_logging/
        self.logger = getLogger(name)
        self.logger.setLevel(DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s %(name) %(levelname)s %(message)s")
        sh = StreamHandler()
        sh.setLevel(DEBUG)
        sh.setFormatter(formatter)
        self.logger.addHandler(sh)

    def debug(self, msg):
        """ DEBUG	10	動作確認などデバッグの記録 """
        self.logger.debug(msg)

    def info(self, msg):
        """ INFO	20	正常動作の記録 """
        self.logger.info(msg)

    def warning(self, msg):
        """ WARNING	30	ログの定義名 """
        self.logger.warning(msg)

    def error(self, msg):
        """ ERROR	40	エラーなど重大な問題 """
        self.logger.error(msg)

    def exception(self, msg, ex):
        """ Exception   40	例外など重大な問題 """
        self.logger.exception(msg, ex)

    def critical(self, msg):
        """ CRITICAL	50	停止など致命的な問題 """
        self.logger.critical(msg)


class Line:
    """ Line機能をまとめたクラス """

    def __init__(self):
        self.line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")

    def check_env(self):
        """ 環境変数のチェック """
        if self.line_notify_token is None:
            emsg = '''
            Please set LINE_NOTIFY_TOKEN in Environment !!
            ex) exoprt LINE_NOTIFY_TOKEN=XXXXXXXXXXXXXXXXXX
            '''
            raise EnvironmentError(emsg)

    def notify_line(self, message):
        """ LINE通知（messageのみ） """
        return self.notify_line_stamp(message, "", "")

    def notify_line_stamp(self, message, stickerPackageId, stickerId):
        """ LINE通知（スタンプ付き）
        LINEスタンプの種類は下記URL参照
        https://devdocs.line.me/files/sticker_list.pdf
        """
        line_notify_api = 'https://notify-api.line.me/api/notify'

        if (stickerPackageId == "") or (stickerId == ""):
            payload = {'message': message}
        else:
            payload = {'message': message,
                       'stickerPackageId': stickerPackageId,
                       'stickerId': stickerId}

        headers = {'Authorization': 'Bearer ' +
                   self.line_notify_token}  # 発行したトークン
        return requests.post(line_notify_api, data=payload, headers=headers)
