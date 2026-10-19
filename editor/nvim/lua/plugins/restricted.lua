return {
  { "mason-org/mason.nvim", enabled = false },
  { "mason-org/mason-lspconfig.nvim", enabled = false },
  { "linux-cultist/venv-selector.nvim", enabled = false },
  { "nvim-treesitter/nvim-treesitter-textobjects", enabled = false },
  { "saghen/blink.cmp", opts = { fuzzy = { implementation = "lua" } } },
  {
    "folke/which-key.nvim",
    keys = { { "<c-w><space>", false } },
    opts = function(_, opts)
      -- Space+w has explicit window commands; Ctrl+W now closes the file.
      opts.plugins = vim.tbl_deep_extend("force", opts.plugins or {}, { presets = { windows = false } })
      local function remove_window_proxy(specs)
        for _, spec in ipairs(specs) do
          if type(spec) == "table" then
            if spec[1] == "<leader>w" then spec.proxy = nil end
            remove_window_proxy(spec)
          end
        end
      end
      remove_window_proxy(opts.spec or {})
    end,
  },
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
      inlay_hints = { enabled = true },
      servers = {
        lua_ls = { enabled = false },
        basedpyright = {
          mason = false,
          settings = { basedpyright = { analysis = { typeCheckingMode = "basic", diagnosticMode = "openFilesOnly", autoSearchPaths = true, inlayHints = { variableTypes = true, callArgumentNames = true, functionReturnTypes = true, genericTypes = true } } } },
          before_init = function(_, config)
            local root = config.root_dir or vim.fn.getcwd()
            local python = vim.env.VIRTUAL_ENV and (vim.env.VIRTUAL_ENV .. "/bin/python") or (root .. "/.venv/bin/python")
            if vim.fn.executable(python) == 1 then
              config.settings = config.settings or {}
              config.settings.python = config.settings.python or {}
              config.settings.python.pythonPath = python
            end
          end,
        },
        ruff = { mason = false },
        vtsls = {
          mason = false,
          settings = {
            vtsls = { autoUseWorkspaceTsdk = true },
            typescript = { inlayHints = {
              enumMemberValues = { enabled = true },
              functionLikeReturnTypes = { enabled = true },
              parameterNames = { enabled = "literals" },
              parameterTypes = { enabled = true },
              propertyDeclarationTypes = { enabled = true },
              variableTypes = { enabled = true },
            } },
          },
        },
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
