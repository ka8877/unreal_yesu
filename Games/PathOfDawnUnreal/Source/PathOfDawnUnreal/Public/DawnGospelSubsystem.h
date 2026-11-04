#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DawnGospelData.h"
#include "../Core/GospelState.h"
#include "DawnGospelSubsystem.generated.h"

class UDawnGospelSaveGame;
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDawnGospelChanged);

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnGospelJournalEntry
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FName Id;
    UPROPERTY(BlueprintReadOnly) FText Title;
    UPROPERTY(BlueprintReadOnly) FText Objective;
    UPROPERTY(BlueprintReadOnly) bool bIsComplete = false;
    UPROPERTY(BlueprintReadOnly) bool bIsCurrent = false;
};

UCLASS()
class PATHOFDAWNUNREAL_API UDawnGospelSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    UFUNCTION(BlueprintCallable) bool NewGame(bool bTemplePreview = false);
    UFUNCTION(BlueprintCallable) bool ContinueGame();
    UFUNCTION(BlueprintCallable) bool Save();
    UFUNCTION(BlueprintCallable) bool RecoverBackup();
    UFUNCTION(BlueprintCallable) bool Arrive(FName QuestId, bool bWithinRange);
    UFUNCTION(BlueprintCallable) bool Talk(FName NpcId);
    UFUNCTION(BlueprintCallable) bool Advance();
    UFUNCTION(BlueprintCallable) void RecordPlayerTransform(const FTransform& Transform);
    UFUNCTION(BlueprintPure) bool GetPlayerTransform(FTransform& OutTransform) const;
    UFUNCTION(BlueprintPure) FDawnGospelQuest GetCurrentQuest() const;
    UFUNCTION(BlueprintPure) FDawnGospelBeat GetCurrentBeat() const;
    // Only discovered readings are returned. Hidden pages never expose metadata.
    UFUNCTION(BlueprintPure) TArray<FDawnGospelReading> GetReadings() const;
    UFUNCTION(BlueprintPure) TArray<FDawnGospelJournalEntry> GetJournal() const;
    UFUNCTION(BlueprintPure) FName GetStage() const;
    UFUNCTION(BlueprintPure) FName GetQuestId() const;
    UFUNCTION(BlueprintPure) FText GetObjective() const;
    UFUNCTION(BlueprintPure) FText GetCampaignTitle() const;
    UFUNCTION(BlueprintPure) FText GetScopeNote() const;
    UFUNCTION(BlueprintPure) FText GetAgeLabel() const;
    UFUNCTION(BlueprintPure) int32 GetTotalReadingCount() const;
    UFUNCTION(BlueprintPure) int32 GetDiscoveredCount() const;
    UFUNCTION(BlueprintPure) bool CanContinue() const;
    UFUNCTION(BlueprintPure) bool IsReady() const { return bDataValid; }
    UFUNCTION(BlueprintPure) bool IsComplete() const;
    UFUNCTION(BlueprintPure) bool IsPreview() const;
    UFUNCTION(BlueprintPure) int64 GetGeneration() const;
    UPROPERTY(BlueprintReadOnly) FText LastError;
    UPROPERTY(BlueprintAssignable) FDawnGospelChanged OnChanged;

private:
    UPROPERTY() TObjectPtr<UDawnGospelData> Data;
    gospel::Session Session;
    bool bDataValid = false;
    bool bStarted = false;
    bool bSaving = false;
    bool bSaveLocked = false;
    bool bHasValidSave = false;
    bool bHasPlayerTransform = false;
    FTransform PlayerTransform;

    bool Ready();
    bool Changed(bool bResult);
    bool LoadSlot(const FString& Slot, gospel::State& Result, FTransform& Transform,
                  bool& bHasTransform, FText& Error) const;
    UDawnGospelSaveGame* CreateSave() const;
    static FString SlotName();
};
