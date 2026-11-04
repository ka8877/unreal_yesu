#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "DawnGospelController.generated.h"

class UDawnGospelSubsystem;
class UDawnGospelWidget;

UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API ADawnGospelController : public APlayerController
{
    GENERATED_BODY()
public:
    ADawnGospelController();
    virtual void BeginPlay() override;
    virtual void OnPossess(APawn* InPawn) override;
    virtual void SetupInputComponent() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    UDawnGospelSubsystem* GetCampaign() const;
    void HandleAction(const FString& Action);
    FName GetPage() const { return ActivePage; }
    FText GetInteractionPrompt() const;
    FText GetStatusMessage() const;
    bool HasActiveSession() const { return bSessionStarted; }
    UFUNCTION() void OnCampaignChanged();
private:
    UPROPERTY() TObjectPtr<UDawnGospelWidget> MainWidget;
    FName ActivePage = TEXT("Title");
    FName ReturnPage = TEXT("Play");
    FText StatusMessage;
    FTransform InitialPlayerTransform;
    bool bHasInitialTransform = false;
    bool bSessionStarted = false;
    float PromptElapsed = 0.f;
    double ActionAllowedAt = 0.0;

    AActor* FindCurrentTarget() const;
    bool IsTargetReachable(const AActor* Target) const;
    void CapturePlayer();
    void RestorePlayer();
    void FaceCurrentTarget();
    void ShowPage(FName Page);
    void RefreshPresentation();
    void Interact();
    void Advance();
    void ToggleMenu();
    void ToggleBook();
    void ToggleJournal();
};
