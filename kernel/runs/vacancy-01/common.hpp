#pragma once
#include "vm.hpp"

#include <algorithm>
#include <array>
#include <fstream>
#include <stdexcept>
#include <string_view>
#include <tuple>

namespace vacancy {
constexpr std::string_view reader = "RSCLD";
constexpr int field_end = 2048, follow_ticks = 512;

inline void require(bool ok, const char* msg) {
    if (!ok) throw std::runtime_error(msg);
}
inline tide::World initial(int seed) {
    tide::Config c;
    c.width = 16; c.height = 4; c.seed = seed; c.max_age = 80; c.mutation_ppm = 20000;
    c.boundary = tide::Boundary::torus; c.placement = tide::Placement::first_free; c.access.read = true;
    tide::World w(c);
    w.seed_site(36, "R.CLD");
    return w;
}
inline std::string hex(std::string_view bytes) {
    constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (unsigned char c : bytes) {
        out += digits[c >> 4]; out += digits[c & 15];
    }
    return out;
}
inline const char* kind(tide::Bank type) {
    if (type == tide::Bank::occupied) return "occupied";
    if (type == tide::Bank::reserved) return "reserved";
    return "free";
}
inline bool can_release(const tide::Site& s) {
    return s.kind == tide::Bank::occupied && s.cpu.target == -1;
}
inline int free_neighbors(const tide::World& w, int site) {
    int free = 0;
    for (int d = 0; d < 4; ++d) free += w.at(w.neighbor(site,d)).kind == tide::Bank::free;
    return free;
}
inline std::vector<int> eligible_sites(const tide::World& w, int site) {
    std::vector<int> options;
    for (int d : {0,2,3}) {
        int neighbor = w.neighbor(site,d);
        if (can_release(w.at(neighbor))) options.push_back(neighbor);
    }
    return options;
}
inline std::ofstream output(const std::string& dir, const char* filename, const char* header) {
    std::ofstream out(dir + "/" + filename);
    out.exceptions(std::ios::badbit | std::ios::failbit);
    out << header << '\n';
    return out;
}
inline std::string site_list(const std::vector<int>& ids) {
    std::string s;
    for (int id : ids) {
        if (!s.empty()) s += ',';
        s += std::to_string(id);
    }
    return s.empty() ? "-" : s;
}
}
