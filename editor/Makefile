.DEFAULT_GOAL := install

OPTIONAL_TARGETS := setup-pi configure-pi doctor-pi setup-tailscale
.PHONY: help install doctor init-pi $(OPTIONAL_TARGETS)

help:
	@printf '%s\n' 'Editor:' \
	  '  make                         Install Neovim and development tools' \
	  '  make doctor                  Check editor prerequisites without installing' \
	  '' 'Pi (optional, Responses by default):' \
	  '  make init-pi                 Install Pi, then interactively save connection settings' \
	  '  make configure-pi            Update saved connection settings' \
	  '  make doctor-pi               Check Pi configuration without network requests' \
	  '  make doctor-pi PROBE=1       Probe the API tool protocol without executing tools' \
	  '  make setup-pi                Install/reinstall Pi without changing connection settings' \
	  '' 'Remote access (optional):' \
	  '  make setup-tailscale         Start Tailscale and log in' \
	  '' 'Options: COPY=1, BUILD_JOBS=1, PYTHON=python3.11, EDITOR_PREFIX=/path'

install:
	@./scripts/bootstrap $(if $(filter 1,$(COPY)),--copy,)

doctor:
	@./scripts/doctor

# Installation must finish before prompting, including with make -j.
init-pi: setup-pi
	@./scripts/_run-installer configure-pi

# None of these are dependencies of the normal editor installation.
$(OPTIONAL_TARGETS):
	@./scripts/_run-installer $@
