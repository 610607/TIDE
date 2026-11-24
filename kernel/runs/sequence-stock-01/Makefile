CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/sequence-stock
VM = ../../src

.PHONY: all
all: $(BUILD)/census

$(BUILD)/census: census.cpp ../vacancy-01/common.hpp $(VM)/vm.cpp $(VM)/vm.hpp
	mkdir -p "$(BUILD)"
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp census.cpp -o "$@"
