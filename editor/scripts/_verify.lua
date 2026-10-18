-- Local startup verification; no project installation or network access.
local function verify()
  assert(vim.v.errmsg == "", "Neovim startup error: " .. vim.v.errmsg)
  assert(_G.LazyVim, "LazyVim did not load")
  local config = require("lazy.core.config")
  local lock = vim.json.decode(table.concat(vim.fn.readfile(vim.fn.stdpath("config") .. "/lazy-lock.json"), "\n"))
  for name in pairs(lock) do
    local plugin = config.plugins[name]
    assert(plugin and vim.fn.isdirectory(plugin.dir) == 1, "Missing plugin: " .. name)
  end
  require("lazy").load({ plugins = { "nvim-treesitter", "blink.cmp", "nvim-lspconfig", "conform.nvim" } })
  for _, language in ipairs({ "python", "tsx" }) do
    assert(vim.treesitter.language.add(language), "Missing parser: " .. language)
    assert(vim.treesitter.query.get(language, "highlights"), "Missing highlight query: " .. language)
  end
  assert(require("blink.cmp.config").fuzzy.implementation == "lua", "Blink must use Lua implementation")
  assert(not config.plugins["mason.nvim"], "Mason must remain disabled")
  vim.wait(100) -- Allow scheduled startup configuration to run.
  assert(vim.v.errmsg == "", "Configuration error: " .. vim.v.errmsg)
  io.stdout:write("PASS LazyVim startup, locked plugins, Python/TSX parsers and highlight queries\n")
  io.stdout:flush()
end

local function run()
  local ok, err = xpcall(verify, debug.traceback)
  if not ok then
    io.stderr:write(tostring(err) .. "\n")
    vim.cmd("cquit 1")
  else
    vim.cmd("qa!")
  end
end

if vim.v.vim_did_enter == 0 then
  vim.api.nvim_create_autocmd("VimEnter", { once = true, callback = function() vim.schedule(run) end })
else
  run()
end
