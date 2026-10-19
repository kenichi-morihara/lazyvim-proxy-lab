return {
  { "folke/snacks.nvim", keys = { { "<leader>gd", false } } },
  {
    "sindrets/diffview.nvim",
    commit = "4516612fe98ff56ae0415a259ff6361a89419b0a",
    cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewFileHistory", "DiffviewFocusFiles", "DiffviewToggleFiles", "DiffviewRefresh" },
    keys = {
      { "<leader>gd", "<cmd>DiffviewOpen<cr>", desc = "Git diff viewer" },
      { "<leader>gH", "<cmd>DiffviewFileHistory %<cr>", desc = "Git file history" },
      { "<leader>gq", "<cmd>DiffviewClose<cr>", desc = "Close diff viewer" },
    },
    opts = function()
      local function close() vim.cmd.DiffviewClose() end
      local function close_maps()
        return {
          { "n", "q", close, { desc = "Close diff viewer" } },
          -- Keep Ctrl+W immediate: these default prefixes would delay it.
          { "n", "<C-w><C-f>", false },
          { "n", "<C-w>gf", false },
        }
      end
      return {
        use_icons = false,
        keymaps = {
          view = close_maps(),
          file_panel = close_maps(),
          file_history_panel = close_maps(),
        },
      }
    end,
  },
}
