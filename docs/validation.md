# 検証記録

初期導入の検証日: 2026-10-17（日本時間）

## SSHクリップボードの追加検証（2026-10-19）

- Neovim 0.11.5で`nvim --headless -u NONE -l tests/clipboard.lua`を実行してPASS。
- 実際のキー割り当てと組み込みOSC 52 providerを使い、選択範囲、行全体、日本語と改行の送信内容を確認。送信部分を捕捉し、ホストのクリップボードは変更していない。
- 通常の`y`・`p`および外部コピー直後の`p`がローカルのレジスタを使い、OSC 52の読み取り要求を発行しないことを確認。
- Windows Terminal実機でのクリップボード受信は未確認。利用端末のOSC 52対応・許可設定、tmux等の中継設定に依存する。ターミナル側の選択コピー手順もチートシートに記載。

## Make入口の追加検証（2026-10-19）

- `make` / `make install`で事前確認から導入・起動確認まで進む入口を追加。
- `make doctor`はインストールと通信を行わず、Neovimや言語ツールの未導入をエラー扱いにしない。
- unit testは計17件PASS。実際のMakefileを一時HOME・代替ツールで実行し、本体の再利用／ビルド、依存不足時の無変更、Pythonの自動選択、失敗後の再実行、コピー配置、起動確認の失敗伝播を確認。
- Rocky Linux 9 / ARM64の既存ベースイメージで、ネットワーク無効・ルートファイルシステムとソースの読み取り専用状態で`make doctor`がPASS。既存のlabサービスは変更しない一時コンテナを使用。
- 別の一時XDG環境へ既存のプラグイン・parserをコピーし、実際のNeovim 0.11.5で新しい起動確認をPASS。LazyVim、固定プラグイン、Python/TSX parserとquery、BlinkのLua実装を確認。言語ツールの実行ファイル有無の確認には代替ファイルを使用。
- この追加検証では、本体ビルドや言語ツールのネットワーク取得をやり直していない。各導入処理は従来のものを使用し、新しい入口による選択と実行順を隔離テストで確認している。

以下は初期導入時の検証結果。

## 環境

- Mac / Docker Desktop、Linux ARM64（aarch64）
- Rocky Linux 9イメージをdigest固定。dev containerの`os-release`は9.3。RPMはRocky 9・EPEL 9のリポジトリから導入
- SSH先Linux役の専用Docker Engine 28.5.1の内部でdev containerを起動
- Neovim 0.11.5、LuaJIT付き。LazyVim 15.13.0を含む29件のプラグインをcommit固定
- 外側Dockerのソケットは共有せず、SSH先Linux役だけprivileged

## 確認結果

| 項目 | 結果 |
|---|---|
| 空の開発用ホームからNeovim・依存をGit経由でビルド | PASS |
| 制限付きproxyでプラグインとparserをGit経由で導入 | PASS |
| npm lock・pip hash lockに従った言語ツール導入 | PASS |
| Git smart HTTPS、npm、pip、dnfの利用 | PASS |
| GitHub archive・Release・codeload・rawにproxy由来の403を返す | PASS |
| proxyを使わない直接外向き通信を拒否 | PASS |
| 一般ユーザーでSSH → 内側dev container → nvim | PASS |
| 実際のSSHターミナルでLazyVimを開く | PASS |
| Python: Pyright接続、型診断、定義、補完、venv内の依存解決 | PASS |
| TSX: vtsls接続、型診断、定義、補完、React型定義の解決 | PASS |
| Python・TSXのTree-sitter構文解析とハイライトquery | PASS |
| プロジェクト内Ruff・Prettierの優先使用と整形 | PASS |
| BlinkのLua実装、Mason無効、起動時エラーなし | PASS |
| proxyサービス停止中にPython・TSXの編集テスト | PASS |
| editorだけを一時ディレクトリへコピーしbootstrap --copy | PASS |
| 配置後にinstallerのディレクトリを移動しても編集可能 | PASS |
| bootstrapの再実行 | PASS |
| lab停止・再起動後のSSH接続と設定保持 | PASS |
| dev --rebuild後もホームを保持し編集テスト成功 | PASS |
| Linux役・dev containerから実行時CA秘密鍵・SSH秘密鍵を隠す | PASS |
| 配置・バックアップ・中断したGit取得の復旧・proxy判定のunit test | 5 tests PASS |

`tests/check-editors`は言語サーバーへの実際のLSPリクエストと、バッファに対する整形を検証します。Python・TSXそれぞれ17項目を確認し、サンプルファイル自体は書き換えません。型エラーはサンプル内の意図的な代入エラーです。

`tests/standalone`は既に導入したユーザー領域の本体・ツールとGitキャッシュを再利用し、editorの移動とコピー配置後の動作を確認します。最初の本体・ツール導入は空のホームから別途確認しています。

## 再実行

Macで:

```bash
python3 -m unittest discover -s tests -p '*_test.py'
./lab/lab up
./lab/lab ssh
```

SSH先で`dev`に入り、bootstrapとサンプル依存導入を済ませてから:

```bash
./tests/network
./tests/check-editors
./tests/standalone
```

オフライン編集の確認は、Macで`docker compose -f lab/compose.yaml stop proxy`、開発用コンテナで`./tests/check-editors`、確認後にMacで`docker compose -f lab/compose.yaml start proxy`です。

## 検証範囲

- 職場のOS・CPU・権限・proxy規則そのものは未確認です。職場では`editor/scripts/doctor`で確認してください。
- AMD64向けの分岐やアーキテクチャ固定の配布バイナリは使っていませんが、AMD64での実行検証はしていません。
- OSリポジトリは固定snapshotではありません。ベースイメージと開発ツールのlockは固定していますが、将来のRPM取得結果までは同一性を保証しません。
- このlabは通常ユーザーによる開発・導入の再現用です。privileged Linux役の管理者に対する隔離を目的とする構成ではありません。
