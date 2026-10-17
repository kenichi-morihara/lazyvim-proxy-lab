# standalone editor

このディレクトリは単独で移動できます。`nvim/`が設定本体、`tools/`が導入とlock、`scripts/`が配置と診断です。lab側への依存はありません。

```bash
export PATH="${EDITOR_PREFIX:-$HOME/.local}/bin:$PATH"
./scripts/bootstrap             # 個別工程はscripts/bootstrap参照
./scripts/bootstrap --copy
```

既存のNeovim 0.11.5（LuaJIT）を使うなら`tools/build-neovim`を飛ばして、配置→言語ツール→プラグイン→parserだけ実行できます。Python 3.11以上、Node.js 22、C/C++・CMake・Ninja等のビルド依存は呼び出し元で用意してください。proxy・CA設定も呼び出し元の環境変数を継承します。

- `tools/versions.json`: Neovim、lazy.nvim、言語ツールのバージョン情報
- `tools/sources.lock.json`: NeovimのGit依存commit
- `tools/package-lock.json` / `requirements.lock`: npm依存とpipのhash lock
- `nvim/lazy-lock.json` / `tools/plugins.sources.json`: プラグインcommitとGit URL
- `tools/parsers.lock.json`: nvim-treesitterのqueryと対応するgrammarのcommit

## 更新

通常起動ではインストール・更新を行いません。設定を変更しても外部コマンドを自動導入しません。

1. テスト用のHOME/XDG環境を用意し、Neovim/LazyVim/プラグインの対応バージョンを確認する。
2. プラグインは`lazy-lock.json`と`plugins.sources.json`を揃える。LazyVim/lazy.nvim/Tree-sitterの明示commitもLua設定と合わせる。
3. Tree-sitterを更新したら、そのcommitの`parsers.lua`から対応grammarのrevisionとlocationを`parsers.lock.json`へ反映する。生成済みparser.cが含まれるrevisionを使う。
4. Neovim更新時は`versions.json`と本体Luaの要件を確認し、新版の`cmake.deps/deps.txt`に対応する`sources.lock.json`を作る。ソースの構成が変わればbuild-neovimも更新する。
5. npm更新は`versions.json`と`package.json`を変更し`npm install --package-lock-only --ignore-scripts`。Ruff更新はPyPI公式メタデータから対象wheelのSHA-256を取得し`requirements.lock`も更新する。
6. 各導入コマンドを再実行し、空の環境・制限付きproxy・Python/TSXの操作を検証してlockと一緒に保存する。

`build-neovim`はインストール済みrevisionを記録します。新バージョンをビルドする場合は`EDITOR_BUILD_CACHE`を別ディレクトリにして古いCMakeキャッシュを再利用しないでください。自分で同じ配置先のnvimを置き換えた場合は`$EDITOR_PREFIX/share/editor-neovim-revision`を削除して再ビルドします。

Neovimの任意provider（Python/Node/Ruby/Perl）は無効です。LSPは独立プロセスなのでpynvimは不要です。`checkhealth`が任意のlazygitやTree-sitter CLIを警告する場合があります。この構成のparser導入はCLIを使いません。Lua用LSPは導入しません。
