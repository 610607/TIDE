CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/bearing-handoff
PREV = ../spatial-transport-01
VM = ../../src

.PHONY: all test
all: $(BUILD)/field
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.%: $(VM)/vm.% vm.%.patch | $(BUILD)
	patch -s -o "$@" "$<" < "vm.$*.patch"
$(BUILD)/field.cpp: $(PREV)/field.cpp field.cpp.patch | $(BUILD)
	patch -s -o "$@" "$<" < field.cpp.patch
$(BUILD)/field: $(BUILD)/field.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp $(PREV)/transport.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) -I$(PREV) $(BUILD)/vm.cpp $(BUILD)/field.cpp -o "$@"
$(BUILD)/controls: controls.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp controls.cpp -o "$@"
test: $(BUILD)/controls
	$(BUILD)/controls
