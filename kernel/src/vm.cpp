#include "vm.hpp"

#include <algorithm>
#include <array>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace tide {
namespace {
Cpu fresh(int site) {
    Cpu cpu;
    cpu.bank = cpu.source = site;
    return cpu;
}
void release(Site& bank, Reclamation policy) {
    auto bytes = std::move(bank.bytes);
    bank = Site{};
    if (policy == Reclamation::retain) bank.bytes = std::move(bytes);
}
Tick mix(Tick x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
Contact contact(int id, const Site& site) {
    return {id, site.kind, site.born, site.owner, site.bytes};
}
}

const char* name(Effect e) {
    constexpr std::array labels{"advance", "reserve", "busy", "jump", "denied_jump",
        "return", "copy", "failed_copy", "loop", "birth", "failed_division",
        "park", "bad_fetch", "death"};
    return labels.at(static_cast<unsigned>(e));
}
World::World(Config config) : cfg_(config) {
    if (cfg_.width < 1 || cfg_.height < 1 || cfg_.width > 128 || cfg_.height > 128 ||
        cfg_.mutation_ppm > 1000000) throw std::invalid_argument("invalid world configuration");
    sites_.resize(cfg_.width * cfg_.height);
    access_.assign(size(), cfg_.access);
}
int World::index(int x, int y) const {
    if (x < 0 || y < 0 || x >= cfg_.width || y >= cfg_.height) return -1;
    return y * cfg_.width + x;
}
int World::neighbor(int id, int dir) const {
    constexpr std::array dx{0, 1, 0, -1}, dy{1, 0, -1, 0};
    int x = id % cfg_.width + dx.at(dir), y = id / cfg_.width + dy.at(dir);
    if (cfg_.boundary == Boundary::torus) {
        x = (x + cfg_.width) % cfg_.width;
        y = (y + cfg_.height) % cfg_.height;
    }
    const int target = index(x, y);
    return target == id ? -1 : target;
}
void World::seed_site(int id, std::string bytes, int pc, int bearing) {
    auto& site = sites_.at(id);
    if (tick_ || site.kind != Bank::free || bytes.empty() || bytes.size() > capacity ||
        pc < 0 || pc >= static_cast<int>(bytes.size()) || bearing < 0 || bearing > 3)
        throw std::invalid_argument("invalid initial individual");
    site.kind = Bank::occupied;
    site.bytes = std::move(bytes);
    site.cpu = fresh(id);
    site.cpu.pc = pc;
    site.cpu.bearing = bearing;
}
void World::set_access(int id, Access access) { access_.at(id) = access; }
void World::replace_bytes(int id, std::string bytes) {
    auto& site = sites_.at(id);
    if (site.kind != Bank::occupied || bytes.size() != site.bytes.size())
        throw std::invalid_argument("invalid knockout bytes");
    site.bytes = std::move(bytes);
}
void World::clear_residue() {
    for (auto& site : sites_) {
        if (site.kind == Bank::free) site.bytes.clear();
        if (site.kind != Bank::reserved) continue;
        const auto written = static_cast<size_t>(sites_.at(site.owner).cpu.written);
        std::fill(site.bytes.begin() + static_cast<long>(std::min(written, site.bytes.size())), site.bytes.end(), '\0');
    }
}
void World::set_reclamation(Reclamation policy) { cfg_.reclamation = policy; }

int World::placement(int id, int bearing) const {
    const int tries = cfg_.placement == Placement::directed ? 1 : 4;
    for (int i = 0; i < tries; ++i) {
        const int dest = neighbor(id, (bearing + 3 + i) % 4);
        if (dest >= 0 && sites_[dest].kind == Bank::free) return dest;
    }
    return -1;
}
char World::copied(char byte, int id, int offset) const {
    if (!cfg_.mutation_ppm) return byte;
    const Tick ctx = mix(mix(mix(cfg_.seed) ^ (tick_ + 1)) ^ static_cast<Tick>(id)) ^
                     static_cast<Tick>(offset);
    if (mix(ctx) % 1000000 >= cfg_.mutation_ppm) return byte;
    constexpr std::string_view alphabet = "R.JTSH+>CLDP";
    const auto old = alphabet.find(byte);
    auto idx = mix(ctx ^ 0xc6a4a7935bd1e995ULL) % (alphabet.size() - (old != alphabet.npos));
    if (idx >= old) ++idx;
    return alphabet[idx];
}

void World::step(std::vector<Event>* events, bool reverse) {
    if (tick_ == std::numeric_limits<Tick>::max()) throw std::overflow_error("tick exhausted");
    if (events) events->clear();
    auto next = sites_;
    std::vector<int> winners(size(), -1);
    std::vector<Event> log;
    if (events) log.resize(size());
    auto priority = [&](int site) { return (site % cfg_.width) * cfg_.height + site / cfg_.width; };

    for (int k = 0; k < size(); ++k) {
        const int id = reverse ? size() - 1 - k : k;
        const Site& actor = sites_[id];
        if (actor.kind != Bank::occupied) continue;
        Cpu& cpu = next[id].cpu;
        Event scratch;
        Event& e = events ? log[id] : scratch;
        e.actor = id;
        e.actor_born = actor.born;
        e.tick = tick_ + 1;
        e.target = cpu.target;
        if (cfg_.max_age && tick_ - actor.born >= cfg_.max_age) {
            if (cpu.target >= 0) release(next[cpu.target], cfg_.reclamation);
            release(next[id], cfg_.reclamation);
            e.effect = Effect::death;
            continue;
        }
        const bool abroad = cpu.bank != id;
        e.fetch_site = cpu.bank;
        e.pc = cpu.pc;
        if ((abroad && !access_[id].fetch) ||
            cpu.pc >= static_cast<int>(sites_[cpu.bank].bytes.size())) {
            cpu.pc = abroad ? cpu.resume : 0;
            cpu.bank = id;
            cpu.resume = -1;
            e.effect = Effect::bad_fetch;
            continue;
        }
        const Site& fetched = sites_[cpu.bank];
        if (events && abroad) e.fetch_contact = contact(cpu.bank, fetched);
        e.op = static_cast<unsigned char>(fetched.bytes[cpu.pc]);
        ++cpu.pc;
        switch (e.op) {
        case 'R': {
            if (cpu.target >= 0) break;
            --cpu.pc;
            e.effect = Effect::busy;
            const int dest = placement(id, cpu.bearing);
            e.target = dest;
            if (dest >= 0 && (winners[dest] < 0 || priority(id) < priority(winners[dest])))
                winners[dest] = id;
            break;
        }
        case 'J': {
            if (abroad) break;
            const int dest = neighbor(id, cpu.bearing);
            if (dest >= 0 && access_[id].fetch && !sites_[dest].bytes.empty()) {
                cpu.resume = cpu.pc;
                cpu.bank = dest;
                cpu.pc = 0;
                e.effect = Effect::jump;
            } else e.effect = Effect::denied_jump;
            break;
        }
        case 'T':
            if (abroad) {
                cpu.bank = id;
                cpu.pc = cpu.resume;
                cpu.resume = -1;
                e.effect = Effect::resume;
            }
            break;
        case 'S': cpu.source = neighbor(id, cpu.bearing); cpu.read = 0; break;
        case 'H': cpu.source = id; cpu.read = 0; break;
        case '+': cpu.read = std::min(capacity, cpu.read + 1); break;
        case '>': cpu.bearing = (cpu.bearing + 1) % 4; break;
        case 'C': {
            e.read_site = cpu.source;
            e.read_offset = cpu.read;
            e.write_offset = cpu.written;
            if (cpu.source < 0 || (cpu.source != id && !access_[id].read) ||
                cpu.read >= static_cast<int>(sites_[cpu.source].bytes.size()) ||
                cpu.target < 0 || cpu.written >= static_cast<int>(sites_[cpu.target].bytes.size())) {
                e.effect = Effect::failed_copy;
                break;
            }
            const Site& source = sites_[cpu.source];
            if (events && cpu.source != id) e.read_contact = contact(cpu.source, source);
            const char input = source.bytes[cpu.read++];
            const char output = copied(input, id, cpu.written);
            next[cpu.target].bytes[cpu.written++] = output;
            e.input = static_cast<unsigned char>(input);
            e.output = static_cast<unsigned char>(output);
            e.effect = Effect::copy;
            break;
        }
        case 'L':
            if (cpu.target >= 0 && cpu.written < static_cast<int>(sites_[cpu.target].bytes.size()) && e.pc > 0) {
                cpu.pc = e.pc - 1;
                e.effect = Effect::loop;
            }
            break;
        case 'D':
            e.effect = Effect::failed_division;
            if (cpu.target >= 0) {
                Site& child = next[cpu.target];
                if (cpu.written == static_cast<int>(child.bytes.size())) {
                    child.kind = Bank::occupied;
                    child.owner = -1;
                    child.born = tick_ + 1;
                    child.cpu = fresh(cpu.target);
                    e.effect = Effect::birth;
                    if (events) e.product = child.bytes;
                } else release(child, cfg_.reclamation);
            }
            cpu = fresh(id);
            break;
        case 'P': --cpu.pc; e.effect = Effect::park; break;
        default: break;
        }
    }
    for (int dest = 0; dest < size(); ++dest) {
        const int id = winners[dest];
        if (id < 0) continue;
        Site& bank = next[dest];
        bank.kind = Bank::reserved;
        bank.owner = id;
        bank.bytes.resize(sites_[id].bytes.size(), 0);
        Cpu& cpu = next[id].cpu;
        cpu.target = dest;
        cpu.source = id;
        cpu.read = cpu.written = 0;
        ++cpu.pc;
        if (events) log[id].effect = Effect::reserve;
    }
    ++tick_;
    sites_.swap(next);
    if (events) for (auto& e : log) if (e.actor >= 0) events->push_back(std::move(e));
}

std::string World::serialize(bool include_time) const {
    std::string out = "TIDE-VM1";
    auto word = [&](Tick n) {
        for (int i = 0; i < 8; ++i, n >>= 8) out.push_back(static_cast<char>(n & 255));
    };
    word(cfg_.width); word(cfg_.height); word(static_cast<unsigned>(cfg_.boundary));
    word(static_cast<unsigned>(cfg_.placement)); word(static_cast<unsigned>(cfg_.reclamation));
    word(static_cast<unsigned>(cfg_.schedule)); word(static_cast<unsigned>(cfg_.arbitration));
    word(static_cast<unsigned>(cfg_.mutation)); word(cfg_.access.read); word(cfg_.access.fetch);
    word(cfg_.seed); word(cfg_.max_age); word(cfg_.mutation_ppm);
    if (include_time) word(tick_);
    for (int i = 0; i < size(); ++i) {
        const Site& s = sites_[i];
        const Cpu& c = s.cpu;
        word(access_[i].read); word(access_[i].fetch); word(static_cast<unsigned>(s.kind));
        word(s.owner);
        if (include_time) word(s.born);
        word(s.bytes.size()); out += s.bytes;
        for (int field : {c.bank, c.pc, c.resume, c.bearing, c.source, c.read, c.target, c.written})
            word(field);
    }
    return out;
}
std::string World::state() const { return serialize(true); }
std::string World::dynamics() const {
    if (cfg_.mutation_ppm || cfg_.max_age) throw std::logic_error("time affects dynamics");
    return serialize(false);
}
std::string World::hash() const {
    Tick digest = 14695981039346656037ULL;
    for (unsigned char c : state()) digest = (digest ^ c) * 1099511628211ULL;
    std::ostringstream out;
    out << std::hex << std::setw(16) << std::setfill('0') << digest;
    return out.str();
}
void World::check() const {
    for (int i = 0; i < size(); ++i) {
        const auto& s = sites_[i];
        const Cpu& c = s.cpu;
        auto local = [&](int n) {
            return n == i || (n >= 0 && (neighbor(i, 0) == n || neighbor(i, 1) == n ||
                                         neighbor(i, 2) == n || neighbor(i, 3) == n));
        };
        if (s.bytes.size() > capacity) throw std::logic_error("bank capacity exceeded");
        if (s.kind == Bank::reserved && (!local(s.owner) || s.owner == i ||
            at(s.owner).kind != Bank::occupied || at(s.owner).cpu.target != i ||
            s.bytes.size() != at(s.owner).bytes.size())) throw std::logic_error("orphan reservation");
        if (s.kind != Bank::reserved && s.owner != -1) throw std::logic_error("stale owner");
        if (s.kind != Bank::occupied) continue;
        if (s.bytes.empty() || !local(c.bank) || (c.source != -1 && !local(c.source)) ||
            (c.bank == i) != (c.resume == -1) || c.read < 0 || c.read > capacity ||
            c.pc < 0 || c.pc > capacity || c.bearing < 0 || c.bearing > 3 ||
            c.written < 0 || c.written > static_cast<int>(s.bytes.size()) ||
            (c.target < 0 && c.written) || (c.target >= 0 && (!local(c.target) ||
            at(c.target).kind != Bank::reserved || at(c.target).owner != i)))
            throw std::logic_error("invalid CPU");
    }
}
}
