-- Retained output buffers for non-interactive commands. No plugin dependency.
local M = { jobs = {}, results = {} }
local sequence = 0

function M.show(buf)
  for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
    if vim.api.nvim_buf_get_name(vim.api.nvim_win_get_buf(win)):match("^editor://") then
      vim.api.nvim_win_set_buf(win, buf)
      vim.api.nvim_set_current_win(win)
      return
    end
  end
  vim.cmd("botright 14split")
  vim.api.nvim_win_set_buf(0, buf)
end

function M.buffer(kind, lines, filetype, editable)
  sequence = sequence + 1
  local buf = vim.api.nvim_create_buf(true, true)
  vim.api.nvim_buf_set_name(buf, "editor://" .. kind .. "/" .. sequence)
  vim.bo[buf].bufhidden = "hide"
  vim.bo[buf].swapfile = false
  vim.bo[buf].filetype = filetype or ""
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.bo[buf].modifiable = editable or false
  vim.bo[buf].modified = false
  vim.keymap.set("n", "q", "<cmd>close<cr>", { buffer = buf, desc = "Close result window" })
  M.show(buf)
  return buf
end

local function append(buf, lines)
  if #lines == 0 or not vim.api.nvim_buf_is_valid(buf) then return end
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, -1, -1, false, lines)
  vim.bo[buf].modifiable = false
  vim.bo[buf].modified = false
end

-- String commands use Neovim's configured shell. argv lists bypass the shell.
function M.run(command, label, opts)
  opts = opts or {}
  local cwd = opts.cwd or vim.fn.getcwd()
  local buf = M.buffer("command", { "$ " .. label, "cwd: " .. cwd, "" })
  M.last_buf = buf
  local pending, bytes, truncated = { stdout = "", stderr = "" }, 0, false
  local function receive(stream, data)
    if not data then return end
    local chunk = table.concat(data, "\n")
    local remaining = 1024 * 1024 - bytes
    if remaining <= 0 then return end
    bytes = bytes + #chunk
    chunk = chunk:sub(1, remaining):gsub("\r\n", "\n"):gsub("\r", "")
    local lines = vim.split(pending[stream] .. chunk, "\n", { plain = true })
    pending[stream] = table.remove(lines)
    if stream == "stderr" then
      for i, line in ipairs(lines) do lines[i] = "[stderr] " .. line end
    end
    append(buf, lines)
    if bytes >= 1024 * 1024 and not truncated then
      truncated = true
      append(buf, { "[output truncated at 1 MiB]" })
    end
  end
  local timer
  local ok, job = pcall(vim.fn.jobstart, command, {
    cwd = cwd,
    stdin = "null",
    on_stdout = function(_, data) receive("stdout", data) end,
    on_stderr = function(_, data) receive("stderr", data) end,
    on_exit = function(_, code)
      if timer then vim.fn.timer_stop(timer) end
      for _, stream in ipairs({ "stdout", "stderr" }) do
        if pending[stream] ~= "" then
          append(buf, { (stream == "stderr" and "[stderr] " or "") .. pending[stream] })
        end
      end
      M.jobs[buf] = nil
      M.results[buf] = code
      append(buf, { "", "[exit " .. code .. "]" })
    end,
  })
  if not ok or job <= 0 then
    M.results[buf] = -1
    append(buf, { "Cannot start command: " .. tostring(job) })
    return buf
  end
  M.jobs[buf] = job
  timer = vim.fn.timer_start(opts.timeout or 120000, function()
    if M.jobs[buf] == job then
      append(buf, { "[timeout; stopping command]" })
      vim.fn.jobstop(job)
    end
  end)
  vim.keymap.set("n", "<C-c>", function() M.stop(buf) end, { buffer = buf, desc = "Stop command" })
  vim.api.nvim_create_autocmd("BufWipeout", {
    buffer = buf, once = true,
    callback = function()
      if M.jobs[buf] then vim.fn.jobstop(M.jobs[buf]) end
      M.results[buf] = nil
    end,
  })
  return buf, job
end

function M.stop(buf)
  local job = M.jobs[buf or vim.api.nvim_get_current_buf()] or M.jobs[M.last_buf]
  if job then vim.fn.jobstop(job) end
end

function M.last()
  if M.last_buf and vim.api.nvim_buf_is_valid(M.last_buf) then
    M.show(M.last_buf)
  else
    vim.notify("No command output yet. Run :EditorRun <command>.", vim.log.levels.INFO)
  end
end

function M.prompt()
  vim.ui.input({ prompt = "Run command: " }, function(command)
    if command and command:match("%S") then M.run(command, command) end
  end)
end

return M
