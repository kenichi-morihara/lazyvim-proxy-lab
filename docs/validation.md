# 検証記録

検証日: 2026-10-17（日本時間）

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
