#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "DawnGospelData.generated.h"

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnGospelReading
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Title;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Reference;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Text;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Source;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Context;
};

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnGospelBeat
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Speaker;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Text;
    // Scripture, Summary or Dramatization: rendered explicitly by the UI.
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString Kind;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Reference;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString VoiceKey;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText SceneTitle;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Location;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText TimeLabel;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString MusicRole;
};

USTRUCT(BlueprintType)
struct PATHOFDAWNUNREAL_API FDawnGospelQuest
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName ChapterId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Title;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText Objective;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName NpcId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText NpcName;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName ReadingId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bIsPrologue = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDawnGospelBeat> Beats;
};

UCLASS(BlueprintType)
class PATHOFDAWNUNREAL_API UDawnGospelData : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 SchemaVersion = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName CampaignId = TEXT("gospel-pilgrimage");
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 ContentVersion = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Title;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(MultiLine=true)) FText ScopeNote;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString SourceRepository;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString SourceCommit;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDawnGospelReading> Readings;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDawnGospelQuest> Quests;

    const FDawnGospelReading* FindReading(FName Id) const;
    const FDawnGospelQuest* FindQuest(FName Id) const;
    bool Validate(FString& Error) const;
    UFUNCTION(BlueprintCallable) FString ValidationError() const;
};
