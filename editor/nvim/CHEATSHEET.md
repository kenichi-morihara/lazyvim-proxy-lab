# Neovim クイック早見表（LazyVim）

Leaderキーは **Space** です。Spaceを押して少し待つとwhich-keyが使える操作を表示します。`Space ?` または `:Cheatsheet` でこのページを開きます。

## 移動・編集

| キー | 操作 |
|---|---|
| `h j k l` | 左・下・上・右へ移動 |
| `i` / `a` | カーソルの前 / 後から入力 |
| `o` / `O` | 下 / 上に行を追加 |
| `Esc` | ノーマルモードに戻る |
| `u` / `Ctrl-r` | 元に戻す / やり直す |
| `yy` / `dd` / `p` | 行をコピー / 削除 / 貼り付け |
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
