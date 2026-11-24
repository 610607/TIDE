CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/spatial-transport
VM = ../../src

.PHONY: all test
all: $(BUILD)/field
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"
$(BUILD)/vm.hpp: $(VM)/vm.hpp | $(BUILD)
	awk '{print} /^class World [{]/ {print "    friend struct SpatialExperiment;"}' "$<" > "$@"
$(BUILD)/field: field.cpp transport.hpp ../vacancy-01/common.hpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp field.cpp -o "$@"
test: $(BUILD)/field
	$(BUILD)/field --test
