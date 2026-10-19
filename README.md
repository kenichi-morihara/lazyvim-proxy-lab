# lazyvim-proxy-lab

Gitによるソース取得とローカルビルドを使う、Python・TSX向けのLazyVim設定です。通信条件を設定して導入手順を確認できる、ローカル検証用のLinux環境も含みます。

**`editor/`だけで使えます。** `lab/`から`editor/`を利用しますが、設定・導入スクリプトはlabを参照しません。dotfilesへ移して利用することもできます。

既存のLinuxや開発用コンテナに導入する場合は、次の手順から始めてください。ローカル検証用環境の起動は不要です。

```text
lab/           proxy、SSH先Linux、入れ子Docker
editor/nvim/   ~/.config/nvim に置く設定とlazy-lock.json
editor/tools/  本体・依存・言語ツール・parserの導入とlock
editor/scripts/ Makeから呼び出す導入・診断処理
examples/      Python・TSXのサンプル（型エラーを意図的に含む）
tests/         通信制限・LSP・構文解析・整形・配置の検証
```

## 既存のLinux / dev containerへ導入する

導入対象のLinux環境（SSH先または既存のdev container）で、clone後に`make`を実行します。`editor/`だけを導入するため、Dockerやローカル検証用環境の起動は不要です。

```bash
git clone https://github.com/kenichi-morihara/lazyvim-proxy-lab.git \
  "$HOME/lazyvim-proxy-lab"
cd "$HOME/lazyvim-proxy-lab"
make
```

Gitの認証が必要な場合は、利用環境の認証方法を事前に設定してください。proxy・CA設定も利用環境で提供されているものを引き継ぎ、TLS証明書の検証を有効にしたまま利用します。接続先や認証情報など、環境固有の値はこのリポジトリに保存しません。

### 通常使うコマンド

| コマンド | 動作 |
|---|---|
| `make` / `make install` | 事前確認 → 必要なら本体ビルド → 設定・言語ツール・プラグイン・parser導入 → 起動確認 |
| `make doctor` | 導入前の依存確認だけ。インストールや通信は行わない |

`make`は事前確認も実行するので、先に`make doctor`を実行する必要はありません。確認だけしたい場合に使ってください。

- PATH上の**Neovim 0.11.5（LuaJIT付き）**を自動的に再利用します。見つからない場合やバージョンが異なる場合は、固定版をユーザー領域へビルドします。
- Neovimや言語ツールが未導入でも、`doctor`ではエラーにしません。これから導入するためのOS依存だけを確認します。
- 必要な依存が不足していれば、その名前を表示して設定変更前に停止します。依存を用意して同じ`make`を再実行してください。
- 導入が途中で失敗した場合も、原因を解消して`make`を再実行できます。本体・parserのビルド情報と取得済みソースを再利用し、同じ設定の配置ではバックアップを増やしません。
- 最後に外部ツールの有無、LazyVimの起動、Python/TSXのparserとハイライトqueryをローカルで確認します。プロジェクト固有の依存はインストールしません。

### OS依存が不足していた場合

| 用途 | 必要なもの |
|---|---|
| 入口・取得・展開 | Bash、Make、Git 2.19以上、tar、gzip、unzip、CA証明書 |
| parserのビルド | C/C++コンパイラ |
| Neovim本体のビルド時のみ | CMake、Ninja、gettext（`msgfmt`） |
| 言語ツール | Python 3.11以上とvenv/pip、Node.js 22以降とnpm（検証済みは22） |
| ファイル・全文検索 | ripgrep、fd |

Python 3.11以上は、`python3`または`python3.11`などの実行名から自動検出します。Python自体がない場合も、必要なバージョンを表示して停止します。

以下は、OSパッケージを管理できるRocky Linux 9の開発用コンテナ向けの例です。ほかのOSや既存の開発イメージでは、利用環境のパッケージ構成に合わせてください。

```bash
sudo dnf install -y dnf-plugins-core epel-release
sudo dnf config-manager --set-enabled crb
sudo dnf module enable -y nodejs:22
sudo dnf install -y git cmake ninja-build gcc gcc-c++ make gettext \
  python3.11 python3.11-pip nodejs npm ripgrep fd-find tar gzip unzip ca-certificates
```

必要なOS依存を追加する権限がない場合は、環境を管理する担当者に提供を依頼してください。`make`による導入は一般ユーザーで実行し、OSパッケージの追加やリポジトリ設定の変更は行いません。

### 配置先と任意の指定

設定は既定で`~/.config/nvim`へリンクし、既存の設定は日時付きでバックアップします。リンク先として使うリポジトリはその場所に保持してください。コピー配置を使う場合は`make COPY=1`を実行します。

| 指定例 | 用途 |
|---|---|
| `make COPY=1` | 設定をシンボリックリンクではなくコピーで配置 |
| `make BUILD_JOBS=1` | 本体・依存のビルド並列数を変更（既定2） |
| `make PYTHON=python3.12` | 使用するPython 3.11以上を明示 |
| `make EDITOR_PREFIX="$HOME/.local/editor"` | 本体・言語ツールの配置先を変更（既定`~/.local`） |

`EDITOR_BUILD_CACHE`でビルドキャッシュを変更でき、設定・プラグイン・parserはXDGディレクトリと`NVIM_APPNAME`に対応します。配置先やコピー指定は、再実行時も同じ値を使ってください。

本体をビルドする場合、配置先にある`nvim`が置き換わることがあります。言語ツールの導入は同名の既存実行ファイルの上書きを拒否します。

`make`の内部では配置先の`bin`をPATHへ追加します。新しいシェルでも使えるよう、シェルの設定ファイル（例: `~/.bashrc`、`~/.zshrc`）に一度だけ次の設定を追加してください。`EDITOR_PREFIX`を指定した場合は、その配置先の`bin`に合わせます。シェルの設定ファイルは自動編集しません。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

作業対象のプロジェクトへ移動し、`nvim .`で開きます。Pythonの依存はそのプロジェクトのvenvに、TSXの依存はそのプロジェクトのパッケージ管理方法で導入してください。動作確認用コードと基本操作は[Python・TSXを試す](#python-tsx)を参照してください。

### 取得とバージョン固定

- Neovim 0.11.5と依存は固定Git commitから取得。CMakeの`USE_EXISTING_SRC_DIR=ON`で依存ダウンロードを停止します。LPegだけは固定Gitリポジトリ内のアーカイブをGit経由で取得し、SHA-256検証後にローカル展開します。
- LazyVim 15.13.0とプラグインは`lazy-lock.json`のcommitのみをGitで取得。通常起動で欠落プラグインを自動取得しません。
- Mason・LuaRocks・更新チェックを無効化。BlinkはLua補完エンジンを使います。
- Tree-sitterは固定した生成済み`parser.c`とscannerをC/C++コンパイラでビルド。`TSInstall`・`TSUpdate`は案内表示に置き換えます。CLIの配布バイナリは不要です。
- Python: basedpyright（型・補完・インライン型ヒント）とRuff（診断・整形）。TSX: vtslsとTypeScript（型・補完）、Prettier（整形）。npm lockとpip hash lockで固定します。

新しい言語やプラグインの追加は明示的な更新作業です。`:Lazy update`だけで更新するとparserとquery、Neovimの対応が崩れる場合があります。更新方法は[editorのREADME](editor/README.md)を参照してください。

## ローカル検証用環境を起動する

必要: Docker Desktop（Docker 23以降、Linuxコンテナ）、Docker Compose v2、SSHクライアント。初回はイメージ・RPM・ソースの取得とビルドに時間と数GBの空き容量が必要です。Apple Siliconで検証し、AMD64も同じDockerfileで構築可能です。

```bash
./lab/lab up
./lab/lab ssh
# 以下はSSH先
dev
# 以下はdev container内（一般ユーザー）
make
nvim examples/python/app.py
# TSXの例は後述のサンプル依存導入後に開く
```

```text
Mac → SSH (localhost:2222) → Rocky Linux 9 / Docker Engine
                                 └─ dev container / Rocky Linux 9 → nvim
                          └─ 外向きHTTP(S) → mitmproxy → 許可先
```

Linux役だけがprivilegedで、**MacのDockerソケットは共有しません**。内側DockerへのアクセスはLinux役のdeveloperユーザーに与えています。ローカルの検証用構成です。

proxyはGitHubのGit smart HTTPSだけを許可し、archive・release assets・raw・APIを拒否します。dnf・npm・pip・Dockerレジストリの必要なドメインも許可します。HTTPSパスの判定用CAはlab内でのみ信頼します。CA秘密鍵はproxyだけが保持し、Linux役には公開証明書のみを渡します。Macの信頼ストアは変更しません。repoのbind mount経由で秘密鍵が見えないよう、Linux役・dev containerでは`lab/.runtime`を空のtmpfsで隠します。

Dockerのinternalネットワークで直接外向き通信を遮断します。SSHの入口には宛先固定のTCP転送サービスを置き、Linux役を外向きネットワークへ接続せずにlocalhostから接続できるようにします。OSパッケージは署名検証、pip/npmはTLS検証を有効にしています。ベースイメージとビルド依存RPMの準備は外側Dockerで行い、Neovim本体・プラグイン・parser・言語ツールはdev container内で制限を受けて導入します。

```bash
./lab/lab stop          # 停止。内側Dockerのデータとホームは保持
./lab/lab up            # 再起動
./lab/lab down          # コンテナ・ネットワークを削除。volumeは保持
./lab/lab logs
./lab/lab reset --yes   # このlabのvolume・鍵・CA・イメージ保存ファイルを削除
```

dev containerのDockerfileを変更した場合は、SSH先で`dev --rebuild`を実行します。開発用ホームのvolumeは保持します。

SSHポートは`LAB_SSH_PORT=2223 ./lab/lab up`で変更できます。同じ値を`ssh`にも渡してください。ネットワークは`10.203.77.0/24`を使います。既存のネットワークやVPNと重なる場合は`lab/compose.yaml`、`lab/host/entrypoint`、`lab/devcontainer/Dockerfile`、`lab/ssh-gateway.py`のアドレスを揃えて変更してください。

<a id="python-tsx"></a>

## Python・TSXを試す

サンプルには型エラーを意図的に残しています。全体の型チェックが成功することを期待するサンプルではありません。

```bash
cd examples/python
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd ../tsx
npm ci --no-audit --no-fund
cd ../..
nvim examples/python/app.py
nvim examples/tsx/App.tsx
```

Pythonのルート直下の`.venv`、または起動シェルの`VIRTUAL_ENV`を利用します。複数環境を切り替える場合は目的のvenvをactivateしてnvimを起動し直してください。TSはプロジェクトのTypeScript、整形はプロジェクトのPrettier/Ruffがあれば優先します。RuffとPrettierはプロジェクトの設定ファイルを読みます。

主な操作:

| 操作 | キー |
|---|---|
| 挿入モード / 戻る | `i` / `Esc` |
| 保存 / 終了 | `:w` / `:q` |
| ファイル検索 / 全文検索 | `Space Space` / `Space /` |
| 定義 / 戻る / 説明 | `gd` / `Ctrl-o` / `K` |
| 補完候補 / 確定 | `Ctrl-Space` / `Ctrl-y` |
| 整形 / 名前変更 | `Space c f` / `Space c r` |
| 診断の表示 | `Space c d` |
| ターミナル | `Ctrl-/` |
| チートシート | `Space ?` / `:Cheatsheet` |
| 接続元クリップボードへコピー | 選択後`Space y` / 現在行`Space Y` |

コマンドの出力を残すには`:EditorRun コマンド`、読み直すには`:EditorRunLast`を使います。職場のLSP状態は`:EditorReport`で確認し、`:EditorReportSend 端末名`でTailscale経由でMacへ送信できます。準備と収集内容は[職場からの診断収集](editor/REMOTE-DIAGNOSTICS.md)を参照してください。

大きなファイルは構文ハイライトを抑えます。inlay hintsを有効にしています。Pythonの解析は開いているファイル中心です。デバッガー・AI補完は含めません。SSH越しのコピーはOSC 52を使います。Windows Terminalでは選択後`Space y`、貼り付けは挿入モードで`Ctrl+Shift+V`です。詳しくは[チートシート](editor/nvim/CHEATSHEET.md#windowsからssh接続したときのコピー貼り付け)を参照してください。Nerd Fontは接続元のターミナルに任意で設定します。

## dotfilesへ移す

`editor/nvim/`をdotfilesのnvim設定ディレクトリへ移し、`~/.config/nvim`へリンクまたはコピーしてください。**`lazy-lock.json`も一緒に移します。** 設定ファイルにはこのrepoの絶対パスやlabのproxy設定は含まれていません。

別のマシンでも同じ手順で導入したい場合は`editor/`全体を持っていくと、本体・言語ツール・parserの固定情報とスクリプトも使えます。設定だけ移す場合、Neovim・外部ツール・プラグイン・parserの導入はdotfiles側で管理してください。Lua設定からrepo内のインストーラーを呼ぶことはありません。

## 検証

```bash
python3 -m unittest discover -s tests -p '*_test.py'
nvim --headless -u NONE -l tests/support.lua
nvim --headless -u NONE -l tests/clipboard.lua
# 以下はbootstrapとサンプル依存導入を済ませたdev container内
./tests/network
./tests/check-editors
./tests/standalone  # editorだけコピーし、コピー配置・移動後の動作も確認
```

確認済みの環境・結果・制約は[検証記録](docs/validation.md)にまとめます。
