CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/read-variants
VM = ../../src

.PHONY: all
all: $(BUILD)/variants

$(BUILD):
	mkdir -p "$@"

$(BUILD)/vm.hpp: $(VM)/vm.hpp setup.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" setup.patch
	mv "$@.tmp" "$@"

$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"

$(BUILD)/variants: variants.cpp ../vacancy-01/common.hpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp variants.cpp -o "$@"
