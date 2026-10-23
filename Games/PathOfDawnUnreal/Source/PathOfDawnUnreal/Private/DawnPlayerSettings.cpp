#include "DawnPlayerSettings.h"
#include "Engine/Engine.h"

UDawnPlayerSettings* UDawnPlayerSettings::Get()
{
    return GEngine ? Cast<UDawnPlayerSettings>(GEngine->GetGameUserSettings()) : nullptr;
}
void UDawnPlayerSettings::Adjust(const FString& Setting, float Delta)
{
    if (Setting == TEXT("Master")) MasterVolume = FMath::Clamp(MasterVolume + Delta, 0.f, 1.f);
    if (Setting == TEXT("Music")) MusicVolume = FMath::Clamp(MusicVolume + Delta, 0.f, 1.f);
    if (Setting == TEXT("Effects")) EffectsVolume = FMath::Clamp(EffectsVolume + Delta, 0.f, 1.f);
    if (Setting == TEXT("Text")) TextScale = FMath::Clamp(TextScale + Delta, .8f, 1.4f);
    if (Setting == TEXT("Camera")) CameraSensitivity = FMath::Clamp(CameraSensitivity + Delta, .3f, 2.f);
    if (Setting == TEXT("Quality")) SetOverallScalabilityLevel(GetOverallScalabilityLevel() < 2 ? 2 : 0);
    if (Setting == TEXT("Window")) SetFullscreenMode(GetFullscreenMode() == EWindowMode::Windowed ? EWindowMode::WindowedFullscreen : EWindowMode::Windowed);
    ApplySettings(false);
    SaveSettings();
}
