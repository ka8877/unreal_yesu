#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "DawnGospelWidget.generated.h"

class ADawnGospelController;
class UDawnGospelWidget;
class UVerticalBox;
class UTextBlock;
class UFont;

UCLASS()
class PATHOFDAWNUNREAL_API UDawnGospelActionButton : public UButton
{
    GENERATED_BODY()
public:
    void SetAction(UDawnGospelWidget* Widget, const FString& InAction);
private:
    UPROPERTY() TObjectPtr<UDawnGospelWidget> OwnerWidget;
    FString Action;
    UFUNCTION() void DispatchAction();
};

/** A source-aware, discovery-only UI for the separately saved Gospel campaign. */
UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API UDawnGospelWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Refresh();
    void RefreshPrompt();
    void Dispatch(const FString& Action);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
private:
    UPROPERTY() TObjectPtr<UFont> KoreanFont;
    UPROPERTY() TObjectPtr<UTextBlock> Prompt;
    UPROPERTY() TArray<TObjectPtr<UDawnGospelActionButton>> ActionButtons;
    ADawnGospelController* Controller() const;
    UTextBlock* AddText(UVerticalBox* Box, const FText& Text, int32 Size = 24,
        FLinearColor Color = FLinearColor(.94f, .91f, .83f, 1));
    void AddButton(UVerticalBox* Box, const FText& Label, const FString& Action,
        bool bEnabled = true, bool bPrimary = false);
    void AddRule(UVerticalBox* Box);
};
