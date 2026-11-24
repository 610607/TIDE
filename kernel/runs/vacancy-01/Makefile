CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= ../../build/vacancy
VM = ../../src

.PHONY: all test
all: $(BUILD)/scan $(BUILD)/fork $(BUILD)/natural $(BUILD)/field $(BUILD)/observe

$(BUILD):
	mkdir -p "$@"

$(BUILD)/scan: scan.cpp common.hpp $(VM)/vm.cpp $(VM)/vm.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp scan.cpp -o "$@"

$(BUILD)/vm.hpp: release-api.patch priority-api.patch $(VM)/vm.hpp | $(BUILD)
	patch -s -o "$@.release" $(VM)/vm.hpp release-api.patch
	patch -s -o "$@.tmp" "$@.release" priority-api.patch
	mv "$@.tmp" "$@"

$(BUILD)/vm.cpp: $(VM)/vm.cpp priority-step.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" priority-step.patch
	mv "$@.tmp" "$@"

$(BUILD)/fork: fork.cpp common.hpp release.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp release.cpp fork.cpp -o "$@"

$(BUILD)/natural.cpp: ../geometry-01/fork.cpp natural-range.patch | $(BUILD)
	patch -s -o "$@.tmp" "$<" natural-range.patch
	mv "$@.tmp" "$@"

$(BUILD)/natural: $(BUILD)/natural.cpp $(VM)/vm.cpp $(VM)/vm.hpp $(VM)/assay.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp $(BUILD)/natural.cpp -o "$@"

$(BUILD)/field: ../geometry-01/field.cpp $(VM)/vm.cpp $(VM)/vm.hpp $(VM)/assay.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp $< -o "$@"

$(BUILD)/observe: ../horizon-01/observe.cpp $(VM)/vm.cpp $(VM)/vm.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(VM) $(VM)/vm.cpp $< -o "$@"

test: $(BUILD)/intervention-test
	$(BUILD)/intervention-test

$(BUILD)/intervention-test: test.cpp common.hpp release.cpp $(BUILD)/vm.cpp $(BUILD)/vm.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) $(BUILD)/vm.cpp release.cpp test.cpp -o "$@"
