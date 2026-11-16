// Phase 1: each activation reads the start-of-tick state and emits one intent.
// Nothing here mutates shared state; the new ip lives in Intent::next until paid.

#include "ps_core.hpp"

namespace ps {

namespace {

constexpr int kMovLength = 3;
constexpr int kOpLength = 2;
constexpr uint8_t kByteValues = 255; // non-inert byte values 1..255

uint8_t decode(uint8_t byte) { return static_cast<uint8_t>((byte - 1) % kOps); }

} // namespace

int op_length(uint8_t byte) {
  if (byte == INERT) return 1;
  return decode(byte) == MOV ? kMovLength : kOpLength;
}

// Reads the pointer stored at offset p of the site: [p] = direction, [p+1] = offset.
bool World::pointer(int32_t site, int p, int32_t& target, uint8_t& dir, uint8_t& offset) const {
  const uint8_t dv = at(site, p);
  dir = dv == INERT ? kSelf : static_cast<uint8_t>((dv - 1) % kDirs);
  target = dir == kSelf ? site : neighbor(site, dir);
  offset = wrap(at(site, p + 1));
  return true;
}

// Price of changing old -> byte beyond e_op. Without bond_store: a barrier (e_bond, or
// e_erase for an external erasure in FillErase) to change a non-inert byte. With
// bond_store: a barrier (e_act, or e_erase) to break a bond plus e_bond to form one; the
// formed bond keeps its e_bond, a broken one releases e_bond at the byte's site.
int32_t World::write_cost(uint8_t old, uint8_t byte, bool ext_erase) const {
  if (old == byte) return 0;
  const int32_t barrier = old == INERT ? 0 : (ext_erase ? cfg_.e_erase : cfg_.e_bond);
  if (!cfg_.bond_store) return barrier;
  const int32_t brk = old == INERT ? 0 : (ext_erase ? cfg_.e_erase : cfg_.e_act);
  return brk + (byte != INERT ? cfg_.e_bond : 0);
}

void World::plan_write(int32_t site, int x, uint8_t byte, Intent& it) const {
  const uint8_t old = at(site, x);
  it.act = Act::Write;
  it.site = site;
  it.offset = wrap(x);
  it.byte = byte;
  it.dir = kSelf;
  it.cost += write_cost(old, byte, false);
}

void World::plan_mov(int32_t site, int ip, Intent& it) const {
  const uint64_t id = static_cast<uint64_t>(it.origin);
  int32_t src = 0, dst = 0;
  uint8_t sdir = 0, soff = 0, ddir = 0, doff = 0;
  pointer(site, at(site, ip + 1), src, sdir, soff);
  pointer(site, at(site, ip + 2), dst, ddir, doff);
  if (sdir != kSelf && !crosses(site, sdir, kReadWall, id)) {
    it.read_walled = true;
    return;
  }
  uint8_t byte = at(src, soff);
  // Copy error replaces a non-inert byte with a random non-inert one.
  if (byte != INERT && t_mut_ > 0 && (key(kMut, id) >> 32) < t_mut_) {
    byte = static_cast<uint8_t>(1 + key(kMutByte, id) % kByteValues);
  }
  const uint8_t old = at(dst, doff);
  it.act = Act::Write;
  it.site = dst;
  it.offset = doff;
  it.byte = byte;
  it.dir = ddir;
  const bool ext_erase = ddir != kSelf && byte == INERT && cfg_.ext_write == ExtWrite::FillErase;
  it.cost += write_cost(old, byte, ext_erase);
}

Intent World::plan(int32_t slot) const {
  const int32_t site = slot_site(slot);
  Intent it;
  it.origin = slot;
  it.origin_site = site;
  it.next = act_[slot];
  it.cost = cfg_.e_op;
  it.key = key(kOrder, static_cast<uint64_t>(slot));
  const int ip = it.next.ip;
  const uint8_t byte = at(site, ip);
  it.next.ip = wrap(ip + op_length(byte));
  if (byte == INERT) return it; // unreachable: wick check ends such activations
  const int x = at(site, ip + 1);
  switch (decode(byte)) {
    case MOV: plan_mov(site, ip, it); break;
    case INC: plan_write(site, x, static_cast<uint8_t>(at(site, x) + 1), it); break;
    case DEC: plan_write(site, x, static_cast<uint8_t>(at(site, x) - 1), it); break;
    case JZ:
      if (at(site, x) == INERT) it.next.ip = wrap(it.next.ip + op_length(at(site, it.next.ip)));
      break;
    case JMP: it.next.ip = wrap(at(site, x)); break;
    case RND:
      plan_write(site, x, static_cast<uint8_t>(1 + key(kRnd, slot) % kByteValues), it);
      break;
    case IGNITE: {
      uint8_t dir = 0, off = 0;
      int32_t target = 0;
      pointer(site, x, target, dir, off);
      it.act = Act::Ignite;
      it.site = target;
      it.offset = off;
      it.dir = dir;
      it.cost = cfg_.e_ignite;
      break;
    }
    case WALL:
    case UNWALL: {
      const uint8_t dv = at(site, x);
      if (dv == INERT) break; // own site has no edge to wall
      it.act = decode(byte) == WALL ? Act::Wall : Act::Unwall;
      it.site = site;
      it.dir = static_cast<uint8_t>((dv - 1) % kDirs);
      if (it.act == Act::Wall) it.cost = cfg_.e_wall;
      break;
    }
    default: break;
  }
  return it;
}

} // namespace ps
