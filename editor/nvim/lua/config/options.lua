vim.g.lazyvim_python_lsp = "basedpyright"
vim.g.lazyvim_python_ruff = "ruff"
vim.g.lazyvim_blink_main = false
vim.opt.clipboard = "" -- SSH clipboard support depends on the local terminal; use its copy action.
vim.opt.updatetime = 300
vim.opt.timeoutlen = 400
vim.opt.swapfile = false

-- External language servers do not need Neovim's optional language providers.
vim.g.loaded_python3_provider = 0
vim.g.loaded_node_provider = 0
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0
