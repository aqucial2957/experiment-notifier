# Experiment notifier

Python で関数の実行が終了した際に Slack に通知を送ります．深層学習モデルの訓練など，時間がかかる処理の経過を知りたいときに便利です．Python ≧ 3.6 が必要です．

## 事前準備

### 依存パッケージのインストール

```sh
pip install -r requirements.txt
```

### Slack API トークンの取得

Slack app をまだ作成していない場合は，[こちらのページ](https://api.slack.com/apps)から作成・インストールし，トークンを取得します．なお，bot がメッセージを投稿できるようにするために，`chat:write` スコープを設定する必要があります．

## 使用方法

目的の関数をデコレートすることで，関数の実行が終了したら通知が飛ぶようになります．
トークンは，デフォルトでは環境変数 `SLACK_API_TOKEN` を読むようになっていますが，`token` キーワードを用いて指定することもできます．

例：
```python
from notify import notify

@notify('#general', mentions='channel')
def main():
    pass

main()  # notification will be sent to the '#general' channel
```
