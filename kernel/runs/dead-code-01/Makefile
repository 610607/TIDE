CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Wpedantic -Werror
BUILD ?= ../../build/dead-code
VM = ../../src

.PHONY: all test
all: $(BUILD)/study
$(BUILD)/study: study.cpp $(VM)/vm.cpp $(VM)/vm.hpp
	mkdir -p "$(BUILD)"
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp study.cpp -o "$@"
test: $(BUILD)/study
	$(BUILD)/study --controls
