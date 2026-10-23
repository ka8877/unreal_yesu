#include <iostream>
#include <cstdint>
#include "DawnState.h"
#define TEXT(s) s
using uint64=uint64_t;
int checks=0,errors=0;
void TestTrue(const char* m,bool v){++checks;if(!v){++errors;std::cerr<<m<<"\n";}}
void TestFalse(const char* m,bool v){TestTrue(m,!v);}
void TestEqual(const char* m,int a,int b){TestTrue(m,a==b);}
bool RunBranches()
{
    for(int A=0;A<2;++A)for(int B=0;B<2;++B)
    {
        dawn::Session S;S.NewGame();S.FinishIntro();
        for(const char* Id:{"Net","Boat","Stone"}){S.Inspect(Id);S.Advance(S.world.node,"Explore");}
        S.Inspect("Simon");S.Advance(S.world.node,"Choice_01");
        TestTrue(TEXT("CP01 exists"),S.checkpoints.count("CP01")>0);
        const uint64 Epoch=S.generation;
        TestTrue(TEXT("First choice accepted"),S.Choose(A,Epoch,"Choice_01"));
        TestFalse(TEXT("Duplicate choice rejected"),S.Choose(A,Epoch,"Choice_01"));
        TestTrue(TEXT("Choice requires physical followthrough"),S.world.stage=="Task");
        TestFalse(TEXT("Task cannot be advanced by dialogue input"),S.Advance(S.world.node,"Scene_Teaching"));
        TestTrue(TEXT("Correct target completes first task"),S.Inspect(A==0?"Net":"Stone"));
        S.Advance(S.world.node,"Scene_Teaching");S.Advance(S.world.node,"Traveler_Crossroads");S.Advance(S.world.node,"Task_ReturnToSimon");
        TestFalse(TEXT("No CP02 until returning to Simon"),S.checkpoints.count("CP02")>0);
        TestTrue(TEXT("Simon creates CP02"),S.Inspect("Simon"));
        S.Choose(B,S.generation,"Choice_02");
        if(B==1)
        {
            TestTrue(TEXT("Departure awaits Village"),S.world.node=="Task_Departure");
            TestTrue(TEXT("No ending before walking"),S.world.ending.empty()&&S.meta.endings.empty());
            TestFalse(TEXT("Village flag deferred"),S.Flag("WalkedToVillage"));
            TestTrue(TEXT("Village finalizes departure"),S.Inspect("Village"));
            TestFalse(TEXT("Duplicate Village input ignored"),S.Inspect("Village"));
        }
        const std::string Expected=B==1?"Ending_Departure":(A==0?"Ending_Together":"Ending_Witness");
        TestTrue(TEXT("Correct ending"),S.world.ending==Expected);
        TestTrue(TEXT("CP01 restoration"),S.Rewind("CP01"));
        TestEqual(TEXT("Rope restored"),S.Item("Rope"),1);
        TestEqual(TEXT("Relationship restored"),S.Relationship("Simon"),0);
        TestFalse(TEXT("Prepared net cleared"),S.Flag("NetPrepared"));
        TestTrue(TEXT("Memory retained"),S.meta.endings.count(Expected)>0);
    }
    return true;
}
int main(){RunBranches();
    dawn::Session Before;Before.NewGame();Before.FinishIntro();
    for(const char* Id:{"Net","Boat","Stone"}){Before.Inspect(Id);Before.Advance(Before.world.node,"Explore");}
    Before.Inspect("Simon");Before.Advance(Before.world.node,"Choice_01");Before.Choose(1,Before.generation,"Choice_01");Before.Inspect("Stone");
    Before.Advance(Before.world.node,"Scene_Teaching");Before.Advance(Before.world.node,"Task_ReturnToSimon");Before.Inspect("Simon");
    Before.Choose(1,Before.generation,"Choice_02");

 dawn::Session After;
 TestTrue("Portable part of USaveGame test payload valid",dawn::Session::Deserialize(Before.Serialize(),After)==dawn::LoadError::None);
 TestTrue("Pending departure preserved",After.world.node=="Task_Departure");
 TestTrue("Memory preserved",After.meta.memories.count("Memory_Net")>0);
 TestTrue("Rope preserved",After.Item("Rope")==1);
 TestTrue("Village resumes",After.Inspect("Village"));
 TestTrue("Result after resume",After.meta.endings.count("Ending_Departure")>0);
 std::cout<<"Automation source core-path replay: "<<checks<<" checks, "<<errors<<" errors. No Unreal or USaveGame API exercised.\n";
 return errors?1:0;}
