CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/placement
VM = ../../src

all: $(BUILD)/placement $(BUILD)/lifetime $(BUILD)/reference

$(BUILD):
	mkdir -p "$@"

$(BUILD)/vm.hpp: $(VM)/vm.hpp setup.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" setup.patch
	mv "$@.tmp" "$@"

$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"

$(BUILD)/placement: placement.cpp ../vacancy-01/common.hpp $(BUILD)/vm.hpp $(BUILD)/vm.cpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp placement.cpp -o "$@"

$(BUILD)/lifetime.cpp: ../geometry-01/fork.cpp range.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" range.patch
	mv "$@.tmp" "$@"

$(BUILD)/lifetime: $(BUILD)/lifetime.cpp $(VM)/vm.cpp $(VM)/vm.hpp $(VM)/assay.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp $< -o "$@"

$(BUILD)/reference: reference.cpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp reference.cpp -o "$@"
