-- nvim --headless -u NONE -l tests/support.lua
local root = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h:h")
local temp = vim.fn.tempname()
vim.fn.mkdir(temp, "p")
vim.env.XDG_STATE_HOME = temp .. "/state"
vim.env.XDG_CONFIG_HOME = root .. "/editor"
vim.opt.rtp:prepend(root .. "/editor/nvim")
local function check(ok, message)
  assert(ok, message)
  print("PASS " .. message)
end
local function contents(buf)
  return table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")
end
local function main()
  require("editor").setup()
  require("editor").setup()
  local output, report = require("editor.output"), require("editor.report")
  vim.fn.mkdir(temp .. "/project", "p")
  vim.fn.writefile({ "[project]" }, temp .. "/project/pyproject.toml")
  vim.fn.writefile({ "source_code_should_never_be_collected = 123" }, temp .. "/project/app.py")
  vim.cmd.edit(vim.fn.fnameescape(temp .. "/project/app.py"))
  vim.bo.filetype = "python"
  local source = vim.api.nvim_get_current_buf()
  vim.fn.mkdir(temp .. "/project/.venv/bin", "p")
  local python = temp .. "/project/.venv/bin/python"
  vim.fn.writefile({ "#!/bin/sh", "exit 0" }, python)
  vim.fn.setfperm(python, "rwx------")
  local specs = dofile(root .. "/editor/nvim/lua/plugins/restricted.lua")
  local server
  for _, spec in ipairs(specs) do
    if spec[1] == "neovim/nvim-lspconfig" then server = spec.opts.servers.basedpyright end
  end
  local config = { root_dir = temp .. "/project", settings = vim.deepcopy(server.settings) }
  local virtual_env = vim.env.VIRTUAL_ENV
  vim.env.VIRTUAL_ENV = nil
  server.before_init({}, config)
  vim.env.VIRTUAL_ENV = virtual_env
  check(config.settings.python.pythonPath == python, "basedpyright initializes the project venv without a pre-existing python settings table")
  vim.lsp.get_clients = function(filter)
    assert(filter.bufnr == source)
    return { {
      name = "basedpyright", initialized = true, server_info = { version = "1.40.2" },
      config = { cmd = { "/private/bin/basedpyright-langserver", "--stdio" }, root_dir = temp .. "/project",
        settings = { basedpyright = { analysis = { typeCheckingMode = "basic" } } } },
      supports_method = function(_, method) return method ~= "textDocument/definition" end,
    } }
  end
  vim.env.EDITOR_TEST_API_TOKEN = "private-fixture-token"
  local namespace = vim.api.nvim_create_namespace("editor-report-test")
  vim.diagnostic.set(namespace, source, { {
    lnum = 0, col = 0, severity = vim.diagnostic.severity.ERROR,
    source = "basedpyright", code = "reportAssignmentType",
    message = "private-fixture-token /private/code.py https://user:pass@internal.invalid token=another-private-value fixture@example.invalid 10.2.3.4",
  } })
  local basic = report.collect(source, false)
  local encoded = vim.json.encode(basic)
  check(basic.diagnostic_total == 1 and basic.diagnostics[1].message == nil, "default report includes diagnostic codes without text")
  check(not encoded:find(temp, 1, true) and not encoded:find("source_code_should_never_be_collected", 1, true), "no source content or project path in report")
  check(basic.clients[1].supports.hover and not basic.clients[1].supports.definition, "live LSP capabilities collected")
  check(basic.plugin_commits.LazyVim == "28db03f958d58dfff3c647ce28fdc1cb88ac158d", "pinned plugin version collected")
  local detailed = vim.json.encode(report.collect(source, true))
  for _, forbidden in ipairs({ "private-fixture-token", "/private/code.py", "user:pass", "another-private-value", "fixture@example.invalid", "10.2.3.4" }) do
    check(not detailed:find(forbidden, 1, true), "sensitive error text redacted")
  end
  local sent_without_preview, preview_error = pcall(report.send, "mac")
  check(not sent_without_preview and tostring(preview_error):find("EditorReport", 1, true), "sending without a preview is rejected")
  local preview = report.preview(true)
  report.preview(false)
  vim.api.nvim_win_set_buf(0, preview) -- Sending must use this visible older preview, not the newest one.
  local reviewed = vim.json.decode(contents(preview))
  reviewed.reviewed = true
  reviewed.diagnostics = nil
  vim.api.nvim_buf_set_lines(preview, 0, -1, false, { vim.json.encode(reviewed) })
  local saved = report.save()
  check(vim.uv.fs_stat(saved).mode % 512 == 384, "saved report has mode 0600")
  check(vim.uv.fs_stat(vim.fs.dirname(saved)).mode % 512 == 448, "report directory has mode 0700")

  -- A stand-in CLI verifies argv and transmitted snapshot without a tailnet.
  vim.fn.mkdir(temp .. "/bin", "p")
  local cli = temp .. "/bin/tailscale"
  vim.fn.writefile({
    "#!" .. vim.fn.exepath("python3"),
    "import json, os, sys",
    "from pathlib import Path",
    "Path(os.environ['EDITOR_TEST_ARGS']).write_text(json.dumps(sys.argv[1:]))",
    "if 'cp' in sys.argv: Path(os.environ['EDITOR_TEST_PAYLOAD']).write_bytes(Path(sys.argv[-2]).read_bytes())",
    "print('transfer complete')",
  }, cli)
  vim.fn.setfperm(cli, "rwx------")
  vim.env.PATH = temp .. "/bin:" .. vim.env.PATH
  vim.env.EDITOR_TEST_ARGS = temp .. "/args.json"
  vim.env.EDITOR_TEST_PAYLOAD = temp .. "/payload.json"
  vim.env.EDITOR_TAILSCALE_SOCKET = temp .. "/user socket"
  check(not pcall(report.send, "mac;touch /tmp/unwanted"), "invalid transfer target rejected")
  local transfer = report.send("my-mac:")
  check(report.last_buf == preview, "reviewed preview remains selected for transfer retries")
  check(vim.wait(3000, function() return output.results[transfer] ~= nil end), "transfer result arrives asynchronously")
  check(output.results[transfer] == 0 and contents(transfer):find("transfer complete", 1, true), "transfer output retained")
  local sent = vim.json.decode(table.concat(vim.fn.readfile(vim.env.EDITOR_TEST_PAYLOAD), "\n"))
  check(sent.reviewed and sent.diagnostics == nil, "exact reviewed snapshot sent without recollecting")
  local args = vim.json.decode(table.concat(vim.fn.readfile(vim.env.EDITOR_TEST_ARGS), "\n"))
  check(args[1] == "--socket=" .. vim.env.EDITOR_TAILSCALE_SOCKET and args[2] == "file" and args[3] == "cp" and args[5] == "my-mac:", "userspace socket and Taildrop argv preserved")

  local buf = output.run("printf 'first\\n'; sleep 0.2; printf 'last'; printf 'bad\\n' >&2; exit 7", "stream test", { cwd = temp })
  check(vim.wait(1000, function() return contents(buf):find("first", 1, true) ~= nil end) and output.results[buf] == nil, "stdout visible before command exits")
  check(vim.wait(3000, function() return output.results[buf] ~= nil end), "command completes")
  local result = contents(buf)
  check(output.results[buf] == 7 and result:find("[stderr] bad", 1, true) and result:find("last", 1, true), "stderr, unterminated output and nonzero exit retained")
  check(result:find("cwd: " .. temp, 1, true), "command uses requested working directory")
  vim.cmd.close()
  output.last()
  check(vim.api.nvim_get_current_buf() == buf and contents(buf) == result, "command output can be reopened")
  local timeout = output.run("sleep 10", "timeout test", { timeout = 50 })
  check(vim.wait(3000, function() return output.results[timeout] ~= nil end), "long-running command stops at timeout")
  check(output.results[timeout] ~= 0 and contents(timeout):find("[timeout", 1, true), "timeout reported in buffer")
end
local ok, err = xpcall(main, debug.traceback)
vim.fn.delete(temp, "rf")
if not ok then io.stderr:write(err .. "\n"); vim.cmd("cquit 1") else vim.cmd("qa!") end
