CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/transport-handoff
PREV = ../spatial-transport-01
VM = ../../src

.PHONY: all test
all: $(BUILD)/field
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"
$(BUILD)/vm.hpp: $(VM)/vm.hpp | $(BUILD)
	awk '{print} /^class World [{]/ {print "    friend struct SpatialExperiment;"}' "$<" > "$@"
$(BUILD)/field.cpp: $(PREV)/field.cpp field.cpp.patch | $(BUILD)
	patch -s -o "$@" "$<" < field.cpp.patch
$(BUILD)/field: $(BUILD)/field.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp $(PREV)/transport.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) -I$(PREV) $(BUILD)/vm.cpp $(BUILD)/field.cpp -o "$@"
test: $(BUILD)/field
	$(BUILD)/field --test
