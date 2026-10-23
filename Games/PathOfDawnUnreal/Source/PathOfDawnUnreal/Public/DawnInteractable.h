#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DawnInteractable.generated.h"

class UStaticMeshComponent;
class UStaticMesh;

UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API ADawnInteractable : public AActor
{
    GENERATED_BODY()
public:
    ADawnInteractable();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dawn") FName StableId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dawn") FName InteractionId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dawn") FText DisplayName;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<USceneComponent> SceneRoot;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dawn") TObjectPtr<UStaticMesh> PreparedMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dawn") bool bCharacter = false;
    UFUNCTION(BlueprintCallable) void ApplyObjectState(bool bInspected, bool bPrepared);
private:
    UPROPERTY() TObjectPtr<UStaticMesh> OriginalMesh;
    float IdleTime = 0.f;
};
