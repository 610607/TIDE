#include "assay.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace tide;
namespace {
void expect(bool pass, const char* message) {
    if (!pass) throw std::runtime_error(message);
}
Event attempt(World& w, int actor) {
    std::vector<Event> events;
    w.step(&events);
    w.check();
    for (const auto& e : events) if (e.actor == actor) return e;
    throw std::logic_error("missing CPU event");
}

void worked_birth() {
    Config cfg;
    cfg.access.fetch = true;
    World w(cfg);
    const int a = w.index(0,0), b = w.index(1,0), n = w.index(0,1);
    w.seed_site(a, "RJD");
    w.seed_site(b, "CCCTP", 4);
    auto e = attempt(w, a);
    expect(e.effect == Effect::reserve && w.at(n).owner == a, "tick 1 reservation");
    expect(attempt(w, a).effect == Effect::jump, "tick 2 cross-site jump");
    World revoked = w;
    revoked.set_access(a, {});
    expect(attempt(revoked, a).effect == Effect::bad_fetch && revoked.at(a).cpu.pc == 2,
           "fetch revoked after entry");
    for (int i = 0; i < 3; ++i) {
        e = attempt(w, a);
        expect(e.fetch_contact.site == b && e.read_site == a && e.target == n &&
               e.write_offset == i && w.at(n).bytes[i] == w.at(a).bytes[i], "copy provenance");
    }
    expect(attempt(w, a).effect == Effect::resume, "tick 6 return");
    std::vector<Event> events;
    w.step(&events);
    expect(events.size() == 2 && events[0].product == "RJD" && w.at(n).born == 7,
           "tick 7 birth has no same-tick slice");
    expect(attempt(w, n).effect == Effect::reserve, "tick 8 newborn starts");
    World denied(cfg);
    denied.seed_site(a, "RJD");
    denied.seed_site(b, "CCCTP", 4);
    denied.set_access(a, {});
    attempt(denied, a);
    expect(attempt(denied, a).effect == Effect::denied_jump &&
           denied.at(a).cpu.resume == -1 && denied.at(a).cpu.pc == 2, "jump failure state");
    expect(attempt(denied, a).effect == Effect::failed_division && denied.at(n).kind == Bank::free &&
           denied.at(n).bytes == std::string(3, 0), "incomplete reservation released");
}

void data_and_product() {
    Config cfg;
    cfg.access.read = true;
    World w(cfg);
    int a = w.index(1,1), b = w.index(2,1), n = w.index(1,2);
    w.seed_site(a, "RSCLD");
    w.seed_site(b, "RSCLDP", 5);
    attempt(w, a); attempt(w, a);
    const auto before = w.at(n).bytes;
    World denied = w;
    denied.set_access(a, {});
    const auto e = attempt(denied, a);
    const auto& c = denied.at(a).cpu;
    expect(e.effect == Effect::failed_copy && c.pc == 3 && c.read == 0 && c.written == 0 &&
           c.source == b && c.target == n && denied.at(n).bytes == before, "denied data read");
    const auto read = attempt(w, a);
    expect(read.fetch_site == a && read.read_contact.site == b && read.input == 'R',
           "data without borrowed execution");
    cfg.access.fetch = true;
    World redirected(cfg);
    redirected.seed_site(a, "RJDPP");
    redirected.seed_site(b, "SCLTP", 4);
    int copies = 0;
    for (int t = 1; t <= 16; ++t) {
        const auto evt = attempt(redirected, a);
        if (evt.effect == Effect::copy) {
            ++copies;
            expect(evt.fetch_site == b && evt.read_site == b && evt.target == n, "redirected copy");
        }
        if (evt.effect == Effect::birth) {
            expect(copies == 5 && evt.product == "SCLTP" && evt.product != redirected.at(a).bytes,
                   "redirected product belongs to provider sequence");
            return;
        }
    }
    throw std::runtime_error("missing redirected birth");
}

void conflict_and_reclamation() {
    Config cfg;
    cfg.max_age = 2;
    for (auto policy : {Reclamation::retain, Reclamation::empty}) {
        cfg.reclamation = policy;
        World w(cfg);
        int a = w.index(1,0), rival = w.index(1,2), target = w.index(1,1);
        w.seed_site(a, "RCP");
        w.seed_site(rival, "RP", 0, 3);
        World rev = w;
        rev.step(nullptr, true);
        expect(attempt(w, rival).effect == Effect::busy && w.at(rival).cpu.pc == 0 &&
               w.at(target).owner == a && rev.state() == w.state(), "contested reservation");
        expect(attempt(w, rival).effect == Effect::busy, "reserved space unavailable");
        expect(attempt(w, a).effect == Effect::death && w.at(target).kind == Bank::free &&
               w.at(a).kind == Bank::free && w.at(rival).kind == Bank::free, "abandoned reservation");
        expect(policy == Reclamation::retain ? w.at(target).bytes[0] == 'R' : w.at(target).bytes.empty(),
               "residual reclamation");
    }
    // The east bank is reserved and written in this tick. A reader sees its opening byte.
    Config reads;
    reads.access.read = true;
    World w(reads);
    int a = w.index(1,1), owner = w.index(2,0), bank = w.index(2,1);
    w.seed_site(a, "RSC");
    w.seed_site(owner, "R.C");
    attempt(w, a); attempt(w, a);
    const auto e = attempt(w, a);
    expect(e.read_contact.kind == Bank::reserved && e.read_contact.reservation_owner == owner &&
           e.input == 0 && w.at(bank).bytes[0] == 'R', "opening-snapshot visibility");
}

void residual_access() {
    for (bool fetch : {false, true}) {
        Config cfg;
        cfg.access = {!fetch, fetch};
        cfg.max_age = fetch ? 7 : 13;
        World w(cfg);
        const auto donor = fetch ? "CCCTP" : "RSCLDP";
        const int parent = w.index(1,0), child = w.index(1,1), provider = w.index(2,1);
        w.seed_site(parent, fetch ? "RJD" : "RSCLD");
        for (int y : {0,1}) w.seed_site(w.index(2,y), donor, fetch ? 4 : 5);
        for (unsigned t = 1; t <= cfg.max_age; ++t) attempt(w, parent);
        expect(w.at(child).kind == Bank::occupied, "expected daughter before reclamation");
        attempt(w, child);
        expect(w.at(provider).kind == Bank::free, "provider bytes outlived CPU");
        attempt(w, child);
        const auto e = attempt(w, child);
        const auto& hit = fetch ? e.fetch_contact : e.read_contact;
        expect(hit.site == provider && hit.kind == Bank::free && hit.bytes == donor,
               "daughter can use unowned residual bytes");
    }
}

void address_edges() {
    Config cfg;
    World w(cfg);
    const int a = w.index(4,0);
    w.seed_site(a, "SR+CH>TD");
    attempt(w, a);
    expect(w.at(a).cpu.source == -1, "missing neighbor");
    attempt(w, a); attempt(w, a);
    auto e = attempt(w, a);
    expect(e.effect == Effect::copy && e.read_offset == 1 && e.input == 'R', "read increment");
    attempt(w, a);
    expect(w.at(a).cpu.read == 0 && w.at(a).cpu.source == a, "home read reset");
    attempt(w, a);
    expect(w.at(a).cpu.bearing == 2, "clockwise rotation");
    attempt(w, a);
    expect(w.at(a).cpu.pc == 7, "local return falls through");
    expect(attempt(w, a).effect == Effect::failed_division && w.at(a).cpu.pc == 0,
           "partly written allocation released");
    World partial(cfg);
    partial.seed_site(a, "RCD");
    attempt(partial, a); attempt(partial, a); attempt(partial, a);
    expect(partial.at(partial.neighbor(a, 0)).bytes == std::string("R\0\0", 3),
           "failed division retains written prefix");
    World wrap(cfg);
    wrap.seed_site(a, "LC?");
    expect(attempt(wrap, a).effect == Effect::advance && attempt(wrap, a).effect == Effect::failed_copy &&
           attempt(wrap, a).effect == Effect::advance && attempt(wrap, a).effect == Effect::bad_fetch &&
           wrap.at(a).cpu.pc == 0, "invalid offsets and unsupported bytes");

    World conflict(cfg);
    int west = conflict.index(0,1), south = conflict.index(1,0);
    conflict.seed_site(west, "R", 0, 2);
    conflict.seed_site(south, "R");
    expect(attempt(conflict, west).effect == Effect::reserve &&
           conflict.at(conflict.index(1,1)).owner == west, "x priority precedes y priority");
}

void boundary_and_replay() {
    Config cfg;
    cfg.width = 1; cfg.height = 2; cfg.boundary = Boundary::torus;
    World thin(cfg);
    expect(thin.neighbor(0, 1) == -1 && thin.neighbor(0, 2) == 1, "degenerate torus");
    cfg.width = cfg.height = 8;
    cfg.max_age = 80; cfg.mutation_ppm = 20000; cfg.placement = Placement::first_free;
    cfg.access = {true, true};
    World forward(cfg), reverse(cfg);
    forward.seed_site(36, ancestor); reverse.seed_site(36, ancestor);
    std::vector<Event> log;
    for (int i = 0; i < 512; ++i) {
        forward.step(&log); reverse.step(nullptr, true);
        forward.check(); reverse.check();
        expect(forward.state() == reverse.state(), "visit order or tracing changed complete state");
    }
    expect(forward.hash() == "b036610108143392", "reference replay hash changed");
    std::cout << "512-tick replay hash " << forward.hash() << '\n';
}
void calibrate() {
    struct Case { Access arm; const char* focal; const char* donor; int park; };
    for (auto x : {Case{{true,false}, "RSCLD", "RSCLDP", 5},
                   Case{{false,true}, "RJD", "CCCTP", 4}}) {
        const auto on = assay(x.focal, x.donor, 1, x.arm, x.arm, x.park);
        const auto off = assay(x.focal, x.donor, 1, x.arm, {}, x.park);
        expect(on.generations == 3 && on.generations_using_channel == 3 &&
               off.generations == 0 && off.cycle, "serial dependency with exact denial cycle");
        const auto entry = assay(x.focal, x.donor, 1, x.arm, x.arm);
        const auto entry_off = assay(x.focal, x.donor, 1, x.arm, {});
        expect(entry.generations_using_channel == 3 && entry_off.cycle && entry_off.generations == 0,
               "positive controls in pilot arenas with donor starting at entry");
        for (auto mask : {Access{}, x.arm}) {
            const auto control = assay(ancestor, x.donor, 1, x.arm, mask, x.park);
            expect(control.generations == 3 && control.generations_using_channel == 0,
                   "independent ancestor failed serial control");
        }
        std::cout << (x.arm.read ? "read" : "fetch") << " control: three births in " << on.elapsed
                  << " ticks, denied cycle by tick " << off.elapsed << '\n';
    }
}
}

void knockout_override() {
    Config cfg;
    cfg.width = 6; cfg.height = 6; cfg.boundary = Boundary::torus; cfg.placement = Placement::first_free;
    cfg.max_age = 80;
    auto births = [&](int offset) {
        World w(cfg);
        const int a = w.index(2,2);
        w.seed_site(a, "R..CLD");
        if (offset >= 0) {
            auto bytes = w.at(a).bytes;
            bytes[offset] = '.';
            w.replace_bytes(a, bytes);
        }
        int n = 0;
        for (int t = 0; t < 81; ++t) {
            const int target = w.at(a).cpu.target;
            w.step();
            if (target >= 0 && w.at(target).kind == Bank::occupied && w.at(target).born == w.tick()) ++n;
        }
        return n;
    };
    World same(cfg), plain(cfg);
    same.seed_site(0, "R..CLD"); plain.seed_site(0, "R..CLD");
    same.replace_bytes(0, "R..CLD");
    expect(same.hash() == plain.hash(), "identical replacement leaves state unchanged");
    bool rejected = false;
    try { same.replace_bytes(1, "R..CLD"); } catch (const std::invalid_argument&) { rejected = true; }
    expect(rejected, "replacement requires an occupied bank");
    const int intact = births(-1);
    expect(intact > 0 && births(1) == intact && births(0) == 0 && births(3) == 0 &&
           births(4) == 0 && births(5) == 0, "knockouts of R, C, L and D stop division");
}

int main() {
    try {
        worked_birth(); data_and_product(); conflict_and_reclamation();
        residual_access(); address_edges(); boundary_and_replay(); calibrate();
        knockout_override();
        std::cout << "All reference checks passed\n";
    } catch (const std::exception& err) {
        std::cerr << err.what() << '\n';
        return 1;
    }
}
