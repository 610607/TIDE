CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/trait-lineage
VM = ../../src

.PHONY: all test
all: $(BUILD)/field
$(BUILD)/field: field.cpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp
	mkdir -p "$(BUILD)"
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp field.cpp -o "$@"
test: $(BUILD)/field
	$(BUILD)/field --test
