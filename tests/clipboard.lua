-- nvim --headless -u NONE -l tests/clipboard.lua
-- Exercise real mappings/provider while capturing OSC 52 instead of changing a clipboard.
local root = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h:h")
vim.g.mapleader = " "
dofile(root .. "/editor/nvim/lua/config/options.lua")
dofile(root .. "/editor/nvim/lua/config/keymaps.lua")

-- Fail immediately if any mapping tries to read the host clipboard.
require("vim.ui.clipboard.osc52").paste = function()
  return function() error("unexpected OSC 52 clipboard read") end
end
local writes = {}
local send = vim.api.nvim_chan_send
vim.api.nvim_chan_send = function(channel, data)
  if channel == 2 and data:sub(1, 5) == "\027]52;" then
    writes[#writes + 1] = data
    return
  end
  return send(channel, data)
end
local function keys(text)
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(text, true, false, true), "xt", false)
end
local function copied()
  local encoded = assert(writes[#writes]:match("^\027%]52;c;([%w+/=]*)\027\\$"))
  return vim.base64.decode(encoded)
end

vim.api.nvim_buf_set_lines(0, 0, -1, false, { "hello world", "日本語", "last" })
vim.cmd("normal! gg0")
keys("v4l y")
assert(copied() == "hello", "visual copy must send only the selection")
vim.cmd("normal! 2G0")
keys(" Y")
assert(copied() == "日本語\n", "line copy must preserve UTF-8 and newline")
keys("p")
assert(vim.api.nvim_buf_get_lines(0, 2, 3, false)[1] == "日本語", "paste after external copy must stay local")
local count = #writes
vim.cmd("normal! 4G0")
keys("yy")
assert(#writes == count, "normal yank must stay internal")
keys("p")
assert(vim.api.nvim_buf_get_lines(0, -2, -1, false)[1] == "last", "normal paste must use internal register")
assert(vim.o.clipboard == "", "ordinary paste must not request OSC 52 clipboard reads")
print("PASS visual/line OSC 52 copy, UTF-8, and internal yank/paste")
vim.cmd("qa!")
