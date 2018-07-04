[![Build Status](https://travis-ci.org/keita69/autoTradeBitBank.svg?branch=master)](https://travis-ci.org/keita69/autoTradeBitBank)　[![codecov](https://codecov.io/gh/keita69/autoTradeBitBank/branch/master/graph/badge.svg)](https://codecov.io/gh/keita69/autoTradeBitBank)

# autoTradeBitBank
## 命名規約（PEP8）
PEP 8は、言語の異なる要素ごとに他と異なるスタイルを推奨しています。これは、コード
を読むときに、名前がどの種類なのかを区別しやすくします。
*  関数、変数、属性は、lowercase_underscoreのように小文字で下線を挟む。
*  プロテクテッド属性は、_leading_underscoreのように下線を先頭につける。
*  プライベート属性は、__double_underscoreのように下線を2つ先頭につける。
*  クラスと例外は、CapitalizedWordのように先頭を大文字にする。
*  モジュールレベルの定数は、ALL_CAPSのようにすべて大文字で下線を挟む。
*  クラスのインスタンスメソッドは、（オブジェクトを参照する）第1仮引数の名前にselfを使う。
*  クラスメソッドは、（クラスを参照する）第1仮引数の名前にclsを使う。

## venv(バーチャル環境設定)
### Anaconda Prompt でvenv作成
```
conda create -n env_zipline python=3.5
```

### git-bash Prompt
```
# venvを有効化
source activate env_zipline
```

```
# venvを無効化
source deactivate
```


## CSV取得
### 楽天証券 米国株式
* curl -O https://www.trkd-asia.com/rakutensec/exportcsvus?name=&r1=on&all=on&vall=on&forwarding=na&target=0&theme=na&returns=na&head_office=na&sector=na
