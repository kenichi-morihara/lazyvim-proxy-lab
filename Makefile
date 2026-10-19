.DEFAULT_GOAL := install
.PHONY: install doctor setup-tailscale setup-pi

install doctor setup-tailscale setup-pi:
	@$(MAKE) --no-print-directory -C editor $@
