#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameUserSettings.h"
#include "DawnPlayerSettings.generated.h"

UCLASS(Config=GameUserSettings)
class PATHOFDAWNUNREAL_API UDawnPlayerSettings : public UGameUserSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(Config, BlueprintReadOnly) float MasterVolume = .8f;
    UPROPERTY(Config, BlueprintReadOnly) float MusicVolume = .45f;
    UPROPERTY(Config, BlueprintReadOnly) float EffectsVolume = .7f;
    UPROPERTY(Config, BlueprintReadOnly) float TextScale = 1.f;
    UPROPERTY(Config, BlueprintReadOnly) float CameraSensitivity = 1.f;
    static UDawnPlayerSettings* Get();
    void Adjust(const FString& Setting, float Delta);
};
