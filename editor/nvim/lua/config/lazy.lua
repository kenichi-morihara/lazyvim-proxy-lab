local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  vim.api.nvim_echo({ { "Run editor/tools/install-plugins before starting Neovim.", "ErrorMsg" } }, true, {})
  return
end
vim.opt.rtp:prepend(lazypath)
require("lazy").setup({
  spec = {
    { "folke/lazy.nvim", branch = "main", commit = "306a05526ada86a7b30af95c5cc81ffba93fef97" },
    { "LazyVim/LazyVim", commit = "28db03f958d58dfff3c647ce28fdc1cb88ac158d", import = "lazyvim.plugins",
      opts = { news = { lazyvim = false, neovim = false } } },
    { import = "lazyvim.plugins.extras.lang.python" },
    { import = "lazyvim.plugins.extras.lang.typescript" },
    { import = "lazyvim.plugins.extras.formatting.prettier" },
    { import = "plugins" },
  },
  defaults = { lazy = false, version = false },
  lockfile = vim.fn.stdpath("config") .. "/lazy-lock.json",
  install = { missing = vim.env.EDITOR_INSTALL == "1", colorscheme = { "habamax" } },
  checker = { enabled = false },
  change_detection = { notify = false },
  pkg = { enabled = false },
  rocks = { enabled = false },
  concurrency = 2,
  performance = { rtp = { disabled_plugins = { "gzip", "tarPlugin", "tohtml", "zipPlugin" } } },
})
