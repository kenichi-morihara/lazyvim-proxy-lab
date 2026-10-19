# Neovim クイック早見表（LazyVim）

Leaderキーは **Space** です。Spaceを押して少し待つとwhich-keyが使える操作を表示します。`Space ?` または `:Cheatsheet` でこのページを開きます。

## 移動・編集

| キー | 操作 |
|---|---|
| `h j k l` | 左・下・上・右へ移動 |
| `i` / `a` | カーソルの前 / 後から入力 |
| `o` / `O` | 下 / 上に行を追加 |
| `Esc` | ノーマルモードに戻る |
| 挿入中のShift＋矢印 / マウスドラッグ | 文字を選択（Selectモード） |
| Selectモードの`Ctrl+C` | 選択範囲を接続元へコピー。選択は維持 |
| Selectモードで文字入力 | 選択範囲を入力した文字で置き換え |
| `u` / `Ctrl-r` | 元に戻す / やり直す |
| `yy` / `dd` / `p` | Neovim内で行をコピー / 削除 / 貼り付け |
| `v`で選択して`Space y` | 選択範囲をWindowsなど接続元のクリップボードへコピー |
| `Space Y` | 現在行を接続元のクリップボードへコピー |
| `gcc` / `gc` | 行 / 選択範囲をコメント化 |
| `Ctrl-s` | 保存 |
| `Space q q` | 終了 |

## ファイル・文字列を探す

| キー | 操作 |
|---|---|
| `Space e` | ファイル一覧 |
| `Space f f` | ファイル名で検索 |
| `Space s g` | プロジェクト内の文字列を検索（`rg`を使用） |
| `Space s r` | 最近開いたファイル |
| `Space b b` | 開いているバッファを切り替え |

## Python・TSX

| キー | 操作 |
|---|---|
| `gd` | 定義へ移動 |
| `gr` | 参照箇所を検索 |
| `K` | 型・ドキュメントを表示 |
| `Space c a` | コードアクション |
| `Space c f` | ファイルを整形 |
| `Space u h` | インライン型ヒントを表示 / 非表示 |
| `Space x x` | 診断一覧 |
| `] d` / `[ d` | 次 / 前の診断 |

Pythonの推定型ヒントはbasedpyright、TypeScript/TSXはvtslsが表示します。対応ファイルをプロジェクト内で開くとLSPが起動します。Pythonでは有効な`$VIRTUAL_ENV`を優先し、なければプロジェクトの`.venv`を使います。

## 型ヒントや補完が出ないとき

1. `:LspInfo`を実行し、Pythonでは`basedpyright`、TS/TSXでは`vtsls`が接続中か確認します。
2. `:checkhealth vim.lsp`でLSPの起動エラーを確認します。
3. `nvim .`のようにプロジェクトのルートから起動します。`pyproject.toml`、`pyrightconfig.json`、`package.json`、`tsconfig.json`をLSPが見つけやすくなります。
4. `Space u h`でバッファのインラインヒントが有効か確認します。
5. Pythonはプロジェクトvenvを有効にするか`.venv`を用意します。TS/TSXはプロジェクト依存をインストールし、TypeScriptと型定義が利用できるようにします。
6. インラインヒントがない式は、カーソルを置いて`K`で型を確認できます。

## コマンドの結果・診断を読む

| コマンド / キー | 操作 |
|---|---|
| `:EditorRun python3 --version` | コマンドを実行し、出力・エラー・終了コードを保持 |
| `Space !` | 実行するコマンドを入力 |
| `:EditorRunLast` | 直前のコマンド結果を再表示 |
| `:EditorRunStop` / 結果画面の`Ctrl-C` | 実行中コマンドを停止 |
| 結果画面の`q` | 画面を閉じる（結果は残る） |
| `:EditorReport` | 問題のファイルで現在のLSP・型ヒント状態を確認 |
| `:EditorReport!` | マスキングしたエラー本文・直近メッセージも含めて確認 |
| `:EditorReportSave` | 編集後の診断JSONをローカルに保存 |
| `:EditorReportSend my-mac` | 確認した診断JSONをTailscaleのTaildropで送信 |
| `:EditorTailscale status` / `:EditorTailscale netcheck` | 接続状態を結果バッファに表示 |

診断は問題のPython/TSXファイルから作成します。`EditorReport!`はメッセージの機密情報を完全に判別できないため、プレビューを編集して必要な項目だけを送ります。コマンド出力やプロジェクトのソースファイルは自動送信しません。対話操作には`:terminal`を使います。

## WindowsからSSH接続したときのコピー・貼り付け

- **Neovim → Windows:** `v`で選択して`Space y`。行全体なら`Space Y`。コピー先のアプリでは`Ctrl+V`で貼り付けます。
- **挿入モードからの選択:** Shift＋矢印、またはShiftを押さずにマウスドラッグします。選択中は`Ctrl+C`でWindowsへコピーできます。SelectモードではSpaceも入力文字になるため、`Space y`ではなく`Ctrl+C`を使います。
- **Windows → Neovim:** Windows側でコピーし、Neovimを`i`で挿入モードにしてWindows Terminalの`Ctrl+Shift+V`で貼り付けます。
- `y`と`p`はNeovim内のコピー・貼り付けです。接続元へのコピーは`Space y`を使います。`Ctrl+C`はNeovimでは通常コピー操作になりません。
- 画面の文字をマウスで取りたいときは、Windows Terminalで**Shiftを押しながらドラッグ**し、`Ctrl+Shift+C`または右クリックでコピーできます。

Shift＋矢印はターミナルがキー入力をNeovimへ渡す必要があります。Windows Terminal側で別操作に割り当てている場合は、その割り当てを調整するか通常のマウスドラッグを使ってください。`v`から始める従来のVisual選択も利用できます。

`Space y`はNeovim標準のOSC 52を使います。Linux側に`xclip`やWindowsの`clip.exe`を追加する必要はありません。OSC 52対応のターミナルが必要です。Windows Terminalで無効化されている場合は、プロファイル設定の`compatibility.allowOSC52`を確認してください。tmuxを使う場合は、そのOSC 52設定にも依存します。まずtmuxなしのSSH接続で確認できます。Windowsの古いコンソールや他のSSHクライアントでは、ターミナル側のコピー操作を使ってください。
