-- Space + ? opens the compact key reference shipped with this config.
local function open_cheatsheet()
  local path = vim.fn.stdpath("config") .. "/CHEATSHEET.md"
  vim.cmd.edit(vim.fn.fnameescape(path))
end

vim.keymap.set("n", "<leader>?", open_cheatsheet, { desc = "Open key cheatsheet" })
vim.api.nvim_create_user_command("Cheatsheet", open_cheatsheet, { desc = "Open key cheatsheet" })

-- Copy through SSH to the terminal host (e.g. Windows Terminal).
vim.keymap.set({ "n", "x" }, "<leader>y", '"+y', { desc = "Copy to system clipboard" })
vim.keymap.set("n", "<leader>Y", '"+yy', { desc = "Copy line to system clipboard" })
