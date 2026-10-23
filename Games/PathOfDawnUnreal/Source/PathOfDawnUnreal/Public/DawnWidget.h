#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "DawnWidget.generated.h"

class ADawnPlayerController;
class UVerticalBox;
class UTextBlock;
class UFont;
class UTexture2D;
class UDawnWidget;

UCLASS()
class PATHOFDAWNUNREAL_API UDawnActionButton : public UButton
{
    GENERATED_BODY()
public:
    void SetAction(UDawnWidget* InOwner, const FString& InAction);
private:
    UPROPERTY() TObjectPtr<UDawnWidget> Owner;
    FString Action;
    UFUNCTION() void Dispatch();
};

UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API UDawnWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Refresh();
    void RefreshPrompt();
    void Dispatch(const FString& Action);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event) override;
private:
    UPROPERTY() TObjectPtr<UFont> KoreanFont;
    UPROPERTY() TObjectPtr<UTextBlock> Prompt;
    UPROPERTY() TObjectPtr<UTextBlock> Objective;
    UPROPERTY() TObjectPtr<UTextBlock> NavigationHint;
    UPROPERTY() TArray<TObjectPtr<UDawnActionButton>> ActionButtons;
    UTextBlock* AddText(UVerticalBox* Box,const FText& Text,int32 Size=26,FLinearColor Color=FLinearColor(.91f,.89f,.82f));
    UDawnActionButton* AddButton(UVerticalBox* Box,const FText& Label,const FString& Action,bool bEnabled=true,bool bPrimary=false);
    void AddImage(UVerticalBox* Box,UTexture2D* Texture,float Height);
    void AddSpace(UVerticalBox* Box,float Height);
    void AddRule(UVerticalBox* Box,float Width=76.f);
    ADawnPlayerController* PC() const;
};
