#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DawnAssetTools.generated.h"
class UFont;
class UFontFace;
class UDawnNarrativeData;

/** Editor-only import bridge. Never loaded by a packaged game. */
UCLASS()
class PATHOFDAWNUNREALEDITOR_API UDawnAssetTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="PathOfDawn|Editor")
    static UFont* CreateCompositeFont(UFontFace* Face, const FString& PackagePath);
    UFUNCTION(BlueprintCallable, Category="PathOfDawn|Editor")
    static FString ValidateNarrative(UDawnNarrativeData* Data);
    UFUNCTION(BlueprintCallable, Category="PathOfDawn|Editor")
    static FText LocalizedText(const FString& Key, const FString& Value);
    UFUNCTION(BlueprintCallable, Category="PathOfDawn|Editor")
    static bool HasRuntimeFont(UFont* Font);
};
