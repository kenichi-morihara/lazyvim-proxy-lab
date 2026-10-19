.DEFAULT_GOAL := install
.PHONY: install doctor setup-tailscale

install:
	@./scripts/bootstrap $(if $(filter 1,$(COPY)),--copy,)

doctor:
	@./scripts/doctor

# Optional: invoke explicitly; never a dependency of install or doctor.
setup-tailscale:
	@./scripts/_run-installer setup-tailscale
