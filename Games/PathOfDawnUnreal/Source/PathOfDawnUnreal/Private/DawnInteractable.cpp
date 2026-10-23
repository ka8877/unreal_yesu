#include "DawnInteractable.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"

ADawnInteractable::ADawnInteractable()
{
    PrimaryActorTick.bCanEverTick = true;
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
    RootComponent = SceneRoot;
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
    Mesh->SetupAttachment(SceneRoot);
    Mesh->SetCollisionProfileName(TEXT("BlockAll"));
}
void ADawnInteractable::ApplyObjectState(bool bInspected, bool bPrepared)
{
    if (!OriginalMesh) OriginalMesh = Mesh->GetStaticMesh();
    if (PreparedMesh) Mesh->SetStaticMesh(bPrepared ? PreparedMesh : OriginalMesh);
    // No narrative effects are fired by restoration or rendering.
    Mesh->SetRenderCustomDepth(bInspected);
    Mesh->SetCustomDepthStencilValue(bPrepared ? 2 : 1);
}
void ADawnInteractable::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    IdleTime += DeltaSeconds;
    // Restrained whole-body sway for temporary sculpted figures; not facial animation.
    if (bCharacter) Mesh->SetRelativeRotation(FRotator(0, FMath::Sin(IdleTime * .65f) * .35f, 0));
}
