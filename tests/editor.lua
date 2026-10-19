-- Run from a shell with the desired config and sample file; writes no project files.
local function check(ok, message)
  if not ok then error(message) end
  io.stdout:write("PASS " .. message .. "\n"); io.stdout:flush()
end
local function main()
  vim.cmd("doautocmd User VeryLazy")
  require("lazy").load({ plugins = { "nvim-lspconfig", "nvim-treesitter", "blink.cmp", "conform.nvim" } })
  vim.api.nvim_exec_autocmds("BufReadPost", { buffer = 0 })
  local name = vim.bo.filetype == "python" and "basedpyright" or "vtsls"
  check(vim.wait(60000, function() return #vim.lsp.get_clients({ bufnr = 0, name = name }) > 0 end, 100), name .. " attached")
  local client = vim.lsp.get_clients({ bufnr = 0, name = name })[1]
  check(vim.wait(60000, function() return #vim.diagnostic.get(0, { severity = vim.diagnostic.severity.ERROR }) > 0 end, 100), "intentional type error diagnosed")
  for _, d in ipairs(vim.diagnostic.get(0)) do
    check(not tostring(d.message):find("could not be resolved"), "project dependency resolved: " .. tostring(d.code))
    check(not tostring(d.message):find("Cannot find module"), "module resolved: " .. tostring(d.code))
  end
  local line, col
  for i, text in ipairs(vim.api.nvim_buf_get_lines(0, 0, -1, false)) do
    local pos = text:find("greet%(")
    if pos then line, col = i - 1, pos - 1; break end
  end
  check(line ~= nil, "sample reference found")
  local params = { textDocument = { uri = vim.uri_from_bufnr(0) }, position = { line = line, character = col + 2 } }
  local definition = client:request_sync("textDocument/definition", params, 30000, 0)
  check(definition and definition.result and #definition.result > 0, "definition returned")
  local location = definition.result[1]
  check((location.uri or location.targetUri):find("helpers"), "definition points to helpers")
  local completion = client:request_sync("textDocument/completion", params, 30000, 0)
  local items = completion and completion.result and (completion.result.items or completion.result)
  check(items and #items > 0, "completion candidates returned")
  local found = false
  for _, item in ipairs(items) do if item.label:find("greet") then found = true end end
  check(found, "greet completion available")
  check(client:supports_method("textDocument/inlayHint", 0), "server supports inline type hints")
  local hints = client:request_sync("textDocument/inlayHint", {
    textDocument = params.textDocument,
    range = { start = { line = 0, character = 0 }, ["end"] = { line = vim.api.nvim_buf_line_count(0), character = 0 } },
  }, 30000, 0)
  check(hints and hints.result and #hints.result > 0, "inline type hints returned")
  check(vim.wait(3000, function() return vim.lsp.inlay_hint.is_enabled({ bufnr = 0 }) end), "inline type hints enabled in buffer")
  local report = require("editor.report").collect(vim.api.nvim_get_current_buf(), false)
  local reported = false
  for _, entry in ipairs(report.clients) do
    if entry.name == name and entry.supports.inlay_hint then reported = true end
  end
  check(reported and report.diagnostic_total > 0, "report captures the actual attached LSP and diagnostics")
  local lang = vim.treesitter.language.get_lang(vim.bo.filetype)
  local parser = vim.treesitter.get_parser(0, lang)
  check(parser and #parser:parse() > 0, "Tree-sitter parser works")
  check(vim.treesitter.query.get(lang, "highlights") ~= nil, "highlight queries load")
  check(vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()] ~= nil, "highlighting attached")
  local formatter = name == "basedpyright" and "ruff_format" or "prettier"
  local info = require("conform").get_formatter_info(formatter, 0)
  local expected = name == "basedpyright" and "/.venv/bin/ruff" or "/node_modules/.bin/prettier"
  check(info.command and info.command:find(expected, 1, true), "project formatter preferred")
  vim.cmd("setlocal nofixendofline")
  local unformatted = name == "basedpyright" and "value={ 'a':1,'b':2 }" or "const value={a:1,b:2}"
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { unformatted })
  require("conform").format({ async = false, timeout_ms = 15000, lsp_format = "never" })
  check(vim.api.nvim_buf_get_lines(0, 0, -1, false)[1] ~= unformatted, "formatter changed unformatted buffer")
  check(require("blink.cmp.config").fuzzy.implementation == "lua", "Blink uses Lua implementation")
  check(not require("lazy.core.config").plugins["mason.nvim"], "Mason disabled")
  check(vim.v.errmsg == "", "no startup errors")
end
local function run_tests()
  local ok, err = xpcall(main, debug.traceback)
  if not ok then io.stderr:write(err .. "\n"); vim.cmd("cquit 1") else vim.cmd("qa!") end
end
if vim.v.vim_did_enter == 0 then
  vim.api.nvim_create_autocmd("VimEnter", { once = true, callback = function() vim.schedule(run_tests) end })
else
  run_tests()
end
