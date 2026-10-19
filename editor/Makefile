.DEFAULT_GOAL := install
.PHONY: install doctor setup-tailscale setup-pi doctor-pi

install:
	@./scripts/bootstrap $(if $(filter 1,$(COPY)),--copy,)

doctor:
	@./scripts/doctor

# Optional: invoke explicitly; never a dependency of install or doctor.
setup-tailscale:
	@./scripts/_run-installer setup-tailscale

setup-pi:
	@./scripts/_run-installer setup-pi

doctor-pi:
	@./scripts/_run-installer doctor-pi
