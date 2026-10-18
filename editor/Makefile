.DEFAULT_GOAL := install
.PHONY: install doctor

install:
	@./scripts/bootstrap $(if $(filter 1,$(COPY)),--copy,)

doctor:
	@./scripts/doctor
