CXX ?= c++
CXXFLAGS ?= -O2 -Wall -Wextra -Werror
BUILD ?= build
.PHONY: all test
all: $(BUILD)/pool
$(BUILD)/pool: pool.cpp
	mkdir -p "$(BUILD)"
	$(CXX) $(CXXFLAGS) -std=c++20 "$<" -o "$@"
test: $(BUILD)/pool
	$(BUILD)/pool --test
