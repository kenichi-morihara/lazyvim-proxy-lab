# lazyvim-proxy-lab

Gitによるソース取得とローカルビルドを使う、Python・TSX向けのLazyVim設定です。通信条件を設定して導入手順を確認できる、ローカル検証用のLinux環境も含みます。

**`editor/`だけで使えます。** `lab/`から`editor/`を利用しますが、設定・導入スクリプトはlabを参照しません。dotfilesへ移して利用することもできます。

既存のLinuxや開発用コンテナに導入する場合は、次の手順から始めてください。ローカル検証用環境の起動は不要です。

```text
lab/           proxy、SSH先Linux、入れ子Docker
editor/nvim/   ~/.config/nvim に置く設定とlazy-lock.json
editor/tools/  本体・依存・言語ツール・parserの導入とlock
editor/scripts/ 設定配置、bootstrap、doctor
examples/      Python・TSXのサンプル（型エラーを意図的に含む）
tests/         通信制限・LSP・構文解析・整形・配置の検証
```

## 既存のLinux / dev containerへ導入する

導入対象のLinux環境（SSH先または既存のdev container）に入ってから作業します。この手順では`editor/`だけを使います。Docker、`lab/lab up`、検証用proxy・CAの導入は不要です。

### 1. リポジトリを取得する

Gitの認証が必要な場合は、利用環境の認証方法を事前に設定してください。

```bash
git clone https://github.com/kenichi-morihara/lazyvim-proxy-lab.git \
  "$HOME/lazyvim-proxy-lab"
cd "$HOME/lazyvim-proxy-lab"
export PATH="$HOME/.local/bin:$PATH"
```

利用環境で提供されているproxy・CA設定を引き継ぎ、TLS証明書の検証を有効にしたまま利用します。Git、OSパッケージ、npm、pipの取得先が利用可能であることを確認してください。接続先、証明書のパス、認証情報など、環境固有の値はこのリポジトリに保存しません。

### 2. 必要なツールを確認する

```bash
./editor/scripts/doctor
```

`doctor`はインストールを行わず、ツールの有無と配置先、Neovimのバージョン、proxy・CA関連の環境変数の設定有無を表示します。初回はNeovimや言語ツールが`MISSING`になり、終了コード1を返す場合があります。これらは後続の手順で導入します。診断結果にはユーザー名やローカルパスも含まれるため、結果を共有する場合は内容を確認してください。

必要なツールは次のとおりです。

| 用途 | 必要なもの |
|---|---|
| 取得・展開 | Git 2.19以上、tar、gzip、unzip、CA証明書 |
| 本体・parserのビルド | C/C++コンパイラ、CMake、Ninja、Make、gettext |
| 言語ツール | Python 3.11以上とvenv/pip、Node.js 22とnpm |
| ファイル・全文検索 | ripgrep、fd |

Neovim本体を再利用する場合も、Tree-sitter parser用のC/C++コンパイラは必要です。以下は、OSパッケージを管理できるRocky Linux 9の開発用コンテナ向けの例です。ほかのOSや、あらかじめ用意された開発イメージでは、利用環境のパッケージ構成に合わせてください。

```bash
sudo dnf install -y dnf-plugins-core epel-release
sudo dnf config-manager --set-enabled crb
sudo dnf module enable -y nodejs:22
sudo dnf install -y git cmake ninja-build gcc gcc-c++ make gettext \
  python3.11 python3.11-pip nodejs npm ripgrep fd-find tar gzip unzip ca-certificates
```

OS依存の追加に管理者権限が必要な場合は、環境を管理する担当者に必要なツールの提供を依頼してください。以降の設定・本体・言語ツールの導入は一般ユーザーで実行します。

この例ではvenv作成に`python3.11`を使います。別のPython 3.11以上を使う場合は、`PYTHON`をその実行コマンドに変更してください。

```bash
export PYTHON=python3.11
```

### 3. Neovim本体の有無に合わせて導入する

**AとBのどちらか一方を実行します。** 通常起動時にツールをインストールする設定ではないため、ここで初回導入を完了させます。

#### A. 既存のNeovimを使う

```bash
command -v nvim
nvim --version
```

この構成で検証済みのNeovimは**0.11.5、LuaJIT付き**です。そのNeovimをPATHから実行できる場合は、本体のビルドを省き、以下を実行します。他のバージョンでの互換性は別途確認してください。

```bash
./editor/scripts/install-config
./editor/tools/install-language-tools
./editor/tools/install-plugins
./editor/tools/install-parsers
```

#### B. Neovim本体から導入する

Neovimが未導入の場合、または固定バージョンをユーザー領域に導入する場合は、一括実行の`bootstrap`を使います。Aのコマンドを追加で実行する必要はありません。

```bash
./editor/scripts/bootstrap
```

`bootstrap`は「設定配置 → Neovimビルド → 言語ツール → プラグイン → parser → 診断」の順に実行します。本体と依存のビルド並列数は既定で2です。

#### 配置先と既存設定

- 設定は既定で`~/.config/nvim`へシンボリックリンクを作成します。既存の設定は日時付きでバックアップします。リンク先として使うリポジトリは、その場所に保持してください。
- コピー配置を使う場合、Aでは最初のコマンドを`./editor/scripts/install-config --copy`に、Bでは`./editor/scripts/bootstrap --copy`に置き換えます。
- 本体・言語ツールの配置先は既定で`~/.local`です。本体を導入するBでは、この配置先にある`nvim`が置き換わる場合があります。言語ツールの導入は、同名の既存実行ファイルの上書きを拒否します。
- `EDITOR_PREFIX`で本体・言語ツールの配置先、`EDITOR_BUILD_CACHE`でビルドキャッシュ、`BUILD_JOBS`でビルド並列数を変更できます。設定・プラグイン・parserはXDGディレクトリと`NVIM_APPNAME`に対応します。

`EDITOR_PREFIX`を変更する場合は初回導入前に設定し、その`bin`をPATHの先頭へ追加してください。`bootstrap`は設定済みの`EDITOR_PREFIX`に対応します。

### 4. 導入結果を確認する

```bash
command -v nvim
nvim --version
./editor/scripts/doctor
```

既定の配置先を使う場合は、利用するシェルの設定ファイル（例: `~/.bashrc`、`~/.zshrc`）にも次の1行を一度だけ追加します。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

作業対象のプロジェクトのディレクトリへ移動し、`nvim .`で開きます。Pythonのプロジェクト依存はそのプロジェクトのvenvに、TSXの依存はそのプロジェクトのパッケージ管理方法で導入してください。言語ツールの導入用venvとは別に管理します。

動作確認用のコードと基本操作は[Python・TSXを試す](#python-tsx)を参照してください。

### 取得とバージョン固定

- Neovim 0.11.5と依存は固定Git commitから取得。CMakeの`USE_EXISTING_SRC_DIR=ON`で依存ダウンロードを停止します。LPegだけは固定Gitリポジトリ内のアーカイブをGit経由で取得し、SHA-256検証後にローカル展開します。
- LazyVim 15.13.0とプラグインは`lazy-lock.json`のcommitのみをGitで取得。通常起動で欠落プラグインを自動取得しません。
- Mason・LuaRocks・更新チェックを無効化。BlinkはLua補完エンジンを使います。
- Tree-sitterは固定した生成済み`parser.c`とscannerをC/C++コンパイラでビルド。`TSInstall`・`TSUpdate`は案内表示に置き換えます。CLIの配布バイナリは不要です。
- Python: Pyright（型・補完）とRuff（診断・整形）。TSX: vtslsとTypeScript（型・補完）、Prettier（整形）。npm lockとpip hash lockで固定します。

新しい言語やプラグインの追加は明示的な更新作業です。`:Lazy update`だけで更新するとparserとquery、Neovimの対応が崩れる場合があります。更新方法は[editorのREADME](editor/README.md)を参照してください。

## ローカル検証用環境を起動する

必要: Docker Desktop（Docker 23以降、Linuxコンテナ）、Docker Compose v2、SSHクライアント。初回はイメージ・RPM・ソースの取得とビルドに時間と数GBの空き容量が必要です。Apple Siliconで検証し、AMD64も同じDockerfileで構築可能です。

```bash
./lab/lab up
./lab/lab ssh
# 以下はSSH先
dev
# 以下はdev container内（一般ユーザー）
./editor/scripts/bootstrap
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

大きなファイルは構文ハイライトを抑えます。inlay hints・アニメーションは無効です。Pythonの解析は開いているファイル中心です。デバッガー・AI補完は含めません。SSH越しのコピーはローカルターミナルの選択・コピーを使ってください。Nerd FontはMac側のターミナルに任意で設定します。

## dotfilesへ移す

`editor/nvim/`をdotfilesのnvim設定ディレクトリへ移し、`~/.config/nvim`へリンクまたはコピーしてください。**`lazy-lock.json`も一緒に移します。** 設定ファイルにはこのrepoの絶対パスやlabのproxy設定は含まれていません。

別のマシンでも同じ手順で導入したい場合は`editor/`全体を持っていくと、本体・言語ツール・parserの固定情報とスクリプトも使えます。設定だけ移す場合、Neovim・外部ツール・プラグイン・parserの導入はdotfiles側で管理してください。Lua設定からrepo内のインストーラーを呼ぶことはありません。

## 検証

```bash
python3 -m unittest discover -s tests -p '*_test.py'
# 以下はbootstrapとサンプル依存導入を済ませたdev container内
./tests/network
./tests/check-editors
./tests/standalone  # editorだけコピーし、コピー配置・移動後の動作も確認
```

確認済みの環境・結果・制約は[検証記録](docs/validation.md)にまとめます。
