CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/vacancy
VM = ../../src

.PHONY: all test
all: $(BUILD)/scan $(BUILD)/fork

$(BUILD):
	mkdir -p "$@"

$(BUILD)/scan: scan.cpp common.hpp $(VM)/vm.cpp $(VM)/vm.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp scan.cpp -o "$@"

$(BUILD)/vm.hpp: release-api.patch $(VM)/vm.hpp | $(BUILD)
	patch -s -o "$@.tmp" $(VM)/vm.hpp release-api.patch
	mv "$@.tmp" "$@"

$(BUILD)/vm.cpp: $(VM)/vm.cpp | $(BUILD)
	cp "$<" "$@"

$(BUILD)/fork: fork.cpp common.hpp release.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp release.cpp fork.cpp -o "$@"

test: $(BUILD)/intervention-test
	$(BUILD)/intervention-test

$(BUILD)/intervention-test: test.cpp common.hpp release.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp release.cpp test.cpp -o "$@"
