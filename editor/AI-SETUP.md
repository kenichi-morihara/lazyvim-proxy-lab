# 社内AIとPiの接続準備

Piは通常の`make`から分離しています。`openai`（従来のOpenAI互換）と`company-chat`（Cookie認証の社内API）の2方式を利用できます。画像から確認できたのはリクエストだけです。社内APIのSSE応答・native tools対応は未確認で、以下の再現サーバーと診断で段階的に確認します。

## 職場で最初に実行するコマンド

```bash
make init-pi
```

Piの導入後、接続先ベースURL・モデル・独自userヘッダー名・user値・Bearerトークンを
対話設定します。API形式はResponses、モデルの初期値は`gpt-6.1-sol`です。
Bearerは`Bearer `を付けずに入力します（付けた場合も取り除きます）。
必要ならproxy・NO_PROXY・追加CAファイルも設定できます。通常の`make`には影響しません。
秘密値は非表示入力で、`~/.config/editor-pi/connection.json`に保存します。
`XDG_CONFIG_HOME`設定時はその配下です。ディレクトリ0700、ファイル0600で、Gitリポジトリ内への保存は拒否します。
既存設定の更新は`make configure-pi`。Enterで既存値を保持します。
proxy等の任意設定は`-`で保存値を解除できます。環境変数による指定は保存値より優先されます。

最後にローカル設定診断を行います。設定時にはAPIへ通信しません。
接続先が変わったときは、既存の`INTERNAL_AI_*`環境変数が保存設定を上書きしないよう整理してください。
設定後は新しいシェルでも`pi`が保存値を自動で読み込みます。

```bash
export PATH="${EDITOR_PREFIX:-$HOME/.local}/bin:$PATH"
make doctor-pi PROBE=1  # 実APIでツール名・nonceを確認（ツールは実行しない）
pi
```

Neovimでは`:terminal pi`で起動できます。

## 職場のCookie認証APIを使う

```bash
make setup-pi
export INTERNAL_AI_TRANSPORT=company-chat
export INTERNAL_AI_ENDPOINT='http://internal-ai.example/nomuchat/sendmessageforstream'
export INTERNAL_AI_COOKIE_FILE="$HOME/.local/state/editor-pi/session.cookies"
```

実際のURLは職場で設定します。画像のHTTP形式にも対応します。Cookieは`Cookie:`ヘッダーの値（`name=value; name=value`の1行）を手動保存します。ブラウザーのログイン操作やSSO更新は自動化しません。Bashで値を履歴や画面に出さず保存する例:

```bash
mkdir -p "$HOME/.local/state/editor-pi"
chmod 700 "$HOME/.local/state/editor-pi"
touch "$INTERNAL_AI_COOKIE_FILE"
chmod 600 "$INTERNAL_AI_COOKIE_FILE"
read -rsp 'Cookie: ' company_cookie; echo
(umask 077; printf '%s' "$company_cookie" > "$INTERNAL_AI_COOKIE_FILE")
unset company_cookie
chmod 600 "$INTERNAL_AI_COOKIE_FILE"
make doctor-pi
```

`make doctor-pi`はローカル確認のみで通信しません。実APIへの診断は明示して実行します。

```bash
make doctor-pi PROBE=1
pi
```

診断はランダムなnonceを持つ無害な`diagnostic_echo`ツールを要求し、応答のツール名・引数を確認します。ツール自体は実行しません。200や通常の文章だけでは成功と判定しません。

- `INTERNAL_AI_TOOL_MODE=native`が既定。画像の5項目に`messages`、`tools`、`tool_choice`、`stream`を追加します。実社内APIがこれらを解釈するかは診断が必要です。
- native非対応なら`INTERNAL_AI_TOOL_MODE=json`を明示します。送るJSONは画像の5項目だけとし、`message`に全履歴・ツール定義・専用JSON応答の指示を含めます。応答のJSON全体を検証してからPiへ渡すため、JSON方式では回答を途中表示しません。
- JSON方式は`{"type":"text","text":"..."}`または`{"type":"tool_calls","calls":[{"id":"id","name":"read","arguments":{"path":"file"}}]}`だけを受け付けます。未登録ツール、不正引数、通常文章、Markdownのコードブロックは実行しません。実行はPiのツール処理に任せ、結果を次のリクエストへ戻します。
- Cookieは毎リクエストで読み直します。認証切れの`COMPANY_AUTH_EXPIRED_UPDATE_COOKIE`はファイルを更新して再試行してください。リダイレクトを追わず、HTMLログインページ・不明な応答・不完全なストリームでは停止します。
- 応答はOpenAI Chat Completions SSE（`data: {...}`、`finish_reason`、`data: [DONE]`）を仮定しています。異なる場合は`COMPANY_*`エラーとし、レスポンス本文をログへ出しません。実応答に合わせたデコーダー修正が必要です。
- `INTERNAL_AI_ORIGIN` / `INTERNAL_AI_REFERER`は必要な場合だけ指定します。既定は接続先から算出します。ブラウザーのUser-AgentやCookie以外の認証ヘッダーを推測して追加しません。
- `INTERNAL_AI_MODEL`の既定表示名は`company-chat`。`INTERNAL_AI_CONTEXT_WINDOW=32768`、`INTERNAL_AI_MAX_TOKENS=4096`、`INTERNAL_AI_TIMEOUT_MS=120000`が既定です。実モデルの制限に合わせて職場で調整してください。
- proxy・CA・`NO_PROXY`は呼び出し元の設定を使用します。実社内ホストへ直接接続すべき場合だけ、そのホストを`NO_PROXY`へ追加します。外部AIへのフォールバックはしません。

社内URL・Cookieファイル・画像はコミットしないでください。Piのセッション履歴には会話やツール結果が残ります。通常ログにはCookie・ヘッダー・リクエスト本文・応答本文を出しません。トークン使用量は応答にusageがある場合だけ取得し、料金は未設定のため0表示です。

## ローカルの再現サーバー

repoルートで:

```bash
make pi-lab
```

既定は`127.0.0.1:8766`のダミーサーバーで、OpenAIを含め外部AIへ接続しません。別のシェルでCookieファイルにダミー値`lab-session=demo`を0600で保存し、上記の`company-chat`設定のURLを`http://127.0.0.1:8766/nomuchat/sendmessageforstream`に変更します。`make doctor-pi PROBE=1`が成功します。

`pi -p --no-session 'edit sample.txt'`はダミーモデルの動作確認用です。作業用ディレクトリに`before`を含む`sample.txt`を作ると、read→edit→完了応答を再現します。実際にそのファイルを書き換えるので、テスト用のディレクトリで実行してください。

OpenAIを包むモードを明示すると実APIへ接続します。キー・モデルは環境変数のみから取得し、社内CookieをOpenAIへ転送しません。

```bash
export PI_LAB_BACKEND=openai
export OPENAI_MODEL='your-model'
read -rsp 'OpenAI API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
make pi-lab
```

`OPENAI_BASE_URL`は既定`https://api.openai.com/v1`。`PI_LAB_PORT`でポートを変更できます。サーバーは`Ctrl+C`で終了します。このサーバーはローカル再現用で、職場では不要です。`editor/`は`lab/`に依存しません。

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

## 従来のOpenAI互換APIへ接続する

職場のシェル内で設定します。キーや実際の社内URLはこのrepoに書かないでください。

```bash
export INTERNAL_AI_TRANSPORT=openai
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

この場合はキーをそのヘッダーへそのまま設定します。API形式の既定はResponses（`openai-responses`）です。Chat Completionsを使う接続先だけ`INTERNAL_AI_API=openai-completions`を指定します。社内AIにはストリーム応答とツール呼び出しの互換性が必要です。URLにqueryが必要なAPI、独自の認証フロー、リクエストのラップ形式は別途対応が必要です。職場APIの接続確認はまだ行っていません。

起動時のモデルカタログ更新・バージョン確認・統計送信・補助バイナリ取得を`PI_OFFLINE=1`、`PI_SKIP_VERSION_CHECK=1`、`PI_TELEMETRY=0`で停止します。**このoffline設定でも指定した社内AIへの推論リクエストは実行できます。** `rg` / `fd`はPATH上のものを使用します。自動発見する拡張は`--no-extensions`で無効にし、company-chatでは今回の専用providerだけを明示ロードします。

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
EDITOR_PI_TEST_PREFIX="$HOME/.local" python3 tests/company_pi_test.py
EDITOR_PI_TEST_PREFIX="$HOME/.local" node --test tests/company-provider.test.mjs
```

`tests/`はrepoルートにあります。`editor/`だけ移す場合は導入・起動に不要です。

## ダミーのリクエスト例を受け取る

受信用MacでPython 3.11以上を使います。

```bash
python3 editor/scripts/ai-request-receiver
```

表示された`http://127.0.0.1:8765/capture/<ランダム値>`へ、同じマシンからダミーJSONをPOSTします。ローカルの形式確認専用として使い、外部公開はしません。

送信例（URLは実行時の値に置き換え）:

```bash
curl 'http://127.0.0.1:8765/capture/<ランダム値>' \
  -H 'Content-Type: application/json' \
  --data '{"model":"dummy-model","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

受信は形式確認のみで、AI推論や社内APIへの転送は行いません。`201`と受領IDを返します。JSONにリクエスト例・ダミーのレスポンス例をまとめて送っても構いません。

- APIキー、認証Cookie、社内URL、実プロンプト、ソースコードを送らず、ダミー値に置き換えてください。
- HTTPヘッダー・URL・アクセスログは保存しません。JSON内の認証情報によく使われるキーもマスクしますが、自由文中の秘密情報は自動判別できません。
- 受信データは既定で`~/.local/state/editor-ai-capture/`（XDG_STATE_HOMEに従う）へ保存し、ディレクトリ0700・ファイル0600にします。Git管理外に置いてください。
- ランダムURLを知る相手が送信できます。URLを共有・コミットしないでください。GETでデータを取得する機能はありません。
- 本体はlocalhostのみで待機し、1件256KiB・1起動20件まで受け付けます。`Ctrl+C`で停止します。再起動すると受信URLのランダム値が変わります。

## Responses互換API＋独自userヘッダー

標準のResponsesリクエスト・SSE応答を使う接続先には、次の設定を使用します。
画像の5項目へ変換する`company-chat`とは別の接続方式です。

```bash
make setup-pi
export INTERNAL_AI_TRANSPORT=openai
# Responsesが既定。以前の設定が残っている場合は解除。
unset INTERNAL_AI_API
export INTERNAL_AI_BASE_URL='https://ai.example/v1'
export INTERNAL_AI_MODEL='gpt-6.1-sol'
# 実サービスのヘッダー名に変更。省略時は user。
export INTERNAL_AI_USER_HEADER='user'
read -rsp 'User header value: ' INTERNAL_AI_USER; echo
export INTERNAL_AI_USER
make doctor-pi
make doctor-pi PROBE=1
pi
```

`BASE_URL`には`/responses`を含めません。Piが`/responses`へPOSTします。
同じベースURLを使う場合の切り替えは次のとおりです。接続先サービスが両方を提供するとは限りません。

| 設定 | POST先（BASE_URLが`https://ai.example/v1`の場合） |
| --- | --- |
| 未指定、または`INTERNAL_AI_API=openai-responses` | `https://ai.example/v1/responses` |
| `INTERNAL_AI_API=openai-completions` | `https://ai.example/v1/chat/completions` |

自動切り替えやフォールバックは行いません。

userヘッダーだけで認証する場合は`INTERNAL_AI_API_KEY`を設定する必要はありません。
APIキーも必要なら`INTERNAL_AI_API_KEY`を追加し、既定のBearer認証と併用できます。
独自キー用の`INTERNAL_AI_AUTH_HEADER`も引き続き使用できます。
ヘッダー値は環境変数から読み込み、一時設定ファイルに実値を保存しません。
SDKのデバッグログは無効にします。HTTPSと呼び出し元のproxy・CA設定を使います。
HTTPはlocalhostのテストに限ります。

`PROBE=1`は`diagnostic_echo`のツール名とランダムnonceを確認し、ツールを実行しません。
通常の起動ではResponsesの`input`・`tools`を送信し、`function_call`と
`function_call_output`をPiが処理します。画像の独自5項目やCookieへは変換しません。
この方式は職場APIが標準Responses形式を公開している前提です。実職場APIでの動作は未確認です。
