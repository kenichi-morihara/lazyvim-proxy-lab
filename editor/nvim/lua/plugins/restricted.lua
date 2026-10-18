return {
  { "mason-org/mason.nvim", enabled = false },
  { "mason-org/mason-lspconfig.nvim", enabled = false },
  { "linux-cultist/venv-selector.nvim", enabled = false },
  { "nvim-treesitter/nvim-treesitter-textobjects", enabled = false },
  { "saghen/blink.cmp", opts = { fuzzy = { implementation = "lua" } } },
  {
    "nvim-treesitter/nvim-treesitter",
    commit = "7caec274fd19c12b55902a5b795100d21531391f",
    build = false,
    opts = function() return { ensure_installed = {} } end,
    config = function(_, opts)
      require("nvim-treesitter").setup(opts)
      -- Install parsers explicitly with tools/install-parsers, never with TSInstall/TSUpdate.
      for _, cmd in ipairs({ "TSInstall", "TSUpdate" }) do
        vim.api.nvim_create_user_command(cmd, function()
          vim.notify("Run make in the configuration checkout (Git transport, pinned parsers)", vim.log.levels.WARN)
        end, { nargs = "*", force = true })
      end
      local function attach(buf)
        if vim.api.nvim_buf_line_count(buf) > 20000 or vim.api.nvim_buf_get_offset(buf, vim.api.nvim_buf_line_count(buf)) > 1024 * 1024 then
          return
        end
        pcall(vim.treesitter.start, buf)
      end
      vim.api.nvim_create_autocmd("FileType", { callback = function(ev) attach(ev.buf) end })
      attach(vim.api.nvim_get_current_buf())
    end,
  },
  {
    "neovim/nvim-lspconfig",
    opts = {
      inlay_hints = { enabled = false },
      servers = {
        lua_ls = { enabled = false },
        pyright = {
          mason = false,
          settings = { python = { analysis = { typeCheckingMode = "basic", diagnosticMode = "openFilesOnly", autoSearchPaths = true } } },
          before_init = function(_, config)
            local root = config.root_dir or vim.fn.getcwd()
            local python = vim.env.VIRTUAL_ENV and (vim.env.VIRTUAL_ENV .. "/bin/python") or (root .. "/.venv/bin/python")
            if vim.fn.executable(python) == 1 then
              config.settings.python.pythonPath = python
            end
          end,
        },
        ruff = { mason = false },
        vtsls = { mason = false, settings = { vtsls = { autoUseWorkspaceTsdk = true } } },
      },
    },
  },
  {
    "stevearc/conform.nvim",
    opts = {
      formatters_by_ft = { python = { "ruff_format" }, typescript = { "prettier" }, typescriptreact = { "prettier" }, javascript = { "prettier" }, javascriptreact = { "prettier" } },
      formatters = {
        ruff_format = { command = function(_, ctx)
          local root = vim.fs.root(ctx.filename, { "pyproject.toml", ".git" })
          local venv = vim.env.VIRTUAL_ENV or (root and (root .. "/.venv"))
          return venv and vim.fn.executable(venv .. "/bin/ruff") == 1 and (venv .. "/bin/ruff") or "ruff"
        end },
      },
    },
  },
  { "folke/snacks.nvim", opts = { dashboard = { enabled = false }, scroll = { enabled = false }, animate = { enabled = false }, bigfile = { enabled = true } } },
}
