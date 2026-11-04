#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "DawnGospelSaveGame.generated.h"

// An independent campaign slot. Never reads or writes the Galilee save class.
UCLASS()
class PATHOFDAWNUNREAL_API UDawnGospelSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 SchemaVersion = 1;
    UPROPERTY(SaveGame) FName CampaignId;
    UPROPERTY(SaveGame) int32 ContentVersion = 1;
    UPROPERTY(SaveGame) FString SourceCommit;
    UPROPERTY(SaveGame) int32 ScopeStart = 0;
    UPROPERTY(SaveGame) int32 ScopeEnd = 0;
    UPROPERTY(SaveGame) int32 QuestIndex = 0;
    UPROPERTY(SaveGame) int32 BeatIndex = 0;
    UPROPERTY(SaveGame) FName Stage;
    UPROPERTY(SaveGame) TArray<FName> DiscoveredReadings;
    UPROPERTY(SaveGame) bool bHasPlayerTransform = false;
    UPROPERTY(SaveGame) FTransform PlayerTransform;
};
