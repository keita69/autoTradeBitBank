from datetime import datetime

import pandas as pd
import pandas_datareader.data as web

NY_DOW_SYMBOLS = ("AAPL", "AXP", "BA", "CAT", "CSCO",
                  "CVX", "DIS", "DWDP", "GS", "HD",
                  "IBM", "INTC", "JNJ", "JPM", "KO",
                  "MCD", "MMM", "MRK", "MSFT", "NKE",
                  "PFE", "PG", "TRV", "UNH", "UTX",
                  "V", "VZ", "WBA", "WMT", "XOM")


class Rakuten():

    def get_rakuten_stocks(self):
        """
        楽天信託で取り扱っている株式情報（取扱が"○"）をpandasのDataFrame形式で返却します。

        # 楽天証券 米国株式 CSV取得コマンド
        curl -O https://www.trkd-asia.com/rakutensec/exportcsvus?name=
        &r1=on&all=on&vall=on&forwarding=na&target=0&theme=na&returns=na&head_office=na&sector=na
        # CSVデータ 抜粋
        現地コード,銘柄名(English),銘柄名,市場,業種,取扱
        AMZN,"AMAZON.COM, INC.",アマゾン・ドット・コム,NASDAQ,小売,○
        KO,THE COCA-COLA COMPANY,コカ・コーラ,NYSE,食品・飲料,○
        MCD,MCDONALD'S CORPORATION,マクドナルド,NYSE,外食・レストラン,○
        AAPL,APPLE INC.,アップル,NASDAQ,コンピュータ関連,○
        ：
        """
        CSV_FILE_PATH = "./csv/rakuten_us_stock.csv"
        df_rakuten = pd.read_csv(CSV_FILE_PATH)
        return df_rakuten


r = Rakuten()
df = r.get_rakuten_stocks()

start = datetime(2018, 5, 24)
end = datetime(2018, 6, 24)

symbols = df["現地コード"].tolist()

step = 75
df_rakuten_candle = pd.DataFrame()
for i in range(0, len(symbols), step):
    # 扱えるリストが最大75
    df_tmp = web.DataReader(symbols[i:i+step], 'robinhood', start, end)
    df_rakuten_candle = df_rakuten_candle.append(df_tmp)

print(df_rakuten_candle)
