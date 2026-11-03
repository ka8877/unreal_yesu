#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "JourneyJournalData.h"
#include "JourneySaveGame.h"
#include "Core/JourneyJournal.h"
#include "JourneyJournalSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FJourneyJournalChanged);

// Staged runtime for the rebuild. No startup asset path or scene-completion
// trigger is installed until the separate graphics gate has passed.
UCLASS()
class PATHOFDAWNUNREAL_API UJourneyJournalSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    UFUNCTION(BlueprintCallable) bool ConfigureJournal(UJourneyJournalData* InData);
    UFUNCTION(BlueprintCallable) bool NewJourney();
    UFUNCTION(BlueprintCallable) bool ContinueJourney();
    UFUNCTION(BlueprintCallable) bool WitnessEvent(FName EventId, int64 ExpectedEpoch);
    UFUNCTION(BlueprintCallable) bool WriteEntry(FName EventId);
    UFUNCTION(BlueprintCallable) bool BeginTempleChapter();
    UFUNCTION(BlueprintCallable) bool FinishDemo();
    UFUNCTION(BlueprintCallable) bool SaveJourney();
    UFUNCTION(BlueprintCallable) bool RecoverBackup();
    UFUNCTION(BlueprintPure) bool CanContinue() const;
    UFUNCTION(BlueprintPure) bool IsCheckpointReady(FName CheckpointId) const;
    UFUNCTION(BlueprintPure) bool IsBusy() const;
    UFUNCTION(BlueprintPure) EJourneyRecordState GetEntryState(FName EventId) const;
    UFUNCTION(BlueprintPure) TArray<FJourneyJournalEntry> GetVisibleEntries() const;
    UFUNCTION(BlueprintPure) FName GetCurrentChapter() const;
    UFUNCTION(BlueprintPure) FName GetCheckpointId() const;
    UFUNCTION(BlueprintPure) int64 GetEpoch() const;
    UFUNCTION(BlueprintPure) FJourneyUserSettings GetSettings() const { return Settings; }
    // Settings are persisted data here. The final player/audio/quality adapters
    // must apply them in the approved scene; no applied-settings claim is made.
    UFUNCTION(BlueprintCallable) bool StoreSettings(const FJourneyUserSettings& InSettings);
    UPROPERTY(BlueprintReadOnly) FText LastError;
    UPROPERTY(BlueprintAssignable) FJourneyJournalChanged OnJournalChanged;

    static FString SaveSlotName();
    static bool DecodeSave(const UJourneySaveGame* Save, Journey::Journal& OutJournal,
        FJourneyUserSettings& OutSettings, FText& Error);
    static bool ReadbackMatches(const Journey::Journal& Expected, const FJourneyUserSettings& ExpectedSettings,
        const Journey::Journal& Actual, const FJourneyUserSettings& ActualSettings);

private:
    UPROPERTY() TObjectPtr<UJourneyJournalData> Data;
    Journey::Journal Session;
    FJourneyUserSettings Settings;
    bool bTransaction = false;
    bool bSaveLocked = false;
    bool bDataValid = false;
    bool bHasValidSave = false;
    FName SavedCheckpoint;
    bool Ready();
    bool Fail(const FText& Error);
    bool Commit(Journey::Journal Candidate);
    bool SaveCandidate(const Journey::Journal& Candidate, const FJourneyUserSettings& CandidateSettings);
    bool LoadSlot(const FString& Slot, Journey::Journal& OutJournal,
        FJourneyUserSettings& OutSettings, FText& Error) const;
};
