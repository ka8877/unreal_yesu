#include "DawnPlayerCharacter.h"
#include "DawnPlayerController.h"
#include "DawnPlayerSettings.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"

ADawnPlayerCharacter::ADawnPlayerCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 90.f);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0, 420, 0);
    GetCharacterMovement()->MaxWalkSpeed = 240.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1400.f;
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 360.f;
    CameraBoom->SocketOffset = FVector(0, 38, 55);
    CameraBoom->bUsePawnControlRotation = true;
    CameraBoom->bEnableCameraLag = true;
    CameraBoom->CameraLagSpeed = 7.f;
    CameraBoom->bDoCollisionTest = true;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom);
    FollowCamera->FieldOfView = 65.f;
    TravelerBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TravelerBody"));
    TravelerBody->SetupAttachment(RootComponent);
    TravelerBody->SetRelativeLocation(VisualOrigin);
    TravelerBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void ADawnPlayerCharacter::BeginPlay()
{
    Super::BeginPlay();
    if (!TravelerBody->GetStaticMesh()) TravelerBody->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Game/PathOfDawn/Characters/SM_Traveler.SM_Traveler")));
    VisualOrigin = TravelerBody->GetRelativeLocation();
    Footstep=LoadObject<USoundBase>(nullptr,TEXT("/Game/PathOfDawn/Audio/A_Footstep.A_Footstep"));
}
void ADawnPlayerCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    UEnhancedInputComponent* Enhanced = CastChecked<UEnhancedInputComponent>(Input);
    Mapping = NewObject<UInputMappingContext>(this);
    auto Axis = [this](const TCHAR* Name, FKey Positive, FKey Negative) {
        UInputAction* Action = NewObject<UInputAction>(this,Name);
        Action->ValueType = EInputActionValueType::Axis1D;
        Mapping->MapKey(Action,Positive);
        FEnhancedActionKeyMapping& Backward = Mapping->MapKey(Action,Negative);
        Backward.Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
        return Action;
    };
    ForwardAction = Axis(TEXT("MoveForward"), EKeys::W, EKeys::S);
    RightAction = Axis(TEXT("MoveRight"), EKeys::D, EKeys::A);
    LookXAction = NewObject<UInputAction>(this,TEXT("LookX"));
    LookYAction = NewObject<UInputAction>(this,TEXT("LookY"));
    LookXAction->ValueType = LookYAction->ValueType = EInputActionValueType::Axis1D;
    Mapping->MapKey(LookXAction,EKeys::MouseX);
    Mapping->MapKey(LookYAction,EKeys::MouseY);
    InteractAction = NewObject<UInputAction>(this,TEXT("Interact"));
    InteractAction->ValueType = EInputActionValueType::Boolean;
    Mapping->MapKey(InteractAction,EKeys::E);
    Enhanced->BindAction(ForwardAction,ETriggerEvent::Triggered,this,&ADawnPlayerCharacter::MoveForward);
    Enhanced->BindAction(RightAction,ETriggerEvent::Triggered,this,&ADawnPlayerCharacter::MoveRight);
    Enhanced->BindAction(LookXAction,ETriggerEvent::Triggered,this,&ADawnPlayerCharacter::LookX);
    Enhanced->BindAction(LookYAction,ETriggerEvent::Triggered,this,&ADawnPlayerCharacter::LookY);
    Enhanced->BindAction(InteractAction,ETriggerEvent::Started,this,&ADawnPlayerCharacter::Interact);
    if (APlayerController* PC = Cast<APlayerController>(Controller))
        if (ULocalPlayer* Local = PC->GetLocalPlayer())
            if (auto* InputSystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Local))
                InputSystem->AddMappingContext(Mapping,0);
}
void ADawnPlayerCharacter::MoveForward(const FInputActionValue& Value)
{
    if (bMovementAllowed && Controller) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::X),Value.Get<float>());
}
void ADawnPlayerCharacter::MoveRight(const FInputActionValue& Value)
{
    if (bMovementAllowed && Controller) AddMovementInput(FRotationMatrix(FRotator(0,Controller->GetControlRotation().Yaw,0)).GetUnitAxis(EAxis::Y),Value.Get<float>());
}
void ADawnPlayerCharacter::LookX(const FInputActionValue& Value)
{
    if (bMovementAllowed) AddControllerYawInput(Value.Get<float>() * (UDawnPlayerSettings::Get() ? UDawnPlayerSettings::Get()->CameraSensitivity : 1.f));
}
void ADawnPlayerCharacter::LookY(const FInputActionValue& Value)
{
    if (bMovementAllowed) AddControllerPitchInput(-Value.Get<float>() * (UDawnPlayerSettings::Get() ? UDawnPlayerSettings::Get()->CameraSensitivity : 1.f));
}
void ADawnPlayerCharacter::Interact()
{
    if (bMovementAllowed) if (auto* PC=Cast<ADawnPlayerController>(Controller)) PC->Interact();
}
void ADawnPlayerCharacter::SetMovementAllowed(bool bAllowed)
{
    bMovementAllowed = bAllowed;
    if (!bAllowed)
    {
        GetCharacterMovement()->StopMovementImmediately();
        if (IsValid(FootstepAudio)) FootstepAudio->Stop();
    }
}
void ADawnPlayerCharacter::RestoreView()
{
    GetCharacterMovement()->StopMovementImmediately();
    TravelerBody->SetRelativeLocation(VisualOrigin);
}
void ADawnPlayerCharacter::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const float Speed = GetVelocity().Size2D();
    if (bMovementAllowed && Speed>20.f && GetCharacterMovement()->IsMovingOnGround())
    {
        StepElapsed+=DeltaSeconds;
        if (StepElapsed>.58f && Footstep)
        {
            const UDawnPlayerSettings* S=UDawnPlayerSettings::Get();
            FootstepAudio=UGameplayStatics::SpawnSoundAtLocation(this,Footstep,GetActorLocation(),FRotator::ZeroRotator,S?S->MasterVolume*S->EffectsVolume:.5f);
            StepElapsed=0.f;
        }
    }
    else StepElapsed=.35f;
    GaitTime += DeltaSeconds * FMath::Clamp(Speed / 30.f,0.f,8.f);
    TravelerBody->SetRelativeLocation(VisualOrigin + FVector(0,0,Speed>10 ? FMath::Sin(GaitTime*2.f)*1.1f : 0.f));
}
