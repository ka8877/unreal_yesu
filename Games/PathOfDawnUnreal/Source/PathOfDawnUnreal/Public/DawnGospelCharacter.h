#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "DawnGospelCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UInputMappingContext;
class UInputAction;
struct FInputActionValue;

/** Independent movement pawn for the Gospel preview. The visible proxy is temporary. */
UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API ADawnGospelCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    ADawnGospelCharacter();
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void SetMovementAllowed(bool bAllowed);

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> PreviewProxy;
private:
    UPROPERTY() TObjectPtr<UInputMappingContext> Mapping;
    UPROPERTY() TObjectPtr<UInputAction> ForwardAction;
    UPROPERTY() TObjectPtr<UInputAction> RightAction;
    UPROPERTY() TObjectPtr<UInputAction> LookXAction;
    UPROPERTY() TObjectPtr<UInputAction> LookYAction;
    bool bMovementAllowed = false;
    void MoveForward(const FInputActionValue& Value);
    void MoveRight(const FInputActionValue& Value);
    void LookX(const FInputActionValue& Value);
    void LookY(const FInputActionValue& Value);
};
