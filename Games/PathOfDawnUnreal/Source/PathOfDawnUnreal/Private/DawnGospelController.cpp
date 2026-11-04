#include "DawnGospelController.h"
#include "DawnGospelCharacter.h"
#include "DawnGospelSubsystem.h"
#include "DawnGospelWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InputComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "InputCoreTypes.h"

namespace { constexpr float GospelInteractionRadius = 225.f; }

ADawnGospelController::ADawnGospelController()
{
    PrimaryActorTick.bCanEverTick = true;
}
UDawnGospelSubsystem* ADawnGospelController::GetCampaign() const
{
    return GetGameInstance() ? GetGameInstance()->GetSubsystem<UDawnGospelSubsystem>() : nullptr;
}
void ADawnGospelController::BeginPlay()
{
    Super::BeginPlay();
    if (GetPawn())
    {
        InitialPlayerTransform = GetPawn()->GetActorTransform();
        bHasInitialTransform = true;
    }
    if (UDawnGospelSubsystem* N = GetCampaign()) N->OnChanged.AddDynamic(this, &ADawnGospelController::OnCampaignChanged);
    MainWidget = CreateWidget<UDawnGospelWidget>(this, UDawnGospelWidget::StaticClass());
    if (MainWidget) MainWidget->AddToViewport();
    if (PlayerCameraManager)
    {
        PlayerCameraManager->ViewPitchMin = -55.f;
        PlayerCameraManager->ViewPitchMax = 35.f;
    }
    ShowPage(TEXT("Title"));
}
void ADawnGospelController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    if (InPawn && !bHasInitialTransform)
    {
        InitialPlayerTransform = InPawn->GetActorTransform();
        bHasInitialTransform = true;
    }
    if (bSessionStarted) RestorePlayer();
    RefreshPresentation();
}
void ADawnGospelController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ADawnGospelController::Interact);
    InputComponent->BindKey(EKeys::Enter, IE_Pressed, this, &ADawnGospelController::Advance);
    InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ADawnGospelController::Advance);
    InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ADawnGospelController::ToggleMenu);
    InputComponent->BindKey(EKeys::M, IE_Pressed, this, &ADawnGospelController::ToggleBook);
    InputComponent->BindKey(EKeys::J, IE_Pressed, this, &ADawnGospelController::ToggleJournal);
}
void ADawnGospelController::Interact() { HandleAction(TEXT("Interact")); }
void ADawnGospelController::Advance() { HandleAction(TEXT("Advance")); }
void ADawnGospelController::ToggleMenu() { HandleAction(TEXT("Menu")); }
void ADawnGospelController::ToggleBook() { HandleAction(TEXT("Book")); }
void ADawnGospelController::ToggleJournal() { HandleAction(TEXT("Journal")); }

AActor* ADawnGospelController::FindCurrentTarget() const
{
    const UDawnGospelSubsystem* N = GetCampaign();
    if (!N || N->IsComplete() || !GetWorld()) return nullptr;
    const FDawnGospelQuest Quest = N->GetCurrentQuest();
    const FName QuestTag(*(TEXT("GospelQuest:") + Quest.Id.ToString()));
    const FName NpcTag(*(TEXT("GospelNpc:") + Quest.NpcId.ToString()));
    // A repeated NPC ID alone is insufficient: use the marker for this exact event.
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(QuestTag) && It->ActorHasTag(NpcTag)) return *It;
    return nullptr;
}
bool ADawnGospelController::IsTargetReachable(const AActor* Target) const
{
    const APawn* Pawn = GetPawn();
    if (!Target || !Pawn || !GetWorld()) return false;
    const FVector From = Pawn->GetActorLocation();
    const FVector To = Target->GetActorLocation();
    if (From.ContainsNaN() || To.ContainsNaN() || FVector::DistSquared(From, To) > FMath::Square(GospelInteractionRadius)) return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(GospelInteraction), false, Pawn);
    Params.AddIgnoredActor(Target);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility, Params);
}
FText ADawnGospelController::GetInteractionPrompt() const
{
    const UDawnGospelSubsystem* N = GetCampaign();
    if (!N || !bSessionStarted) return FText::GetEmpty();
    if (N->GetStage() == TEXT("Reading")) return NSLOCTEXT("GospelUI", "NextHint", "Enter / Space · 다음 이야기");
    if (N->IsComplete()) return NSLOCTEXT("GospelUI", "CompleteHint", "M · 발견한 말씀   J · 여정 기록");
    const AActor* Target = FindCurrentTarget();
    if (!Target || !GetPawn()) return NSLOCTEXT("GospelUI", "MissingTarget", "현재 목적지의 표식이 없습니다. 생성된 성전 지도를 확인해 주세요.");
    const double Meters = FVector::Dist(GetPawn()->GetActorLocation(), Target->GetActorLocation()) / 100.0;
    if (IsTargetReachable(Target))
        return FText::Format(NSLOCTEXT("GospelUI", "TalkHint", "E · {0}에게 말 걸기"), N->GetCurrentQuest().NpcName);
    FNumberFormattingOptions Formatting;
    Formatting.SetMaximumFractionalDigits(1);
    return FText::Format(NSLOCTEXT("GospelUI", "DistanceHint", "{0} · {1}m   WASD 이동 · 마우스 시점"),
        N->GetCurrentQuest().NpcName, FText::AsNumber(Meters, &Formatting));
}
FText ADawnGospelController::GetStatusMessage() const
{
    const UDawnGospelSubsystem* N = GetCampaign();
    return N && !N->LastError.IsEmpty() ? N->LastError : StatusMessage;
}
void ADawnGospelController::CapturePlayer()
{
    if (bSessionStarted && GetPawn())
        if (UDawnGospelSubsystem* N = GetCampaign()) N->RecordPlayerTransform(GetPawn()->GetActorTransform());
}
void ADawnGospelController::RestorePlayer()
{
    if (!GetPawn()) return;
    FTransform Saved;
    UDawnGospelSubsystem* N = GetCampaign();
    if (N && N->GetPlayerTransform(Saved)) GetPawn()->SetActorTransform(Saved, false, nullptr, ETeleportType::TeleportPhysics);
    else if (bHasInitialTransform) GetPawn()->SetActorTransform(InitialPlayerTransform, false, nullptr, ETeleportType::TeleportPhysics);
    const FRotator Facing = GetPawn()->GetActorRotation();
    SetControlRotation(FRotator(-12.f, Facing.Yaw, 0));
}
void ADawnGospelController::FaceCurrentTarget()
{
    AActor* Target = FindCurrentTarget();
    APawn* Pawn = GetPawn();
    if (!Target || !Pawn) return;
    FVector Direction = Target->GetActorLocation() - Pawn->GetActorLocation();
    Direction.Z = 0;
    if (!Direction.IsNearlyZero())
    {
        const float Yaw = Direction.Rotation().Yaw;
        Pawn->SetActorRotation(FRotator(0, Yaw, 0));
        SetControlRotation(FRotator(-12.f, Yaw, 0));
    }
    if (ADawnGospelCharacter* Character = Cast<ADawnGospelCharacter>(Pawn)) Character->SetMovementAllowed(false);
    CapturePlayer();
}
void ADawnGospelController::ShowPage(FName Page)
{
    ActivePage = Page;
    RefreshPresentation();
}
void ADawnGospelController::RefreshPresentation()
{
    UDawnGospelSubsystem* N = GetCampaign();
    const bool bWalking = bSessionStarted && ActivePage == TEXT("Play") && N &&
        (N->GetStage() == TEXT("Travel") || N->GetStage() == TEXT("Talk"));
    if (ADawnGospelCharacter* Character = Cast<ADawnGospelCharacter>(GetPawn())) Character->SetMovementAllowed(bWalking);
    if (MainWidget) MainWidget->Refresh();
    bShowMouseCursor = !bWalking;
    if (bWalking)
    {
        SetInputMode(FInputModeGameOnly());
    }
    else if (MainWidget)
    {
        FInputModeGameAndUI Mode;
        Mode.SetWidgetToFocus(MainWidget->TakeWidget());
        Mode.SetHideCursorDuringCapture(false);
        SetInputMode(Mode);
        MainWidget->SetKeyboardFocus();
    }
}
void ADawnGospelController::OnCampaignChanged()
{
    RefreshPresentation();
}
void ADawnGospelController::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    UDawnGospelSubsystem* N = GetCampaign();
    if (!N || !bSessionStarted || ActivePage != TEXT("Play")) return;
    PromptElapsed += DeltaSeconds;
    if (PromptElapsed < .15f) return;
    PromptElapsed = 0;
    if (N->GetStage() == TEXT("Travel") && IsTargetReachable(FindCurrentTarget()))
    {
        CapturePlayer();
        N->Arrive(N->GetQuestId(), true);
    }
    if (MainWidget) MainWidget->RefreshPrompt();
}

void ADawnGospelController::HandleAction(const FString& Action)
{
    UDawnGospelSubsystem* N = GetCampaign();
    if (!N || !GetWorld()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < ActionAllowedAt) return;
    ActionAllowedAt = Now + .12;
    StatusMessage = FText::GetEmpty();

    if (Action == TEXT("Start") && N->CanContinue())
    {
        ShowPage(TEXT("ConfirmNew"));
        return;
    }
    if (Action == TEXT("ConfirmStart") || Action == TEXT("Start"))
    {
        if (N->NewGame(true))
        {
            bSessionStarted = true;
            RestorePlayer();
            CapturePlayer();
            N->Save();
            ShowPage(TEXT("Play"));
        }
        else RefreshPresentation();
        return;
    }
    if (Action == TEXT("Continue"))
    {
        if (N->ContinueGame())
        {
            if (!N->IsPreview())
            {
                bSessionStarted = false;
                StatusMessage = NSLOCTEXT("GospelUI", "OtherCampaignScope", "이 저장은 성전 미리보기 범위가 아닙니다. 원본 저장을 보존했습니다.");
                ShowPage(TEXT("Title"));
                return;
            }
            bSessionStarted = true;
            RestorePlayer();
            ShowPage(TEXT("Play"));
        }
        else RefreshPresentation();
        return;
    }
    if (Action == TEXT("Recover"))
    {
        if (N->RecoverBackup())
        {
            if (bSessionStarted && N->IsPreview()) RestorePlayer();
            else if (bSessionStarted)
            {
                bSessionStarted = false;
                ActivePage = TEXT("Title");
            }
            StatusMessage = NSLOCTEXT("GospelUI", "Recovered", "백업을 복구했습니다. 이어하기로 돌아갈 수 있습니다.");
        }
        RefreshPresentation();
        return;
    }
    if (Action == TEXT("Back"))
    {
        if (!bSessionStarted) ShowPage(TEXT("Title"));
        else ShowPage(ActivePage == TEXT("Pause") ? FName(TEXT("Play")) : ReturnPage);
        return;
    }
    if (Action == TEXT("Menu"))
    {
        if (ActivePage == TEXT("Title")) return;
        if (ActivePage == TEXT("Play")) { ReturnPage = TEXT("Play"); ShowPage(TEXT("Pause")); }
        else if (!bSessionStarted) ShowPage(TEXT("Title"));
        else if (ActivePage == TEXT("Book") || ActivePage == TEXT("Journal") || ActivePage == TEXT("UnsavedTitle")) ShowPage(ReturnPage);
        else ShowPage(TEXT("Play"));
        return;
    }
    if (Action == TEXT("Book") || Action == TEXT("Journal"))
    {
        if (!bSessionStarted) return;
        const FName Page(*Action);
        if (ActivePage == Page) ShowPage(ReturnPage);
        else
        {
            if (ActivePage != TEXT("Book") && ActivePage != TEXT("Journal"))
                ReturnPage = ActivePage == TEXT("Pause") ? FName(TEXT("Pause")) : FName(TEXT("Play"));
            ShowPage(Page);
        }
        return;
    }
    if (Action == TEXT("Save"))
    {
        if (!bSessionStarted) return;
        CapturePlayer();
        if (N->Save()) StatusMessage = NSLOCTEXT("GospelUI", "Saved", "현재 여정을 저장했습니다.");
        RefreshPresentation();
        return;
    }
    if (Action == TEXT("Title"))
    {
        if (!bSessionStarted) { ShowPage(TEXT("Title")); return; }
        CapturePlayer();
        if (!N->Save()) { ReturnPage = ActivePage; ShowPage(TEXT("UnsavedTitle")); return; }
        bSessionStarted = false;
        ShowPage(TEXT("Title"));
        return;
    }
    if (Action == TEXT("LeaveTitle"))
    {
        bSessionStarted = false;
        ShowPage(TEXT("Title"));
        return;
    }
    if (!bSessionStarted || ActivePage != TEXT("Play")) return;
    if (Action == TEXT("Interact"))
    {
        AActor* Target = FindCurrentTarget();
        if (!IsTargetReachable(Target)) { StatusMessage = NSLOCTEXT("GospelUI", "Approach", "현재 목적지의 인물에게 가까이 다가가세요."); RefreshPresentation(); return; }
        CapturePlayer();
        if (N->GetStage() == TEXT("Travel")) N->Arrive(N->GetQuestId(), true);
        if (N->GetStage() == TEXT("Talk")) { FaceCurrentTarget(); N->Talk(N->GetCurrentQuest().NpcId); }
    }
    else if (Action == TEXT("Advance") && N->GetStage() == TEXT("Reading"))
    {
        CapturePlayer();
        N->Advance();
    }
    RefreshPresentation();
}
void ADawnGospelController::EndPlay(const EEndPlayReason::Type Reason)
{
    if (UDawnGospelSubsystem* N = GetCampaign())
    {
        N->OnChanged.RemoveDynamic(this, &ADawnGospelController::OnCampaignChanged);
        if (bSessionStarted) { CapturePlayer(); N->Save(); }
    }
    Super::EndPlay(Reason);
}
