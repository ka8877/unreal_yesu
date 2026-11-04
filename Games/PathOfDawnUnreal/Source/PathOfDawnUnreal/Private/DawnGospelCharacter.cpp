#include "DawnGospelCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "UObject/ConstructorHelpers.h"

ADawnGospelCharacter::ADawnGospelCharacter()
{
    GetCapsuleComponent()->InitCapsuleSize(28.f, 72.f);
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0, 420, 0);
    GetCharacterMovement()->MaxWalkSpeed = 220.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1400.f;

    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 330.f;
    CameraBoom->SocketOffset = FVector(0, 34, 40);
    CameraBoom->bUsePawnControlRotation = true;
    CameraBoom->bEnableCameraLag = true;
    CameraBoom->CameraLagSpeed = 8.f;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom);
    FollowCamera->FieldOfView = 65.f;

    // An obvious engine-shape stand-in, never presented as a finished child character.
    PreviewProxy = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DevelopmentProxy"));
    PreviewProxy->SetupAttachment(RootComponent);
    PreviewProxy->SetRelativeLocation(FVector(0, 0, -6));
    PreviewProxy->SetRelativeScale3D(FVector(.28f, .22f, .62f));
    PreviewProxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    if (Shape.Succeeded()) PreviewProxy->SetStaticMesh(Shape.Object);
}

void ADawnGospelCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input);
    if (!Enhanced) return;
    Mapping = NewObject<UInputMappingContext>(this);
    auto Axis = [this](const TCHAR* Name, FKey Positive, FKey Negative) {
        UInputAction* Action = NewObject<UInputAction>(this, Name);
        Action->ValueType = EInputActionValueType::Axis1D;
        Mapping->MapKey(Action, Positive);
        Mapping->MapKey(Action, Negative).Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
        return Action;
    };
    ForwardAction = Axis(TEXT("GospelForward"), EKeys::W, EKeys::S);
    RightAction = Axis(TEXT("GospelRight"), EKeys::D, EKeys::A);
    LookXAction = NewObject<UInputAction>(this, TEXT("GospelLookX"));
    LookYAction = NewObject<UInputAction>(this, TEXT("GospelLookY"));
    LookXAction->ValueType = LookYAction->ValueType = EInputActionValueType::Axis1D;
    Mapping->MapKey(LookXAction, EKeys::MouseX);
    Mapping->MapKey(LookYAction, EKeys::MouseY);
    Enhanced->BindAction(ForwardAction, ETriggerEvent::Triggered, this, &ADawnGospelCharacter::MoveForward);
    Enhanced->BindAction(RightAction, ETriggerEvent::Triggered, this, &ADawnGospelCharacter::MoveRight);
    Enhanced->BindAction(LookXAction, ETriggerEvent::Triggered, this, &ADawnGospelCharacter::LookX);
    Enhanced->BindAction(LookYAction, ETriggerEvent::Triggered, this, &ADawnGospelCharacter::LookY);
    if (APlayerController* PC = Cast<APlayerController>(Controller))
        if (ULocalPlayer* Local = PC->GetLocalPlayer())
            if (auto* System = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Local))
                System->AddMappingContext(Mapping, 0);
}

void ADawnGospelCharacter::EndPlay(const EEndPlayReason::Type Reason)
{
    if (APlayerController* PC = Cast<APlayerController>(Controller))
        if (ULocalPlayer* Local = PC->GetLocalPlayer())
            if (auto* System = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Local))
                if (Mapping) System->RemoveMappingContext(Mapping);
    Super::EndPlay(Reason);
}

void ADawnGospelCharacter::SetMovementAllowed(bool bAllowed)
{
    bMovementAllowed = bAllowed;
    if (!bAllowed) GetCharacterMovement()->StopMovementImmediately();
}
void ADawnGospelCharacter::MoveForward(const FInputActionValue& Value)
{
    if (bMovementAllowed && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0, Controller->GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::X), Value.Get<float>());
}
void ADawnGospelCharacter::MoveRight(const FInputActionValue& Value)
{
    if (bMovementAllowed && Controller)
        AddMovementInput(FRotationMatrix(FRotator(0, Controller->GetControlRotation().Yaw, 0)).GetUnitAxis(EAxis::Y), Value.Get<float>());
}
void ADawnGospelCharacter::LookX(const FInputActionValue& Value)
{
    if (bMovementAllowed) AddControllerYawInput(Value.Get<float>());
}
void ADawnGospelCharacter::LookY(const FInputActionValue& Value)
{
    if (bMovementAllowed) AddControllerPitchInput(-Value.Get<float>());
}
