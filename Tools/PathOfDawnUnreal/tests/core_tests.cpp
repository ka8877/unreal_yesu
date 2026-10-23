#define check(expression) static_assert(false, "Unreal check macro collision")
#include "DawnState.h"
#undef check
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <cstdio>
#include <functional>
using dawn::Session;
static int checks=0;
#define REQUIRE(x) do{++checks;if(!(x)){std::cerr<<"FAIL line "<<__LINE__<<": " #x "\n";std::exit(1);}}while(0)
static void Explore(Session& s){s.NewGame();s.FinishIntro();for(const char* id:{"Net","Boat","Stone"}){REQUIRE(s.Inspect(id));REQUIRE(s.Advance(s.world.node,"Explore"));}}
static void FirstCheckpoint(Session& s){Explore(s);REQUIRE(s.Inspect("Simon"));REQUIRE(s.Advance("Simon_Greeting","Choice_01"));REQUIRE(s.checkpoints.count("CP01"));}
static void Roundtrip(const Session& s) {
    Session loaded;const auto bytes=s.Serialize();
    REQUIRE(dawn::ValidateWorld(s.world));
    REQUIRE(Session::Deserialize(bytes,loaded)==dawn::LoadError::None);
    REQUIRE(loaded.Serialize()==bytes);
}
static void FirstChoice(Session&s,int choice){
    REQUIRE(s.Choose(choice,s.generation,"Choice_01"));
    REQUIRE(s.world.node==(choice==0?"Task_HelpNet":"Task_ObserveShore"));
    REQUIRE(s.world.stage=="Task");Roundtrip(s);
    const auto waiting=s.Serialize();const auto epoch=s.generation;
    REQUIRE(!s.Inspect("Village"));REQUIRE(!s.Advance(s.world.node,"Scene_Teaching"));
    REQUIRE(s.Serialize()==waiting);
    REQUIRE(s.Inspect(choice==0?"Net":"Stone"));
    REQUIRE(!s.CallbackIsCurrent(epoch));
    REQUIRE(s.Advance(s.world.node,"Scene_Teaching"));
    REQUIRE(!s.Advance("Scene_Teaching","Choice_02"));
    REQUIRE(s.Advance("Scene_Teaching","Traveler_Crossroads"));
    REQUIRE(s.Advance("Traveler_Crossroads","Task_ReturnToSimon"));
    REQUIRE(s.world.stage=="Task");REQUIRE(!s.checkpoints.count("CP02"));Roundtrip(s);
    REQUIRE(!s.Advance(s.world.node,"Choice_02"));REQUIRE(!s.Inspect("Net"));
    REQUIRE(s.Inspect("Simon"));REQUIRE(s.checkpoints.count("CP02"));
}
static void FinishDeparture(Session& s) {
    REQUIRE(s.world.node=="Task_Departure");REQUIRE(s.world.stage=="Task");
    REQUIRE(s.world.ending.empty());REQUIRE(!s.Flag("WalkedToVillage"));REQUIRE(!s.Flag("StayedWithSimon"));
    Roundtrip(s);const auto pending=s.Serialize();
    REQUIRE(!s.Inspect("Simon"));REQUIRE(!s.Advance(s.world.node,"Ending_Departure"));REQUIRE(s.Serialize()==pending);
    REQUIRE(s.Inspect("Village"));REQUIRE(s.Flag("WalkedToVillage"));REQUIRE(s.world.ending=="Ending_Departure");
    const auto finished=s.Serialize();REQUIRE(!s.Inspect("Village"));REQUIRE(s.Serialize()==finished);
}
static std::string Rechecksum(std::string body){auto at=body.rfind("CHECKSUM ");if(at!=std::string::npos)body.resize(at);return body+"CHECKSUM "+std::to_string(dawn::Hash(body))+"\n";}
int main(){
    for(int a=0;a<2;a++)for(int b=0;b<2;b++){
        Session s;FirstCheckpoint(s);FirstChoice(s,a);const auto generation=s.generation;
        REQUIRE(s.Choose(b,generation,"Choice_02"));
        if(b==1){REQUIRE(s.meta.endings.empty());REQUIRE(!s.meta.memories.count("Memory_Departure"));FinishDeparture(s);}
        REQUIRE(s.world.ending==(b==1?"Ending_Departure":(a==0?"Ending_Together":"Ending_Witness")));
        REQUIRE(s.meta.endings.size()==1);REQUIRE(dawn::ValidateWorld(s.world));
        const std::string saved=s.Serialize();Session loaded;
        REQUIRE(Session::Deserialize(saved,loaded)==dawn::LoadError::None);
        REQUIRE(loaded.Serialize()==saved);REQUIRE(loaded.checkpoints.size()==2);
        REQUIRE(!s.Choose(b,generation,"Choice_02"));REQUIRE(s.meta.endings.size()==1);
    }
    {
        Session s;FirstCheckpoint(s);s.world.actors["Player"]={120,34,56,0,90,0,1,1,1};s.Capture("CP01");
        const auto epoch=s.generation;REQUIRE(s.Choose(0,epoch,"Choice_01"));
        REQUIRE(s.Item("Rope")==0);REQUIRE(s.Relationship("Simon")==1);REQUIRE(s.Flag("NetPrepared"));
        REQUIRE(!s.Choose(0,epoch,"Choice_01"));REQUIRE(s.Item("Rope")==0);REQUIRE(s.Relationship("Simon")==1);
        s.world.actors["Player"].x=900;s.world.inspected.insert("NotARealObject");
        REQUIRE(s.Rewind("CP01"));REQUIRE(s.Item("Rope")==1);REQUIRE(s.Relationship("Simon")==0);REQUIRE(!s.Flag("NetPrepared"));REQUIRE(!s.Flag("ShoreClueFound"));
        REQUIRE(s.world.actors.at("Player").x==120);REQUIRE(!s.world.inspected.count("NotARealObject"));REQUIRE(s.world.choices.empty());
        REQUIRE(!s.CallbackIsCurrent(epoch));REQUIRE(s.meta.memories.count("Memory_SharedWork"));
        FirstChoice(s,1);REQUIRE(s.Item("Rope")==1);REQUIRE(s.Flag("ShoreClueFound"));REQUIRE(!s.Flag("NetPrepared"));
        REQUIRE(s.Choose(0,s.generation,"Choice_02"));REQUIRE(s.world.ending=="Ending_Witness");
        const auto memories=s.meta.memories;REQUIRE(s.Rewind("CP02"));REQUIRE(s.world.choices.size()==1);REQUIRE(s.Flag("ShoreClueFound"));REQUIRE(s.meta.memories==memories);
        REQUIRE(s.Choose(1,s.generation,"Choice_02"));REQUIRE(s.meta.endings.size()==1);FinishDeparture(s);REQUIRE(s.meta.endings.size()==2);
        REQUIRE(s.Rewind("CP01"));REQUIRE(!s.checkpoints.count("CP02"));FirstChoice(s,0);REQUIRE(!s.Flag("ShoreClueFound"));
        REQUIRE(s.Choose(0,s.generation,"Choice_02"));REQUIRE(s.meta.endings.size()==3);
        const auto endings=s.meta.endings;s.NewGame();REQUIRE(s.meta.endings==endings);REQUIRE(s.checkpoints.empty());REQUIRE(s.world.items.empty());
        s.ResetMemories(false);REQUIRE(s.meta.endings==endings);s.ResetMemories(true);REQUIRE(s.meta.endings.empty());
    }
    {
        Session s;s.NewGame();s.FinishIntro();REQUIRE(!s.Inspect("Simon"));REQUIRE(!s.Inspect("Jesus"));
        REQUIRE(s.Inspect("Net"));REQUIRE(!s.Inspect("Net"));REQUIRE(s.Advance(s.world.node,"Explore"));REQUIRE(s.Inspect("Net"));REQUIRE(s.Item("Rope")==1);REQUIRE(s.meta.memories.size()==1);
        REQUIRE(!s.EnterNode("Choice_01"));REQUIRE(!s.Choose(-1,s.generation,s.world.node));
        const auto before=s.Serialize();REQUIRE(!s.ApplyEffects({{dawn::EffectKind::ChangeRelationship,"Simon",1},{dawn::EffectKind::RemoveItem,"Rope",9}}));REQUIRE(s.Serialize()==before);
    }
    {
        Session s;s.NewGame();const auto introEpoch=s.generation;
        s.meta.endings.insert("Ending_Together");s.ResetMemories(true);
        REQUIRE(s.CallbackIsCurrent(introEpoch));REQUIRE(s.meta.endings.empty());
        s.FinishIntro();REQUIRE(s.world.stage=="Explore");
    }
    {
        Session s;Explore(s);REQUIRE(s.Inspect("Jesus"));REQUIRE(s.world.node=="Simon_Greeting");
    }
    {
        Session s;FirstCheckpoint(s);REQUIRE(s.Choose(0,s.generation,"Choice_01"));
        const auto epoch=s.generation;Session loaded;
        REQUIRE(Session::Deserialize(s.Serialize(),loaded)==dawn::LoadError::None);
        REQUIRE(loaded.Inspect("Net"));REQUIRE(loaded.Item("Rope")==0);REQUIRE(loaded.Relationship("Simon")==1);
        REQUIRE(!loaded.Inspect("Net"));REQUIRE(loaded.Relationship("Simon")==1);
        REQUIRE(s.Rewind("CP01"));REQUIRE(!s.CallbackIsCurrent(epoch));REQUIRE(!s.Inspect("Net"));
        REQUIRE(s.Item("Rope")==1);REQUIRE(s.Choose(1,s.generation,"Choice_01"));REQUIRE(s.world.node=="Task_ObserveShore");
        Session impossible=s;impossible.world.node="Task_HelpNet";
        REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        impossible=s;impossible.world.node="Task_Unknown";
        REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        s.NewGame();REQUIRE(s.world.node=="Intro_Arrival");REQUIRE(s.world.choices.empty());REQUIRE(s.checkpoints.empty());REQUIRE(s.Item("Rope")==0);
    }
    {
        Session s;FirstCheckpoint(s);FirstChoice(s,1);REQUIRE(s.Choose(1,s.generation,"Choice_02"));
        REQUIRE(s.world.node=="Task_Departure");const auto epoch=s.generation;
        REQUIRE(!s.Choose(1,epoch,"Choice_02"));REQUIRE(s.meta.endings.empty());
        Session loaded;REQUIRE(Session::Deserialize(s.Serialize(),loaded)==dawn::LoadError::None);FinishDeparture(loaded);
        Session impossible=s;impossible.world.flags["WalkedToVillage"]=true;
        REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        impossible=s;impossible.world.ending="Ending_Departure";
        REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        REQUIRE(s.Rewind("CP02"));REQUIRE(!s.CallbackIsCurrent(epoch));REQUIRE(!s.Inspect("Village"));REQUIRE(s.meta.endings.empty());
        REQUIRE(s.Choose(0,s.generation,"Choice_02"));REQUIRE(s.world.ending=="Ending_Witness");REQUIRE(!s.Flag("WalkedToVillage"));
    }
    {
        Session s;FirstCheckpoint(s);FirstChoice(s,0);const auto good=s.Serialize();Session loaded;
        std::string corrupt=good;corrupt[20]^=1;REQUIRE(Session::Deserialize(corrupt,loaded)==dawn::LoadError::Corrupt);
        REQUIRE(Session::Deserialize(good.substr(0,good.size()/2),loaded)==dawn::LoadError::Corrupt);
        REQUIRE(Session::Deserialize(good+"TRAILING",loaded)==dawn::LoadError::Corrupt);
        std::string schema=good;schema.replace(10,1,"9");REQUIRE(Session::Deserialize(Rechecksum(schema),loaded)==dawn::LoadError::SchemaMismatch);
        std::string content=good;content.replace(12,1,"1");REQUIRE(Session::Deserialize(Rechecksum(content),loaded)==dawn::LoadError::ContentMismatch);
        Session impossible=s;impossible.world.items["Rope"]=99;REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        impossible=s;impossible.checkpoints.at("CP01").stage="Ending";REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        impossible=s;impossible.world.stage="Explore";REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        impossible=s;impossible.meta.endings.insert("Ending_Fourth");REQUIRE(Session::Deserialize(impossible.Serialize(),loaded)==dawn::LoadError::Corrupt);
        REQUIRE(Session::Deserialize(good,loaded)==dawn::LoadError::None);const auto preserved=loaded.Serialize();REQUIRE(Session::Deserialize(corrupt,loaded)==dawn::LoadError::Corrupt);REQUIRE(loaded.Serialize()==preserved);
        // Persist bytes, create a fresh Session (same format used inside USaveGame), and restore.
        const char* path="dawn_core_test_save.tmp";{std::ofstream file(path,std::ios::binary);file<<good;REQUIRE(file.good());}
        std::ifstream file(path,std::ios::binary);const std::string bytes((std::istreambuf_iterator<char>(file)),{});Session fresh;
        REQUIRE(Session::Deserialize(bytes,fresh)==dawn::LoadError::None);REQUIRE(fresh.Serialize()==good);file.close();REQUIRE(std::remove(path)==0);
    }
    std::cout<<"PASS "<<checks<<" assertions: 4 routes/3 endings, spatial tasks and pending departure, duplicate input, value checkpoints, stale callbacks, branch isolation, meta persistence, fresh-session disk roundtrip, corrupt/version rejection.\n";
    return 0;
}
