#pragma once
// Engine-independent authoritative state. This exact implementation is used by UE and tests.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace dawn {
constexpr int SchemaVersion = 1;
constexpr int ContentVersion = 2;
struct Pose { double x=0,y=0,z=0,pitch=0,yaw=0,roll=0,sx=1,sy=1,sz=1; };
struct World {
    std::string level="L_Galilee", node="Intro_Arrival", stage="Intro", checkpoint, ending;
    std::map<std::string,Pose> actors;
    std::set<std::string> inspected, appliedChoices;
    std::map<std::string,int> items, relationships;
    std::map<std::string,bool> flags;
    std::vector<std::string> choices;
};
struct Meta { std::set<std::string> clues, endings, memories, scenes; };
enum class EffectKind { SetFlag, AddItem, RemoveItem, ChangeRelationship };
struct Effect { EffectKind kind; std::string id; int value; };
enum class LoadError { None, Corrupt, SchemaMismatch, ContentMismatch };

inline uint64_t Hash(const std::string& s) { uint64_t h=14695981039346656037ull; for(unsigned char c:s){h^=c;h*=1099511628211ull;} return h; }
class Session {
public:
    World world;
    Meta meta;
    std::map<std::string,World> checkpoints;
    uint64_t generation=1;
    bool busy=false;
    bool started=false;

    bool Flag(const std::string& key) const { auto i=world.flags.find(key);return i!=world.flags.end()&&i->second; }
    int Item(const std::string& key) const {auto i=world.items.find(key);return i==world.items.end()?0:i->second;}
    int Relationship(const std::string& key) const {auto i=world.relationships.find(key);return i==world.relationships.end()?0:i->second;}
    void NewGame() { ++generation;busy=false;started=true;world=World{};checkpoints.clear(); }
    // Memory reset does not restore/mutate World: keep in-flight intro callbacks valid.
    void ResetMemories(bool confirmed) {if(confirmed){meta=Meta{};}}
    bool CallbackIsCurrent(uint64_t epoch) const { return epoch==generation&&!busy; }
    void FinishIntro() {if(world.stage=="Intro"&&!busy){meta.scenes.insert("Intro");EnterNode("Explore");}}
    bool Inspect(const std::string& id) {
        if(busy)return false;
        if(world.stage=="Task") {
            std::string next;
            if(world.node=="Task_HelpNet"&&id=="Net")next="Simon_Helped";
            else if(world.node=="Task_ObserveShore"&&id=="Stone")next="Shore_Clue";
            else if(world.node=="Task_ReturnToSimon"&&id=="Simon")next="Choice_02";
            else if(world.node=="Task_Departure"&&id=="Village") {
                world.flags["WalkedToVillage"]=true;
                world.ending="Ending_Departure";
                meta.endings.insert(world.ending);meta.memories.insert("Memory_Departure");
                next=world.ending;
            } else return false;
            // Choice effects have already committed. Physical followthrough only
            // advances the authored scene (or finalizes the departure once).
            if(!EnterNode(next))return false;
            ++generation;return true;
        }
        if(world.stage!="Explore")return false;
        if(id=="Simon"||id=="Jesus") {
            if(world.inspected.count("Net")&&world.inspected.count("Boat")&&world.inspected.count("Stone")) {EnterNode("Simon_Greeting");return true;}
            return false;
        }
        if(id!="Net"&&id!="Boat"&&id!="Stone")return false;
        if(world.inspected.insert(id).second) {
            meta.clues.insert(id);meta.memories.insert("Memory_"+id);
            if(id=="Net")world.items["Rope"]+=1;
        }
        EnterNode("Inspect_"+id);return true;
    }
    bool ApplyEffects(const std::vector<Effect>& effects) {
        World candidate=world;
        for(const auto& e:effects) {
            if(e.id.empty()||e.value < -10000||e.value>10000)return false;
            switch(e.kind) {
            case EffectKind::SetFlag:candidate.flags[e.id]=e.value!=0;break;
            case EffectKind::AddItem:if(e.value<0)return false;candidate.items[e.id]+=e.value;break;
            case EffectKind::RemoveItem:if(e.value<0||candidate.items[e.id]<e.value)return false;candidate.items[e.id]-=e.value;break;
            case EffectKind::ChangeRelationship:candidate.relationships[e.id]+=e.value;break;
            }
        }
        world=std::move(candidate);return true;
    }
    bool EnterNode(const std::string& id) {
        if(busy||id.empty())return false;
        if(id=="Choice_01") {
            if(!world.appliedChoices.empty()||Item("Rope")!=1||!world.inspected.count("Net")||!world.inspected.count("Boat")||!world.inspected.count("Stone"))return false;
        }
        const bool first=world.appliedChoices.count("Choice_01")>0,second=world.appliedChoices.count("Choice_02")>0;
        if(id=="Choice_02"&&(!first||second||world.node!="Task_ReturnToSimon"))return false;
        if(id=="Task_HelpNet"&&(!first||second||!Flag("NetPrepared")))return false;
        if(id=="Task_ObserveShore"&&(!first||second||!Flag("ShoreClueFound")))return false;
        if(id=="Task_ReturnToSimon"&&(!first||second))return false;
        if(id=="Task_Departure"&&(!second||world.choices.size()!=2||world.choices.back()!="Choice2_B"||!world.ending.empty()))return false;
        if(id.rfind("Task_",0)==0&&id!="Task_HelpNet"&&id!="Task_ObserveShore"&&id!="Task_ReturnToSimon"&&id!="Task_Departure")return false;
        world.node=id;
        if(id=="Explore")world.stage="Explore";
        else if(id=="Choice_01")world.stage="Choice1";
        else if(id=="Choice_02")world.stage="Choice2";
        else if(id.rfind("Intro_",0)==0)world.stage="Intro";
        else if(id.rfind("Scene_",0)==0)world.stage="Scene";
        else if(id.rfind("Task_",0)==0)world.stage="Task";
        else if(id.rfind("Ending_",0)==0)world.stage="Ending";
        else world.stage="Dialogue";
        if(id=="Choice_01")Capture("CP01");
        if(id=="Choice_02") {meta.scenes.insert("Scene");Capture("CP02");}
        return true;
    }
    bool Advance(const std::string& expectedNode,const std::string& next) {
        if(busy||expectedNode!=world.node||world.stage=="Choice1"||world.stage=="Choice2"||world.stage=="Ending"||world.stage=="Task")return false;
        return EnterNode(next);
    }
    bool Choose(int index,uint64_t expectedGeneration,const std::string& expectedNode) {
        if(busy||expectedGeneration!=generation||expectedNode!=world.node||index<0||index>1)return false;
        const std::string choice=world.node;
        if(choice!="Choice_01"&&choice!="Choice_02")return false;
        if(world.appliedChoices.count(choice))return false;
        if(choice=="Choice_01") {
            if(index==0) {
                if(!ApplyEffects({{EffectKind::RemoveItem,"Rope",1},{EffectKind::SetFlag,"NetPrepared",1},{EffectKind::ChangeRelationship,"Simon",1}}))return false;
            } else {
                if(!ApplyEffects({{EffectKind::SetFlag,"ShoreClueFound",1}}))return false;
                meta.clues.insert("ShoreClue");meta.memories.insert("Memory_Shore");
            }
            if(index==0)meta.memories.insert("Memory_SharedWork");
            world.appliedChoices.insert(choice);world.choices.push_back(index==0?"Choice1_A":"Choice1_B");
            EnterNode(index==0?"Task_HelpNet":"Task_ObserveShore");
        } else {
            world.appliedChoices.insert(choice);world.choices.push_back(index==0?"Choice2_A":"Choice2_B");
            world.flags["StayedWithSimon"]=index==0;
            world.flags["WalkedToVillage"]=false;
            if(index==1)EnterNode("Task_Departure");
            else {
                world.ending=Flag("NetPrepared")?"Ending_Together":"Ending_Witness";
                meta.endings.insert(world.ending);meta.memories.insert("Memory_"+world.ending.substr(7));
                EnterNode(world.ending);
            }
        }
        ++generation;return true;
    }
    void Capture(const std::string& id) {world.checkpoint=id;checkpoints[id]=world;}
    bool Rewind(const std::string& id) {
        auto it=checkpoints.find(id);if(busy||it==checkpoints.end())return false;
        busy=true;++generation;
        world=it->second; // value copy; never points to a live object
        if(id=="CP01")checkpoints.erase("CP02"); // stale downstream branch cannot be revisited
        busy=false;return true;
    }
    std::string Serialize() const;
    static LoadError Deserialize(const std::string& bytes,Session& out);
};
inline bool ValidateWorld(const World& w) {
    auto flag=[&](const std::string& id){auto v=w.flags.find(id);return v!=w.flags.end()&&v->second;};
    auto item=[&](const std::string& id){auto v=w.items.find(id);return v==w.items.end()?0:v->second;};
    auto rel=[&](const std::string& id){auto v=w.relationships.find(id);return v==w.relationships.end()?0:v->second;};
    std::string expectedStage="Dialogue";
    if(w.node=="Explore")expectedStage="Explore";
    else if(w.node=="Choice_01")expectedStage="Choice1";
    else if(w.node=="Choice_02")expectedStage="Choice2";
    else if(w.node.rfind("Intro_",0)==0)expectedStage="Intro";
    else if(w.node.rfind("Scene_",0)==0)expectedStage="Scene";
    else if(w.node.rfind("Ending_",0)==0)expectedStage="Ending";
    else if(w.node.rfind("Task_",0)==0)expectedStage="Task";
    if(w.stage!=expectedStage)return false;
    if(!w.checkpoint.empty()&&w.checkpoint!="CP01"&&w.checkpoint!="CP02")return false;
    if(w.choices.size()>2||w.appliedChoices.size()!=w.choices.size())return false;
    const bool first=!w.choices.empty(), second=w.choices.size()==2;
    if(first && w.choices[0]!="Choice1_A" && w.choices[0]!="Choice1_B")return false;
    if(second && w.choices[1]!="Choice2_A" && w.choices[1]!="Choice2_B")return false;
    if(first!=(w.appliedChoices.count("Choice_01")>0)||second!=(w.appliedChoices.count("Choice_02")>0))return false;
    const bool helped=first&&w.choices[0]=="Choice1_A", shore=first&&!helped;
    if(flag("NetPrepared")!=helped||flag("ShoreClueFound")!=shore||rel("Simon")!=(helped?1:0))return false;
    for(const auto& id:w.inspected)if(id!="Net"&&id!="Boat"&&id!="Stone")return false;
    if(item("Rope")!=(w.inspected.count("Net")?(helped?0:1):0))return false;
    if(first&&w.inspected.size()!=3)return false;
    if(w.stage=="Choice1"&&(w.node!="Choice_01"||first||w.inspected.size()!=3))return false;
    if(w.stage=="Choice2"&&(w.node!="Choice_02"||!first||second))return false;
    const bool pendingDeparture=w.node=="Task_Departure";
    if(w.stage=="Task") {
        if(w.node=="Task_HelpNet") {if(!helped||second)return false;}
        else if(w.node=="Task_ObserveShore") {if(!shore||second)return false;}
        else if(w.node=="Task_ReturnToSimon") {if(!first||second)return false;}
        else if(pendingDeparture) {if(!second||w.choices[1]!="Choice2_B")return false;}
        else return false;
    }
    if(w.stage=="Ending") {
        if(!second)return false;
        const std::string expected=w.choices[1]=="Choice2_B"?"Ending_Departure":(helped?"Ending_Together":"Ending_Witness");
        if(w.ending!=expected||w.node!=expected)return false;
    } else if(!w.ending.empty()||(second&&!pendingDeparture))return false;
    if(flag("StayedWithSimon")!=(second&&w.choices[1]=="Choice2_A"))return false;
    if(flag("WalkedToVillage")!=(second&&w.choices[1]=="Choice2_B"&&!pendingDeparture))return false;
    return true;
}
namespace codec {
inline void S(std::ostream&o,const std::string&s){o<<std::quoted(s)<<'\n';}
inline bool S(std::istream&i,std::string&s){if(!(i>>std::quoted(s)))return false;return s.size()<=16384;}
inline void Set(std::ostream&o,const std::set<std::string>&s){o<<s.size()<<'\n';for(auto&v:s)S(o,v);}
inline bool Count(std::istream&i,size_t&n){return bool(i>>n)&&n<=4096;}
inline bool Set(std::istream&i,std::set<std::string>&s){size_t n;if(!Count(i,n))return false;
    for(size_t k=0;k<n;k++){std::string v;if(!S(i,v)||!s.insert(v).second)return false;}return true;}
inline void IntMap(std::ostream&o,const std::map<std::string,int>&m){o<<m.size()<<'\n';for(auto&v:m){S(o,v.first);o<<v.second<<'\n';}}
inline bool IntMap(std::istream&i,std::map<std::string,int>&m){size_t n;if(!Count(i,n))return false;
    for(size_t k=0;k<n;k++){std::string key;int v;if(!S(i,key)||!(i>>v)||v < -100000||v>100000||!m.emplace(key,v).second)return false;}return true;}
inline void WriteWorld(std::ostream&o,const World&w){
    S(o,w.level);S(o,w.node);S(o,w.stage);S(o,w.checkpoint);S(o,w.ending);
    Set(o,w.inspected);Set(o,w.appliedChoices);IntMap(o,w.items);IntMap(o,w.relationships);
    o<<w.flags.size()<<'\n';for(auto&v:w.flags){S(o,v.first);o<<int(v.second)<<'\n';}
    o<<w.choices.size()<<'\n';for(auto&v:w.choices)S(o,v);
    o<<w.actors.size()<<'\n';for(auto&v:w.actors){S(o,v.first);auto&p=v.second;o<<p.x<<' '<<p.y<<' '<<p.z<<' '<<p.pitch<<' '<<p.yaw<<' '<<p.roll<<' '<<p.sx<<' '<<p.sy<<' '<<p.sz<<'\n';}
}
inline bool ReadWorld(std::istream&i,World&w){
    if(!S(i,w.level)||!S(i,w.node)||!S(i,w.stage)||!S(i,w.checkpoint)||!S(i,w.ending)||!Set(i,w.inspected)||!Set(i,w.appliedChoices)||!IntMap(i,w.items)||!IntMap(i,w.relationships))return false;
    size_t n;if(!Count(i,n))return false;
    for(size_t k=0;k<n;k++){std::string key;int b;if(!S(i,key)||!(i>>b)||b<0||b>1||!w.flags.emplace(key,b!=0).second)return false;}
    if(!Count(i,n))return false;
    for(size_t k=0;k<n;k++){std::string s;if(!S(i,s))return false;w.choices.push_back(s);}
    if(!Count(i,n))return false;
    for(size_t k=0;k<n;k++){std::string key;Pose p;if(!S(i,key)||!(i>>p.x>>p.y>>p.z>>p.pitch>>p.yaw>>p.roll>>p.sx>>p.sy>>p.sz))return false;double values[]={p.x,p.y,p.z,p.pitch,p.yaw,p.roll,p.sx,p.sy,p.sz};for(double v:values)if(!std::isfinite(v)||std::abs(v)>1e8)return false;if(!w.actors.emplace(key,p).second)return false;}
    static const std::set<std::string> stages={"Intro","Explore","Dialogue","Choice1","Scene","Choice2","Ending","Task"};
    if(!stages.count(w.stage)||w.node.empty()||w.level!="L_Galilee")return false;
    for(auto& item:w.items)if(item.second<0)return false;
    return ValidateWorld(w);
}
}
inline std::string Session::Serialize() const {
    std::ostringstream o;o<<std::setprecision(17)<<"DAWN_SAVE "<<SchemaVersion<<' '<<ContentVersion<<'\n'<<int(started)<<'\n';
    codec::WriteWorld(o,world);o<<checkpoints.size()<<'\n';for(auto& cp:checkpoints){codec::S(o,cp.first);codec::WriteWorld(o,cp.second);}
    codec::Set(o,meta.clues);codec::Set(o,meta.endings);codec::Set(o,meta.memories);codec::Set(o,meta.scenes);
    const std::string body=o.str();o<<"CHECKSUM "<<Hash(body)<<'\n';return o.str();
}
inline LoadError Session::Deserialize(const std::string& bytes,Session& out) {
    if(bytes.size()>4*1024*1024)return LoadError::Corrupt;
    auto end=bytes.rfind("CHECKSUM ");if(end==std::string::npos)return LoadError::Corrupt;
    uint64_t checksum=0;std::istringstream checksumStream(bytes.substr(end+9));if(!(checksumStream>>checksum))return LoadError::Corrupt;checksumStream>>std::ws;if(!checksumStream.eof()||Hash(bytes.substr(0,end))!=checksum)return LoadError::Corrupt;
    std::istringstream i(bytes.substr(0,end));std::string magic;int schema,content,startedValue;
    if(!(i>>magic>>schema>>content)||magic!="DAWN_SAVE")return LoadError::Corrupt;
    if(schema!=SchemaVersion)return LoadError::SchemaMismatch;
    if(content!=ContentVersion)return LoadError::ContentMismatch;
    Session candidate;if(!(i>>startedValue)||startedValue<0||startedValue>1||!codec::ReadWorld(i,candidate.world))return LoadError::Corrupt;candidate.started=startedValue!=0;
    size_t n;if(!codec::Count(i,n)||n>2)return LoadError::Corrupt;
    for(size_t k=0;k<n;k++){std::string id;World w;if(!codec::S(i,id)||(id!="CP01"&&id!="CP02")||!codec::ReadWorld(i,w)||w.checkpoint!=id||(id=="CP01"&&(w.stage!="Choice1"||w.node!="Choice_01"))||(id=="CP02"&&(w.stage!="Choice2"||w.node!="Choice_02"))||!candidate.checkpoints.emplace(id,w).second)return LoadError::Corrupt;}
    if(!codec::Set(i,candidate.meta.clues)||!codec::Set(i,candidate.meta.endings)||!codec::Set(i,candidate.meta.memories)||!codec::Set(i,candidate.meta.scenes))return LoadError::Corrupt;
    const std::set<std::string> clueIds={"Net","Boat","Stone","ShoreClue"};
    const std::set<std::string> endingIds={"Ending_Together","Ending_Witness","Ending_Departure"};
    const std::set<std::string> memoryIds={"Memory_Net","Memory_Boat","Memory_Stone","Memory_SharedWork","Memory_Shore","Memory_Together","Memory_Witness","Memory_Departure"};
    const std::set<std::string> sceneIds={"Intro","Scene"};
    for(const auto& v:candidate.meta.clues)if(!clueIds.count(v))return LoadError::Corrupt;
    for(const auto& v:candidate.meta.endings)if(!endingIds.count(v))return LoadError::Corrupt;
    for(const auto& v:candidate.meta.memories)if(!memoryIds.count(v))return LoadError::Corrupt;
    for(const auto& v:candidate.meta.scenes)if(!sceneIds.count(v))return LoadError::Corrupt;
    i>>std::ws;if(!i.eof())return LoadError::Corrupt;
    candidate.generation=out.generation+1;out=std::move(candidate);return LoadError::None;
}
} // namespace dawn
