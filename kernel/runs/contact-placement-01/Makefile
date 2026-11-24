CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/contact-placement
VM = ../../src
BEARING = ../bearing-handoff-01

.PHONY: all test
all: $(BUILD)/trial
$(BUILD):
	mkdir -p "$@"
$(BUILD)/vm.%: $(VM)/vm.% $(BEARING)/vm.%.patch | $(BUILD)
	patch -s -o "$@" "$<" < "$(BEARING)/vm.$*.patch"
$(BUILD)/trial: trial.cpp match.hpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp ../spatial-transport-01/transport.hpp ../vacancy-01/common.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp trial.cpp -o "$@"
test: $(BUILD)/trial
	$(BUILD)/trial --test
