# dev containerから診断を集める

Windowsは通常のSSH端末として使います。Tailscaleを入れるのはdev containerと収集先のMacです。Neovim内で診断をプレビューし、必要なときだけTaildropで送ります。`editor/`だけでも利用できます。

## Macの準備（初回だけ）

1. [Tailscaleアプリ](https://tailscale.com/docs/install/mac)を入れ、利用を認められたtailnetへログインします。
2. tailnetの管理画面のGeneral設定で **Send Files** を有効にします。
3. Macとdev containerは同じユーザーとしてログインします。Taildropは他ユーザーの端末やタグ付き端末には送れません。
4. Tailscaleに表示されるMacの端末名を控えます。以下の`my-mac`はその名前に置き換えます。

Macのアプリ版では受信ファイルが`~/Downloads`に入ります。MacにSSHサーバーやHTTP受信サーバーを立てる必要はありません。CLI版のMac daemonはTaildropの対応が異なるため、ここではアプリ版を使います。[Taildrop公式手順](https://tailscale.com/docs/features/taildrop?tab=macos)

Macで初めて使う際に共有拡張機能の有効化を求められたら、システム設定の「一般 → ログイン項目と機能拡張 → 共有」でTailscaleを有効にします。

## dev containerの準備（初回だけ）

`tailscale`と`tailscaled`がPATHにあればOSへの追加は不要です。Rocky Linux 9で未導入の場合は、OSパッケージを追加できる環境で次を実行します。

```bash
sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/rhel/9/tailscale.repo
sudo dnf install tailscale
```

Tailscaleは任意のOSパッケージとして扱い、`make`やNeovim起動時にはインストールしません。上の操作にはパッケージ管理権限が必要です。[公式RPM導入手順](https://pkgs.tailscale.com/stable/)

リポジトリのルートから、一般ユーザーで専用daemonを起動します。

```bash
./editor/scripts/tailscale-local start
./editor/scripts/tailscale-local up --accept-dns=false
```

表示された認証URLをWindowsのブラウザーで開き、Macと同じユーザーでログインします。WindowsにTailscaleを入れる必要はありません。`editor/`だけをコピーした場合は`./scripts/tailscale-local`を使います。

このdaemonはuserspaceモードなので`sudo`、`/dev/net/tun`、追加のコンテナ権限を使いません。DNSを変更する設定やSSHサーバーの有効化も行いません。[userspaceモード](https://tailscale.com/docs/concepts/userspace-networking)

状態・認証情報・ログは`$XDG_STATE_HOME/editor-tailscale`（既定`~/.local/state/editor-tailscale`）へ保存します。ディレクトリは0700、新しいファイルは0600です。`start`は起動済みdaemonを再利用します。コンテナを再作成しても認証を維持したい場合は、このディレクトリを既存の開発用ホームとともに保持してください。

## Neovimから接続を確かめる

```vim
:EditorTailscale status
:EditorTailscale netcheck
```

どちらも結果が専用バッファに残ります。認証もNeovim内で行うなら、daemon起動後に`:EditorTailscale up --accept-dns=false`を実行できます。認証URLが結果バッファに表示されます。2分でタイムアウトした場合は再実行します。

`EditorTailscale`と診断送信は専用socketがあれば自動使用し、なければ通常のシステムdaemonを使います。配置を変える場合は、Neovim起動前に`EDITOR_TAILSCALE_STATE_DIR`または`EDITOR_TAILSCALE_SOCKET`を絶対パスで指定します。スクリプトとNeovimは同じ変数を参照します。

proxy・CA設定は既存の環境設定を引き継ぎます。先に確認したHTTPSの200だけでは、Tailscaleのログイン・中継通信まで成功するとは限りません。`netcheck`と実際の送信結果で確認してください。ローカル再現環境`lab/`の既定proxyはTailscaleのドメインを許可していません。この追加機能の実接続は利用先dev containerで確認します。

## 診断を確認して送る

**問題が起きているPython/TSXファイルを開いた状態**で実行します。

```vim
:EditorReport
```

収集するのはNeovim/OSのバージョン、固定プラグインcommit、外部ツールの有無、現在のファイル種別、接続中LSP、補完・hover・定義・型ヒントの対応、型ヒント設定、venvとプロジェクト設定の検出、診断コードと件数です。接続中LSPのserver versionはサーバーから提供されている場合に記録します。パス・ファイル名・ソース本文・環境変数の値・生のLSPログは収集しません。

エラーメッセージ本文や直近のNeovimメッセージも必要な場合は、明示的に次を使います。

```vim
:EditorReport!
```

この場合は既知の認証情報、URL、メール、IPv4、絶対パスをマスキングします。メッセージにはシンボル名やコード断片などが含まれることがあるため、JSONのプレビューを確認し、不要な項目を編集・削除できます。自動マスキングですべての機密情報を判別できるわけではありません。診断は最大100件、Neovimメッセージは直近30行です。

```vim
:EditorReportSave
:EditorReportSend my-mac
```

`Save`はローカル保存だけです。`Send`は**編集後のプレビューそのもの**を保存して送信し、勝手に再収集しません。送信結果もバッファに残ります。毎回の端末名入力を省く場合は、起動前に`EDITOR_REPORT_TARGET=my-mac`を環境変数へ設定できます。送信コマンドは省略して`:EditorReportSend`を使います。

保存先はNeovimのstateディレクトリ内の`editor-reports/`、ファイル名は`editor-report-日時-識別子.json`です。ディレクトリは0700、ファイルは0600です。これらの診断結果やTailscale状態は公開repoへ保存しません。Macで受信したファイルをこのチャットで確認すれば、職場の実際の状態に基づいて調査できます。

切断するときは`./editor/scripts/tailscale-local down`を使います。Tailscale認証を解除する場合は同じ入口で`logout`を実行します。

## コマンドの結果をNeovim内で読む

```vim
:EditorRun python3 --version
:EditorRun curl -I --connect-timeout 10 https://controlplane.tailscale.com/derpmap/default
:EditorRunLast
:EditorRunStop
```

`EditorRun`は現在の作業ディレクトリとシェルでコマンドを実行します。標準出力・標準エラー・終了コードを表示し、`q`で画面を閉じても`EditorRunLast`で読み直せます。Spaceに続けて`!`でもコマンド入力を開けます。実行中のバッファで`Ctrl-C`、または`EditorRunStop`で停止できます。通常は2分で停止し、出力は1 MiBまで保持します。

標準入力が必要なコマンドや`sudo`などの対話操作には`:terminal`を使います。`EditorRun`のコマンド文字列・出力はローカルに保持し、診断ファイルへ自動追加・送信しません。`:LspInfo`などのNeovimコマンドは、そのままNeovim内で実行します。
