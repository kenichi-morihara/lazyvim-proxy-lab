# 社内AIとPiの接続準備

社内APIの呼び出し形式を確認してから、Piのcustom provider設定か変換アダプターを作ります。通常の`make`ではAIツール・受信サーバーを起動しません。

## ダミーのリクエスト例を受け取る

受信用MacでPython 3.11以上を使います。

```bash
python3 editor/scripts/ai-request-receiver
```

表示された`http://127.0.0.1:8765/capture/<ランダム値>`へJSONをPOSTします。職場からアクセスするには、到達可能な接続経路が別途必要です。Cloudflare Tunnelを使う場合、通信はCloudflareを経由します。社内で許可された場合にダミーデータだけを使ってください。

送信例（URLは実行時の値に置き換え）:

```bash
curl 'https://<受信ホスト>/capture/<ランダム値>' \
  -H 'Content-Type: application/json' \
  --data '{"model":"dummy-model","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

受信は形式確認のみで、AI推論や社内APIへの転送は行いません。`201`と受領IDを返します。JSONにリクエスト例・ダミーのレスポンス例をまとめて送っても構いません。

- APIキー、認証Cookie、社内URL、実プロンプト、ソースコードを送らず、ダミー値に置き換えてください。
- HTTPヘッダー・URL・アクセスログは保存しません。JSON内の認証情報によく使われるキーもマスクしますが、自由文中の秘密情報は自動判別できません。
- 受信データは既定で`~/.local/state/editor-ai-capture/`（XDG_STATE_HOMEに従う）へ保存し、ディレクトリ0700・ファイル0600にします。Git管理外に置いてください。
- ランダムURLを知る相手が送信できます。URLを共有・コミットしないでください。GETでデータを取得する機能はありません。
- 本体はlocalhostのみで待機し、1件256KiB・1起動20件まで受け付けます。`Ctrl+C`で停止します。再起動すると受信URLのランダム値が変わります。
