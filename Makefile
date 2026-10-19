.DEFAULT_GOAL := install
.PHONY: install doctor setup-tailscale

install doctor setup-tailscale:
	@$(MAKE) --no-print-directory -C editor $@
