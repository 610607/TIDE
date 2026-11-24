CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/lineage
VM = ../../src

all: $(BUILD)/direction

$(BUILD):
	mkdir -p "$@"

$(BUILD)/vm.hpp: $(VM)/vm.hpp direction.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" direction.patch
	mv "$@.tmp" "$@"

$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"

$(BUILD)/direction: direction.cpp ../vacancy-01/common.hpp $(BUILD)/vm.hpp $(BUILD)/vm.cpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp direction.cpp -o "$@"
