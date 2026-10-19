# 社内AIとPiの接続準備

Piは通常の`make`から分離しています。社内APIの呼び出し形式は未確認のため、まずOpenAI Chat Completions互換の接続設定を用意しています。独自のJSON形式が必要なら変換アダプターを追加します。

## Piだけを導入する

repoルートでも`editor/`単独でも実行できます。

```bash
make setup-pi
```

- Node.js **22.19.0以上**、npm、Git、Bash、`rg`、`fd`が必要です。OSのパッケージ管理で用意してください。本体・OSパッケージの自動更新はしません。
- 公式Piのnpmパッケージ`@earendil-works/pi-coding-agent` **1.3.0**を使用します（旧`@mariozechner/pi-coding-agent`の後継）。`tools/pi/package-lock.json`で推移依存・integrityも固定しています。
- `npm ci --ignore-scripts --omit=optional --no-audit --no-fund`で導入し、GitHub Release・archive・rawのダウンロードやnpm lifecycle hookを使いません。npmレジストリからの`.tgz`取得は必要です。
- 呼び出し元のproxy・CA・npm設定を使います。必要に応じて`HTTPS_PROXY`、`HTTP_PROXY`、`NO_PROXY`、`NODE_EXTRA_CA_CERTS=/path/to/company-ca.pem`を設定してください。TLS検証は無効にしません。
- 導入先は`~/.local/share/editor-pi`と`~/.local/bin/pi`です。`EDITOR_PREFIX`で変更できます。既存の別の`pi`実行ファイルは上書きしません。再実行で固定版を再導入できます。
- 通常の`make` / `make doctor`はPiの導入・起動・認証を行いません。Neovim・ビルドツール・TailscaleなしでPiだけを導入できます。

新しいシェルでは`~/.local/bin`（prefixを変更したらその`bin`）をPATHに追加します。

```bash
export PATH="$HOME/.local/bin:$PATH"
pi --version
```

## 社内AIへ接続する

職場のシェル内で設定します。キーや実際の社内URLはこのrepoに書かないでください。

```bash
export INTERNAL_AI_BASE_URL='https://internal-ai.example/v1'
export INTERNAL_AI_MODEL='your-internal-model'
read -rsp '社内AI API key: ' INTERNAL_AI_API_KEY; echo
export INTERNAL_AI_API_KEY
pi
```

`BASE_URL`は`/chat/completions`を含めないAPIのベースURLです。`pi`は専用ランチャーで、providerを`internal`・modelを上記環境変数に指定します。起動時にキーを引数や設定ファイルへ展開しません。`Authorization: Bearer ...`が標準です。独自ヘッダーなら、例えば次を追加します。

```bash
export INTERNAL_AI_AUTH_HEADER='api-key'
```

この場合はキーをそのヘッダーへそのまま設定します。Responses互換APIを使う場合は`INTERNAL_AI_API=openai-responses`を指定できます（既定は`openai-completions`）。社内AIにはストリーム応答とツール呼び出しの互換性が必要です。URLにqueryが必要なAPI、独自の認証フロー、リクエストのラップ形式は別途対応が必要です。職場APIの接続確認はまだ行っていません。

起動時のモデルカタログ更新・バージョン確認・統計送信・補助バイナリ取得を`PI_OFFLINE=1`、`PI_SKIP_VERSION_CHECK=1`、`PI_TELEMETRY=0`で停止します。**このoffline設定でも指定した社内AIへの推論リクエストは実行できます。** `rg` / `fd`はPATH上のものを使用します。自動発見する拡張も`--no-extensions`で無効にします。

既存の`~/.pi/agent`には書き込みません。実行ごとの設定は`~/.local/state/editor-pi/runtime-*`へ0700/0600で作り、終了時に削除します。セッション履歴は`~/.local/state/editor-pi/sessions`に保持します（XDG_STATE_HOMEに従う）。外部providerへの自動フォールバックは設定していません。ネットワークの接続制限そのものは職場のproxy・ファイアウォールに従います。

## Neovimから使う

```vim
:terminal pi
```

対話して開発する場合はこちらを使います。Neovimの通常モードに戻るキーは`Ctrl+\\` → `Ctrl+N`、再度操作するときは`i`です。短い非対話実行なら`:EditorRun pi -p --no-session "説明してほしい内容"`で、結果を保持できます。社内AI用環境変数はNeovimを起動する前に設定してください。

## 検証

導入後、ローカルのダミーChat Completionsサーバーでストリーム・ツール呼び出し・認証ヘッダーと外部通信が発生しないことを確認できます。実APIや外部AIには接続しません。

```bash
EDITOR_PI_TEST_PREFIX="$HOME/.local" python3 tests/pi_test.py
```

`tests/`はrepoルートにあります。`editor/`だけ移す場合は導入・起動に不要です。

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
