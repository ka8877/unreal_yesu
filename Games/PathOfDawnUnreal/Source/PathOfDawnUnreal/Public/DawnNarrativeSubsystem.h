#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DawnNarrativeData.h"
#include "../Core/DawnState.h"
#include "DawnNarrativeSubsystem.generated.h"
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDawnStateChanged);

UCLASS()
class PATHOFDAWNUNREAL_API UDawnNarrativeSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    UFUNCTION(BlueprintCallable) bool NewGame();
    UFUNCTION(BlueprintCallable) bool ContinueGame();
    UFUNCTION(BlueprintCallable) bool Inspect(FName ActorId);
    UFUNCTION(BlueprintCallable) bool Advance();
    UFUNCTION(BlueprintCallable) bool Choose(int32 Index);
    UFUNCTION(BlueprintCallable) bool Rewind(FName Checkpoint);
    UFUNCTION(BlueprintCallable) bool Save();
    UFUNCTION(BlueprintCallable) bool RecoverBackup();
    UFUNCTION(BlueprintCallable) void ResetMemories(bool Confirm);
    UFUNCTION(BlueprintCallable) void FinishIntro();
    UFUNCTION(BlueprintCallable) void FinishScene(int64 Generation);
    UFUNCTION(BlueprintCallable) void RecordActor(FName ActorId, const FTransform& Transform);
    UFUNCTION(BlueprintPure) bool GetActorTransform(FName ActorId, FTransform& OutTransform) const;
    UFUNCTION(BlueprintPure) FDawnDialogueNode GetCurrentNode() const;
    UFUNCTION(BlueprintPure) FName GetNodeId() const;
    UFUNCTION(BlueprintPure) FName GetStage() const;
    UFUNCTION(BlueprintPure) FName GetEndingId() const;
    UFUNCTION(BlueprintPure) FText GetObjective() const;
    UFUNCTION(BlueprintPure) bool HasCheckpoint(FName Id) const;
    UFUNCTION(BlueprintPure) bool CanContinue() const;
    UFUNCTION(BlueprintPure) bool IsBusy() const;
    UFUNCTION(BlueprintPure) bool GetFlag(FName Id) const;
    UFUNCTION(BlueprintPure) bool IsInspected(FName Id) const;
    UFUNCTION(BlueprintPure) int32 GetItemCount(FName Id) const;
    UFUNCTION(BlueprintPure) int32 GetRelationship(FName Id) const;
    UFUNCTION(BlueprintPure) TArray<FName> GetMemories() const;
    UFUNCTION(BlueprintPure) TArray<FName> GetSeenEndings() const;
    UFUNCTION(BlueprintPure) TArray<FName> GetChoiceHistory() const;
    UFUNCTION(BlueprintPure) bool HasSeenScene(FName Id) const;
    UFUNCTION(BlueprintPure) int64 GetGeneration() const;
    UPROPERTY(BlueprintReadOnly) FText LastError;
    UPROPERTY(BlueprintAssignable) FDawnStateChanged OnChanged;
    // Caller stops timers, sequences, sound and camera transitions here, before state restoration.
    UPROPERTY(BlueprintAssignable) FDawnStateChanged OnBeforeRestore;
    UPROPERTY(BlueprintAssignable) FDawnStateChanged OnRestored;
private:
    UPROPERTY() TObjectPtr<UDawnNarrativeData> Data;
    dawn::Session Session;
    bool bSaving=false;
    bool bRestoring=false;
    bool bSaveLocked=false;
    bool bDataValid=false;
    bool bHasValidSave=false;
    bool LoadSlot(const FString& Slot, dawn::Session& Result, FText& Error) const;
    bool Changed(bool bResult, bool bPersist=true);
    bool Ready();
    void CaptureWorldActors();
    static FString SlotName();
};
