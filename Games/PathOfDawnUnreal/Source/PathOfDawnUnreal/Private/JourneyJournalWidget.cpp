#include "JourneyJournalWidget.h"

#include "JourneyJournalData.h"
#include "JourneyJournalSubsystem.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Font.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Styling/SlateTypes.h"

namespace
{
const FLinearColor Paper(.88f, .83f, .72f, 1.f);
const FLinearColor Ink(.115f, .105f, .086f, 1.f);
const FLinearColor QuietInk(.30f, .28f, .235f, 1.f);
const FLinearColor Accent(.29f, .235f, .14f, 1.f);
const FLinearColor LightInk(.95f, .92f, .84f, 1.f);

FSlateBrush Fill(const FLinearColor& Color)
{
    FSlateBrush Brush;
    Brush.DrawAs = ESlateBrushDrawType::Image;
    Brush.ImageSize = FVector2D(1.f, 1.f);
    Brush.TintColor = Color;
    return Brush;
}

FText TextKindLabel(EJourneyTextKind Kind)
{
    switch (Kind)
    {
    case EJourneyTextKind::Summary:
        return NSLOCTEXT("WordJourneyBook", "SummaryKind", "성경 내용 요약");
    case EJourneyTextKind::GameGuidance:
        return NSLOCTEXT("WordJourneyBook", "GuidanceKind", "게임 진행 안내");
    case EJourneyTextKind::DirectQuotation:
        return NSLOCTEXT("WordJourneyBook", "QuotationKind", "성경 직접 인용");
    default:
        return FText::GetEmpty();
    }
}

FText JoinedText(const TArray<FText>& Values)
{
    return FText::Join(FText::FromString(TEXT(" · ")), Values);
}

FText ScriptureReferenceLabel(const TArray<FString>& References)
{
    TArray<FText> Labels;
    Labels.Reserve(References.Num());
    for (const FString& Reference : References)
    {
        // Stored references remain canonical for validation and save stability.
        // Only the presentation translates the book name and range separator.
        if (Reference.StartsWith(TEXT("Luke "), ESearchCase::CaseSensitive))
        {
            const FString ChapterAndVerses = Reference.RightChop(5).Replace(TEXT("-"), TEXT("–"));
            Labels.Add(FText::Format(NSLOCTEXT("WordJourneyBook", "LukeReference", "누가복음 {0}"),
                FText::FromString(ChapterAndVerses)));
        }
        else
        {
            Labels.Add(FText::FromString(Reference));
        }
    }
    return FText::Join(FText::FromString(TEXT(" · ")), Labels);
}
}

void UJourneyBookButton::Configure(UJourneyJournalWidget* Widget, FName InAction, FName InEntryId)
{
    Book = Widget;
    Action = InAction;
    EntryId = InEntryId;
    OnClicked.AddUniqueDynamic(this, &UJourneyBookButton::Activate);
}

void UJourneyBookButton::Activate()
{
    if (Book.IsValid()) Book->Dispatch(Action, EntryId);
}

void UJourneyJournalWidget::ConfigureJournal(UJourneyJournalSubsystem* InJournal, UFont* InKoreanFont)
{
    if (Journal) Journal->OnJournalChanged.RemoveDynamic(this, &UJourneyJournalWidget::RefreshJournal);
    Journal = InJournal;
    KoreanFont = InKoreanFont;
    SelectedEntry = NAME_None;
    if (bConstructed)
    {
        BindJournal();
        RefreshJournal();
    }
}

bool UJourneyJournalWidget::OpenFromGameplay(APlayerController* Controller)
{
    // This explicit contract lets us restore GameOnly safely. An existing menu,
    // dialogue or sequence retains ownership of its cursor and input locks.
    if (!IsValid(Controller) || !Controller->IsLocalController() || !Journal || IsInViewport()
        || bOwnsInputLocks || Controller->bShowMouseCursor
        || Controller->IsMoveInputIgnored() || Controller->IsLookInputIgnored())
    {
        return false;
    }
    SetOwningPlayer(Controller);
    bPreviousCursorVisible = Controller->bShowMouseCursor;
    LockedController = Controller;
    Controller->SetIgnoreMoveInput(true);
    Controller->SetIgnoreLookInput(true);
    bOwnsInputLocks = true;
    AddToViewport(40);
    // UIOnly also blocks interaction/advance actions such as E from reaching
    // gameplay; ignore-move/look locks alone would not consume those actions.
    FInputModeUIOnly Input;
    Input.SetWidgetToFocus(TakeWidget());
    Input.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    Controller->SetInputMode(Input);
    Controller->bShowMouseCursor = true;
    SetKeyboardFocus();
    return true;
}

void UJourneyJournalWidget::ReleaseInput()
{
    if (!bOwnsInputLocks) return;
    // Each false removes only the matching lock this widget acquired. Never
    // reset another system's ignore-input stack using ResetIgnore*Input().
    if (APlayerController* Controller = LockedController.Get())
    {
        Controller->SetIgnoreMoveInput(false);
        Controller->SetIgnoreLookInput(false);
        Controller->bShowMouseCursor = bPreviousCursorVisible;
        Controller->SetInputMode(FInputModeGameOnly());
    }
    bOwnsInputLocks = false;
    LockedController.Reset();
}

void UJourneyJournalWidget::CloseBook()
{
    const bool bWasOpen = IsInViewport() || bOwnsInputLocks;
    ReleaseInput();
    RemoveFromParent();
    if (bWasOpen) OnBookClosed.Broadcast();
}

TSharedRef<SWidget> UJourneyJournalWidget::RebuildWidget()
{
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"));
    if (!WidgetTree->RootWidget)
        WidgetTree->RootWidget = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("JourneyBookRoot"));
    return Super::RebuildWidget();
}

void UJourneyJournalWidget::BindJournal()
{
    if (Journal) Journal->OnJournalChanged.AddUniqueDynamic(this, &UJourneyJournalWidget::RefreshJournal);
}

void UJourneyJournalWidget::NativeConstruct()
{
    Super::NativeConstruct();
    bConstructed = true;
    SetIsFocusable(true);
    BindJournal();
    RefreshJournal();
}

void UJourneyJournalWidget::NativeDestruct()
{
    if (Journal) Journal->OnJournalChanged.RemoveDynamic(this, &UJourneyJournalWidget::RefreshJournal);
    ReleaseInput();
    Buttons.Empty();
    bConstructed = false;
    Super::NativeDestruct();
}

void UJourneyJournalWidget::NativeTick(const FGeometry& Geometry, float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    const float Width = Geometry.GetLocalSize().X;
    const bool bNowCompact = Width > 0.f && Width < 900.f;
    if (Width > 0.f && bNowCompact != bCompactLayout)
    {
        bCompactLayout = bNowCompact;
        RefreshJournal();
    }
}

FReply UJourneyJournalWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::B)
    {
        CloseBook();
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, Event);
}

UTextBlock* UJourneyJournalWidget::Text(UVerticalBox* Parent, const FText& Content, int32 Size, FLinearColor Color)
{
    UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
    Label->SetText(Content);
    Label->SetAutoWrapText(true);
    Label->SetColorAndOpacity(Color);
    Label->SetLineHeightPercentage(1.45f);
    FSlateFontInfo Font = Label->GetFont();
    if (KoreanFont) Font.FontObject = KoreanFont;
    Font.Size = Size;
    Label->SetFont(Font);
    Parent->AddChildToVerticalBox(Label)->SetPadding(FMargin(0.f, 3.f, 0.f, 9.f));
    return Label;
}

UJourneyBookButton* UJourneyJournalWidget::Button(UVerticalBox* Parent, const FText& Label,
    FName Action, FName EntryId, bool bEmphasized)
{
    UJourneyBookButton* Control = WidgetTree->ConstructWidget<UJourneyBookButton>();
    Control->Configure(this, Action, EntryId);
    FButtonStyle Style = Control->GetStyle();
    Style.SetNormal(Fill(bEmphasized ? Accent : FLinearColor(.77f, .72f, .61f, 1.f)));
    Style.SetHovered(Fill(bEmphasized ? FLinearColor(.39f, .32f, .20f, 1.f) : FLinearColor(.82f, .77f, .66f, 1.f)));
    Style.SetPressed(Fill(FLinearColor(.47f, .39f, .27f, 1.f)));
    Style.SetNormalPadding(FMargin(16.f, 12.f));
    Style.SetPressedPadding(FMargin(17.f, 13.f, 15.f, 11.f));
    Control->SetStyle(Style);
    UVerticalBox* Content = WidgetTree->ConstructWidget<UVerticalBox>();
    UTextBlock* Caption = Text(Content, Label, 22, bEmphasized ? LightInk : Ink);
    CastChecked<UVerticalBoxSlot>(Caption->Slot)->SetPadding(FMargin(0.f));
    Control->AddChild(Content);
    Parent->AddChildToVerticalBox(Control)->SetPadding(FMargin(0.f, 5.f));
    Buttons.Add(Control);
    return Control;
}

void UJourneyJournalWidget::Rule(UVerticalBox* Parent)
{
    USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>();
    Size->SetHeightOverride(1.f);
    UBorder* Line = WidgetTree->ConstructWidget<UBorder>();
    Line->SetBrushColor(FLinearColor(.42f, .36f, .26f, .35f));
    Line->SetPadding(FMargin(0.f));
    Size->AddChild(Line);
    Parent->AddChildToVerticalBox(Size)->SetPadding(FMargin(0.f, 13.f));
}

void UJourneyJournalWidget::Dispatch(FName Action, FName EntryId)
{
    if (Action == TEXT("Close")) { CloseBook(); return; }
    if (!Journal) return;
    if (Action == TEXT("Select"))
    {
        // GetVisibleEntries is authoritative: a fabricated/locked ID cannot
        // cause the widget to read or reveal a future entry's body.
        for (const FJourneyJournalEntry& Entry : Journal->GetVisibleEntries())
        {
            if (Entry.Id == EntryId) { SelectedEntry = EntryId; break; }
        }
    }
    else if (Action == TEXT("Write") && Journal->GetEntryState(EntryId) == EJourneyRecordState::Available)
    {
        Journal->WriteEntry(EntryId);
    }
    RefreshJournal();
}

void UJourneyJournalWidget::RefreshJournal()
{
    UOverlay* Root = WidgetTree ? Cast<UOverlay>(WidgetTree->RootWidget) : nullptr;
    if (!Root) return;
    Buttons.Empty();
    Root->ClearChildren();
    UBorder* Surround = WidgetTree->ConstructWidget<UBorder>();
    Surround->SetBrushColor(FLinearColor(.027f, .023f, .018f, .88f));
    Surround->SetPadding(FMargin(bCompactLayout ? 14.f : 34.f));
    Root->AddChildToOverlay(Surround);
    UVerticalBox* Book = WidgetTree->ConstructWidget<UVerticalBox>();
    Surround->AddChild(Book);

    // Avoid presenting broken Korean glyphs as a valid configured journal.
    if (!KoreanFont || !Journal)
    {
        Text(Book, FText::FromString(TEXT("Journal setup required")), 30, LightInk);
        Text(Book, FText::FromString(TEXT("Configure a cooked journal data asset and Korean UFont before opening this book.")), 24, LightInk);
        Button(Book, FText::FromString(TEXT("Close [Esc / B]")), TEXT("Close"), NAME_None, true);
        return;
    }

    Text(Book, NSLOCTEXT("WordJourneyBook", "BookName", "성경 여정 기록책"), bCompactLayout ? 28 : 34, LightInk);
    Text(Book, NSLOCTEXT("WordJourneyBook", "BookPurpose", "이야기 속에서 만난 사건을 정리하는 기록입니다."), 19, FLinearColor(.75f, .71f, .63f));

    UBorder* IndexPaper = WidgetTree->ConstructWidget<UBorder>();
    IndexPaper->SetBrushColor(FLinearColor(.82f, .77f, .65f, 1.f));
    IndexPaper->SetPadding(FMargin(bCompactLayout ? 16.f : 24.f));
    UScrollBox* IndexScroll = WidgetTree->ConstructWidget<UScrollBox>();
    UVerticalBox* Index = WidgetTree->ConstructWidget<UVerticalBox>();
    IndexScroll->AddChild(Index);
    IndexPaper->AddChild(IndexScroll);

    UBorder* DetailPaper = WidgetTree->ConstructWidget<UBorder>();
    DetailPaper->SetBrushColor(Paper);
    DetailPaper->SetPadding(FMargin(bCompactLayout ? 20.f : 38.f));
    UScrollBox* DetailScroll = WidgetTree->ConstructWidget<UScrollBox>();
    UVerticalBox* Detail = WidgetTree->ConstructWidget<UVerticalBox>();
    DetailScroll->AddChild(Detail);
    DetailPaper->AddChild(DetailScroll);

    if (bCompactLayout)
    {
        USizeBox* IndexHeight = WidgetTree->ConstructWidget<USizeBox>();
        IndexHeight->SetMaxDesiredHeight(190.f);
        IndexHeight->AddChild(IndexPaper);
        Book->AddChildToVerticalBox(IndexHeight)->SetPadding(FMargin(0.f, 8.f));
        Book->AddChildToVerticalBox(DetailPaper)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    }
    else
    {
        UHorizontalBox* Spread = WidgetTree->ConstructWidget<UHorizontalBox>();
        USizeBox* IndexWidth = WidgetTree->ConstructWidget<USizeBox>();
        IndexWidth->SetWidthOverride(310.f);
        IndexWidth->AddChild(IndexPaper);
        Spread->AddChildToHorizontalBox(IndexWidth)->SetPadding(FMargin(0.f, 0.f, 3.f, 0.f));
        Spread->AddChildToHorizontalBox(DetailPaper)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        UVerticalBoxSlot* SpreadSlot = Book->AddChildToVerticalBox(Spread);
        SpreadSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        SpreadSlot->SetPadding(FMargin(0.f, 10.f));
    }

    Text(Index, NSLOCTEXT("WordJourneyBook", "Contents", "나의 기록"), 24, Ink);
    Rule(Index);
    const TArray<FJourneyJournalEntry> Entries = Journal->GetVisibleEntries();
    if (!Entries.ContainsByPredicate([this](const FJourneyJournalEntry& Entry) { return Entry.Id == SelectedEntry; }))
        SelectedEntry = Entries.IsEmpty() ? NAME_None : Entries.Last().Id;

    const FJourneyJournalEntry* Selected = nullptr;
    for (const FJourneyJournalEntry& Entry : Entries)
    {
        const bool bWritten = Journal->GetEntryState(Entry.Id) == EJourneyRecordState::Written;
        const FText State = bWritten
            ? NSLOCTEXT("WordJourneyBook", "WrittenMarker", "기록 완료")
            : NSLOCTEXT("WordJourneyBook", "AvailableMarker", "새 기록 · 작성 전");
        Button(Index, Entry.Title, TEXT("Select"), Entry.Id, Entry.Id == SelectedEntry);
        Text(Index, State, 16, QuietInk);
        if (Entry.Id == SelectedEntry) Selected = &Entry;
    }
    // No locked titles, references, people, places or summaries are queried.
    Text(Index, NSLOCTEXT("WordJourneyBook", "Unfilled", "아직 비어 있는 페이지"), 19, QuietInk);

    if (!Selected)
    {
        Text(Detail, NSLOCTEXT("WordJourneyBook", "BlankTitle", "첫 기록을 기다리며"), 30, Ink);
        Rule(Detail);
        Text(Detail, NSLOCTEXT("WordJourneyBook", "BlankBody", "아직 작성한 기록이 없습니다.\n이야기 속 사건을 만난 뒤, 이 빈 페이지에 기록을 남길 수 있습니다."), 25, QuietInk);
    }
    else
    {
        const EJourneyRecordState State = Journal->GetEntryState(Selected->Id);
        Text(Detail, TextKindLabel(Selected->TextKind), 17, Accent);
        Text(Detail, Selected->Title, bCompactLayout ? 29 : 34, Ink);
        Rule(Detail);
        Text(Detail, Selected->Summary, 25, Ink);
        Rule(Detail);
        Text(Detail, NSLOCTEXT("WordJourneyBook", "ReferenceTitle", "성경 출처"), 18, Accent);
        Text(Detail, ScriptureReferenceLabel(Selected->ScriptureReferences), 22, Ink);
        Text(Detail, NSLOCTEXT("WordJourneyBook", "PeopleTitle", "관련 인물"), 18, Accent);
        Text(Detail, JoinedText(Selected->People), 21, Ink);
        Text(Detail, NSLOCTEXT("WordJourneyBook", "PlacesTitle", "장소"), 18, Accent);
        Text(Detail, JoinedText(Selected->Places), 21, Ink);
        Text(Detail, Selected->SourceNote, 18, QuietInk);
        Rule(Detail);
        if (State == EJourneyRecordState::Available)
        {
            Text(Detail, NSLOCTEXT("WordJourneyBook", "WriteInstruction", "사건을 확인했습니다. 아래 버튼을 눌러 기록을 확정하고 저장합니다."), 21, QuietInk);
            Button(Detail, NSLOCTEXT("WordJourneyBook", "WriteButton", "이 페이지에 기록하기"), TEXT("Write"), Selected->Id, true);
        }
        else if (State == EJourneyRecordState::Written)
        {
            Text(Detail, NSLOCTEXT("WordJourneyBook", "WrittenStamp", "기록 완료"), 24, Accent);
        }
    }
    if (!Journal->LastError.IsEmpty()) Text(Book, Journal->LastError, 20, FLinearColor(1.f, .63f, .49f));
    Button(Book, NSLOCTEXT("WordJourneyBook", "CloseButton", "기록책 닫기   Esc / B"), TEXT("Close"), NAME_None, true);
    if (bOwnsInputLocks && IsInViewport()) SetKeyboardFocus();
}
