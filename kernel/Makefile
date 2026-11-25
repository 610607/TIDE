CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Wpedantic
CPPFLAGS += -Isrc
COMMON = src/vm.cpp src/assay.cpp
HEADERS = src/vm.hpp src/assay.hpp
.PHONY: all test bench
all: build/tide
build:
	mkdir -p $@
build/tide: $(COMMON) $(HEADERS) src/pilot.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 $(COMMON) src/pilot.cpp -o $@
build/vm_tests: $(COMMON) $(HEADERS) tests/vm_tests.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 $(COMMON) tests/vm_tests.cpp -o $@
test: build/vm_tests
	./build/vm_tests
bench: build/tick_timing
build/tick_timing: src/vm.cpp src/vm.hpp bench/tick_timing.cpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++20 src/vm.cpp bench/tick_timing.cpp -o $@
