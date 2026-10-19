.DEFAULT_GOAL := install
.PHONY: install doctor setup-tailscale setup-pi doctor-pi pi-lab

install doctor setup-tailscale setup-pi doctor-pi:
	@$(MAKE) --no-print-directory -C editor $@

pi-lab:
	@python3 lab/ai/server.py
