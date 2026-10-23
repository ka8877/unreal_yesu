#include "DawnNarrativeSubsystem.h"
#include "DawnSaveGame.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"
#include "Misc/DateTime.h"
#include "Misc/Guid.h"

namespace {
std::string Utf8(const FString& Value) { return std::string(TCHAR_TO_UTF8(*Value)); }
std::string Id(FName Value) { return Utf8(Value.ToString()); }
FName Name(const std::string& Value) { return FName(UTF8_TO_TCHAR(Value.c_str())); }
FText LoadMessage(dawn::LoadError Error)
{
    switch(Error) {
    case dawn::LoadError::SchemaMismatch:return NSLOCTEXT("Dawn", "SaveSchema", "저장 형식이 현재 게임과 다릅니다. 원본을 보존했습니다.");
    case dawn::LoadError::ContentMismatch:return NSLOCTEXT("Dawn", "SaveContent", "저장된 서사 버전이 현재 게임과 다릅니다. 원본을 보존했습니다.");
    default:return NSLOCTEXT("Dawn", "SaveCorrupt", "저장 데이터를 읽을 수 없습니다. 원본을 덮어쓰지 않았습니다. 백업 복구를 선택할 수 있습니다.");
    }
}
}
FString UDawnNarrativeSubsystem::SlotName() { return TEXT("PathOfDawn_Progress_v1"); }
void UDawnNarrativeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Data=LoadObject<UDawnNarrativeData>(nullptr,TEXT("/Game/PathOfDawn/Narrative/DA_DawnNarrative.DA_DawnNarrative"));
    FString Error;
    bDataValid=Data && Data->Validate(Error);
    if(!bDataValid) LastError=NSLOCTEXT("Dawn","MissingContent","대화 에셋이 없거나 유효하지 않습니다. 에디터 에셋 생성과 Cook을 확인하세요.");
    if(UGameplayStatics::DoesSaveGameExist(SlotName(),0))
    {
        FText LoadError;
        bHasValidSave=LoadSlot(SlotName(),Session,LoadError);
        if(!bHasValidSave){bSaveLocked=true;LastError=LoadError;}
    }
    UE_LOG(LogTemp,Display,TEXT("PathOfDawn save slots under %sSaveGames. Schema=%d Content=%d"),*FPaths::ProjectSavedDir(),dawn::SchemaVersion,dawn::ContentVersion);
}
bool UDawnNarrativeSubsystem::Ready()
{
    if(!bDataValid) {LastError=NSLOCTEXT("Dawn","MissingContent","대화 에셋이 없거나 유효하지 않습니다. 에디터 에셋 생성과 Cook을 확인하세요.");OnChanged.Broadcast();return false;}
    return !IsBusy();
}
bool UDawnNarrativeSubsystem::Changed(bool bResult,bool bPersist)
{
    if(!bResult)return false;
    OnChanged.Broadcast();
    if(bPersist)Save(); // Save publishes after its transaction lock has been released.
    return true;
}
bool UDawnNarrativeSubsystem::NewGame()
{
    if(!Ready())return false;
    bRestoring=true;OnBeforeRestore.Broadcast();Session.NewGame();OnRestored.Broadcast();bRestoring=false;
    return Changed(true);
}
bool UDawnNarrativeSubsystem::ContinueGame()
{
    if(!Ready())return false;
    dawn::Session Loaded;FText Error;
    if(!LoadSlot(SlotName(),Loaded,Error)){LastError=Error;bSaveLocked=true;bHasValidSave=false;OnChanged.Broadcast();return false;}
    bRestoring=true;OnBeforeRestore.Broadcast();Loaded.generation=Session.generation+1;Session=std::move(Loaded);OnRestored.Broadcast();bRestoring=false;bHasValidSave=true;bSaveLocked=false;LastError=FText::GetEmpty();
    return Changed(true,false);
}
bool UDawnNarrativeSubsystem::Inspect(FName ActorId)
{
    if(!Ready())return false;
    // A spatial interaction may create CP02. Capture positions before that value snapshot.
    CaptureWorldActors();
    const bool bResult=Session.Inspect(Id(ActorId));
    if(!bResult && ActorId==TEXT("Simon") && Session.world.stage=="Explore")
    {
        LastError=NSLOCTEXT("Dawn","ExploreFirst","시몬에게 말을 걸기 전에 그물·배·물가의 돌을 살펴보세요.");OnChanged.Broadcast();
    }
    else if(bResult) LastError=FText::GetEmpty();
    return Changed(bResult);
}
bool UDawnNarrativeSubsystem::Advance()
{
    if(!Ready())return false;
    const FDawnDialogueNode* Node=Data->Find(GetNodeId());
    if(!Node||Node->NextNode.IsNone())return false;
    CaptureWorldActors();
    return Changed(Session.Advance(Session.world.node,Id(Node->NextNode)));
}
bool UDawnNarrativeSubsystem::Choose(int32 Index)
{
    if(!Ready())return false;
    const FDawnDialogueNode* Node=Data->Find(GetNodeId());
    if(!Node||!Node->Choices.IsValidIndex(Index))return false;
    return Changed(Session.Choose(Index,Session.generation,Session.world.node));
}
bool UDawnNarrativeSubsystem::Rewind(FName Checkpoint)
{
    if(!Ready()||!HasCheckpoint(Checkpoint))return false;
    bRestoring=true;OnBeforeRestore.Broadcast();
    const bool bResult=Session.Rewind(Id(Checkpoint));
    if(bResult)OnRestored.Broadcast();
    bRestoring=false;return Changed(bResult);
}
void UDawnNarrativeSubsystem::FinishIntro()
{
    if(!Ready()||Session.world.stage!="Intro")return;
    Session.FinishIntro();Changed(true);
}
void UDawnNarrativeSubsystem::FinishScene(int64 Generation)
{
    if(!Ready()||!Session.CallbackIsCurrent(static_cast<uint64_t>(Generation))||Session.world.stage!="Scene"||!HasSeenScene(TEXT("Scene")))return;
    // Skipping an already seen scene still returns control at its spatial endpoint.
    CaptureWorldActors();Changed(Session.EnterNode("Task_ReturnToSimon"));
}
void UDawnNarrativeSubsystem::ResetMemories(bool Confirm)
{
    if(!Ready()||!Confirm)return;
    Session.ResetMemories(true);Changed(true);
}
void UDawnNarrativeSubsystem::CaptureWorldActors()
{
    UWorld* World=GetWorld();if(!World||bRestoring)return;
    if(APawn* Pawn=UGameplayStatics::GetPlayerPawn(World,0))RecordActor(TEXT("Player"),Pawn->GetActorTransform());
    for(TActorIterator<AActor> It(World);It;++It)
        for(FName Tag:It->Tags)
        {
            const FString Value=Tag.ToString();
            if(Value.StartsWith(TEXT("DawnId:")))RecordActor(FName(*Value.RightChop(7)),It->GetActorTransform());
        }
}
void UDawnNarrativeSubsystem::RecordActor(FName ActorId,const FTransform& Transform)
{
    if(bRestoring||Session.busy||ActorId.IsNone())return;
    const FVector L=Transform.GetLocation(),S=Transform.GetScale3D();const FRotator R=Transform.Rotator();
    Session.world.actors[Id(ActorId)]={L.X,L.Y,L.Z,R.Pitch,R.Yaw,R.Roll,S.X,S.Y,S.Z};
}
bool UDawnNarrativeSubsystem::GetActorTransform(FName ActorId,FTransform& OutTransform) const
{
    auto It=Session.world.actors.find(Id(ActorId));if(It==Session.world.actors.end())return false;
    const dawn::Pose& P=It->second;OutTransform=FTransform(FRotator(P.pitch,P.yaw,P.roll),FVector(P.x,P.y,P.z),FVector(P.sx,P.sy,P.sz));return true;
}
bool UDawnNarrativeSubsystem::LoadSlot(const FString& Slot,dawn::Session& Result,FText& Error) const
{
    UDawnSaveGame* Save=Cast<UDawnSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save){Error=LoadMessage(dawn::LoadError::Corrupt);return false;}
    if(Save->SchemaVersion!=dawn::SchemaVersion){Error=LoadMessage(dawn::LoadError::SchemaMismatch);return false;}
    if(Save->ContentVersion!=dawn::ContentVersion){Error=LoadMessage(dawn::LoadError::ContentMismatch);return false;}
    const dawn::LoadError ResultCode=dawn::Session::Deserialize(Utf8(Save->Payload),Result);
    if(ResultCode!=dawn::LoadError::None){Error=LoadMessage(ResultCode);return false;}
    if(Data && !Data->Find(Name(Result.world.node))){Error=LoadMessage(dawn::LoadError::ContentMismatch);return false;}
    return true;
}
bool UDawnNarrativeSubsystem::Save()
{
    if(bSaving||bRestoring||Session.busy||!Session.started)return false;
    // Every write/error exit returns from this inner transaction first. Its guard
    // is destroyed before observers rebuild input state, including manual Save.
    const bool bSaved=[this]()
    {
        if(bSaveLocked)
        {
            if(LastError.IsEmpty())LastError=NSLOCTEXT("Dawn","SaveLocked","기존 저장 파일을 보호하고 있어 자동 저장이 중단되었습니다. 백업 복구를 확인하세요.");
            return false;
        }
        TGuardValue<bool> Guard(bSaving,true);
        CaptureWorldActors();
        UDawnSaveGame* NewSave=Cast<UDawnSaveGame>(UGameplayStatics::CreateSaveGameObject(UDawnSaveGame::StaticClass()));
        NewSave->SchemaVersion=dawn::SchemaVersion;
        NewSave->ContentVersion=dawn::ContentVersion;
        NewSave->Payload=UTF8_TO_TCHAR(Session.Serialize().c_str());
        const FString Main=SlotName(),Pending=Main+TEXT("_Pending"),Backup=Main+TEXT("_Backup");
        // Validate active before replacing its backup. An unreadable active slot locks further writes.
        UDawnSaveGame* OldSave=nullptr;
        if(UGameplayStatics::DoesSaveGameExist(Main,0))
        {
            dawn::Session Old;FText Error;
            if(!LoadSlot(Main,Old,Error)){bSaveLocked=true;LastError=Error;return false;}
            OldSave=Cast<UDawnSaveGame>(UGameplayStatics::LoadGameFromSlot(Main,0));
        }
        auto Fail=[this]() { LastError=NSLOCTEXT("Dawn","SaveFailed","저장에 실패했습니다. 백업이 있으면 복구할 수 있습니다. 저장 공간과 권한을 확인하세요.");return false; };
        if(!UGameplayStatics::SaveGameToSlot(NewSave,Pending,0))return Fail();
        dawn::Session Readback;FText Error;
        if(!LoadSlot(Pending,Readback,Error))return Fail();
        if(OldSave&&!UGameplayStatics::SaveGameToSlot(OldSave,Backup,0))return Fail();
        if(!UGameplayStatics::SaveGameToSlot(NewSave,Main,0)||!LoadSlot(Main,Readback,Error))
        {
            if(OldSave)UGameplayStatics::SaveGameToSlot(OldSave,Main,0);
            return Fail();
        }
        UGameplayStatics::DeleteGameInSlot(Pending,0);bHasValidSave=true;
        LastError=FText::GetEmpty();return true;
    }();
    // Current observers only refresh world/UI/input; they do not call Save.
    OnChanged.Broadcast();
    return bSaved;
}
bool UDawnNarrativeSubsystem::RecoverBackup()
{
    if(bSaving||bRestoring)return false;
    dawn::Session Recovered;FText Error;const FString Main=SlotName(),Backup=Main+TEXT("_Backup");
    if(!LoadSlot(Backup,Recovered,Error)){LastError=Error;OnChanged.Broadcast();return false;}
    TArray<uint8> Rejected;
    if(UGameplayStatics::DoesSaveGameExist(Main,0) && (!UGameplayStatics::LoadDataFromSlot(Rejected,Main,0) || !UGameplayStatics::SaveDataToSlot(Rejected,Main+TEXT("_Rejected_")+FDateTime::UtcNow().ToString(TEXT("%Y%m%d_%H%M%S"))+TEXT("_")+FGuid::NewGuid().ToString(EGuidFormats::Digits),0)))
    {LastError=NSLOCTEXT("Dawn","RecoveryArchiveFailed","기존 저장 보관에 실패하여 복구를 중단했습니다.");OnChanged.Broadcast();return false;}
    UDawnSaveGame* Valid=Cast<UDawnSaveGame>(UGameplayStatics::LoadGameFromSlot(Backup,0));
    if(!UGameplayStatics::SaveGameToSlot(Valid,Main,0)){LastError=NSLOCTEXT("Dawn","RecoveryFailed","백업을 정상 저장 위치에 복구하지 못했습니다.");OnChanged.Broadcast();return false;}
    bSaveLocked=false;bHasValidSave=true;LastError=FText::GetEmpty();return ContinueGame();
}
FDawnDialogueNode UDawnNarrativeSubsystem::GetCurrentNode() const
{
    if(Data)if(const FDawnDialogueNode* Found=Data->Find(GetNodeId()))
    {FDawnDialogueNode Result=*Found;if(!Session.meta.endings.empty()&&!Result.RepeatText.IsEmpty())Result.Text=Result.RepeatText;return Result;}
    return FDawnDialogueNode();
}
FName UDawnNarrativeSubsystem::GetNodeId() const{return Name(Session.world.node);}
FName UDawnNarrativeSubsystem::GetStage() const{return Name(Session.world.stage);}
FName UDawnNarrativeSubsystem::GetEndingId() const{return Name(Session.world.ending);}
FText UDawnNarrativeSubsystem::GetObjective() const
{
    if(Session.world.stage=="Task" && Data)
        if(const FDawnDialogueNode* Task=Data->Find(GetNodeId()))return Task->Text;
    if(Session.world.stage=="Explore")
    {
        if(!Session.world.inspected.count("Net"))return NSLOCTEXT("Dawn","ObjectiveNet","낡은 그물을 살펴보세요 · E 조사");
        if(!Session.world.inspected.count("Boat"))return NSLOCTEXT("Dawn","ObjectiveBoat","호숫가의 작은 배를 살펴보세요");
        if(!Session.world.inspected.count("Stone"))return NSLOCTEXT("Dawn","ObjectiveStone","물가의 돌을 살펴보세요");
        return NSLOCTEXT("Dawn","ObjectiveSimon","그물 곁에 있는 시몬에게 말을 걸어보세요");
    }
    if(Session.world.stage=="Ending")return NSLOCTEXT("Dawn","ObjectiveRewind","기억을 간직한 채 다른 아침으로 돌아갈 수 있습니다");
    return NSLOCTEXT("Dawn","ObjectiveListen","그 아침의 이야기에 귀를 기울여 보세요");
}
bool UDawnNarrativeSubsystem::HasCheckpoint(FName IdValue) const{return Session.checkpoints.count(Id(IdValue))>0;}
bool UDawnNarrativeSubsystem::CanContinue() const{return bHasValidSave;}
bool UDawnNarrativeSubsystem::IsBusy() const{return bRestoring||bSaving||Session.busy;}
bool UDawnNarrativeSubsystem::GetFlag(FName IdValue) const{return Session.Flag(Id(IdValue));}
bool UDawnNarrativeSubsystem::IsInspected(FName IdValue) const{return Session.world.inspected.count(Id(IdValue))>0;}
int32 UDawnNarrativeSubsystem::GetItemCount(FName IdValue) const{return Session.Item(Id(IdValue));}
int32 UDawnNarrativeSubsystem::GetRelationship(FName IdValue) const{return Session.Relationship(Id(IdValue));}
TArray<FName> UDawnNarrativeSubsystem::GetMemories() const {TArray<FName> Result;for(const auto& Value:Session.meta.memories)Result.Add(Name(Value));return Result;}
TArray<FName> UDawnNarrativeSubsystem::GetSeenEndings() const {TArray<FName> Result;for(const auto& Value:Session.meta.endings)Result.Add(Name(Value));return Result;}
TArray<FName> UDawnNarrativeSubsystem::GetChoiceHistory() const {TArray<FName> Result;for(const auto& Value:Session.world.choices)Result.Add(Name(Value));return Result;}
bool UDawnNarrativeSubsystem::HasSeenScene(FName IdValue) const{return Session.meta.scenes.count(Id(IdValue))>0;}
int64 UDawnNarrativeSubsystem::GetGeneration() const{return static_cast<int64>(Session.generation);}
