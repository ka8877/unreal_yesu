#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Engine/Texture2D.h"
#include "DawnNarrativeData.generated.h"

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnChoice
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Text;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName NextNode;
};
USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnDialogueNode
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Speaker;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Text;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText RepeatText;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UTexture2D> Portrait;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSoftObjectPtr<UTexture2D> Illustration;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDawnChoice> Choices;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName NextNode;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayNote;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString ContentKind;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString ScriptureReference;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FString SourceNote;
};
UCLASS(BlueprintType)
class PATHOFDAWNUNREAL_API UDawnNarrativeData : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 ContentVersion = 2;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDawnDialogueNode> Nodes;
    const FDawnDialogueNode* Find(FName Id) const;
    bool Validate(FString& Error) const;
};
