#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace tide {
constexpr int capacity = 32;
using Tick = std::uint64_t;

enum class Bank { free, reserved, occupied };
enum class Boundary { bounded, torus };
enum class Placement { directed, first_free };
enum class Reclamation { retain, empty };
enum class Schedule { synchronous_next_tick };
enum class Arbitration { coordinate_priority };
enum class Mutation { copy_substitution };

struct Access {
    bool read = false;
    bool fetch = false;
    bool operator==(const Access&) const = default;
};

struct Config {
    int width = 5, height = 5;
    Boundary boundary = Boundary::bounded;
    Placement placement = Placement::directed;
    Reclamation reclamation = Reclamation::retain;
    Schedule schedule = Schedule::synchronous_next_tick;
    Arbitration arbitration = Arbitration::coordinate_priority;
    Mutation mutation = Mutation::copy_substitution;
    Access access;
    unsigned max_age = 0, mutation_ppm = 0;
    Tick seed = 1;
};

struct Cpu {
    int bank = -1, pc = 0, resume = -1, bearing = 1; // N, E, S, W
    int source = -1, read = 0, target = -1, written = 0;
};

struct Site {
    Bank kind = Bank::free;
    std::string bytes;
    int owner = -1;
    Tick born = 0;
    Cpu cpu;
};

enum class Effect {
    advance, reserve, busy, jump, denied_jump, resume, copy, failed_copy,
    loop, birth, failed_division, park, bad_fetch, death
};
const char* name(Effect effect);

struct Contact {
    int site = -1;
    Bank kind = Bank::free;
    Tick born = 0;
    int reservation_owner = -1;
    std::string bytes;
};

// Addresses and supplier bytes refer to the opening snapshot.
struct Event {
    Tick tick = 0, actor_born = 0;
    int actor = -1, fetch_site = -1, pc = -1, op = -1;
    int read_site = -1, read_offset = -1, target = -1, write_offset = -1;
    int input = -1, output = -1;
    Effect effect = Effect::advance;
    Contact fetch_contact, read_contact;
    std::string product;
};

class World {
public:
    explicit World(Config config);
    const Config& config() const { return cfg_; }
    Tick tick() const { return tick_; }
    int size() const { return static_cast<int>(sites_.size()); }
    int index(int x, int y) const;
    int neighbor(int origin, int direction) const;
    const Site& at(int site) const { return sites_.at(site); }
    void seed_site(int site, std::string bytes, int pc = 0, int bearing = 1);
    void set_access(int site, Access access);
    // Analysis override for paired knockout assays: same-length bytes for an occupied bank.
    void replace_bytes(int site, std::string bytes);
    // Analysis overrides for residue-cleared forks: empty every free bank and zero every
    // reservation's unwritten offsets; set the reclamation rule used by later releases.
    void clear_residue();
    void set_reclamation(Reclamation policy);
    void step(std::vector<Event>* events = nullptr, bool reverse = false);
    std::string state() const;
    std::string dynamics() const; // Exact cycle key when age and mutation are disabled.
    std::string hash() const;
    void check() const;
private:
    Config cfg_;
    Tick tick_ = 0;
    std::vector<Site> sites_;
    std::vector<Access> access_;
    std::string serialize(bool include_time) const;
    int placement(int origin, int bearing) const;
    char copied(char byte, int origin, int offset) const;
};
}
