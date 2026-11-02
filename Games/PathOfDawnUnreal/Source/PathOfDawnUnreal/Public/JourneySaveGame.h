#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "JourneySaveGame.generated.h"

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FJourneyUserSettings
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float MasterVolume = 0.8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float MusicVolume = 0.6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float EffectsVolume = 0.8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float MouseSensitivity = 1.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float TextScale = 1.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) bool bSubtitles = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Quality = 2;

    bool IsValid() const
    {
        return FMath::IsFinite(MasterVolume) && MasterVolume >= 0 && MasterVolume <= 1 &&
            FMath::IsFinite(MusicVolume) && MusicVolume >= 0 && MusicVolume <= 1 &&
            FMath::IsFinite(EffectsVolume) && EffectsVolume >= 0 && EffectsVolume <= 1 &&
            FMath::IsFinite(MouseSensitivity) && MouseSensitivity >= 0.1f && MouseSensitivity <= 3.0f &&
            FMath::IsFinite(TextScale) && TextScale >= 0.8f && TextScale <= 1.6f && Quality >= 0 && Quality <= 3;
    }
};

// Value fields only. No actor pointers, runtime object names or source JSON.
// New namespace intentionally never reads/writes PathOfDawn_Progress_v1.
UCLASS()
class PATHOFDAWNUNREAL_API UJourneySaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 SchemaVersion = 1;
    UPROPERTY(SaveGame) int32 ContentVersion = 1;
    UPROPERTY(SaveGame) bool bStarted = false;
    UPROPERTY(SaveGame) FString CheckpointId = TEXT("Arrival");
    UPROPERTY(SaveGame) TArray<FString> ExperiencedEventIds;
    UPROPERTY(SaveGame) TArray<FString> WrittenEventIds;
    UPROPERTY(SaveGame) FJourneyUserSettings Settings;
};
