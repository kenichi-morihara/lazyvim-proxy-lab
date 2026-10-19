return {
  {
    "dstein64/nvim-scrollview",
    commit = "b9e6ee00e9e20330b426fbec47812c2213d371ca",
    event = "VeryLazy",
    opts = {
      base = "right",
      column = 1,
      current_only = false,
      excluded_filetypes = { "snacks_picker_list", "snacks_picker_input", "lazy", "DiffviewFiles", "DiffviewFileHistory" },
      signs_on_startup = { "diagnostics", "search" },
    },
  },
}
