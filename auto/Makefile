# Shared AUTO-07p model-core build helpers.
#
# The evaluator does not run AUTO continuation; it compiles with ordinary
# gfortran so tests and scripts can compare the Fortran model core to Python
# before episode-specific AUTO runs are introduced.

FC = gfortran
FFLAGS ?= -O2 -Wall -Wextra -Werror -std=f2008
SRC_DIR := src
BUILD_DIR := build
BIN_DIR := bin
EVALUATOR := $(BIN_DIR)/bs2026_evaluator
SOURCES := $(SRC_DIR)/bs2026_constants.f90 $(SRC_DIR)/bs2026_model.f90 $(SRC_DIR)/bs2026_evaluator.f90

.PHONY: all clean check-auto smoke

all: $(EVALUATOR)

$(EVALUATOR): $(SOURCES) | $(BUILD_DIR) $(BIN_DIR)
	$(FC) $(FFLAGS) -J$(BUILD_DIR) -I$(BUILD_DIR) $(SOURCES) -o $@

$(BUILD_DIR) $(BIN_DIR):
	mkdir -p $@

check-auto:
	@test -x /usr/local/bin/auto || { echo "AUTO-07p executable not found at /usr/local/bin/auto"; exit 1; }
	@/usr/local/bin/auto --help >/dev/null 2>&1 || true
	@echo "AUTO-07p executable found at /usr/local/bin/auto"

smoke: $(EVALUATOR)
	$(EVALUATOR) coefficients 30000 225 0.1 1
	$(EVALUATOR) rhs 30000 225 0.1 1 1.0e4 1.0e-6 1.4

clean:
	rm -rf $(BUILD_DIR) $(EVALUATOR)
