CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/partner-placement
VM = ../../src
PREV = ../trait-lineage-01

.PHONY: all
all: $(BUILD)/field
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"
$(BUILD)/vm.hpp: $(VM)/vm.hpp | $(BUILD)
	awk '{print} /^class World [{]/ {print "    friend struct SpatialExperiment;\n    friend struct PartnerPlacement;"}' "$<" > "$@"
# Reuse the versioned founder, byte tracing and full-lifetime permission assay verbatim.
$(BUILD)/lifetime.hpp: $(PREV)/field.cpp | $(BUILD)
	awk '/^struct Field [{]/{exit} {print} END{print "}"}' "$<" > "$@"
$(BUILD)/field: field.cpp ../spatial-transport-01/transport.hpp ../vacancy-01/common.hpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp $(BUILD)/lifetime.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) -I$(PREV) $(BUILD)/vm.cpp field.cpp -o "$@"
