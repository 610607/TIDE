// Fixed programs test separate bearings, rotations and orientation reset on division.
#include "../vacancy-01/common.hpp"
#include <iostream>

int main() {
    using vacancy::require;
    tide::Config config;
    config.width=16; config.height=4; config.boundary=tide::Boundary::torus;
    config.placement=tide::Placement::first_free; config.access.read=true;
    for (int read=0;read<4;++read) {
        for (int place=0;place<4;++place) {
            tide::World w(config);
            const int center=18;
            w.seed_site(center,">RSD"); w.set_birth_bearings(center,read,place);
            w.step(); // Rotate both effective directions.
            w.step();
            require(w.at(center).cpu.target==w.neighbor(center,place),"placement scan rotation");
            w.step();
            require(w.at(center).cpu.source==w.neighbor(center,(read+1)%4),"read rotation");
            w.step();
            const auto& c=w.at(center).cpu;
            require(c.target==-1 && c.bearing==1 && c.placement_offset==0,"failed D resets both");
            w.check();
            tide::World self(config);
            self.seed_site(center,"R..CLD"); self.set_birth_bearings(center,read,place);
            const int target=self.neighbor(center,(place+3)%4);
            for (int i=0;i<16;++i) self.step();
            require(self.at(target).kind==tide::Bank::occupied && self.at(target).born==16 &&
                    self.at(center).cpu.bearing==1 && self.at(center).cpu.placement_offset==0,
                    "successful D resets both");
            self.check();
        }
    }
    tide::World left(config),right(config);
    left.seed_site(18,"R..CLD"); right.seed_site(18,"R..CLD");
    left.set_birth_bearings(18,1,2);
    require(left.hash()!=right.hash(),"state hash includes split bearing");
    std::cout<<"All split-bearing controls passed\n";
}
