# lazyvim-proxy-lab

GitHubのアーカイブ・配布バイナリを取得できず、`git clone`・dnf・npm・pipは使える環境向けのLazyVim設定と検証用Linuxです。

**`editor/`だけで使えます。** `lab/`から`editor/`を利用しますが、設定・導入スクリプトはlabを参照しません。後でdotfilesへ移せます。

```text
lab/           proxy、SSH先Linux、入れ子Docker
editor/nvim/   ~/.config/nvim に置く設定とlazy-lock.json
editor/tools/  本体・依存・言語ツール・parserの導入とlock
editor/scripts/ 設定配置、bootstrap、doctor
examples/      Python・TSXのサンプル（型エラーを意図的に含む）
tests/         通信制限・LSP・構文解析・整形・配置の検証
```

## ローカルで職場環境を再現する

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

SSHポートは`LAB_SSH_PORT=2223 ./lab/lab up`で変更できます。同じ値を`ssh`にも渡してください。ネットワークは`10.203.77.0/24`を使います。社内VPN等と重なる場合は`lab/compose.yaml`、`lab/host/entrypoint`、`lab/devcontainer/Dockerfile`、`lab/ssh-gateway.py`のアドレスを揃えて変更してください。

## 職場の既存dev containerへ導入する

**職場では`lab/`を起動せず、`editor/`だけ使います。** proxy・社内CAは職場で既に許可された設定を継承します。TLS検証の無効化やproxyの迂回は行いません。

まずdev container内で確認します。診断は値・認証情報を出さず、設定の有無を表示します。

```bash
./editor/scripts/doctor
```

必要なもの: Linux、Git 2.19以上、C/C++コンパイラ、CMake、Ninja、Make、gettext、Python 3.11以上とvenv/pip、Node.js 22とnpm、ripgrep、fd、tar/gzip/unzip、CA証明書。sudoはOS依存の導入にだけ必要です。本体と開発ツールはユーザー領域へ置きます。

Rocky Linux 9のコンテナを管理できる場合の依存導入例:

```bash
sudo dnf install -y epel-release
sudo dnf config-manager --set-enabled crb
sudo dnf module enable -y nodejs:22
sudo dnf install -y git cmake ninja-build gcc gcc-c++ make gettext \
  python3.11 python3.11-pip nodejs npm ripgrep fd-find tar gzip unzip ca-certificates
```

`dnf config-manager`がなければ管理者に`dnf-plugins-core`の提供を依頼してください。ホスト全体のパッケージやNodeモジュール設定を変えず、開発コンテナ内で実行します。sudo不可なら必要依存を管理者に提供してもらい、その後は一般ユーザーで進めます。

```bash
export PATH="$HOME/.local/bin:$PATH"
# 必要なら職場の許可されたproxy/CAをここで設定する。
# NodeはNODE_EXTRA_CA_CERTS、pipはPIP_CERT等も設定する。
PYTHON=python3.11 ./editor/scripts/bootstrap
```

`PATH`をシェルの設定にも追加してください。各工程は独立しています。

```bash
./editor/scripts/install-config          # 既定: symlink、既存設定は日時付きバックアップ
./editor/scripts/install-config --copy   # symlinkをコピー配置へ変更できる
./editor/tools/build-neovim
./editor/tools/install-language-tools
./editor/tools/install-plugins
./editor/tools/install-parsers
```

`bootstrap --copy`でもコピー配置できます。`EDITOR_PREFIX`で本体・言語ツールの配置先（既定`~/.local`）、`EDITOR_BUILD_CACHE`でビルドキャッシュ、`BUILD_JOBS`で並列数（既定2）、`PYTHON`でvenv作成用Pythonを指定できます。配置先を変えたらその`bin`をPATHに追加してください。設定・プラグイン・parserは標準のXDGディレクトリと`NVIM_APPNAME`に対応します。

### 通信が制限されても動く理由

- Neovim 0.11.5と依存は固定Git commitから取得。CMakeの`USE_EXISTING_SRC_DIR=ON`で依存ダウンロードを停止します。LPegだけは固定Gitリポジトリ内のアーカイブをGit経由で取得し、SHA-256検証後にローカル展開します。
- LazyVim 15.13.0とプラグインは`lazy-lock.json`のcommitのみをGitで取得。通常起動で欠落プラグインを自動取得しません。
- Mason・LuaRocks・更新チェックを無効化。BlinkはLua補完エンジンを使います。
- Tree-sitterは固定した生成済み`parser.c`とscannerをC/C++コンパイラでビルド。`TSInstall`・`TSUpdate`は案内表示に置き換えます。CLIの配布バイナリは不要です。
- Python: Pyright（型・補完）とRuff（診断・整形）。TSX: vtslsとTypeScript（型・補完）、Prettier（整形）。npm lockとpip hash lockで固定します。

新しい言語やプラグインの追加は明示的な更新作業です。`:Lazy update`だけで更新するとparserとquery、Neovimの対応が崩れる場合があります。更新方法は[editorのREADME](editor/README.md)を参照してください。

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
