#include "DawnPlayerController.h"
#include "DawnPlayerCharacter.h"
#include "DawnPlayerSettings.h"
#include "DawnNarrativeSubsystem.h"
#include "DawnInteractable.h"
#include "DawnWidget.h"
#include "EngineUtils.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Blueprint/UserWidget.h"
#include "CineCameraActor.h"
#include "CineCameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/InputComponent.h"
#include "Sound/SoundBase.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"

namespace
{
bool IsWalkingStage(FName Stage)
{
    return Stage==TEXT("Explore") || Stage==TEXT("Task");
}
constexpr float InteractionRadius=200.f;
}

UDawnNarrativeSubsystem* ADawnPlayerController::GetNarrative() const
{
    return GetGameInstance() ? GetGameInstance()->GetSubsystem<UDawnNarrativeSubsystem>() : nullptr;
}
void ADawnPlayerController::BeginPlay()
{
    Super::BeginPlay();
    FParse::Value(FCommandLine::Get(),TEXT("DawnBuildId="),BuildId);
    if (GetPawn()) InitialTransforms.Add(TEXT("Player"),GetPawn()->GetActorTransform());
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
    {
        if (!It->StableId.IsNone())
        {
            InitialTransforms.Add(It->StableId,It->GetActorTransform());
            It->Tags.AddUnique(FName(*(TEXT("DawnId:")+It->StableId.ToString())));
        }
    }
    if (UDawnNarrativeSubsystem* N=GetNarrative())
    {
        N->OnChanged.AddDynamic(this,&ADawnPlayerController::OnStateChanged);
        N->OnBeforeRestore.AddDynamic(this,&ADawnPlayerController::BeforeRestore);
        N->OnRestored.AddDynamic(this,&ADawnPlayerController::OnWorldRestored);
    }
    DialogueCamera=GetWorld()->SpawnActor<ACineCameraActor>();
    if (DialogueCamera) DialogueCamera->GetCineCameraComponent()->SetCurrentFocalLength(42.f);
    MainWidget=CreateWidget<UDawnWidget>(this,UDawnWidget::StaticClass());
    if (MainWidget) MainWidget->AddToViewport();
    auto Audio=[this](const TCHAR* Path) {
        USoundBase* Sound=LoadObject<USoundBase>(nullptr,Path);
        return Sound ? UGameplayStatics::SpawnSound2D(this,Sound,1.f,1.f,0.f,nullptr,true,false) : nullptr;
    };
    WaterAudio=Audio(TEXT("/Game/PathOfDawn/Audio/A_Water.A_Water"));
    WindAudio=Audio(TEXT("/Game/PathOfDawn/Audio/A_Wind.A_Wind"));
    // No score track is bundled; environmental sound is the intentional audio bed.
    ApplyAudioSettings();
    if (PlayerCameraManager) { PlayerCameraManager->ViewPitchMin=-55.f; PlayerCameraManager->ViewPitchMax=35.f; }
    ShowPage(TEXT("Title"));
}
void ADawnPlayerController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    if (InPawn && !InitialTransforms.Contains(TEXT("Player"))) InitialTransforms.Add(TEXT("Player"),InPawn->GetActorTransform());
    if (ActivePage==TEXT("Play")) RestoreActors();
    RefreshInput();
}
void ADawnPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
    BeforeRestore();
    if (UDawnNarrativeSubsystem* N=GetNarrative())
    {
        // Save publishes its final unlocked state. Unsubscribe before teardown save
        // so that it cannot recreate UI/camera/timers during EndPlay.
        N->OnChanged.RemoveDynamic(this,&ADawnPlayerController::OnStateChanged);
        N->OnBeforeRestore.RemoveDynamic(this,&ADawnPlayerController::BeforeRestore);
        N->OnRestored.RemoveDynamic(this,&ADawnPlayerController::OnWorldRestored);
        if (ActivePage!=TEXT("Title")) { CaptureWorld(); N->Save(); }
    }
    Super::EndPlay(Reason);
}
void ADawnPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::Escape,IE_Pressed,this,&ADawnPlayerController::ToggleMenu);
    InputComponent->BindKey(EKeys::Enter,IE_Pressed,this,&ADawnPlayerController::AdvanceOrSkip);
    InputComponent->BindKey(EKeys::SpaceBar,IE_Pressed,this,&ADawnPlayerController::AdvanceOrSkip);
    InputComponent->BindKey(EKeys::One,IE_Pressed,this,&ADawnPlayerController::SelectFirst);
    InputComponent->BindKey(EKeys::Two,IE_Pressed,this,&ADawnPlayerController::SelectSecond);
}
void ADawnPlayerController::ToggleMenu() { HandleUIAction(TEXT("Menu")); }
void ADawnPlayerController::AdvanceOrSkip() { HandleUIAction(TEXT("Advance")); }
void ADawnPlayerController::SelectFirst() { HandleUIAction(TEXT("Choice0")); }
void ADawnPlayerController::SelectSecond() { HandleUIAction(TEXT("Choice1")); }
FName ADawnPlayerController::GetTaskTargetId() const
{
    const UDawnNarrativeSubsystem* N=GetNarrative();
    if (!N || N->GetStage()!=TEXT("Task")) return NAME_None;
    const FName Node=N->GetNodeId();
    if (Node==TEXT("Task_HelpNet")) return TEXT("Net");
    if (Node==TEXT("Task_ObserveShore")) return TEXT("Stone");
    if (Node==TEXT("Task_ReturnToSimon")) return TEXT("Simon");
    if (Node==TEXT("Task_Departure")) return TEXT("Village");
    return NAME_None;
}
ADawnInteractable* ADawnPlayerController::FindInteractionTarget() const
{
    const UDawnNarrativeSubsystem* N=GetNarrative();
    if (ActivePage!=TEXT("Play") || !N || N->IsBusy() || !IsWalkingStage(N->GetStage()) || !GetPawn()) return nullptr;
    const bool bTask=N->GetStage()==TEXT("Task");
    const FName RequiredId=GetTaskTargetId();
    // Unknown task IDs cannot accidentally interact with an unrelated nearby object.
    if (bTask && RequiredId.IsNone()) return nullptr;
    ADawnInteractable* Target=nullptr;
    float Nearest=InteractionRadius;
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
    {
        const FName Id=It->InteractionId.IsNone() ? It->StableId : It->InteractionId;
        if ((bTask && Id!=RequiredId) || (!bTask && Id==TEXT("Village"))) continue;
        const float Distance=FVector::Dist2D(GetPawn()->GetActorLocation(),It->GetActorLocation());
        if (Distance>Nearest) continue;
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(DawnInteraction),false,GetPawn());
        const bool bHit=GetWorld()->LineTraceSingleByChannel(Hit,GetPawn()->GetActorLocation(),It->GetActorLocation()+FVector(0,0,65),ECC_Visibility,Params);
        if (!bHit || Hit.GetActor()==*It) { Target=*It; Nearest=Distance; }
    }
    return Target;
}
void ADawnPlayerController::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    PromptElapsed+=DeltaSeconds;
    if (PromptElapsed<.12f) return;
    PromptElapsed=0;
    FocusTarget=FindInteractionTarget();
    if (MainWidget) MainWidget->RefreshPrompt();
}
FText ADawnPlayerController::GetInteractionPrompt() const
{
    const UDawnNarrativeSubsystem* N=GetNarrative();
    if (FocusTarget)
    {
        const FName Node=N ? N->GetNodeId() : NAME_None;
        if (Node==TEXT("Task_HelpNet")) return NSLOCTEXT("Dawn","HelpNetPrompt","E · 밧줄을 꺼내 그물 매듭을 함께 묶기");
        if (Node==TEXT("Task_ObserveShore")) return NSLOCTEXT("Dawn","ObserveShorePrompt","E · 물가의 돌에 남은 흔적 살피기");
        if (Node==TEXT("Task_ReturnToSimon")) return NSLOCTEXT("Dawn","ReturnSimonPrompt","E · 시몬 곁에서 다음 발걸음 정하기");
        if (Node==TEXT("Task_Departure")) return NSLOCTEXT("Dawn","VillagePrompt","E · 마을 입구에서 걸어온 아침 돌아보기");
        return FText::Format(NSLOCTEXT("Dawn","InteractionPrompt","E · {0}"),FocusTarget->DisplayName);
    }
    if (N && N->GetStage()==TEXT("Task")) return NSLOCTEXT("Dawn","TaskApproachHint","목표 가까이 다가가 E를 누르세요. 막힌 곳은 돌아갈 수 있습니다.");
    return NSLOCTEXT("Dawn","InteractionHint","그물, 배, 물가의 돌 가까이 다가가 살펴보세요.");
}
FText ADawnPlayerController::GetNavigationHint() const
{
    const UDawnNarrativeSubsystem* N=GetNarrative();
    if (!N || !GetPawn() || ActivePage!=TEXT("Play") || !IsWalkingStage(N->GetStage())) return FText::GetEmpty();
    FName TargetId=GetTaskTargetId();
    if (N->GetStage()==TEXT("Explore"))
    {
        TargetId=!N->IsInspected(TEXT("Net")) ? FName(TEXT("Net")) :
            !N->IsInspected(TEXT("Boat")) ? FName(TEXT("Boat")) :
            !N->IsInspected(TEXT("Stone")) ? FName(TEXT("Stone")) : FName(TEXT("Simon"));
    }
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
    {
        const FName Id=It->InteractionId.IsNone() ? It->StableId : It->InteractionId;
        if (Id!=TargetId) continue;
        const FVector Delta=It->GetActorLocation()-GetPawn()->GetActorLocation();
        const float Angle=FMath::FindDeltaAngleDegrees(GetControlRotation().Yaw,Delta.Rotation().Yaw);
        const FText Direction=FMath::Abs(Angle)<30.f ? NSLOCTEXT("Dawn","Ahead","앞쪽") :
            FMath::Abs(Angle)>150.f ? NSLOCTEXT("Dawn","Behind","뒤쪽") :
            Angle>0.f ? NSLOCTEXT("Dawn","Right","오른쪽") : NSLOCTEXT("Dawn","Left","왼쪽");
        return FText::Format(NSLOCTEXT("Dawn","NavigationDistance","{0} · 약 {1}m · 시선 기준 {2}"),
            It->DisplayName,FText::AsNumber(FMath::CeilToInt(Delta.Size2D()/100.f)),Direction);
    }
    return FText::GetEmpty();
}
void ADawnPlayerController::Interact()
{
    // Revalidate range, visibility, task and phase at input time, not only at HUD refresh.
    FocusTarget=FindInteractionTarget();
    if (FocusTarget && GetNarrative())
    {
        CaptureWorld();
        if (FocusTarget->StableId==TEXT("Net"))
            if (USoundBase* Rustle=LoadObject<USoundBase>(nullptr,TEXT("/Game/PathOfDawn/Audio/A_NetRustle.A_NetRustle")))
            {
                const UDawnPlayerSettings* S=UDawnPlayerSettings::Get();
                RustleAudio=UGameplayStatics::SpawnSound2D(this,Rustle,S?S->MasterVolume*S->EffectsVolume:.5f);
            }
        GetNarrative()->Inspect(FocusTarget->InteractionId.IsNone() ? FocusTarget->StableId : FocusTarget->InteractionId);
    }
}
void ADawnPlayerController::CaptureWorld()
{
    if (UDawnNarrativeSubsystem* N=GetNarrative())
    {
        if (GetPawn()) N->RecordActor(TEXT("Player"),GetPawn()->GetActorTransform());
        for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
            if (!It->StableId.IsNone()) N->RecordActor(It->StableId,It->GetActorTransform());
    }
}
void ADawnPlayerController::RestoreActors(bool bInitial)
{
    UDawnNarrativeSubsystem* N=GetNarrative();
    if (!N) return;
    FTransform Transform;
    auto GetTransform=[this,N,bInitial](FName Id,FTransform& Out) {
        if (!bInitial && N->GetActorTransform(Id,Out)) return true;
        if (const FTransform* Initial=InitialTransforms.Find(Id)) { Out=*Initial; return true; }
        return false;
    };
    if (GetPawn() && GetTransform(TEXT("Player"),Transform)) GetPawn()->SetActorTransform(Transform,false,nullptr,ETeleportType::TeleportPhysics);
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
        if (GetTransform(It->StableId,Transform)) It->SetActorTransform(Transform,false,nullptr,ETeleportType::TeleportPhysics);
    if (ADawnPlayerCharacter* TravelerPawn=Cast<ADawnPlayerCharacter>(GetPawn())) TravelerPawn->RestoreView();
}
void ADawnPlayerController::BeforeRestore()
{
    if (ADawnPlayerCharacter* TravelerPawn=Cast<ADawnPlayerCharacter>(GetPawn())) TravelerPawn->SetMovementAllowed(false);
    GetWorldTimerManager().ClearTimer(SequenceTimer);
    GetWorldTimerManager().ClearTimer(IntroImageTimer);
    if (ActiveSequence) { ActiveSequence->Stop(); ActiveSequence=nullptr; }
    for (UAudioComponent* Audio:{WaterAudio.Get(),WindAudio.Get(),MusicAudio.Get()}) if (Audio) Audio->Stop();
    if (IsValid(RustleAudio)) RustleAudio->Stop();
    if (PlayerCameraManager) PlayerCameraManager->StopCameraFade();
    SetViewTarget(GetPawn());
    LastStage=NAME_None;
    ActionAllowedAt=FPlatformTime::Seconds()+.25;
}
void ADawnPlayerController::OnWorldRestored()
{
    RestoreActors();
    ApplyAudioSettings();
}
void ADawnPlayerController::ApplyAudioSettings()
{
    const UDawnPlayerSettings* S=UDawnPlayerSettings::Get();
    for (UAudioComponent* Audio:{WaterAudio.Get(),WindAudio.Get()}) if (Audio)
    {
        Audio->SetVolumeMultiplier(S ? S->MasterVolume*S->EffectsVolume : .5f);
        if (!Audio->IsPlaying()) Audio->Play();
    }
    if (MusicAudio)
    {
        MusicAudio->SetVolumeMultiplier(S ? S->MasterVolume*S->MusicVolume : .3f);
        if (!MusicAudio->IsPlaying()) MusicAudio->Play();
    }
}
void ADawnPlayerController::BeginTimedScene(FName Stage)
{
    if (Stage!=TEXT("Intro")) return;
    bIntroImage=true;
    if (ULevelSequence* Sequence=LoadObject<ULevelSequence>(nullptr,TEXT("/Game/PathOfDawn/Cinematics/LS_Arrival.LS_Arrival")))
    {
        ALevelSequenceActor* SequenceActor=nullptr;
        FMovieSceneSequencePlaybackSettings Settings;
        Settings.bAutoPlay=false;
        ActiveSequence=ULevelSequencePlayer::CreateLevelSequencePlayer(GetWorld(),Sequence,Settings,SequenceActor);
        if (ActiveSequence) ActiveSequence->Play();
    }
    const int64 Generation=GetNarrative()->GetGeneration();
    TWeakObjectPtr<ADawnPlayerController> WeakThis(this);
    GetWorldTimerManager().SetTimer(IntroImageTimer,[WeakThis,Generation] {
        if (WeakThis.IsValid() && WeakThis->GetNarrative() && WeakThis->GetNarrative()->GetGeneration()==Generation)
        { WeakThis->bIntroImage=false; if (WeakThis->MainWidget) WeakThis->MainWidget->Refresh(); }
    },7.f,false);
    GetWorldTimerManager().SetTimer(SequenceTimer,[WeakThis,Generation] {
        if (WeakThis.IsValid() && WeakThis->GetNarrative() && WeakThis->GetNarrative()->GetGeneration()==Generation)
            WeakThis->GetNarrative()->FinishIntro();
    },20.f,false);
}
void ADawnPlayerController::SetDialogueCamera()
{
    if (!DialogueCamera || !GetNarrative() || !GetPawn()) return;
    const FDawnDialogueNode Node=GetNarrative()->GetCurrentNode();
    const FName TargetId=Node.Speaker.ToString().Contains(TEXT("예수")) ? FName(TEXT("Jesus")) : FName(TEXT("Simon"));
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It) if (It->StableId==TargetId)
    {
        const FVector Aim=It->GetActorLocation()+FVector(0,0,135);
        FVector Direction=(GetPawn()->GetActorLocation()-It->GetActorLocation()).GetSafeNormal2D();
        if (Direction.IsNearlyZero()) Direction=FVector(1,0,0);
        FVector Desired=Aim+Direction*380.f+FVector(0,0,30);
        FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(DawnDialogueCamera),false,*It);
        Params.AddIgnoredActor(GetPawn());
        if (GetWorld()->SweepSingleByChannel(Hit,Aim,Desired,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(12.f),Params)) Desired=Hit.Location;
        DialogueCamera->SetActorLocationAndRotation(Desired,(Aim-Desired).Rotation());
        SetViewTargetWithBlend(DialogueCamera,.65f);
        break;
    }
}
void ADawnPlayerController::OnStateChanged()
{
    UDawnNarrativeSubsystem* N=GetNarrative(); if (!N) return;
    for (TActorIterator<ADawnInteractable> It(GetWorld()); It; ++It)
    {
        const bool bPrepared=It->StableId==TEXT("Net") && N->GetFlag(TEXT("NetPrepared")) && N->GetNodeId()!=TEXT("Task_HelpNet");
        It->ApplyObjectState(N->IsInspected(It->StableId),bPrepared);
    }
    const FName Stage=N->GetStage();
    if (Stage!=LastStage)
    {
        GetWorldTimerManager().ClearTimer(SequenceTimer);
        GetWorldTimerManager().ClearTimer(IntroImageTimer);
        if (ActiveSequence) { ActiveSequence->Stop(); ActiveSequence=nullptr; }
        LastStage=Stage;
        if (ActivePage==TEXT("Play")) BeginTimedScene(Stage);
    }
    if (ActivePage==TEXT("Play") && (Stage==TEXT("Dialogue") || Stage==TEXT("Scene") || Stage==TEXT("Choice1") || Stage==TEXT("Choice2"))) SetDialogueCamera();
    if (ActivePage==TEXT("Play") && IsWalkingStage(Stage)) SetViewTargetWithBlend(GetPawn(),.45f);
    FocusTarget=FindInteractionTarget();
    if (MainWidget) MainWidget->Refresh();
    RefreshInput();
}
void ADawnPlayerController::RefreshInput()
{
    const bool bCanWalk=ActivePage==TEXT("Play") && GetNarrative() && IsWalkingStage(GetNarrative()->GetStage()) && !GetNarrative()->IsBusy();
    if (ADawnPlayerCharacter* TravelerPawn=Cast<ADawnPlayerCharacter>(GetPawn())) TravelerPawn->SetMovementAllowed(bCanWalk);
    bShowMouseCursor=!bCanWalk;
    SetIgnoreMoveInput(false); SetIgnoreLookInput(false);
    if (bCanWalk)
    {
        FInputModeGameOnly Mode; Mode.SetConsumeCaptureMouseDown(true); SetInputMode(Mode);
    }
    else
    {
        FInputModeGameAndUI Mode;
        Mode.SetHideCursorDuringCapture(false);
        Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        if (MainWidget) Mode.SetWidgetToFocus(MainWidget->TakeWidget());
        SetInputMode(Mode);
    }
    FlushPressedKeys();
}
void ADawnPlayerController::ShowPage(FName Page)
{
    ActivePage=Page;
    if (Page==TEXT("Title")) ReturnPage=TEXT("Title");
    if (Page==TEXT("Play"))
    {
        if (GetWorldTimerManager().IsTimerPaused(SequenceTimer)) GetWorldTimerManager().UnPauseTimer(SequenceTimer);
        if (GetWorldTimerManager().IsTimerPaused(IntroImageTimer)) GetWorldTimerManager().UnPauseTimer(IntroImageTimer);
        if (ActiveSequence && ActiveSequence->IsPaused()) ActiveSequence->Play();
    }
    else
    {
        GetWorldTimerManager().PauseTimer(SequenceTimer);
        GetWorldTimerManager().PauseTimer(IntroImageTimer);
        if (ActiveSequence && ActiveSequence->IsPlaying()) ActiveSequence->Pause();
    }
    if (MainWidget) MainWidget->Refresh();
    RefreshInput();
}
void ADawnPlayerController::HandleUIAction(const FString& Action)
{
    UDawnNarrativeSubsystem* N=GetNarrative();
    if (!N || FPlatformTime::Seconds()<ActionAllowedAt || N->IsBusy()) return;
    ActionAllowedAt=FPlatformTime::Seconds()+.22;
    if (Action==TEXT("Menu"))
    {
        if (ActivePage==TEXT("Title")) return;
        if (ActivePage==TEXT("Play")) { ReturnPage=TEXT("Play"); ShowPage(TEXT("Menu")); }
        else if (ActivePage==TEXT("Menu")) ShowPage(TEXT("Play"));
        else ShowPage(ReturnPage);
        return;
    }
    if (Action==TEXT("New"))
    {
        BeforeRestore(); RestoreActors(true);
        ActivePage=TEXT("Play");
        if (N->NewGame()) { CaptureWorld(); N->Save(); OnStateChanged(); }
        else ShowPage(TEXT("Title"));
    }
    else if (Action==TEXT("Continue"))
    {
        ActivePage=TEXT("Play");
        if (!N->ContinueGame()) ShowPage(TEXT("Title"));
    }
    else if (Action==TEXT("Recover"))
    {
        if (N->RecoverBackup()) { ActivePage=TEXT("Play"); LastStage=NAME_None; OnStateChanged(); }
        else if (MainWidget) MainWidget->Refresh();
    }
    else if (Action==TEXT("Advance") || Action==TEXT("Skip"))
    {
        if (ActivePage!=TEXT("Play")) return;
        if (N->GetStage()==TEXT("Intro")) N->FinishIntro();
        else if (Action==TEXT("Skip")) N->FinishScene(N->GetGeneration());
        else N->Advance();
    }
    else if (Action.StartsWith(TEXT("Choice")))
    {
        if (ActivePage==TEXT("Play")) { CaptureWorld(); N->Choose(FCString::Atoi(*Action.RightChop(6))); }
    }
    else if (Action==TEXT("CP01") || Action==TEXT("CP02"))
    {
        ActivePage=TEXT("Play"); N->Rewind(FName(*Action));
    }
    else if (Action==TEXT("BackPlay")) ShowPage(TEXT("Play"));
    else if (Action==TEXT("Settings") || Action==TEXT("Records") || Action==TEXT("Credits"))
    {
        if (ActivePage!=TEXT("ResetConfirm")) ReturnPage=ActivePage;
        ShowPage(FName(*Action));
    }
    else if (Action==TEXT("Back")) ShowPage(ReturnPage);
    else if (Action==TEXT("ResetConfirm")) ShowPage(TEXT("ResetConfirm"));
    else if (Action==TEXT("ResetMemories")) { N->ResetMemories(true); ShowPage(TEXT("Records")); }
    else if (Action==TEXT("Save")) { CaptureWorld(); N->Save(); if (MainWidget) MainWidget->Refresh(); }
    else if (Action==TEXT("Title"))
    {
        CaptureWorld(); if (N->Save()) { BeforeRestore(); ShowPage(TEXT("Title")); ApplyAudioSettings(); }
        else { ReturnPage=ActivePage; ShowPage(TEXT("UnsavedTitle")); }
    }
    else if (Action==TEXT("LeaveTitle") && ActivePage==TEXT("UnsavedTitle"))
    {
        BeforeRestore(); ShowPage(TEXT("Title")); ApplyAudioSettings();
    }
    else if (Action==TEXT("Quit")) UKismetSystemLibrary::QuitGame(this,this,EQuitPreference::Quit,false);
    else if (Action.StartsWith(TEXT("Setting")))
    {
        if (UDawnPlayerSettings* S=UDawnPlayerSettings::Get()) S->Adjust(Action.RightChop(8),Action[7]==TCHAR('+')?.1f:-.1f);
        ApplyAudioSettings(); if (MainWidget) MainWidget->Refresh(); RefreshInput();
    }
}
