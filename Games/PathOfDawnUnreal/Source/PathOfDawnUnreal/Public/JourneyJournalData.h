#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JourneyJournalData.generated.h"

UENUM(BlueprintType)
enum class EJourneyTextKind : uint8 { Summary, GameGuidance, DirectQuotation };

UENUM(BlueprintType)
enum class EJourneyRecordState : uint8 { Locked, Available, Written };

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FJourneyJournalEntry
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName ChapterId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Title;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Summary;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FString> ScriptureReferences;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FText> People;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FText> Places;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText SourceNote;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) EJourneyTextKind TextKind = EJourneyTextKind::Summary;
    // This flag is NOT a graphics certificate. The editor pipeline sets it only
    // after actual scene/capture review. Unavailable scenes must never unlock.
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bSceneReady = false;
};

UCLASS(BlueprintType)
class PATHOFDAWNUNREAL_API UJourneyJournalData : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 ContentVersion = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FJourneyJournalEntry> Entries;
    const FJourneyJournalEntry* Find(FName Id) const;
    bool Validate(FString& Error) const;
    bool IsSceneReady(FName Id) const;
};
