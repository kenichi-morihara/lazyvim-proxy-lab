-- Collect the running editor's state, never project source or the raw LSP log.
local M = {}
local uv = vim.uv

local function scrubber()
  local secrets = {}
  for key, value in pairs(vim.fn.environ()) do
    if key:upper():match("TOKEN") or key:upper():match("SECRET") or key:upper():match("PASSWORD")
      or key:upper():match("AUTH") or key:upper():match("API_KEY") then
      if #value >= 6 then secrets[#secrets + 1] = value end
    end
  end
  table.sort(secrets, function(a, b) return #a > #b end)
  return function(value)
    local text = tostring(value)
    for _, secret in ipairs(secrets) do
      text = text:gsub(secret:gsub("([^%w])", "%%%1"), "<secret>")
    end
    text = text:gsub("\027%[[%d;]*[A-Za-z]", "")
    text = text:gsub("https?://[^%s<>]+", "<url>")
    text = text:gsub("[%w._%%+%-]+@[%w.%-]+", "<email>")
    text = text:gsub("%d+%.%d+%.%d+%.%d+", "<ip>")
    text = text:gsub("[A-Za-z]:[\\/][^%s\"'<>]+", "<path>")
    text = text:gsub("/[^%s\"'<>]+", "<path>")
    text = text:gsub("[Bb]earer%s+[^%s]+", "Bearer <secret>")
    text = text:gsub("([%w_-]+)(%s*[=:]%s*)([^%s,;]+)", function(key, separator, value)
      local lower = key:lower()
      if lower:match("token") or lower:match("secret") or lower:match("password")
        or lower:match("auth") or lower:match("api.?key") then return key .. separator .. "<secret>" end
      return key .. separator .. value
    end)
    return vim.fn.strcharpart(text, 0, 2000)
  end
end

local function read_json(path)
  local ok, lines = pcall(vim.fn.readfile, path)
  if not ok then return nil end
  local decoded, value = pcall(vim.json.decode, table.concat(lines, "\n"))
  return decoded and type(value) == "table" and value or nil
end

local function supported(client, method, buf)
  local ok, result = pcall(client.supports_method, client, method, buf)
  return ok and result == true
end

function M.collect(buf, include_messages)
  local clean = scrubber()
  local version, uname = vim.version(), uv.os_uname()
  local report = {
    schema_version = 1,
    created_at = os.date("!%Y-%m-%dT%H:%M:%SZ"),
    neovim = ("%d.%d.%d"):format(version.major, version.minor, version.patch),
    system = { os = uname.sysname, release = uname.release, arch = uname.machine },
    buffer = { filetype = vim.bo[buf].filetype, line_count = vim.api.nvim_buf_line_count(buf) },
    environment = {
      proxy_configured = not not (vim.env.HTTPS_PROXY or vim.env.https_proxy or vim.env.HTTP_PROXY or vim.env.http_proxy),
      ca_configured = not not (vim.env.SSL_CERT_FILE or vim.env.NODE_EXTRA_CA_CERTS or vim.env.PIP_CERT),
      virtual_env_set = vim.env.VIRTUAL_ENV ~= nil,
    },
    clipboard = { provider = type(vim.g.clipboard) == "string" and clean(vim.g.clipboard) or "custom/auto", option = vim.o.clipboard },
    inlay_hints_enabled = vim.lsp.inlay_hint.is_enabled({ bufnr = buf }),
    tools = {}, clients = {}, diagnostics = {}, diagnostic_counts = {},
    messages_included = include_messages == true,
  }
  for _, name in ipairs({ "node", "python3", "basedpyright-langserver", "vtsls", "ruff", "prettier", "tailscale", "tailscaled" }) do
    report.tools[name] = { available = vim.fn.executable(name) == 1 }
  end
  local root = vim.fs.root(buf, { "pyproject.toml", "pyrightconfig.json", "tsconfig.json", "package.json", ".git" })
  report.project = { root_detected = root ~= nil, markers = {} }
  if root then
    for _, name in ipairs({ "pyproject.toml", "pyrightconfig.json", "tsconfig.json", "package.json" }) do
      report.project.markers[name] = uv.fs_stat(root .. "/" .. name) ~= nil
    end
    report.project.venv_python_available = vim.fn.executable(root .. "/.venv/bin/python") == 1
    local ts = read_json(root .. "/node_modules/typescript/package.json")
    report.project.typescript_version = ts and ts.version and clean(ts.version) or nil
  end
  local lock = read_json(vim.fn.stdpath("config") .. "/lazy-lock.json") or {}
  report.plugin_commits = {}
  for _, name in ipairs({ "LazyVim", "nvim-lspconfig", "blink.cmp" }) do
    report.plugin_commits[name] = lock[name] and lock[name].commit or "unknown"
  end
  for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf })) do
    local settings = client.config.settings or {}
    local analysis = (settings.basedpyright or settings.python or {}).analysis or {}
    local cmd = client.config.cmd
    local python = settings.python and settings.python.pythonPath
    local hints = {}
    for _, key in ipairs({ "variableTypes", "callArgumentNames", "functionReturnTypes", "genericTypes",
      "parameterNames", "parameterTypes", "functionLikeReturnTypes", "propertyDeclarationTypes" }) do
      local value = (analysis.inlayHints or {})[key]
      if value == nil then value = ((settings.typescript or {}).inlayHints or {})[key] end
      if type(value) == "table" then value = value.enabled end
      if type(value) == "boolean" then hints[key] = value
      elseif type(value) == "string" then hints[key] = clean(value) end
    end
    report.clients[#report.clients + 1] = {
      name = clean(client.name), initialized = client.initialized == true,
      server_version = client.server_info and client.server_info.version and clean(client.server_info.version) or nil,
      command = type(cmd) == "table" and type(cmd[1]) == "string" and clean(vim.fs.basename(cmd[1])) or "function/unknown",
      root_detected = type(client.config.root_dir) == "string",
      workspace_folder_count = #(client.workspace_folders or {}),
      python_interpreter_configured = type(python) == "string",
      python_interpreter_available = type(python) == "string" and vim.fn.executable(python) == 1,
      type_checking_mode = analysis.typeCheckingMode and clean(analysis.typeCheckingMode) or nil,
      diagnostic_mode = analysis.diagnosticMode and clean(analysis.diagnosticMode) or nil,
      inlay_settings = hints,
      supports = {
        completion = supported(client, "textDocument/completion", buf),
        hover = supported(client, "textDocument/hover", buf),
        definition = supported(client, "textDocument/definition", buf),
        inlay_hint = supported(client, "textDocument/inlayHint", buf),
      },
    }
  end
  local diagnostics = vim.diagnostic.get(buf)
  report.diagnostic_total = #diagnostics
  for index, diagnostic in ipairs(diagnostics) do
    local severity = vim.diagnostic.severity[diagnostic.severity] or "UNKNOWN"
    report.diagnostic_counts[severity] = (report.diagnostic_counts[severity] or 0) + 1
    if index <= 100 then
      report.diagnostics[#report.diagnostics + 1] = {
        source = clean(diagnostic.source or "unknown"),
        code = diagnostic.code and clean(diagnostic.code) or nil,
        severity = severity, line = diagnostic.lnum + 1, column = diagnostic.col + 1,
        message = include_messages and clean(diagnostic.message) or nil,
      }
    end
  end
  if include_messages then
    local messages = vim.split(vim.api.nvim_exec2("messages", { output = true }).output, "\n", { plain = true })
    report.recent_messages = {}
    for index = math.max(1, #messages - 29), #messages do
      report.recent_messages[#report.recent_messages + 1] = clean(messages[index])
    end
  end
  return report
end

local function pretty(value)
  local raw, out, depth, quoted, escaped = vim.json.encode(value), {}, 0, false, false
  local function newline() out[#out + 1] = "\n" .. string.rep("  ", depth) end
  for index = 1, #raw do
    local char = raw:sub(index, index)
    if quoted then
      out[#out + 1] = char
      if escaped then escaped = false elseif char == "\\" then escaped = true elseif char == '"' then quoted = false end
    elseif char == '"' then
      quoted = true; out[#out + 1] = char
    elseif char == "{" or char == "[" then
      out[#out + 1] = char; depth = depth + 1
      local next_char = raw:sub(index + 1, index + 1)
      if next_char ~= "}" and next_char ~= "]" then newline() end
    elseif char == "}" or char == "]" then
      depth = depth - 1
      local previous = raw:sub(index - 1, index - 1)
      if previous ~= "{" and previous ~= "[" then newline() end
      out[#out + 1] = char
    elseif char == "," then
      out[#out + 1] = char; newline()
    elseif char == ":" then
      out[#out + 1] = ": "
    else out[#out + 1] = char end
  end
  return table.concat(out)
end

function M.preview(include_messages)
  local buf = vim.api.nvim_get_current_buf()
  local source = vim.b[buf].editor_report_source or M.source_buf
  if vim.bo[buf].buftype ~= "" and source and vim.api.nvim_buf_is_valid(source) then buf = source end
  M.source_buf = buf
  local report = M.collect(buf, include_messages)
  M.last_buf = require("editor.output").buffer("report", vim.split(pretty(report), "\n", { plain = true }), "json", true)
  vim.b[M.last_buf].editor_report = true
  vim.b[M.last_buf].editor_report_source = buf
  vim.notify("Report preview: edit/remove fields, then :EditorReportSave or :EditorReportSend <device>.")
  return M.last_buf
end

local function reviewed_buffer()
  local current = vim.api.nvim_get_current_buf()
  local buf = vim.b[current].editor_report and current or M.last_buf
  assert(buf and vim.api.nvim_buf_is_valid(buf), "Run :EditorReport on the affected file first.")
  M.last_buf = buf
  M.source_buf = vim.b[buf].editor_report_source or M.source_buf
  return buf
end

function M.save()
  local contents = table.concat(vim.api.nvim_buf_get_lines(reviewed_buffer(), 0, -1, false), "\n") .. "\n"
  assert(#contents <= 1024 * 1024, "Report is larger than 1 MiB.")
  local data = vim.json.decode(contents)
  assert(type(data) == "table" and data.schema_version == 1, "Report must be valid JSON with schema_version=1.")
  local dir = vim.fn.stdpath("state") .. "/editor-reports"
  vim.fn.mkdir(dir, "p", 448)
  assert(uv.fs_chmod(dir, 448)) -- 0700
  local path = dir .. "/editor-report-" .. os.date("!%Y%m%dT%H%M%SZ") .. "-" .. uv.hrtime() .. ".json"
  local fd = assert(uv.fs_open(path, "wx", 384)) -- 0600, no overwrite
  local written, err = uv.fs_write(fd, contents, 0)
  uv.fs_close(fd)
  assert(written == #contents, err or "Incomplete report write")
  M.last_path = path
  return path
end

function M.tailscale_args()
  local binary = vim.fn.exepath("tailscale")
  assert(binary ~= "", "tailscale is not installed or not on PATH.")
  local args = { binary }
  local state = vim.env.EDITOR_TAILSCALE_STATE_DIR
    or ((vim.env.XDG_STATE_HOME or (vim.env.HOME .. "/.local/state")) .. "/editor-tailscale")
  local socket = vim.env.EDITOR_TAILSCALE_SOCKET or (state .. "/tailscaled.sock")
  if vim.env.EDITOR_TAILSCALE_SOCKET or uv.fs_stat(socket) then args[#args + 1] = "--socket=" .. socket end
  return args
end

function M.send(target)
  target = (target or ""):gsub(":$", "")
  assert(target:match("^[%w][%w._%-]*$"), "Use a Tailscale device name or IPv4 address (not user@host).")
  reviewed_buffer()
  local args = M.tailscale_args()
  local path = M.save() -- Snapshot exactly the reviewed/edited preview, never recollect here.
  vim.list_extend(args, { "file", "cp", path, target .. ":" })
  return require("editor.output").run(args, "Send reviewed report to " .. target .. " (Taildrop)")
end

return M
