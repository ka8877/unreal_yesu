#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "JourneyJournalWidget.generated.h"

class UFont;
class APlayerController;
class UTextBlock;
class UVerticalBox;
class UJourneyJournalSubsystem;
class UJourneyJournalWidget;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FJourneyBookClosed);

/** An internal UMG action; it never stores a separate copy of journal state. */
UCLASS()
class PATHOFDAWNUNREAL_API UJourneyBookButton : public UButton
{
    GENERATED_BODY()
public:
    void Configure(UJourneyJournalWidget* Widget, FName InAction, FName InEntryId = NAME_None);
private:
    UPROPERTY() TWeakObjectPtr<UJourneyJournalWidget> Book;
    FName Action;
    FName EntryId;
    UFUNCTION() void Activate();
};

/**
 * Standalone journal presentation for the Luke 2 rebuild. Configure with the
 * cooked journal subsystem/data and an actual Korean UFont before opening.
 * The existing Dawn player controller and map do not instantiate this widget.
 */
UCLASS(Blueprintable)
class PATHOFDAWNUNREAL_API UJourneyJournalWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="WordJourney|Journal")
    void ConfigureJournal(UJourneyJournalSubsystem* InJournal, UFont* InKoreanFont);

    /** Only opens from normal gameplay, never over a dialogue/menu/cutscene. */
    UFUNCTION(BlueprintCallable, Category="WordJourney|Journal")
    bool OpenFromGameplay(APlayerController* Controller);

    UFUNCTION(BlueprintCallable, Category="WordJourney|Journal")
    void CloseBook();

    UFUNCTION(BlueprintCallable, Category="WordJourney|Journal")
    void RefreshJournal();

    UPROPERTY(BlueprintAssignable, Category="WordJourney|Journal")
    FJourneyBookClosed OnBookClosed;

    void Dispatch(FName Action, FName EntryId);

protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;

private:
    UPROPERTY(Transient) TObjectPtr<UJourneyJournalSubsystem> Journal;
    UPROPERTY(Transient) TObjectPtr<UFont> KoreanFont;
    UPROPERTY(Transient) TArray<TObjectPtr<UJourneyBookButton>> Buttons;
    UPROPERTY(Transient) TWeakObjectPtr<APlayerController> LockedController;
    FName SelectedEntry;
    bool bOwnsInputLocks = false;
    bool bPreviousCursorVisible = false;
    bool bCompactLayout = false;
    bool bConstructed = false;

    void BindJournal();
    void ReleaseInput();
    UTextBlock* Text(UVerticalBox* Parent, const FText& Content, int32 Size, FLinearColor Color);
    UJourneyBookButton* Button(UVerticalBox* Parent, const FText& Label, FName Action,
        FName EntryId = NAME_None, bool bEmphasized = false);
    void Rule(UVerticalBox* Parent);
};
