#include "DawnGospelSubsystem.h"
#include "DawnGospelSaveGame.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/DateTime.h"
#include "Misc/Guid.h"

namespace
{
std::string Utf8(const FString& Value) { return std::string(TCHAR_TO_UTF8(*Value)); }
std::string Id(FName Value) { return Utf8(Value.ToString()); }
FName Name(const std::string& Value) { return FName(UTF8_TO_TCHAR(Value.c_str())); }

FName StageName(gospel::Stage Stage)
{
    switch (Stage)
    {
    case gospel::Stage::Travel: return TEXT("Travel");
    case gospel::Stage::Talk: return TEXT("Talk");
    case gospel::Stage::Reading: return TEXT("Reading");
    default: return TEXT("Complete");
    }
}
bool ReadStage(FName Name, gospel::Stage& Result)
{
    if (Name == TEXT("Travel")) Result = gospel::Stage::Travel;
    else if (Name == TEXT("Talk")) Result = gospel::Stage::Talk;
    else if (Name == TEXT("Reading")) Result = gospel::Stage::Reading;
    else if (Name == TEXT("Complete")) Result = gospel::Stage::Complete;
    else return false;
    return true;
}
bool ValidTransform(const FTransform& Transform)
{
    // NaNs, invalid quaternions or a manipulated scale must never teleport a pawn.
    return Transform.IsValid() && Transform.GetRotation().IsNormalized() &&
           Transform.GetLocation().GetAbsMax() <= 100000000.0 &&
           Transform.GetScale3D().Equals(FVector::OneVector, 0.001);
}
bool SameState(const gospel::State& A, const gospel::State& B)
{
    return A.schemaVersion == B.schemaVersion && A.campaignId == B.campaignId &&
           A.contentVersion == B.contentVersion && A.scopeStart == B.scopeStart &&
           A.scopeEnd == B.scopeEnd && A.questIndex == B.questIndex &&
           A.beatIndex == B.beatIndex && A.stage == B.stage && A.discovered == B.discovered;
}
FText CorruptSave()
{
    return NSLOCTEXT("DawnGospel", "CorruptSave", "저장을 읽을 수 없거나 현재 이야기와 맞지 않습니다. 원본을 보존했습니다. 백업 복구를 선택할 수 있습니다.");
}
}

FString UDawnGospelSubsystem::SlotName() { return TEXT("PathOfDawn_Gospel_Progress_v1"); }

void UDawnGospelSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Data = LoadObject<UDawnGospelData>(nullptr, TEXT("/Game/PathOfDawnGospel/Data/DA_GospelCampaign.DA_GospelCampaign"));
    FString ValidationError;
    bDataValid = Data && Data->Validate(ValidationError);
    if (bDataValid)
    {
        gospel::Campaign Definition;
        Definition.id = Id(Data->CampaignId);
        Definition.contentVersion = Data->ContentVersion;
        for (const FDawnGospelQuest& Quest : Data->Quests)
        {
            gospel::Quest Entry;
            Entry.id = Id(Quest.Id); Entry.chapterId = Id(Quest.ChapterId);
            Entry.npcId = Id(Quest.NpcId);
            Entry.readingId = Quest.ReadingId.IsNone() ? std::string() : Id(Quest.ReadingId);
            Entry.isPrologue = Quest.bIsPrologue;
            Entry.beatCount = static_cast<size_t>(Quest.Beats.Num());
            Definition.quests.push_back(std::move(Entry));
        }
        bDataValid = Session.Configure(Definition);
    }
    if (!bDataValid)
    {
        LastError = NSLOCTEXT("DawnGospel", "MissingData", "복음서 이야기 에셋이 없거나 유효하지 않습니다. Gospel 에셋 생성·검증과 Cook을 확인하세요.");
        // This subsystem also exists in the preserved Galilee game. Missing new
        // campaign assets must not turn its unrelated automation runs into errors.
        UE_LOG(LogTemp, Warning, TEXT("Gospel campaign unavailable: %s"), *ValidationError);
        return;
    }
    if (UGameplayStatics::DoesSaveGameExist(SlotName(), 0))
    {
        gospel::State Candidate; FTransform Transform; bool bHasTransform = false; FText Error;
        bHasValidSave = LoadSlot(SlotName(), Candidate, Transform, bHasTransform, Error);
        if (!bHasValidSave) { bSaveLocked = true; LastError = Error; }
    }
}

bool UDawnGospelSubsystem::Ready()
{
    if (bDataValid && !bSaving) return true;
    if (!bDataValid)
        LastError = NSLOCTEXT("DawnGospel", "MissingData", "복음서 이야기 에셋이 없거나 유효하지 않습니다. Gospel 에셋 생성·검증과 Cook을 확인하세요.");
    OnChanged.Broadcast();
    return false;
}

bool UDawnGospelSubsystem::Changed(bool bResult)
{
    if (!bResult)
    {
        LastError = NSLOCTEXT("DawnGospel", "TransitionRejected", "현재 목표를 확인하고 목적지의 인물과 이야기를 이어가세요.");
        OnChanged.Broadcast();
        return false;
    }
    LastError = FText::GetEmpty();
    Save(); // Publishes after the save transaction has released its guard.
    return true; // An accepted state transition remains accepted if disk persistence failed.
}

bool UDawnGospelSubsystem::NewGame(bool bTemplePreview)
{
    if (!Ready()) return false;
    if (bSaveLocked)
    {
        LastError = CorruptSave(); OnChanged.Broadcast(); return false;
    }
    // Recheck the actual slot so corruption introduced after initialization is protected too.
    if (UGameplayStatics::DoesSaveGameExist(SlotName(), 0))
    {
        gospel::State Existing; FTransform Transform; bool bHasTransform = false; FText Error;
        if (!LoadSlot(SlotName(), Existing, Transform, bHasTransform, Error))
        { bSaveLocked = true; bHasValidSave = false; LastError = Error; OnChanged.Broadcast(); return false; }
    }
    if (!Session.NewGame(bTemplePreview)) return Changed(false);
    bStarted = true; bHasPlayerTransform = false; PlayerTransform = FTransform::Identity;
    return Changed(true);
}

bool UDawnGospelSubsystem::ContinueGame()
{
    if (!Ready()) return false;
    gospel::State Loaded; FTransform Transform; bool bHasTransform = false; FText Error;
    if (!LoadSlot(SlotName(), Loaded, Transform, bHasTransform, Error))
    {
        bHasValidSave = false;
        bSaveLocked = UGameplayStatics::DoesSaveGameExist(SlotName(), 0);
        LastError = Error; OnChanged.Broadcast(); return false;
    }
    if (!Session.Restore(Loaded)) return Changed(false);
    bStarted = true; bHasPlayerTransform = bHasTransform; PlayerTransform = Transform;
    bHasValidSave = true; bSaveLocked = false; LastError = FText::GetEmpty();
    OnChanged.Broadcast(); return true;
}

bool UDawnGospelSubsystem::Arrive(FName QuestId, bool bWithinRange)
{
    if (!Ready() || !bStarted) return false;
    return Changed(Session.Arrive(Id(QuestId), bWithinRange));
}
bool UDawnGospelSubsystem::Talk(FName NpcId)
{
    if (!Ready() || !bStarted) return false;
    return Changed(Session.Talk(Id(NpcId)));
}
bool UDawnGospelSubsystem::Advance()
{
    if (!Ready() || !bStarted) return false;
    return Changed(Session.Advance());
}

void UDawnGospelSubsystem::RecordPlayerTransform(const FTransform& Transform)
{
    if (bStarted && !bSaving && ValidTransform(Transform))
    { PlayerTransform = Transform; bHasPlayerTransform = true; }
}
bool UDawnGospelSubsystem::GetPlayerTransform(FTransform& OutTransform) const
{
    if (!bStarted || !bHasPlayerTransform || !ValidTransform(PlayerTransform)) return false;
    OutTransform = PlayerTransform; return true;
}

bool UDawnGospelSubsystem::LoadSlot(const FString& Slot, gospel::State& Result, FTransform& Transform,
                                   bool& bHasTransform, FText& Error) const
{
    UDawnGospelSaveGame* Saved = Cast<UDawnGospelSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
    if (!Saved || !Data || Saved->SchemaVersion != 1 || Saved->CampaignId != Data->CampaignId ||
        Saved->ContentVersion != Data->ContentVersion || Saved->SourceCommit != Data->SourceCommit ||
        (Saved->bHasPlayerTransform && !ValidTransform(Saved->PlayerTransform)))
    { Error = CorruptSave(); return false; }
    gospel::State Candidate;
    Candidate.schemaVersion = Saved->SchemaVersion; Candidate.campaignId = Id(Saved->CampaignId);
    Candidate.contentVersion = Saved->ContentVersion; Candidate.scopeStart = Saved->ScopeStart;
    Candidate.scopeEnd = Saved->ScopeEnd; Candidate.questIndex = Saved->QuestIndex;
    Candidate.beatIndex = Saved->BeatIndex;
    if (!ReadStage(Saved->Stage, Candidate.stage)) { Error = CorruptSave(); return false; }
    for (FName Reading : Saved->DiscoveredReadings) Candidate.discovered.push_back(Id(Reading));
    std::string ValidationError;
    if (!Session.Validate(Candidate, ValidationError)) { Error = CorruptSave(); return false; }
    Result = std::move(Candidate);
    Transform = Saved->bHasPlayerTransform ? Saved->PlayerTransform : FTransform::Identity;
    bHasTransform = Saved->bHasPlayerTransform;
    Error = FText::GetEmpty(); return true;
}

UDawnGospelSaveGame* UDawnGospelSubsystem::CreateSave() const
{
    UDawnGospelSaveGame* Saved = Cast<UDawnGospelSaveGame>(UGameplayStatics::CreateSaveGameObject(UDawnGospelSaveGame::StaticClass()));
    if (!Saved) return nullptr;
    const gospel::State State = Session.Snapshot();
    Saved->SchemaVersion = State.schemaVersion; Saved->CampaignId = Name(State.campaignId);
    Saved->ContentVersion = State.contentVersion; Saved->SourceCommit = Data->SourceCommit;
    Saved->ScopeStart = State.scopeStart; Saved->ScopeEnd = State.scopeEnd;
    Saved->QuestIndex = State.questIndex; Saved->BeatIndex = State.beatIndex; Saved->Stage = StageName(State.stage);
    for (const std::string& Reading : State.discovered) Saved->DiscoveredReadings.Add(Name(Reading));
    Saved->bHasPlayerTransform = bHasPlayerTransform;
    Saved->PlayerTransform = bHasPlayerTransform ? PlayerTransform : FTransform::Identity;
    return Saved;
}

bool UDawnGospelSubsystem::Save()
{
    if (!bDataValid || !bStarted || bSaving) return false;
    const bool bSaved = [this]()
    {
        if (bSaveLocked) { LastError = CorruptSave(); return false; }
        TGuardValue<bool> Guard(bSaving, true);
        auto Fail = [this]()
        {
            LastError = NSLOCTEXT("DawnGospel", "SaveFailed", "저장에 실패했습니다. 진행은 현재 세션에 남아 있으며, 백업과 저장 공간을 확인해 주세요.");
            return false;
        };
        std::string ValidationError;
        if (!Session.Validate(Session.Snapshot(), ValidationError) ||
            (bHasPlayerTransform && !ValidTransform(PlayerTransform))) return Fail();
        const FString Main = SlotName(), Pending = Main + TEXT("_Pending"), Backup = Main + TEXT("_Backup");
        UDawnGospelSaveGame* Previous = nullptr;
        gospel::State PreviousState; FTransform PreviousTransform; bool bPreviousTransform = false;
        if (UGameplayStatics::DoesSaveGameExist(Main, 0))
        {
            FText Error;
            if (!LoadSlot(Main, PreviousState, PreviousTransform, bPreviousTransform, Error))
            { bSaveLocked = true; bHasValidSave = false; LastError = Error; return false; }
            Previous = Cast<UDawnGospelSaveGame>(UGameplayStatics::LoadGameFromSlot(Main, 0));
            if (!Previous) return Fail();
        }
        UDawnGospelSaveGame* Next = CreateSave();
        if (!Next || !UGameplayStatics::SaveGameToSlot(Next, Pending, 0)) return Fail();
        const gospel::State Expected = Session.Snapshot();
        auto Matches = [this, &Expected](const FString& Slot)
        {
            gospel::State Readback; FTransform Transform; bool bHasTransform = false; FText Error;
            return LoadSlot(Slot, Readback, Transform, bHasTransform, Error) && SameState(Readback, Expected) &&
                   bHasTransform == bHasPlayerTransform && (!bHasTransform || Transform.Equals(PlayerTransform, 0.0001));
        };
        if (!Matches(Pending)) return Fail();
        if (Previous)
        {
            if (!UGameplayStatics::SaveGameToSlot(Previous, Backup, 0)) return Fail();
            gospel::State BackupState; FTransform BackupTransform; bool bBackupTransform = false; FText Error;
            if (!LoadSlot(Backup, BackupState, BackupTransform, bBackupTransform, Error) ||
                !SameState(PreviousState, BackupState) || bPreviousTransform != bBackupTransform ||
                (bPreviousTransform && !PreviousTransform.Equals(BackupTransform, 0.0001))) return Fail();
        }
        if (!UGameplayStatics::SaveGameToSlot(Next, Main, 0) || !Matches(Main))
        {
            if (Previous)
            {
                gospel::State RollbackState; FTransform RollbackTransform; bool bRollbackTransform = false; FText Error;
                const bool bRestored = UGameplayStatics::SaveGameToSlot(Previous, Main, 0) &&
                    LoadSlot(Main, RollbackState, RollbackTransform, bRollbackTransform, Error) &&
                    SameState(PreviousState, RollbackState) && bPreviousTransform == bRollbackTransform &&
                    (!bPreviousTransform || PreviousTransform.Equals(RollbackTransform, 0.0001));
                bSaveLocked = !bRestored;
                bHasValidSave = bRestored;
            }
            else
            {
                bSaveLocked = UGameplayStatics::DoesSaveGameExist(Main, 0);
                bHasValidSave = false;
            }
            return Fail();
        }
        UGameplayStatics::DeleteGameInSlot(Pending, 0);
        bHasValidSave = true; LastError = FText::GetEmpty(); return true;
    }();
    OnChanged.Broadcast(); return bSaved;
}

bool UDawnGospelSubsystem::RecoverBackup()
{
    if (!Ready()) return false;
    gospel::State Recovered; FTransform Transform; bool bHasTransform = false; FText Error;
    const FString Main = SlotName(), Backup = Main + TEXT("_Backup");
    if (!LoadSlot(Backup, Recovered, Transform, bHasTransform, Error))
    { LastError = Error; OnChanged.Broadcast(); return false; }
    // Preserve the actual rejected bytes before an explicitly requested recovery.
    if (UGameplayStatics::DoesSaveGameExist(Main, 0))
    {
        TArray<uint8> Rejected;
        const FString RejectedSlot = Main + TEXT("_Rejected_") + FDateTime::UtcNow().ToString(TEXT("%Y%m%d_%H%M%S")) +
                                     TEXT("_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
        TArray<uint8> Check;
        if (!UGameplayStatics::LoadDataFromSlot(Rejected, Main, 0) ||
            !UGameplayStatics::SaveDataToSlot(Rejected, RejectedSlot, 0) ||
            !UGameplayStatics::LoadDataFromSlot(Check, RejectedSlot, 0) || Check != Rejected)
        {
            LastError = NSLOCTEXT("DawnGospel", "PreserveFailed", "기존 저장 원본을 보존하지 못해 복구를 중단했습니다.");
            OnChanged.Broadcast(); return false;
        }
    }
    TArray<uint8> Bytes;
    if (!UGameplayStatics::LoadDataFromSlot(Bytes, Backup, 0) || !UGameplayStatics::SaveDataToSlot(Bytes, Main, 0))
    {
        bSaveLocked = true; bHasValidSave = false; LastError = CorruptSave(); OnChanged.Broadcast(); return false;
    }
    gospel::State Verified; FTransform VerifiedTransform; bool bVerifiedTransform = false;
    if (!LoadSlot(Main, Verified, VerifiedTransform, bVerifiedTransform, Error) || !SameState(Recovered, Verified) ||
        bHasTransform != bVerifiedTransform || (bHasTransform && !Transform.Equals(VerifiedTransform, 0.0001)))
    {
        bSaveLocked = true; bHasValidSave = false; LastError = CorruptSave(); OnChanged.Broadcast(); return false;
    }
    if (!Session.Restore(Verified)) return Changed(false);
    bStarted = true; bHasPlayerTransform = bVerifiedTransform; PlayerTransform = VerifiedTransform;
    bSaveLocked = false; bHasValidSave = true; LastError = FText::GetEmpty();
    OnChanged.Broadcast(); return true;
}

FDawnGospelQuest UDawnGospelSubsystem::GetCurrentQuest() const
{
    if (!bDataValid || !bStarted) return {};
    const gospel::State State = Session.Snapshot();
    return Data->Quests.IsValidIndex(State.questIndex) && !Session.IsComplete() ? Data->Quests[State.questIndex] : FDawnGospelQuest();
}
FDawnGospelBeat UDawnGospelSubsystem::GetCurrentBeat() const
{
    if (!bStarted || Session.CurrentStage() != gospel::Stage::Reading) return {};
    const FDawnGospelQuest Quest = GetCurrentQuest();
    const int32 Index = Session.Snapshot().beatIndex;
    return Quest.Beats.IsValidIndex(Index) ? Quest.Beats[Index] : FDawnGospelBeat();
}
TArray<FDawnGospelReading> UDawnGospelSubsystem::GetReadings() const
{
    TArray<FDawnGospelReading> Result;
    if (bDataValid && bStarted)
        for (const FDawnGospelReading& Reading : Data->Readings)
            if (Session.HasReading(Id(Reading.Id))) Result.Add(Reading);
    return Result;
}
TArray<FDawnGospelJournalEntry> UDawnGospelSubsystem::GetJournal() const
{
    TArray<FDawnGospelJournalEntry> Result;
    if (!bDataValid || !bStarted) return Result;
    const gospel::State State = Session.Snapshot();
    for (int32 Index = State.scopeStart; Index < State.scopeEnd && Index <= State.questIndex; ++Index)
    {
        const FDawnGospelQuest& Quest = Data->Quests[Index];
        FDawnGospelJournalEntry Entry;
        Entry.Id = Quest.Id; Entry.Title = Quest.Title; Entry.Objective = Quest.Objective;
        Entry.bIsComplete = Index < State.questIndex; Entry.bIsCurrent = Index == State.questIndex;
        Result.Add(Entry);
    }
    return Result;
}
FName UDawnGospelSubsystem::GetStage() const
{
    return bDataValid && bStarted ? StageName(Session.CurrentStage()) : FName(TEXT("Title"));
}
FName UDawnGospelSubsystem::GetQuestId() const { return GetCurrentQuest().Id; }
FText UDawnGospelSubsystem::GetObjective() const
{
    if (!bStarted || !bDataValid) return FText::GetEmpty();
    if (IsComplete()) return IsPreview() ? NSLOCTEXT("DawnGospel", "PreviewComplete", "성전 대표 구간을 마쳤습니다. 발견한 말씀과 여정 기록을 돌아볼 수 있습니다.") :
                                          NSLOCTEXT("DawnGospel", "CampaignComplete", "요단의 기록까지 여정을 마쳤습니다. 이후 사역은 이번 구간에 포함되지 않습니다.");
    if (Session.CurrentStage() == gospel::Stage::Talk)
        return FText::Format(NSLOCTEXT("DawnGospel", "TalkObjective", "{0}에게 말을 걸어 보세요."), GetCurrentQuest().NpcName);
    return GetCurrentQuest().Objective;
}
FText UDawnGospelSubsystem::GetCampaignTitle() const { return Data ? Data->Title : FText::GetEmpty(); }
FText UDawnGospelSubsystem::GetScopeNote() const { return Data ? Data->ScopeNote : FText::GetEmpty(); }
FText UDawnGospelSubsystem::GetAgeLabel() const
{
    if (GetCurrentQuest().ChapterId == TEXT("birth")) return NSLOCTEXT("DawnGospel", "Infancy", "탄생과 아기 때의 기록");
    if (GetCurrentQuest().ChapterId == TEXT("temple") || IsPreview()) return NSLOCTEXT("DawnGospel", "Twelve", "열두 살 · 유월절의 여정");
    return NSLOCTEXT("DawnGospel", "Adult", "공생애 시작 · 삼십세쯤");
}
int32 UDawnGospelSubsystem::GetTotalReadingCount() const { return bDataValid ? Data->Readings.Num() : 0; }
int32 UDawnGospelSubsystem::GetDiscoveredCount() const { return bStarted ? static_cast<int32>(Session.Snapshot().discovered.size()) : 0; }
bool UDawnGospelSubsystem::CanContinue() const { return bDataValid && bHasValidSave && !bSaveLocked && !bSaving; }
bool UDawnGospelSubsystem::IsComplete() const { return bDataValid && bStarted && Session.IsComplete(); }
bool UDawnGospelSubsystem::IsPreview() const { return bDataValid && bStarted && Session.IsTemplePreview(); }
int64 UDawnGospelSubsystem::GetGeneration() const { return static_cast<int64>(Session.Generation()); }
