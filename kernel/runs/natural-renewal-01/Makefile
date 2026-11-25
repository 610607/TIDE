CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/natural-renewal
VM = ../../src
PREV = ../trait-lineage-01

.PHONY: all test
all: $(BUILD)/field
$(BUILD)/history.hpp: $(PREV)/field.cpp
	mkdir -p "$(BUILD)"
	awk '/^int main\(/{exit} {print}' "$<" > "$@"
$(BUILD)/field: field.cpp $(BUILD)/history.hpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) -I$(PREV) -I$(VM) $(VM)/vm.cpp field.cpp -o "$@"
test: $(BUILD)/field
	$(BUILD)/field --test
	python3 -B controls.py
