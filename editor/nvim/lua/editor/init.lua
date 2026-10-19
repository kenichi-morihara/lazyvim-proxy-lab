local M = {}

local function guarded(callback)
  return function(...)
    local ok, result = pcall(callback, ...)
    if not ok then vim.notify(tostring(result), vim.log.levels.ERROR) end
    return ok and result or nil
  end
end

function M.setup()
  if M.initialized then return end
  M.initialized = true
  vim.api.nvim_create_user_command("EditorRun", function(args)
    if args.args == "" then require("editor.output").prompt()
    else require("editor.output").run(args.args, args.args) end
  end, { nargs = "*", desc = "Run a shell command and retain its output" })
  vim.api.nvim_create_user_command("EditorRunLast", function() require("editor.output").last() end, {})
  vim.api.nvim_create_user_command("EditorRunStop", function() require("editor.output").stop() end, {})
  vim.api.nvim_create_user_command("EditorTailscale", guarded(function(args)
    local command = require("editor.report").tailscale_args()
    vim.list_extend(command, #args.fargs > 0 and args.fargs or { "status" })
    require("editor.output").run(command, "tailscale " .. args.args)
  end), { nargs = "*", desc = "Run Tailscale with the optional userspace socket" })
  vim.api.nvim_create_user_command("EditorReport", guarded(function(args)
    require("editor.report").preview(args.bang)
  end), { bang = true, desc = "Preview editor diagnostics (! includes redacted messages)" })
  vim.api.nvim_create_user_command("EditorReportSave", guarded(function()
    vim.notify("Saved: " .. require("editor.report").save())
  end), { desc = "Save the reviewed report privately" })
  vim.api.nvim_create_user_command("EditorReportSend", guarded(function(args)
    local target = args.args ~= "" and args.args or vim.env.EDITOR_REPORT_TARGET
    if target then require("editor.report").send(target)
    else
      vim.ui.input({ prompt = "Send report to Tailscale device: " }, guarded(function(value)
        if value and value ~= "" then require("editor.report").send(value) end
      end))
    end
  end), { nargs = "?", desc = "Send reviewed report using Taildrop" })
  vim.keymap.set("n", "<leader>!", function() require("editor.output").prompt() end,
    { desc = "Run command (retained output)" })
end

return M
