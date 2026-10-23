#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "DawnPlayerController.generated.h"

class UDawnWidget;
class UDawnNarrativeSubsystem;
class ADawnInteractable;
class ACineCameraActor;
class ULevelSequencePlayer;
class UAudioComponent;

UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API ADawnPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void OnPossess(APawn* InPawn) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void SetupInputComponent() override;
    virtual void Tick(float DeltaSeconds) override;
    void Interact();
    void HandleUIAction(const FString& Action);
    void ShowPage(FName Page);
    FName GetPage() const { return ActivePage; }
    FString GetBuildId() const { return BuildId; }
    FText GetInteractionPrompt() const;
    FText GetNavigationHint() const;
    UDawnNarrativeSubsystem* GetNarrative() const;
    void CaptureWorld();
    bool IsArrivalIllustrationVisible() const { return bIntroImage; }
    UFUNCTION() void OnWorldRestored();
    UFUNCTION() void OnStateChanged();
    UFUNCTION() void BeforeRestore();
private:
    UPROPERTY() TObjectPtr<UDawnWidget> MainWidget;
    UPROPERTY() TObjectPtr<ACineCameraActor> DialogueCamera;
    UPROPERTY() TObjectPtr<ULevelSequencePlayer> ActiveSequence;
    UPROPERTY() TObjectPtr<UAudioComponent> WaterAudio;
    UPROPERTY() TObjectPtr<UAudioComponent> WindAudio;
    UPROPERTY() TObjectPtr<UAudioComponent> MusicAudio;
    UPROPERTY() TObjectPtr<UAudioComponent> RustleAudio;
    UPROPERTY() TObjectPtr<ADawnInteractable> FocusTarget;
    FName ActivePage = TEXT("Title");
    FName ReturnPage = TEXT("Title");
    FName LastStage;
    FString BuildId = TEXT("source-dev");
    TMap<FName,FTransform> InitialTransforms;
    FTimerHandle SequenceTimer;
    FTimerHandle IntroImageTimer;
    bool bIntroImage = true;
    float PromptElapsed = 0.f;
    double ActionAllowedAt = 0.0;
    FName GetTaskTargetId() const;
    ADawnInteractable* FindInteractionTarget() const;
    void ToggleMenu();
    void AdvanceOrSkip();
    void SelectFirst();
    void SelectSecond();
    void RestoreActors(bool bInitial = false);
    void SetDialogueCamera();
    void ApplyAudioSettings();
    void BeginTimedScene(FName Stage);
    void RefreshInput();
};
