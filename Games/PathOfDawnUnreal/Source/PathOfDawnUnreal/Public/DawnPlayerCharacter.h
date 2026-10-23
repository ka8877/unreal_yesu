#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "DawnPlayerCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UInputAction;
class USoundBase;
class UAudioComponent;
class UInputMappingContext;
struct FInputActionValue;

UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API ADawnPlayerCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    ADawnPlayerCharacter();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> TravelerBody;
    UFUNCTION(BlueprintCallable) void SetMovementAllowed(bool bAllowed);
    void RestoreView();
private:
    UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
    UPROPERTY() TObjectPtr<UInputAction> ForwardAction;
    UPROPERTY() TObjectPtr<UInputAction> RightAction;
    UPROPERTY() TObjectPtr<UInputAction> LookXAction;
    UPROPERTY() TObjectPtr<UInputAction> LookYAction;
    UPROPERTY() TObjectPtr<UInputAction> InteractAction;
    bool bMovementAllowed = false;
    float GaitTime = 0.f;
    float StepElapsed = 0.f;
    UPROPERTY() TObjectPtr<USoundBase> Footstep;
    UPROPERTY() TObjectPtr<UAudioComponent> FootstepAudio;
    FVector VisualOrigin = FVector(0,0,-90);
    void MoveForward(const FInputActionValue& Value);
    void MoveRight(const FInputActionValue& Value);
    void LookX(const FInputActionValue& Value);
    void LookY(const FInputActionValue& Value);
    void Interact();
};
