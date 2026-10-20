.DEFAULT_GOAL := install

# Editor commands are also available when editor/ is copied on its own.
EDITOR_TARGETS := install doctor init-pi setup-pi configure-pi doctor-pi setup-tailscale
LAB_TARGETS := pi-lab pi-demo
.PHONY: help $(EDITOR_TARGETS) $(LAB_TARGETS)

$(EDITOR_TARGETS):
	@$(MAKE) --no-print-directory -C editor $@

help:
	@$(MAKE) --no-print-directory -C editor help
	@printf '%s\n' '' 'Lab (repository root only):' \
	  '  make pi-lab                  Start the local mock company API' \
	  '  make pi-demo                 Run mock Pi tests in the restricted dev container'

# Lab commands stay outside the standalone editor.
pi-lab:
	@python3 lab/ai/server.py

pi-demo:
	@./lab/lab up
	@./lab/lab exec 'dev bash -lc "cd /workspace && EDITOR_PREFIX=/tmp/pi-demo-tools make setup-pi && EDITOR_PI_TEST_PREFIX=/tmp/pi-demo-tools python3.11 tests/company_pi_test.py"'
