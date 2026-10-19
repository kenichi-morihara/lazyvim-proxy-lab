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
-- Printable leader keys replace text in Select mode, so use Ctrl+C there.
vim.keymap.set("s", "<C-c>", '<C-g>"+ygv<C-g>', { desc = "Copy selected text to system clipboard" })

vim.keymap.set({ "n", "i", "x", "s" }, "<C-a>", "<Esc>gg0vG$<C-g>", { desc = "Select all text" })

local function close_file()
  if vim.bo.modified then
    vim.notify("Unsaved changes: save with Ctrl+S before closing.", vim.log.levels.WARN)
    return
  end
  if _G.Snacks then
    Snacks.bufdelete()
  else
    vim.cmd.bdelete()
  end
end
vim.api.nvim_create_user_command("EditorClose", close_file, { desc = "Close the current saved buffer" })
vim.keymap.set({ "n", "i", "x", "s" }, "<C-w>", "<Esc><cmd>EditorClose<cr>", { desc = "Close current file" })

-- Call window commands directly: remapped <C-w> sequences would now close files.
local windows = {
  h = { "h", "Go to left window" }, j = { "j", "Go to lower window" },
  k = { "k", "Go to upper window" }, l = { "l", "Go to right window" },
  w = { "w", "Next window" }, p = { "p", "Previous window" },
  s = { "s", "Split below" }, v = { "v", "Split right" },
  c = { "c", "Close window" }, d = { "c", "Close window" },
  q = { "q", "Quit window" }, o = { "o", "Only this window" },
  ["="] = { "=", "Equal window sizes" },
  ["+"] = { "+", "Increase height" }, ["-"] = { "-", "Decrease height" },
  [">"] = { ">", "Increase width" }, ["<"] = { "<", "Decrease width" },
  H = { "H", "Move window left" }, J = { "J", "Move window down" },
  K = { "K", "Move window up" }, L = { "L", "Move window right" },
  r = { "r", "Rotate windows" }, R = { "R", "Rotate windows backwards" },
  x = { "x", "Exchange windows" }, T = { "T", "Move window to new tab" },
}
local function window_map(key, command, description)
  vim.keymap.set("n", key, function()
    local count = vim.v.count > 0 and tostring(vim.v.count) or ""
    vim.cmd(count .. "wincmd " .. command)
  end, { desc = description })
end
for key, action in pairs(windows) do window_map("<leader>w" .. key, action[1], action[2]) end
for key, command in pairs({ ["<C-h>"] = "h", ["<C-j>"] = "j", ["<C-k>"] = "k", ["<C-l>"] = "l" }) do
  window_map(key, command, windows[command][2])
end
window_map("<leader>-", "s", "Split window below")
window_map("<leader>|", "v", "Split window right")
