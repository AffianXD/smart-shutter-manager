SHELL := /bin/bash
DEV_ACTIONS := up down restart sync wait logs status clean reset
TEST_ACTIONS := up down restart sync wait logs status review review-clear

ifneq ($(wildcard .playwright-browsers),)
export PLAYWRIGHT_BROWSERS_PATH ?= $(CURDIR)/.playwright-browsers
endif

.PHONY: $(addprefix dev-,$(DEV_ACTIONS)) $(addprefix test-,$(TEST_ACTIONS)) dev-list dev-clean-all test-run

$(addprefix dev-,$(DEV_ACTIONS)):
	@$(if $(value AGENT),,$(error AGENT is required, e.g. make $@ AGENT=codex-1))
	@./scripts/$@.sh "$$HA_MAKE_AGENT" $(if $(filter yes,$(CONFIRM)),--yes,)

# Pass user input as an environment value rather than interpolating it into shell code.
export HA_MAKE_AGENT = $(value AGENT)

$(addprefix test-,$(TEST_ACTIONS)):
	@./scripts/$@.sh $(if $(filter yes,$(CONFIRM)),--yes,)

dev-list:
	@./scripts/dev-list.sh

dev-clean-all:
	@./scripts/dev-clean.sh --all $(if $(filter yes,$(CONFIRM)),--yes,)

test-run:
	@./scripts/test-wait.sh
	@python3 -m unittest discover -s tests/local_ha -v
	@.venv/bin/python -m pytest -q
	@npm run check:card
	@npm run test:card
	@node scripts/ha_ui_check.cjs test
