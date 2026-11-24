// Phase 2: resolve intents in keyed-hash order, then run physics and wick checks.
// Ordering keys are (target, keyed hash of origin slot, origin slot), so outcomes do not
// depend on storage order.

#include "ps_core.hpp"

#include <algorithm>
#include <tuple>

namespace ps {

namespace {

template <typename Pred, typename KeyFn>
std::vector<uint32_t> ordered(const std::vector<Intent>& intents, Pred keep, KeyFn sort_key) {
  std::vector<uint32_t> idx;
  for (uint32_t i = 0; i < intents.size(); ++i) {
    if (keep(intents[i])) idx.push_back(i);
  }
  std::sort(idx.begin(), idx.end(),
            [&](uint32_t x, uint32_t y) { return sort_key(x) < sort_key(y); });
  return idx;
}

} // namespace

void World::run(uint64_t ticks) {
  for (uint64_t i = 0; i < ticks; ++i) step();
}

size_t World::active_count() const {
  return static_cast<size_t>(
      std::count_if(act_.begin(), act_.end(), [](const Activation& a) { return a.on; }));
}

int World::active_at(int32_t site) const {
  int n = 0;
  for (int k = 0; k < cfg_.act_cap; ++k) n += act_[site * cfg_.act_cap + k].on;
  return n;
}

int32_t World::free_slot(int32_t site) const {
  for (int k = 0; k < cfg_.act_cap; ++k) {
    if (!act_[site * cfg_.act_cap + k].on) return site * cfg_.act_cap + k;
  }
  return -1;
}

void World::step() {
  rotate_blocks();
  std::vector<Intent> intents;
  const int32_t slots = static_cast<int32_t>(act_.size());
  for (int32_t s = 0; s < slots; ++s) {
    if (act_[s].on) intents.push_back(plan(s));
  }
  fresh_.assign(act_.size(), false);
  births_log_.clear();
  mass_refusals_.clear();
  pay_energy(intents);
  apply_writes(intents);
  apply_walls(intents);
  apply_arrivals(intents);
  commit(intents);
  diffuse();
  hydrolyze();
  erode();
  feed_energy();
  check_wicks();
  tick_ += 1;
}

// Activations pay from their site's energy in keyed order: basal first (failing it ends
// the activation), then the instruction price. If the price is unaffordable the action is
// dropped; with stall_fail the activation still advances, otherwise it waits.
void World::pay_energy(std::vector<Intent>& intents) {
  const auto idx = ordered(
      intents, [](const Intent&) { return true; },
      [&](uint32_t i) {
        return std::make_tuple(intents[i].origin_site, intents[i].key, intents[i].origin);
      });
  for (uint32_t i : idx) {
    Intent& it = intents[i];
    int32_t& e = energy_[it.origin_site];
    if (e < cfg_.e_basal) {
      act_[it.origin].on = false;
      stats_.deaths_starve += 1;
      continue;
    }
    e -= cfg_.e_basal;
    energy_spent_ += cfg_.e_basal;
    if (e < it.cost) {
      stats_.stalls += 1;
      if (cfg_.stall_fail) {
        it.act = Act::None;
        it.paid = true; // advance registers without acting or paying the price
      }
      continue;
    }
    e -= it.cost;
    energy_spent_ += it.cost;
    it.paid = true;
    stats_.instructions += 1;
    if (it.read_walled) stats_.reads_walled += 1;
    if (it.operand_inert) stats_.operand_inert += 1;
  }
}

// Whether a write arriving from a neighbor may replace `old` with `byte`.
bool World::ext_allowed(uint8_t old, uint8_t byte) const {
  if (old == INERT || old == byte) return true;
  switch (cfg_.ext_write) {
    case ExtWrite::Allow: return true;
    case ExtWrite::FillOnly: return false;
    case ExtWrite::FillErase: return byte == INERT;
  }
  return false;
}

void World::apply_writes(std::vector<Intent>& intents) {
  const auto idx = ordered(
      intents, [](const Intent& it) { return it.paid && it.act == Act::Write; },
      [&](uint32_t i) {
        const Intent& it = intents[i];
        return std::make_tuple(it.site, it.offset, it.key, it.origin);
      });
  int32_t last_site = -1;
  int last_offset = -1;
  for (uint32_t i : idx) {
    const Intent& it = intents[i];
    if (it.site == last_site && it.offset == last_offset) {
      stats_.write_conflict += 1;
      continue;
    }
    last_site = it.site;
    last_offset = it.offset;
    if (it.dir != kSelf) note_copy_write(it.origin_site, it.site, it.dir);
    if (it.dir != kSelf &&
        !crosses(it.origin_site, it.dir, kWriteWall, static_cast<uint64_t>(it.origin))) {
      stats_.write_walled += 1;
      continue;
    }
    if (it.dir != kSelf && cfg_.ext_active == ExtActive::Refuse && active_at(it.site) > 0) {
      stats_.ext_active_blocked += 1;
      continue;
    }
    uint8_t& slot = site_ptr(it.site)[it.offset];
    const uint8_t old = slot;
    if (it.dir != kSelf && !ext_allowed(old, it.byte)) {
      stats_.ext_blocked += 1;
      continue;
    }
    if (it.dir != kSelf && old != INERT && it.byte == INERT) stats_.ext_erasures += 1;
    if (old == INERT && it.byte != INERT) {
      if (free_[it.site] == 0) {
        stats_.write_no_mass += 1;
        if (log_mass_refusals_ && it.dir != kSelf) mass_refusals_.push_back(it.origin_site);
        continue;
      }
      free_[it.site] -= 1;       // polymerization embeds one monomer
    } else if (old != INERT && it.byte == INERT) {
      free_[it.site] += 1;       // erasure releases the monomer
      stats_.erasures += 1;
    } else if (old != INERT && old != it.byte) {
      stats_.overwrites += 1;    // substitution: matter unchanged
    }
    if (cfg_.bond_store && old != it.byte) {
      if (it.byte != INERT) energy_spent_ -= cfg_.e_bond; // paid e_bond now held by the bond
      if (old != INERT) energy_[it.site] += cfg_.e_bond;  // broken bond releases in place
    }
    slot = it.byte;
    last_write_[it.site] = static_cast<int64_t>(tick_);
    stats_.writes += 1;
    const size_t at = static_cast<size_t>(it.site) * cfg_.site_len + it.offset;
    writer_[at] = body_[it.origin_site];
    written_at_[at] = tick_;
  }
}

void World::note_copy_write(int32_t origin_site, int32_t site, uint8_t dir) {
  if (copy_to_[origin_site] < 0) stats_.copies_started += 1;
  copy_to_[origin_site] = body_[site];
  copy_dir_[origin_site] = dir;
}

void World::apply_walls(std::vector<Intent>& intents) {
  const auto idx = ordered(
      intents,
      [](const Intent& it) { return it.paid && (it.act == Act::Wall || it.act == Act::Unwall); },
      [&](uint32_t i) {
        const Intent& it = intents[i];
        return std::make_tuple(it.site, it.dir, it.key, it.origin);
      });
  for (uint32_t i : idx) {
    const Intent& it = intents[i];
    uint8_t& w = wall_[it.site * kDirs + it.dir];
    if (it.act == Act::Unwall) {
      if (w == 0) continue;
      w -= 1;
      free_[it.site] += 1;
      continue;
    }
    if (w >= cfg_.w_max || free_[it.site] == 0) continue;
    w += 1;
    free_[it.site] -= 1;
    stats_.walls_built += 1;
  }
}

// An ignition needs a free slot at the target, a non-inert byte at the target offset, and a
// passing crossing when the target is a neighbor. The new activation runs from next tick.
void World::apply_arrivals(std::vector<Intent>& intents) {
  const auto idx = ordered(
      intents, [](const Intent& it) { return it.paid && it.act == Act::Ignite; },
      [&](uint32_t i) {
        const Intent& it = intents[i];
        return std::make_tuple(it.site, it.key, it.origin);
      });
  for (uint32_t i : idx) {
    const Intent& it = intents[i];
    // Copy observer: a paid ignition into a neighbor ends the emitting activation's copy.
    const int32_t o = it.origin_site;
    const bool copy_ends = it.dir != kSelf && copy_to_[o] >= 0;
    const bool was_cut = copy_cut_[o] != 0;
    if (copy_ends) {
      copy_to_[o] = -1;
      copy_cut_[o] = 0;
    }
    const bool passes = it.dir == kSelf ||
        crosses(it.origin_site, it.dir, kIgniteWall, static_cast<uint64_t>(it.origin));
    const int32_t slot = free_slot(it.site);
    if (!passes || site_ptr(it.site)[it.offset] == INERT || slot < 0) {
      stats_.ignite_fail += 1;
      continue;
    }
    fresh_[slot] = true;
    act_[slot] = Activation{true, it.offset};
    if (copy_ends) {
      stats_.copies_born += 1;
      stats_.copies_born_cut += was_cut;
    }
    copy_to_[it.site] = -1;  // the new activation starts with no copy
    copy_cut_[it.site] = 0;
    if (it.site != it.origin_site) lineage_[it.site] = lineage_[it.origin_site];
    stats_.births += 1;
    births_log_.push_back(observe_birth(it.origin_site, it.site));
    for (int k = 0; k < cfg_.site_len; ++k) {
      stats_.birth_hamming += site_ptr(it.site)[k] != site_ptr(it.origin_site)[k];
    }
  }
}

World::Birth World::observe_birth(int32_t parent, int32_t child) {
  Birth b{parent, child, 0, 0};
  const size_t base = static_cast<size_t>(child) * cfg_.site_len;
  for (int k = 0; k < cfg_.site_len; ++k) {
    const int32_t wr = writer_[base + k];
    if (wr >= 0 && static_cast<int64_t>(written_at_[base + k]) > ignited_at_[child]) {
      (wr == body_[parent] ? b.by_parent : b.by_other) |= uint64_t{1} << k;
    }
    if (code_[base + k] == INERT) continue;
    b.code += 1;
    b.written += writer_[base + k] == body_[parent] &&
                 static_cast<int64_t>(written_at_[base + k]) > ignited_at_[child];
  }
  ignited_at_[child] = static_cast<int64_t>(tick_);
  return b;
}

void World::commit(const std::vector<Intent>& intents) {
  for (const Intent& it : intents) {
    if (it.paid && act_[it.origin].on && !fresh_[it.origin]) act_[it.origin] = it.next;
  }
}

// An activation ceases when its active byte has become inert.
void World::check_wicks() {
  const int32_t slots = static_cast<int32_t>(act_.size());
  for (int32_t s = 0; s < slots; ++s) {
    if (act_[s].on && site_ptr(slot_site(s))[act_[s].ip] == INERT) {
      act_[s].on = false;
      stats_.deaths_wick += 1;
    }
  }
}

} // namespace ps
