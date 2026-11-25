// Untreated fields, with a read-only observer for changed readers' living neighbors.
#include "history.hpp"

namespace {
constexpr int enrollment=8192, follow=324;
struct ContactHistory {
    int id,at_birth=0,ticks=0,reads=0,first_contact=-1,first_read=-1;
    int birth_distance=-1,min_distance=-1,anywhere_ticks=0;
};
// Supplementary distance census of the same execution openings as the local observer.
int distance_between(int a,int b) {
    int dx=std::abs(a%16-b%16), dy=std::abs(a/16-b/16);
    return std::min(dx,16-dx)+std::min(dy,4-dy);
}
int nearest_match(const World& w,int focal) {
    int nearest=-1;
    for (int i=0;i<w.size();++i) {
        if (i==focal || w.at(i).kind!=Bank::occupied || w.at(i).bytes!=w.at(focal).bytes) continue;
        int distance=distance_between(i,focal);
        if (nearest<0 || distance<nearest) nearest=distance;
    }
    return nearest;
}
void distance_control() {
    auto w=initial(1,0);
    w.seed_site(31,"RS.CLD");
    w.seed_site(16,"R.SCLD");
    require(nearest_match(w,31)<0,"unmatched control");
    w.seed_site(24,"RS.CLD");
    require(nearest_match(w,31)==7,"distant match control");
    w.seed_site(15,"RS.CLD");
    require(nearest_match(w,31)==1,"neighbor match control");
    w.seed_site(0,"RS.CLD");
    require(nearest_match(w,0)==1,"wraparound control");
    for (int executor=0;executor<w.size();++executor)
        for (int read=0;read<4;++read)
            for (int write=0;write<4;++write)
                if (read!=write)
                    require(distance_between(w.neighbor(executor,read),w.neighbor(executor,write))==2,
                            "unexpected donor-to-newborn distance");
}
void contacts(const Field& field,const std::string& dir) {
    auto out=vacancy::output(dir,"contacts.tsv","seed\tid\tat_birth\tcontact_ticks\tmatching_reads\tfirst_contact\tfirst_read\tbirth_distance\tmin_distance\tanywhere_ticks");
    std::vector<ContactHistory> focals;
    int end=0;
    for (int i=1;i<int(field.lives.size());++i) {
        const auto& p=field.lives[i];
        const auto& maker=field.lives[p.actor];
        if (p.born<=enrollment && p.confirmed && maker.confirmed && p.genome!=maker.genome) {
            focals.push_back({i});
            end=std::max(end,p.born+age-1);
        }
    }
    World w=initial(field.seed);
    std::vector<Event> events;
    for (int t=1;t<=end;++t) {
        bool watched=false;
        for (auto& focus:focals) {
            const auto& p=field.lives[focus.id];
            if (t<=p.born || t>=p.born+age) continue;
            watched=true;
            require(w.at(p.site).kind==Bank::occupied && int(w.at(p.site).born)==p.born,"changed focal missing");
            bool near=false;
            for (int d=0;d<4;++d) {
                const auto& neighbor=w.at(w.neighbor(p.site,d));
                near|=neighbor.kind==Bank::occupied && neighbor.bytes==p.genome;
            }
            int distance=nearest_match(w,p.site);
            require(near==(distance==1),"distance census disagrees with cardinal observer");
            if (t==p.born+1) focus.birth_distance=distance;
            if (distance>=0) {
                ++focus.anywhere_ticks;
                if (focus.min_distance<0 || distance<focus.min_distance) focus.min_distance=distance;
            }
            if (near) {
                if (t==p.born+1) focus.at_birth=1;
                if (!focus.ticks) focus.first_contact=t;
                ++focus.ticks;
            }
        }
        w.step(watched?&events:nullptr,field.reverse);
        if (!watched) continue;
        for (const auto& e:events) {
            if (e.effect!=Effect::copy || e.read_site==e.actor || e.read_contact.kind!=Bank::occupied) continue;
            for (auto& focus:focals) {
                const auto& p=field.lives[focus.id];
                if (p.site==e.actor && Tick(p.born)==e.actor_born && p.genome==e.read_contact.bytes) {
                    if (!focus.reads) focus.first_read=t;
                    ++focus.reads;
                }
            }
        }
    }
    for (const auto& f:focals)
        out<<field.seed<<'\t'<<f.id<<'\t'<<f.at_birth<<'\t'<<f.ticks<<'\t'<<f.reads
           <<'\t'<<f.first_contact<<'\t'<<f.first_read<<'\t'<<f.birth_distance<<'\t'<<f.min_distance<<'\t'<<f.anywhere_ticks<<'\n';
}
}
int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string_view(argv[1])=="--test") {controls();distance_control();return 0;}
        require(argc==3 || (argc==4 && std::string_view(argv[3])=="--reverse"),"usage: field SEED DIR [--reverse]");
        int seed=std::stoi(argv[1]);
        require(seed>=26689 && seed<=27712,"seed outside protocol");
        Field field(seed,enrollment+follow,argc==4);
        field.observe(); field.confirm(); field.write(argv[2]); contacts(field,argv[2]);
    } catch (const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
