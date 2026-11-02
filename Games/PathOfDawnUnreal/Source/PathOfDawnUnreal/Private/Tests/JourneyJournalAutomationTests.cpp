#include "Misc/AutomationTest.h"
#include "JourneyJournalData.h"
#include "JourneyJournalSubsystem.h"
#include "JourneySaveGame.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJourneySaveMemoryTest, "WordJourney.SaveGame.ValidatedMemoryRoundtrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FJourneySaveMemoryTest::RunTest(const FString& Parameters)
{
    UJourneySaveGame* Save = NewObject<UJourneySaveGame>();
    Save->bStarted = true;
    Save->CheckpointId = TEXT("BirthRecorded");
    Save->ExperiencedEventIds.Add(TEXT("Birth"));
    Save->WrittenEventIds.Add(TEXT("Birth"));
    Save->Settings.MusicVolume = 0.2f;
    TArray<uint8> Bytes;
    if (!TestTrue(TEXT("Real USaveGame serializes value fields"), UGameplayStatics::SaveGameToMemory(Save, Bytes))) return false;
    UJourneySaveGame* Loaded = Cast<UJourneySaveGame>(UGameplayStatics::LoadGameFromMemory(Bytes));
    if (!TestNotNull(TEXT("The dedicated journey SaveGame class reloads"), Loaded)) return false;
    Journey::Journal Session;
    FJourneyUserSettings Settings;
    FText Error;
    TestTrue(TEXT("A valid save passes checkpoint/set validation"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    TestTrue(TEXT("Written record survives"), Session.GetRecordState(Journey::Event::Birth) == Journey::RecordState::Written);
    TestTrue(TEXT("A future event stays hidden"), Session.GetRecordState(Journey::Event::Temple) == Journey::RecordState::Locked);
    TestEqual(TEXT("User settings survive"), Settings.MusicVolume, 0.2f);
    Journey::Journal Expected = Session;
    FJourneyUserSettings ExpectedSettings = Settings;
    TestTrue(TEXT("Exact saved values match after memory readback"),
        UJourneyJournalSubsystem::ReadbackMatches(Expected, ExpectedSettings, Session, Settings));
    Journey::Journal OtherCheckpoint;
    OtherCheckpoint.NewGame();
    TestFalse(TEXT("A valid but stale checkpoint cannot pass readback equality"),
        UJourneyJournalSubsystem::ReadbackMatches(Expected, ExpectedSettings, OtherCheckpoint, Settings));
    float FJourneyUserSettings::* const FloatSettings[] = {
        &FJourneyUserSettings::MasterVolume, &FJourneyUserSettings::MusicVolume,
        &FJourneyUserSettings::EffectsVolume, &FJourneyUserSettings::MouseSensitivity,
        &FJourneyUserSettings::TextScale
    };
    for (auto Field : FloatSettings)
    {
        FJourneyUserSettings Changed = Settings;
        Changed.*Field += 0.01f;
        TestFalse(TEXT("Every persisted float setting participates in exact readback equality"),
            UJourneyJournalSubsystem::ReadbackMatches(Expected, ExpectedSettings, Session, Changed));
    }
    FJourneyUserSettings Changed = Settings;
    Changed.bSubtitles = !Changed.bSubtitles;
    TestFalse(TEXT("Subtitle mismatch rejects readback"), UJourneyJournalSubsystem::ReadbackMatches(Expected, ExpectedSettings, Session, Changed));
    Changed = Settings;
    Changed.Quality = (Changed.Quality + 1) % 4;
    TestFalse(TEXT("Quality mismatch rejects readback"), UJourneyJournalSubsystem::ReadbackMatches(Expected, ExpectedSettings, Session, Changed));
    const uint64 Epoch = Session.Epoch();
    Loaded->WrittenEventIds.Add(TEXT("Birth"));
    TestFalse(TEXT("Duplicate record arrays are corruption"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    TestEqual(TEXT("Rejected save does not mutate the live epoch"), Session.Epoch(), Epoch);
    Loaded->WrittenEventIds.Pop();
    Loaded->ExperiencedEventIds.Add(TEXT("Temple"));
    TestFalse(TEXT("A future event cannot be inserted into an earlier checkpoint"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    Loaded->ExperiencedEventIds.Pop();
    Loaded->SchemaVersion = 99;
    TestFalse(TEXT("Schema mismatch is rejected before mutation"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    Loaded->SchemaVersion = 1;
    Loaded->ContentVersion = 99;
    TestFalse(TEXT("Content mismatch is rejected"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    Loaded->ContentVersion = 1;
    Loaded->Settings.MasterVolume = -1;
    TestFalse(TEXT("Invalid settings are rejected"), UJourneyJournalSubsystem::DecodeSave(Loaded, Session, Settings, Error));
    TestEqual(TEXT("Failed loads leave user settings unchanged"), Settings.MusicVolume, 0.2f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJourneyDataPrivacyTest, "WordJourney.Journal.BlockedSceneAndHiddenPages",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FJourneyDataPrivacyTest::RunTest(const FString& Parameters)
{
    UJourneyJournalData* Data = NewObject<UJourneyJournalData>();
    const TCHAR* Ids[] = {TEXT("Birth"), TEXT("Shepherds"), TEXT("Temple")};
    const TCHAR* References[] = {TEXT("Luke 2:1-7"), TEXT("Luke 2:8-20"), TEXT("Luke 2:41-52")};
    for (int32 Index = 0; Index < 3; ++Index)
    {
        FJourneyJournalEntry Entry;
        Entry.Id = FName(Ids[Index]);
        Entry.ChapterId = FName(Index == 2 ? TEXT("Temple") : TEXT("Birth"));
        Entry.Title = FText::FromString(TEXT("Test summary"));
        Entry.Summary = FText::FromString(TEXT("Authored summary, not a quotation."));
        Entry.SourceNote = FText::FromString(TEXT("Automated data fixture, no scene claim."));
        Entry.People.Add(FText::FromString(TEXT("Joseph")));
        Entry.Places.Add(FText::FromString(TEXT("Fixture")));
        Entry.ScriptureReferences.Add(References[Index]);
        Data->Entries.Add(Entry);
    }
    FString Error;
    TestTrue(TEXT("Three correctly sourced summaries validate as data"), Data->Validate(Error));
    TestFalse(TEXT("Data validation is not a playable scene certificate"), Data->IsSceneReady(TEXT("Birth")));
    UGameInstance* Instance = NewObject<UGameInstance>();
    UJourneyJournalSubsystem* Journal = NewObject<UJourneyJournalSubsystem>(Instance);
    TestTrue(TEXT("The staged data can be configured without a guessed asset path"), Journal->ConfigureJournal(Data));
    TestEqual(TEXT("The blank book exposes no future titles/bodies"), Journal->GetVisibleEntries().Num(), 0);
    TestFalse(TEXT("New game is blocked before the graphics gate"), Journal->NewJourney());
    TestEqual(TEXT("A blocked scene does not create records"), Journal->GetVisibleEntries().Num(), 0);
    TestFalse(TEXT("An unavailable event cannot be witnessed"), Journal->WitnessEvent(TEXT("Birth"), Journal->GetEpoch()));
    Data->Entries[0].bSceneReady = true;
    TestTrue(TEXT("Birth checkpoint uses the verified Birth scene"), Journal->IsCheckpointReady(TEXT("BirthRecorded")));
    TestTrue(TEXT("Public FName checkpoint IDs tolerate display-case differences"), Journal->IsCheckpointReady(TEXT("birthrecorded")));
    TestFalse(TEXT("Birth approval cannot authorize an unavailable shepherd checkpoint"), Journal->IsCheckpointReady(TEXT("ShepherdsWitnessed")));
    TestFalse(TEXT("Birth chapter completion still needs the shepherd scene"), Journal->IsCheckpointReady(TEXT("BirthChapterComplete")));
    TestFalse(TEXT("Birth approval cannot authorize a temple checkpoint"), Journal->IsCheckpointReady(TEXT("TempleArrival")));
    TestFalse(TEXT("Unknown checkpoint cannot be resumed"), Journal->IsCheckpointReady(TEXT("NotARealCheckpoint")));
    Data->Entries[1].bSceneReady = true;
    TestTrue(TEXT("Shepherd checkpoint becomes available after its own scene approval"), Journal->IsCheckpointReady(TEXT("ShepherdsWitnessed")));
    TestTrue(TEXT("End of birth chapter uses the approved shepherd scene"), Journal->IsCheckpointReady(TEXT("BirthChapterComplete")));
    Data->Entries[2].bSceneReady = true;
    TestTrue(TEXT("Temple checkpoint requires its own scene approval"), Journal->IsCheckpointReady(TEXT("TempleArrival")));
    Data->Entries[0].TextKind = EJourneyTextKind::DirectQuotation;
    TestFalse(TEXT("An unlicensed quotation cannot be substituted for a summary"), Data->Validate(Error));
    Data->Entries[0].TextKind = EJourneyTextKind::Summary;
    Data->Entries[0].ScriptureReferences[0] = TEXT("Luke 5:1-11");
    TestFalse(TEXT("The older episode cannot be mixed into the new Luke 2 record"), Data->Validate(Error));
    TestEqual(TEXT("The new save never shares the old demo's slot"), UJourneyJournalSubsystem::SaveSlotName(), FString(TEXT("WordJourney_v1")));
    return true;
}
#endif
