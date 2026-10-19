-- Space + ? opens the compact key reference shipped with this config.
local function open_cheatsheet()
  local path = vim.fn.stdpath("config") .. "/CHEATSHEET.md"
  vim.cmd.edit(vim.fn.fnameescape(path))
end

vim.keymap.set("n", "<leader>?", open_cheatsheet, { desc = "Open key cheatsheet" })
vim.api.nvim_create_user_command("Cheatsheet", open_cheatsheet, { desc = "Open key cheatsheet" })
