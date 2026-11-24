CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/template-pulse
VM = ../../src

.PHONY: all
all: $(BUILD)/pulse

$(BUILD):
	mkdir -p "$@"

$(BUILD)/vm.%: $(VM)/vm.% vm.%.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" "vm.$*.patch"
	mv "$@.tmp" "$@"

$(BUILD)/pulse: pulse.cpp ../vacancy-01/common.hpp $(BUILD)/vm.hpp $(BUILD)/vm.cpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp pulse.cpp -o "$@"
