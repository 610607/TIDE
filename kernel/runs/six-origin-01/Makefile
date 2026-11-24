CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/six-origin
VM = ../../src

.PHONY: all
all: $(BUILD)/reference $(BUILD)/field $(BUILD)/lifetime

$(BUILD):
	mkdir -p "$@"

$(BUILD)/field.cpp: ../geometry-01/field.cpp field.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" field.patch
	mv "$@.tmp" "$@"

$(BUILD)/lifetime.cpp: ../geometry-01/fork.cpp ../inheritance-01/lifetime.patch lifetime.patch | $(BUILD)
	patch -s -o "$@.base" "$<" ../inheritance-01/lifetime.patch
	patch -s -o "$@.tmp" "$@.base" lifetime.patch
	mv "$@.tmp" "$@"

$(BUILD)/reference: reference.cpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp "$<" -o "$@"

$(BUILD)/%: $(BUILD)/%.cpp $(VM)/vm.cpp $(VM)/vm.hpp $(VM)/assay.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp "$<" -o "$@"
