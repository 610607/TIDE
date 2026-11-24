CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/inheritance
VM = ../../src

.PHONY: all
all: $(BUILD)/reference $(BUILD)/lifetime $(BUILD)/natural.py

$(BUILD):
	mkdir -p "$@"

$(BUILD)/reference.cpp: ../placement-01/reference.cpp reference.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" reference.patch
	mv "$@.tmp" "$@"

$(BUILD)/reference: $(BUILD)/reference.cpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I../placement-01 -I$(VM) $(VM)/vm.cpp "$<" -o "$@"

$(BUILD)/natural.py: ../placement-01/natural.py natural.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" natural.patch
	mv "$@.tmp" "$@"

$(BUILD)/lifetime.cpp: ../geometry-01/fork.cpp lifetime.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" lifetime.patch
	mv "$@.tmp" "$@"

$(BUILD)/lifetime: $(BUILD)/lifetime.cpp $(VM)/vm.cpp $(VM)/vm.hpp $(VM)/assay.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp "$<" -o "$@"
