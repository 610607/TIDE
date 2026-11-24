CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/handoff-window
VM = ../../src
BEARING = ../bearing-handoff-01

.PHONY: all test
all: $(BUILD)/observe
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.%: $(VM)/vm.% $(BEARING)/vm.%.patch | $(BUILD)
	patch -s -o "$@" "$<" < "$(BEARING)/vm.$*.patch"
$(BUILD)/observe: observe.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp ../spatial-transport-01/transport.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp observe.cpp -o "$@"
$(BUILD)/controls: $(BEARING)/controls.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp $(BEARING)/controls.cpp -o "$@"
test: $(BUILD)/controls
	$(BUILD)/controls
