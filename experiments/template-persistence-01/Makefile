CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= build
BASE = ../template-pool-01/pool.cpp
.PHONY: all test
all: $(BUILD)/persist
# The first study's proposal, guide choice and attachment engine are used verbatim.
$(BUILD)/chamber.hpp: $(BASE)
	mkdir -p "$(BUILD)"
	awk '/^Chamber run\(/{exit} {print} END{print "}"}' "$<" > "$@"
$(BUILD)/persist: persist.cpp $(BUILD)/chamber.hpp
	$(CXX) $(CXXFLAGS) -std=c++20 -I$(BUILD) persist.cpp -o "$@"
test: $(BUILD)/persist
	$(BUILD)/persist --test
