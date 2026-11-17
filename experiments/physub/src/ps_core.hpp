#pragma once

// Exploratory physical-substrate prototype (not the TIDE kernel).
// No ownership and no thread entity. Matter is a closed integer ledger (free monomers +
// non-inert code bytes + wall units). Energy is a per-site integer field fed by a uniform
// source. Execution state is the activation state of a site (active byte + registers): it
// pays basal and per-instruction energy from its site and ceases when starved or when its
// active byte becomes inert. Update is two-phase: phase 1 reads the start-of-tick state and
// emits intents; phase 2 resolves them in keyed-hash order, then runs diffusion, decay and
// energy inflow. Keys use site coordinates only.

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace ps {

// Every byte is code and data at once. Byte 0 is INERT (embodies no monomer); any other
// value v decodes as opcode (v - 1) % kOps. Operands are the following bytes, each read as
// an offset (mod site_len) into the executing site. A pointer is the byte pair at an
// offset: [p] is the direction (INERT = own site, v > 0 = neighbor (v - 1) % 4) and [p+1]
// is the offset there. Activations carry only ip; all other state lives in bytes.
enum Op : uint8_t {
  MOV = 0,    // MOV p q : byte at pointer p -> pointer q          (3 bytes)
  INC = 1,    // INC x   : [x] += 1 (mod 256)                       (2 bytes)
  DEC = 2,    // DEC x   : [x] -= 1 (mod 256)
  JZ = 3,     // JZ x    : if [x] is INERT, skip the next instruction
  JMP = 4,    // JMP x   : ip = [x] mod site_len
  RND = 5,    // RND x   : [x] = keyed random non-inert byte
  IGNITE = 6, // IGNITE p: start an activation at pointer p
  WALL = 7,   // WALL x  : deposit a wall unit toward direction [x] (no-op if own site)
  UNWALL = 8, // UNWALL x: retract one unit toward direction [x]
  kOps = 9,
};
inline constexpr uint8_t INERT = 0;

// Independent keyed random streams; every draw is a pure function of
// (seed, tick, stream, identifiers), so results do not depend on iteration order.
enum Stream : uint64_t {
  kOrder = 1, kRnd, kMut, kMutByte, kReadWall, kWriteWall, kIgniteWall,
  kDiffuse, kGuard, kHydro, kErode,
  kEDiffuse, kEGuard,  // appended: earlier streams keep their values
  kWhole, kRotate, kRotWall,
};

inline constexpr uint8_t kDirs = 4;   // N, E, S, W
inline constexpr uint8_t kSelf = 4;   // direction value for own site
inline constexpr int kMinSiteLen = 8;
inline constexpr int kMaxSiteLen = 64;

// Rule for a write that crosses into a neighbor and meets a non-inert byte.
//  Allow     : any change (substitution or erasure)
//  FillOnly  : only INERT bytes can be filled from outside
//  FillErase : fill INERT, or erase to INERT (paying e_erase); no substitution
// A blocked write still pays its price. Writes within a site are unaffected.
enum class ExtWrite : uint8_t { Allow, FillOnly, FillErase };

// Parses "allow" | "fill" | "erase"; returns false on anything else.
inline bool parse_ext_write(const std::string& s, ExtWrite& out) {
  if (s == "allow") out = ExtWrite::Allow;
  else if (s == "fill") out = ExtWrite::FillOnly;
  else if (s == "erase") out = ExtWrite::FillErase;
  else return false;
  return true;
}

struct Config {
  int width = 48;
  int height = 48;
  int site_len = 64;
  int act_cap = 1;             // activation slots per site
  bool stall_fail = false;     // unaffordable action: false = wait, true = fail and advance
  int32_t mass0 = 40;          // initial free monomers per site
  int32_t d_div = 8;           // diffusion divisor; >= 2 * kDirs keeps the floor part stable
  int32_t e0 = 32;             // initial energy per site
  int32_t e_in = 3;            // energy inflow per site per tick
  int32_t e_max = 64;          // energy cap per site
  int32_t e_basal = 1;         // paid by every active site each tick
  int32_t e_op = 1;            // price of an ordinary instruction
  int32_t e_bond = 1;          // bond_store off: extra price to change a non-inert byte;
                               // bond_store on: energy held by each non-inert byte
  ExtWrite ext_write = ExtWrite::Allow;
  int32_t e_erase = 1;         // FillErase: price of erasing a neighbor's byte (replaces
                               // e_bond, or e_act under bond_store)
  // Energy transport and storage; both off reproduce the earlier model exactly.
  bool e_diffuse = false;      // the energy field diffuses like free monomers; walls insulate
  int32_t e_div = 8;           // energy diffusion divisor
  bool bond_store = false;     // forming a bond stores e_bond in the byte; breaking it
                               // (write or hydrolysis) releases e_bond to the byte's site
  int32_t e_act = 1;           // bond_store: barrier paid (dissipated) to break a bond
  int32_t e_ignite = 16;       // price of IGNITE
  int32_t e_wall = 2;          // price of WALL
  uint8_t w_max = 8;           // wall units per half-edge
  double p_mut = 0.0;          // copy error per written byte
  double p_hydro = 1e-5;       // per non-inert byte per tick
  // Diagnostic only, not a candidate rule: hydrolysis rate for bytes of sites with no
  // activation. Negative = same as p_hydro (off).
  double p_dead = -1.0;
  // Diagnostic only: with dead_quiet > 0, p_dead applies only to inactive sites that no
  // write has reached for more than dead_quiet ticks; recently written inactive sites
  // (copies under construction) keep p_hydro. 0 = p_dead applies to every inactive site.
  int32_t dead_quiet = 0;
  double p_erode = 1e-4;      // per wall half-edge per tick (removes one unit)
  // Decay form. false (P): each non-inert byte becomes inert on its own with probability
  // p_hydro per tick. true (M): a site's program decays in one event with probability
  // 1 - (1 - r)^n per tick, n = its non-inert bytes and r = p_hydro (p_dead and dead_quiet
  // select r as in form P); every non-inert byte returns to the site's free monomers, which
  // ends any activation there.
  bool hydro_whole = false;
  // Whole-site mobility by Margolus block rotation. At the start of each tick the lattice is
  // split into 2x2 blocks, offset by (0,0) on even ticks and (1,1) on odd ticks; each block
  // rotates clockwise or counterclockwise with probability p_rot / 2 each. A rotation moves
  // code bytes and activation slots; free monomers, energy and walls stay in place. Each of
  // the block's four internal edges must pass a crossing (1/(W+1)), or the block stays.
  // 0 = off.
  double p_rot = 0.0;
  uint64_t seed = 1;
};

// Activation: which byte of the site is active. No other hidden state.
struct Activation {
  bool on = false;
  uint8_t ip = 0;
};

struct Stats {
  uint64_t instructions = 0;
  uint64_t stalls = 0;           // could not pay the instruction price
  uint64_t deaths_starve = 0;    // activation could not pay basal energy
  uint64_t deaths_wick = 0;      // active byte became inert
  uint64_t births = 0;
  uint64_t birth_hamming = 0;    // summed byte differences, child vs parent site, at ignition
  uint64_t ignite_fail = 0;      // no code at offset 0, target already active, or wall
  uint64_t writes = 0;
  uint64_t overwrites = 0;       // a non-inert byte changed to a different value
  uint64_t erasures = 0;         // a non-inert byte became inert by a write
  uint64_t write_conflict = 0;
  uint64_t write_no_mass = 0;
  uint64_t write_walled = 0;     // stopped while crossing a wall
  uint64_t ext_blocked = 0;      // neighbor write refused by ext_write
  uint64_t ext_erasures = 0;     // neighbor byte erased from outside
  uint64_t reads_walled = 0;
  uint64_t walls_built = 0;
  uint64_t hydrolyzed = 0;
  uint64_t eroded = 0;
  uint64_t whole_decays = 0;         // hydro_whole: programs decayed in one event
  uint64_t whole_decays_active = 0;  // of which the site was active
  uint64_t rotations = 0;            // p_rot: blocks rotated
  uint64_t rot_walled = 0;           // rotations stopped by a wall crossing
  // Copy observer (no effect on dynamics). A copy starts with an activation's first write
  // into a neighbor and ends when that activation emits a paid ignition into a neighbor.
  // A copy is cut when a rotation leaves its last target outside the direction it was
  // written through; the program keeps writing into whatever site now lies there.
  uint64_t copies_started = 0;
  uint64_t copies_cut = 0;
  uint64_t copies_born = 0;          // copies that ended in a birth
  uint64_t copies_born_cut = 0;      // of which cut
};

struct Ledger {
  int64_t free_mass = 0;
  int64_t code_mass = 0;
  int64_t wall_mass = 0;
  int64_t energy = 0;       // field only
  int64_t bond_energy = 0;  // bond_store: e_bond per non-inert byte
  int64_t total_mass() const { return free_mass + code_mass + wall_mass; }
};

enum class Act : uint8_t { None, Write, Ignite, Wall, Unwall };

struct Intent {
  int32_t origin = 0;    // activation slot that emitted the intent
  int32_t origin_site = 0;
  Activation next;       // tentative state, committed only if paid
  int32_t cost = 0;      // energy beyond basal
  Act act = Act::None;
  int32_t site = 0;      // write or ignite target, or wall owner site
  uint8_t offset = 0;
  uint8_t byte = 0;
  uint8_t dir = kSelf;   // direction crossed, kSelf if local
  uint64_t key = 0;
  bool paid = false;
  bool read_walled = false;  // a cross-edge read was stopped by a wall
};

const std::vector<uint8_t>& ancestor();
const std::vector<uint8_t>& polite();
int op_length(uint8_t byte);
std::string disassemble(const std::vector<uint8_t>& bytes);

class World {
public:
  explicit World(const Config& cfg);

  bool seed_program(int x, int y, const std::vector<uint8_t>& program);
  void run(uint64_t ticks);

  const Config& config() const { return cfg_; }
  const Stats& stats() const { return stats_; }
  uint64_t tick() const { return tick_; }
  size_t active_count() const;
  Ledger ledger() const;
  bool ledger_ok() const;
  uint64_t digest() const;
  int32_t site_index(int x, int y) const { return y * cfg_.width + x; }
  int32_t free_mass(int32_t site) const { return free_[site]; }
  void set_free_mass(int32_t site, int32_t v);
  void set_wall(int32_t site, uint8_t dir, uint8_t units);
  void set_energy(int32_t site, int32_t v); // test helper; adjusts the energy total
  std::vector<uint8_t> site_bytes(int32_t site) const;
  bool site_active(int32_t site) const { return active_at(site) > 0; }
  bool place_bytes(int32_t site, const std::vector<uint8_t>& bytes); // no activation

  // Observation only (no effect on dynamics, not in the digest).
  int32_t energy_at(int32_t site) const { return energy_[site]; }
  uint8_t wall_units(int32_t site, uint8_t dir) const { return wall_[site * kDirs + dir]; }
  int first_ip(int32_t site) const;           // ip of the lowest active slot, -1 if none
  uint16_t lineage(int32_t site) const { return lineage_[site]; }
  const uint8_t* bytes_at(int32_t site) const { return site_ptr(site); }
  // code: non-inert bytes at the child; written: those last written by the parent's site
  // after the child's previous ignition (a copy has most bytes written, a re-ignition few).
  // by_parent / by_other: offsets last written by the parent / by any other site after the
  // child's previous ignition (bit k = offset k; site_len <= 64).
  struct Birth {
    int32_t parent; int32_t child; int code; int written;
    uint64_t by_parent = 0, by_other = 0;
  };
  const std::vector<Birth>& births_this_tick() const { return births_log_; }
  // Site moves made by this tick's rotations, as (from, to); observers that index by site
  // apply them before reading this tick's births.
  const std::vector<std::pair<int32_t, int32_t>>& moves_this_tick() const { return moves_log_; }

private:
  Config cfg_;
  uint64_t tick_ = 0;
  std::vector<uint8_t> code_;
  std::vector<int32_t> free_;
  std::vector<int32_t> energy_;
  std::vector<uint8_t> wall_;        // [site * kDirs + dir], deposited by site
  std::vector<Activation> act_;      // [site * act_cap + slot]
  std::vector<bool> fresh_;          // slot filled by an arrival this tick
  std::vector<uint16_t> lineage_;    // observer: founder id inherited at ignition
  uint16_t next_lineage_ = 1;
  std::vector<Birth> births_log_;    // observer: cleared every tick
  std::vector<int32_t> writer_;      // observer: site whose activation last wrote each byte
  std::vector<uint64_t> written_at_; // observer: tick of that write
  std::vector<int64_t> ignited_at_;  // observer: tick of the site's last ignition, -1 if none
  std::vector<int64_t> last_write_;  // dead_quiet: tick of the last applied write into the site
  // Observer: identity of a site's contents, initially its index; moves with rotations so
  // writer_ and copy targets follow contents rather than positions.
  std::vector<int32_t> body_;
  std::vector<int32_t> copy_to_;     // copy observer: body of the last target, -1 if none
  std::vector<uint8_t> copy_dir_;    // direction of that write
  std::vector<uint8_t> copy_cut_;    // copy cut by a rotation
  std::vector<std::pair<int32_t, int32_t>> moves_log_;  // observer: cleared every tick
  Stats stats_;
  int64_t mass_total_ = 0;
  int64_t energy_in_ = 0;            // cumulative inflow
  int64_t energy_spent_ = 0;         // cumulative spending
  int64_t energy_initial_ = 0;
  uint64_t t_hydro_ = 0;
  uint64_t t_dead_ = 0;
  uint64_t t_erode_ = 0;
  uint64_t t_mut_ = 0;
  std::vector<uint64_t> t_whole_;    // hydro_whole: threshold by non-inert count, p_hydro
  std::vector<uint64_t> t_whole_dead_;  // the same for p_dead
  uint64_t t_rot_ = 0;               // per rotation sense

  // geometry and randomness
  int32_t neighbor(int32_t site, uint8_t dir) const;
  uint8_t wrap(int v) const;
  int32_t edge_wall(int32_t site, uint8_t dir) const;
  uint64_t key(uint64_t stream, uint64_t a, uint64_t b = 0) const;
  bool crosses(int32_t site, uint8_t dir, uint64_t stream, uint64_t id) const;
  uint8_t* site_ptr(int32_t s) { return &code_[static_cast<size_t>(s) * cfg_.site_len]; }
  const uint8_t* site_ptr(int32_t s) const { return &code_[static_cast<size_t>(s) * cfg_.site_len]; }

  // phase 1 (ps_exec.cpp)
  int32_t slot_site(int32_t slot) const { return slot / cfg_.act_cap; }
  int32_t free_slot(int32_t site) const;
  int active_at(int32_t site) const;
  Intent plan(int32_t slot) const;
  uint8_t at(int32_t site, int offset) const { return site_ptr(site)[wrap(offset)]; }
  bool pointer(int32_t site, int p, int32_t& target, uint8_t& dir, uint8_t& offset) const;
  void plan_write(int32_t site, int x, uint8_t byte, Intent& it) const;
  void plan_mov(int32_t site, int ip, Intent& it) const;

  // phase 2 (ps_resolve.cpp)
  void step();
  int32_t write_cost(uint8_t old, uint8_t byte, bool ext_erase) const;
  bool ext_allowed(uint8_t old, uint8_t byte) const;
  Birth observe_birth(int32_t parent, int32_t child);
  void pay_energy(std::vector<Intent>& intents);
  void apply_writes(std::vector<Intent>& intents);
  void apply_walls(std::vector<Intent>& intents);
  void apply_arrivals(std::vector<Intent>& intents);
  void note_copy_write(int32_t origin_site, int32_t site, uint8_t dir);
  void commit(const std::vector<Intent>& intents);
  void check_wicks();

  // physics (ps_physics.cpp)
  void diffuse();
  void diffuse_field(std::vector<int32_t>& field, int32_t div, Stream flux_stream,
                     Stream guard_stream);
  void hydrolyze();
  void hydrolyze_whole();
  void erode();
  void rotate_blocks();
  void move_cycle(const int32_t (&s)[4]);
  void check_copy_cuts();
  void feed_energy();
};

} // namespace ps
