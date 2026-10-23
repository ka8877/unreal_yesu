#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "DawnSaveGame.generated.h"
UCLASS()
class PATHOFDAWNUNREAL_API UDawnSaveGame : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 SchemaVersion = 1;
    UPROPERTY(SaveGame) int32 ContentVersion = 2;
    // Complete value snapshot: current WorldState, CP01/CP02, MetaProgress. No UObject/Actor pointers.
    UPROPERTY(SaveGame) FString Payload;
};
