.DEFAULT_GOAL := install
.PHONY: install doctor

install doctor:
	@$(MAKE) --no-print-directory -C editor $@
