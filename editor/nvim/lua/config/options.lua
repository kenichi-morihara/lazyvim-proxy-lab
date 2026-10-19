vim.g.lazyvim_python_lsp = "basedpyright"
vim.g.lazyvim_python_ruff = "ruff"
vim.g.lazyvim_blink_main = false
-- OSC 52 sends explicit + register yanks through SSH to the local terminal.
-- Keep normal y/p internal; unnamedplus would also request clipboard reads,
-- which Windows Terminal may not answer. Paste with the terminal's paste key.
vim.g.clipboard = "osc52"
vim.opt.clipboard = ""
-- Shift+arrows and mouse dragging use Select mode; typing replaces the selection.
vim.opt.mouse = "a"
vim.opt.selectmode = { "mouse", "key" }
vim.opt.keymodel = { "startsel", "stopsel" }
-- Use a thin vertical cursor in every mode, including Normal and Select.
vim.opt.guicursor = "a:ver25"
vim.opt.updatetime = 300
vim.opt.timeoutlen = 400
vim.opt.swapfile = false

-- External language servers do not need Neovim's optional language providers.
vim.g.loaded_python3_provider = 0
vim.g.loaded_node_provider = 0
vim.g.loaded_ruby_provider = 0
vim.g.loaded_perl_provider = 0
