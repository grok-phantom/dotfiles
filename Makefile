.PHONY: test
SUITE ?= all
REPORT_DIR ?=
test:
	@PYTHON="$(PYTHON)" ./scripts/test "$(SUITE)" $(if $(REPORT_DIR),--report-dir "$(REPORT_DIR)")
