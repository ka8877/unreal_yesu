#include "JourneyJournalSubsystem.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/DateTime.h"
#include "Misc/Guid.h"
#include <utility>

namespace
{
std::string JourneyUtf8(const FString& Value) { return std::string(TCHAR_TO_UTF8(*Value)); }
FName JourneyName(const char* Value) { return FName(UTF8_TO_TCHAR(Value)); }
bool ParseJourneyName(FName Value, Journey::Event& OutEvent)
{
    // FName comparisons are case-insensitive; do not feed its display spelling
    // back into the strict, case-sensitive save-ID parser.
    for (const Journey::Event Event : {Journey::Event::Birth, Journey::Event::Shepherds, Journey::Event::Temple})
        if (Value == JourneyName(Journey::EventId(Event))) { OutEvent = Event; return true; }
    return false;
}
FName ChapterName(const Journey::Journal& Journal)
{
    return Journal.GetChapter() == Journey::Chapter::Temple ? FName(TEXT("Temple")) : FName(TEXT("Birth"));
}
FName RequiredSceneForCheckpoint(Journey::Checkpoint Checkpoint)
{
    switch (Checkpoint)
    {
    case Journey::Checkpoint::Arrival:
    case Journey::Checkpoint::BirthWitnessed:
    case Journey::Checkpoint::BirthRecorded: return TEXT("Birth");
    case Journey::Checkpoint::ShepherdsWitnessed:
    case Journey::Checkpoint::BirthChapterComplete: return TEXT("Shepherds");
    case Journey::Checkpoint::TempleArrival:
    case Journey::Checkpoint::TempleWitnessed:
    case Journey::Checkpoint::TempleRecorded:
    case Journey::Checkpoint::Complete: return TEXT("Temple");
    default: return NAME_None;
    }
}
FText CorruptSave()
{
    return NSLOCTEXT("Journey", "SaveCorrupt", "기록책 저장을 읽을 수 없습니다. 기존 파일을 보존했으며 자동 저장을 중단했습니다. 백업 복구를 확인하세요.");
}
}

FString UJourneyJournalSubsystem::SaveSlotName() { return TEXT("WordJourney_v1"); }

void UJourneyJournalSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    // Do not load a guessed content path or activate an unavailable scene.
    // Read only this demo's host save; old Galilee progress remains independent.
    if (UGameplayStatics::DoesSaveGameExist(SaveSlotName(), 0))
    {
        Journey::Journal Loaded;
        FJourneyUserSettings LoadedSettings;
        FText Error;
        if (LoadSlot(SaveSlotName(), Loaded, LoadedSettings, Error))
        {
            bHasValidSave = Loaded.State().started;
            SavedCheckpoint = JourneyName(Journey::CheckpointId(Loaded.State().checkpoint));
            Settings = LoadedSettings;
        }
        else
        {
            bSaveLocked = true;
            LastError = Error;
        }
    }
}

bool UJourneyJournalSubsystem::ConfigureJournal(UJourneyJournalData* InData)
{
    if (IsBusy()) return false;
    FString Error;
    if (!InData || !InData->Validate(Error))
        return Fail(NSLOCTEXT("Journey", "MissingData", "기록책 콘텐츠가 없거나 유효하지 않습니다. 에디터 변환과 Cook 결과를 확인하세요."));
    Data = InData;
    bDataValid = true;
    // Keep any protected-save warning visible after assets are configured.
    if (!bSaveLocked) LastError = FText::GetEmpty();
    OnJournalChanged.Broadcast();
    return true;
}

bool UJourneyJournalSubsystem::Ready()
{
    if (IsBusy()) return false;
    if (!bDataValid || !Data)
        return Fail(NSLOCTEXT("Journey", "MissingData", "기록책 콘텐츠가 없거나 유효하지 않습니다. 에디터 변환과 Cook 결과를 확인하세요."));
    return true;
}

bool UJourneyJournalSubsystem::Fail(const FText& Error)
{
    LastError = Error;
    OnJournalChanged.Broadcast();
    return false;
}

bool UJourneyJournalSubsystem::NewJourney()
{
    if (!Ready()) return false;
    if (!Data->IsSceneReady(TEXT("Birth")))
        return Fail(NSLOCTEXT("Journey", "BirthBlocked", "탄생 장면은 에셋과 실제 화면 검증을 기다리고 있습니다."));
    Journey::Journal Candidate = Session;
    Candidate.NewGame();
    return Commit(std::move(Candidate));
}

bool UJourneyJournalSubsystem::ContinueJourney()
{
    if (!Ready()) return false;
    Journey::Journal Loaded;
    FJourneyUserSettings LoadedSettings;
    FText Error;
    if (!LoadSlot(SaveSlotName(), Loaded, LoadedSettings, Error))
    {
        bHasValidSave = false;
        bSaveLocked = UGameplayStatics::DoesSaveGameExist(SaveSlotName(), 0);
        return Fail(Error);
    }
    if (!Loaded.State().started)
        return Fail(NSLOCTEXT("Journey", "NoProgress", "이어갈 진행 기록이 없습니다."));
    if (!IsCheckpointReady(JourneyName(Journey::CheckpointId(Loaded.State().checkpoint))))
        return Fail(NSLOCTEXT("Journey", "ChapterBlocked", "저장된 장면은 아직 실제 화면 검증을 통과하지 않았습니다."));
    // Restore into the existing session so its transient epoch increases rather
    // than being reset to a low value from a new object after every reload.
    if (Session.Restore(Loaded.State()) != Journey::LoadError::None) return Fail(CorruptSave());
    Settings = LoadedSettings;
    bHasValidSave = true;
    bSaveLocked = false;
    SavedCheckpoint = JourneyName(Journey::CheckpointId(Session.State().checkpoint));
    LastError = FText::GetEmpty();
    OnJournalChanged.Broadcast();
    return true;
}

bool UJourneyJournalSubsystem::WitnessEvent(FName EventId, int64 ExpectedEpoch)
{
    if (!Ready()) return false;
    Journey::Event Event;
    if (ExpectedEpoch < 0 || !ParseJourneyName(EventId, Event)) return false;
    if (!Data->IsSceneReady(EventId))
        return Fail(NSLOCTEXT("Journey", "SceneBlocked", "아직 체험할 수 없는 사건은 기록을 해금하지 않습니다."));
    Journey::Journal Candidate = Session;
    if (!Candidate.Experience(Event, static_cast<std::uint64_t>(ExpectedEpoch))) return false;
    return Commit(std::move(Candidate));
}

bool UJourneyJournalSubsystem::WriteEntry(FName EventId)
{
    if (!Ready()) return false;
    Journey::Event Event;
    if (!ParseJourneyName(EventId, Event)) return false;
    Journey::Journal Candidate = Session;
    if (!Candidate.Write(Event)) return false;
    return Commit(std::move(Candidate));
}

bool UJourneyJournalSubsystem::BeginTempleChapter()
{
    if (!Ready()) return false;
    if (!Data->IsSceneReady(TEXT("Temple")))
        return Fail(NSLOCTEXT("Journey", "TempleBlocked", "성전 공간과 아동 캐릭터 검증이 완료되지 않아 다음 장으로 이동할 수 없습니다."));
    Journey::Journal Candidate = Session;
    if (!Candidate.BeginTemple()) return false;
    return Commit(std::move(Candidate));
}

bool UJourneyJournalSubsystem::FinishDemo()
{
    if (!Ready()) return false;
    Journey::Journal Candidate = Session;
    if (!Candidate.CompleteDemo()) return false;
    return Commit(std::move(Candidate));
}

bool UJourneyJournalSubsystem::Commit(Journey::Journal Candidate)
{
    if (IsBusy()) return false;
    const bool bSaved = [this, &Candidate]()
    {
        TGuardValue<bool> Guard(bTransaction, true);
        if (!SaveCandidate(Candidate, Settings)) return false;
        Session = std::move(Candidate);
        bHasValidSave = Session.State().started;
        SavedCheckpoint = JourneyName(Journey::CheckpointId(Session.State().checkpoint));
        return true;
    }();
    // Observers must see an unlocked transaction, including on save failure.
    OnJournalChanged.Broadcast();
    return bSaved;
}

bool UJourneyJournalSubsystem::SaveJourney()
{
    if (!Ready()) return false;
    if (!Session.State().started) return false;
    return Commit(Session);
}

bool UJourneyJournalSubsystem::StoreSettings(const FJourneyUserSettings& InSettings)
{
    if (IsBusy()) return false;
    if (!InSettings.IsValid())
        return Fail(NSLOCTEXT("Journey", "InvalidSettings", "설정 값의 범위를 확인하세요."));
    const bool bSaved = [this, &InSettings]()
    {
        TGuardValue<bool> Guard(bTransaction, true);
        // Title settings must not replace saved progress with the unstarted
        // in-memory journal while the user has not chosen Continue yet.
        Journey::Journal SettingsJournal = Session;
        if (!Session.State().started && UGameplayStatics::DoesSaveGameExist(SaveSlotName(), 0))
        {
            FJourneyUserSettings PreviousSettings;
            FText Error;
            if (!LoadSlot(SaveSlotName(), SettingsJournal, PreviousSettings, Error))
            {
                bSaveLocked = true;
                LastError = Error;
                return false;
            }
        }
        if (!SaveCandidate(SettingsJournal, InSettings)) return false;
        Settings = InSettings;
        return true;
    }();
    OnJournalChanged.Broadcast();
    return bSaved;
}

bool UJourneyJournalSubsystem::DecodeSave(const UJourneySaveGame* Save, Journey::Journal& OutJournal,
    FJourneyUserSettings& OutSettings, FText& Error)
{
    if (!Save) { Error = CorruptSave(); return false; }
    if (Save->SchemaVersion != Journey::SchemaVersion || Save->ContentVersion != Journey::ContentVersion)
    {
        Error = NSLOCTEXT("Journey", "VersionMismatch", "저장 형식 또는 이야기 버전이 다릅니다. 원본을 덮어쓰지 않았습니다.");
        return false;
    }
    if (!Save->Settings.IsValid()) { Error = CorruptSave(); return false; }
    Journey::Snapshot Candidate;
    Candidate.schemaVersion = Save->SchemaVersion;
    Candidate.contentVersion = Save->ContentVersion;
    Candidate.started = Save->bStarted;
    if (!Journey::ParseCheckpoint(JourneyUtf8(Save->CheckpointId), Candidate.checkpoint)) { Error = CorruptSave(); return false; }
    for (const FString& Id : Save->ExperiencedEventIds)
        if (!Candidate.experienced.insert(JourneyUtf8(Id)).second) { Error = CorruptSave(); return false; }
    for (const FString& Id : Save->WrittenEventIds)
        if (!Candidate.written.insert(JourneyUtf8(Id)).second) { Error = CorruptSave(); return false; }
    // Restore validates exact checkpoint/event sets before mutating OutJournal.
    if (OutJournal.Restore(Candidate) != Journey::LoadError::None) { Error = CorruptSave(); return false; }
    OutSettings = Save->Settings;
    Error = FText::GetEmpty();
    return true;
}

bool UJourneyJournalSubsystem::LoadSlot(const FString& Slot, Journey::Journal& OutJournal,
    FJourneyUserSettings& OutSettings, FText& Error) const
{
    if (!UGameplayStatics::DoesSaveGameExist(Slot, 0))
    {
        Error = NSLOCTEXT("Journey", "NoProgress", "이어갈 진행 기록이 없습니다.");
        return false;
    }
    return DecodeSave(Cast<UJourneySaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0)), OutJournal, OutSettings, Error);
}

bool UJourneyJournalSubsystem::ReadbackMatches(const Journey::Journal& Expected, const FJourneyUserSettings& ExpectedSettings,
    const Journey::Journal& Actual, const FJourneyUserSettings& ActualSettings)
{
    const Journey::Snapshot& A = Expected.State();
    const Journey::Snapshot& B = Actual.State();
    return A.schemaVersion == B.schemaVersion && A.contentVersion == B.contentVersion && A.started == B.started &&
        A.checkpoint == B.checkpoint && A.experienced == B.experienced && A.written == B.written &&
        ExpectedSettings.MasterVolume == ActualSettings.MasterVolume && ExpectedSettings.MusicVolume == ActualSettings.MusicVolume &&
        ExpectedSettings.EffectsVolume == ActualSettings.EffectsVolume && ExpectedSettings.MouseSensitivity == ActualSettings.MouseSensitivity &&
        ExpectedSettings.TextScale == ActualSettings.TextScale && ExpectedSettings.bSubtitles == ActualSettings.bSubtitles &&
        ExpectedSettings.Quality == ActualSettings.Quality;
}

bool UJourneyJournalSubsystem::SaveCandidate(const Journey::Journal& Candidate, const FJourneyUserSettings& CandidateSettings)
{
    if (bSaveLocked)
    {
        if (LastError.IsEmpty()) LastError = CorruptSave();
        return false;
    }
    const Journey::Snapshot& State = Candidate.State();
    if (State.schemaVersion != Journey::SchemaVersion || State.contentVersion != Journey::ContentVersion ||
        !Journey::Journal::Valid(State) || !CandidateSettings.IsValid())
    {
        LastError = CorruptSave();
        return false;
    }
    const FString Main = SaveSlotName(), Pending = Main + TEXT("_Pending"), Backup = Main + TEXT("_Backup");
    UJourneySaveGame* OldSave = nullptr;
    Journey::Journal OldJournal;
    FJourneyUserSettings OldSettings;
    if (UGameplayStatics::DoesSaveGameExist(Main, 0))
    {
        FText Error;
        if (!LoadSlot(Main, OldJournal, OldSettings, Error)) { bSaveLocked = true; LastError = Error; return false; }
        OldSave = Cast<UJourneySaveGame>(UGameplayStatics::LoadGameFromSlot(Main, 0));
        if (!OldSave) { bSaveLocked = true; LastError = CorruptSave(); return false; }
    }
    UJourneySaveGame* NewSave = Cast<UJourneySaveGame>(UGameplayStatics::CreateSaveGameObject(UJourneySaveGame::StaticClass()));
    if (!NewSave) { LastError = CorruptSave(); return false; }
    NewSave->SchemaVersion = State.schemaVersion;
    NewSave->ContentVersion = State.contentVersion;
    NewSave->bStarted = State.started;
    NewSave->CheckpointId = UTF8_TO_TCHAR(Journey::CheckpointId(State.checkpoint));
    NewSave->Settings = CandidateSettings;
    for (const std::string& Id : State.experienced) NewSave->ExperiencedEventIds.Add(UTF8_TO_TCHAR(Id.c_str()));
    for (const std::string& Id : State.written) NewSave->WrittenEventIds.Add(UTF8_TO_TCHAR(Id.c_str()));
    const auto Failed = [this]()
    {
        LastError = NSLOCTEXT("Journey", "SaveFailed", "기록을 저장하지 못해 진행을 변경하지 않았습니다. 저장 공간과 권한을 확인하세요.");
        return false;
    };
    if (!UGameplayStatics::SaveGameToSlot(NewSave, Pending, 0)) return Failed();
    Journey::Journal Readback;
    FJourneyUserSettings ReadSettings;
    FText Error;
    if (!LoadSlot(Pending, Readback, ReadSettings, Error) || !ReadbackMatches(Candidate, CandidateSettings, Readback, ReadSettings)) return Failed();
    if (OldSave && (!UGameplayStatics::SaveGameToSlot(OldSave, Backup, 0) ||
        !LoadSlot(Backup, Readback, ReadSettings, Error) || !ReadbackMatches(OldJournal, OldSettings, Readback, ReadSettings))) return Failed();
    if (!UGameplayStatics::SaveGameToSlot(NewSave, Main, 0) || !LoadSlot(Main, Readback, ReadSettings, Error) ||
        !ReadbackMatches(Candidate, CandidateSettings, Readback, ReadSettings))
    {
        const bool bRestored = OldSave && UGameplayStatics::SaveGameToSlot(OldSave, Main, 0) &&
            LoadSlot(Main, Readback, ReadSettings, Error) && ReadbackMatches(OldJournal, OldSettings, Readback, ReadSettings);
        if (!bRestored) bSaveLocked = UGameplayStatics::DoesSaveGameExist(Main, 0);
        return Failed();
    }
    UGameplayStatics::DeleteGameInSlot(Pending, 0);
    LastError = FText::GetEmpty();
    return true;
}

bool UJourneyJournalSubsystem::RecoverBackup()
{
    if (IsBusy()) return false;
    const bool bRecovered = [this]()
    {
        TGuardValue<bool> Guard(bTransaction, true);
        const FString Main = SaveSlotName(), Backup = Main + TEXT("_Backup");
        Journey::Journal Recovered;
        FJourneyUserSettings RecoveredSettings;
        FText Error;
        if (!LoadSlot(Backup, Recovered, RecoveredSettings, Error)) { LastError = Error; return false; }
        // Preserve rejected raw bytes before any replacement, even if their
        // USaveGame class or version cannot be understood by this build.
        if (UGameplayStatics::DoesSaveGameExist(Main, 0))
        {
            TArray<uint8> Rejected;
            const FString Archive = Main + TEXT("_Rejected_") + FDateTime::UtcNow().ToString(TEXT("%Y%m%d_%H%M%S")) + TEXT("_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
            if (!UGameplayStatics::LoadDataFromSlot(Rejected, Main, 0) || !UGameplayStatics::SaveDataToSlot(Rejected, Archive, 0))
            {
                LastError = NSLOCTEXT("Journey", "ArchiveFailed", "기존 저장 보관에 실패하여 복구를 중단했습니다.");
                return false;
            }
        }
        TArray<uint8> ValidBytes;
        if (!UGameplayStatics::LoadDataFromSlot(ValidBytes, Backup, 0) || !UGameplayStatics::SaveDataToSlot(ValidBytes, Main, 0))
        {
            bSaveLocked = UGameplayStatics::DoesSaveGameExist(Main, 0);
            bHasValidSave = false;
            LastError = NSLOCTEXT("Journey", "RecoveryFailed", "백업 복구에 실패했습니다. 원본 보관본과 백업을 확인하세요.");
            return false;
        }
        Journey::Journal Verified;
        FJourneyUserSettings VerifiedSettings;
        if (!LoadSlot(Main, Verified, VerifiedSettings, Error)) { LastError = Error; bSaveLocked = true; return false; }
        if (!ReadbackMatches(Recovered, RecoveredSettings, Verified, VerifiedSettings))
        { LastError = CorruptSave(); bSaveLocked = true; return false; }
        bSaveLocked = false;
        bHasValidSave = Verified.State().started;
        SavedCheckpoint = JourneyName(Journey::CheckpointId(Verified.State().checkpoint));
        Settings = VerifiedSettings;
        // Invalidate any callbacks from the old scene and hide its old pages.
        // The user explicitly resumes the recovered checkpoint with Continue.
        Session.Restore(Journey::Snapshot{});
        LastError = FText::GetEmpty();
        // Recovery repairs storage only. ContinueJourney performs the explicit
        // in-world resume after the caller has disposed old scene callbacks.
        return true;
    }();
    OnJournalChanged.Broadcast();
    return bRecovered;
}

bool UJourneyJournalSubsystem::CanContinue() const
{
    return bHasValidSave && !bSaveLocked && IsCheckpointReady(SavedCheckpoint);
}
bool UJourneyJournalSubsystem::IsCheckpointReady(FName CheckpointId) const
{
    if (!bDataValid || !Data) return false;
    // Public FName IDs use name comparison; only persisted FString IDs are
    // parsed strictly. Display-case differences cannot block a valid resume.
    for (const Journey::Checkpoint Checkpoint : {Journey::Checkpoint::Arrival, Journey::Checkpoint::BirthWitnessed,
        Journey::Checkpoint::BirthRecorded, Journey::Checkpoint::ShepherdsWitnessed, Journey::Checkpoint::BirthChapterComplete,
        Journey::Checkpoint::TempleArrival, Journey::Checkpoint::TempleWitnessed, Journey::Checkpoint::TempleRecorded, Journey::Checkpoint::Complete})
        if (CheckpointId == JourneyName(Journey::CheckpointId(Checkpoint)))
            return Data->IsSceneReady(RequiredSceneForCheckpoint(Checkpoint));
    return false;
}
bool UJourneyJournalSubsystem::IsBusy() const { return bTransaction; }
EJourneyRecordState UJourneyJournalSubsystem::GetEntryState(FName EventId) const
{
    Journey::Event Event;
    if (!bDataValid || !ParseJourneyName(EventId, Event)) return EJourneyRecordState::Locked;
    switch (Session.GetRecordState(Event))
    {
    case Journey::RecordState::Available: return EJourneyRecordState::Available;
    case Journey::RecordState::Written: return EJourneyRecordState::Written;
    default: return EJourneyRecordState::Locked;
    }
}
TArray<FJourneyJournalEntry> UJourneyJournalSubsystem::GetVisibleEntries() const
{
    TArray<FJourneyJournalEntry> Result;
    if (bDataValid && Data)
        for (const Journey::Event Event : Session.VisibleEntries())
            if (const FJourneyJournalEntry* Entry = Data->Find(JourneyName(Journey::EventId(Event)))) Result.Add(*Entry);
    return Result;
}
FName UJourneyJournalSubsystem::GetCurrentChapter() const { return ChapterName(Session); }
FName UJourneyJournalSubsystem::GetCheckpointId() const { return JourneyName(Journey::CheckpointId(Session.State().checkpoint)); }
int64 UJourneyJournalSubsystem::GetEpoch() const { return static_cast<int64>(Session.Epoch()); }
