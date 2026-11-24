#pragma once

#include "vm.hpp"

#include <functional>

namespace tide {
inline constexpr char ancestor[] = "R.CLD";
struct Assay {
    int generations = 0;
    int generations_using_channel = 0;
    int elapsed = 0;
    bool cycle = false;
};
using FocalTrace = std::function<void(int, const Event&)>;
Assay assay(std::string focal, const std::string& donor, int direction, Access arm,
            Access focal_access, int donor_pc = 0, const FocalTrace& trace = {});
}
