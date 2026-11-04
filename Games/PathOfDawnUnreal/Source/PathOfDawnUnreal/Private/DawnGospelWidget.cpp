#include "DawnGospelWidget.h"
#include "DawnGospelController.h"
#include "DawnGospelSubsystem.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Font.h"
#include "InputCoreTypes.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"

namespace
{
const FLinearColor GospelIvory(.94f, .91f, .83f, 1);
const FLinearColor GospelGold(.78f, .64f, .39f, 1);
const FLinearColor GospelMuted(.63f, .71f, .72f, 1);
FSlateBrush GospelBrush(FLinearColor Color)
{
    FSlateBrush Brush;
    Brush.DrawAs = ESlateBrushDrawType::Image;
    Brush.ImageSize = FVector2D(1, 1);
    Brush.TintColor = Color;
    return Brush;
}
FText ContentKindLabel(const FString& Kind)
{
    if (Kind == TEXT("Scripture")) return NSLOCTEXT("GospelUI", "ScriptureLabel", "성경 직접 인용");
    if (Kind == TEXT("Dramatization")) return NSLOCTEXT("GospelUI", "DramatizationLabel", "게임을 위한 극화");
    return NSLOCTEXT("GospelUI", "SummaryLabel", "본문 요약");
}
}

void UDawnGospelActionButton::SetAction(UDawnGospelWidget* Widget, const FString& InAction)
{
    OwnerWidget = Widget;
    Action = InAction;
    OnClicked.AddDynamic(this, &UDawnGospelActionButton::DispatchAction);
}
void UDawnGospelActionButton::DispatchAction()
{
    if (OwnerWidget) OwnerWidget->Dispatch(Action);
}
ADawnGospelController* UDawnGospelWidget::Controller() const
{
    return Cast<ADawnGospelController>(GetOwningPlayer());
}
TSharedRef<SWidget> UDawnGospelWidget::RebuildWidget()
{
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("WidgetTree"));
    if (!WidgetTree->RootWidget)
        WidgetTree->RootWidget = WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(), TEXT("GospelRoot"));
    return Super::RebuildWidget();
}
void UDawnGospelWidget::NativeConstruct()
{
    Super::NativeConstruct();
    SetIsFocusable(true);
    KoreanFont = LoadObject<UFont>(nullptr, TEXT("/Game/PathOfDawnGospel/UI/F_Korean.F_Korean"));
    if (!KoreanFont) KoreanFont = LoadObject<UFont>(nullptr, TEXT("/Game/PathOfDawn/UI/F_Korean.F_Korean"));
    Refresh();
}
UTextBlock* UDawnGospelWidget::AddText(UVerticalBox* Box, const FText& Text, int32 Size, FLinearColor Color)
{
    UTextBlock* Block = WidgetTree->ConstructWidget<UTextBlock>();
    Block->SetText(Text);
    Block->SetAutoWrapText(true);
    Block->SetColorAndOpacity(Color);
    Block->SetLineHeightPercentage(1.3f);
    FSlateFontInfo Font = Block->GetFont();
    if (KoreanFont) Font.FontObject = KoreanFont;
    Font.Size = Size;
    Block->SetFont(Font);
    Box->AddChildToVerticalBox(Block)->SetPadding(FMargin(0, 3, 0, 9));
    return Block;
}
void UDawnGospelWidget::AddButton(UVerticalBox* Box, const FText& Label, const FString& Action, bool bEnabled, bool bPrimary)
{
    UDawnGospelActionButton* Button = WidgetTree->ConstructWidget<UDawnGospelActionButton>();
    Button->SetAction(this, Action);
    Button->SetIsEnabled(bEnabled);
    FButtonStyle Style = Button->GetStyle();
    Style.SetNormal(GospelBrush(bPrimary ? FLinearColor(.32f, .25f, .14f, 1) : FLinearColor(.07f, .12f, .14f, 1)));
    Style.SetHovered(GospelBrush(FLinearColor(.23f, .31f, .33f, 1)));
    Style.SetPressed(GospelBrush(FLinearColor(.15f, .22f, .24f, 1)));
    Style.SetDisabled(GospelBrush(FLinearColor(.04f, .07f, .08f, .7f)));
    Style.SetNormalPadding(FMargin(18, 10));
    Style.SetPressedPadding(FMargin(19, 11, 17, 9));
    Button->SetStyle(Style);
    UVerticalBox* LabelBox = WidgetTree->ConstructWidget<UVerticalBox>();
    UTextBlock* LabelBlock = AddText(LabelBox, Label, 22, bEnabled ? GospelIvory : GospelMuted);
    if (UVerticalBoxSlot* Slot = Cast<UVerticalBoxSlot>(LabelBlock->Slot)) Slot->SetPadding(FMargin(0));
    Button->AddChild(LabelBox);
    Box->AddChildToVerticalBox(Button)->SetPadding(FMargin(0, 4));
    ActionButtons.Add(Button);
}
void UDawnGospelWidget::AddRule(UVerticalBox* Box)
{
    USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>();
    Size->SetHeightOverride(2);
    Size->SetWidthOverride(72);
    UBorder* Rule = WidgetTree->ConstructWidget<UBorder>();
    Rule->SetBrushColor(GospelGold);
    Rule->SetPadding(FMargin(0));
    Size->AddChild(Rule);
    UVerticalBoxSlot* Slot = Box->AddChildToVerticalBox(Size);
    Slot->SetHorizontalAlignment(HAlign_Left);
    Slot->SetPadding(FMargin(0, 9, 0, 16));
}

void UDawnGospelWidget::Refresh()
{
    ADawnGospelController* PC = Controller();
    UDawnGospelSubsystem* N = PC ? PC->GetCampaign() : nullptr;
    if (!PC || !N || !WidgetTree) return;
    UOverlay* Root = Cast<UOverlay>(WidgetTree->RootWidget);
    if (!Root) return;
    Root->ClearChildren();
    ActionButtons.Empty();
    Prompt = nullptr;
    Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    Root->SetClipping(EWidgetClipping::ClipToBounds);

    const FName Page = PC->GetPage();
    const bool bPlay = Page == TEXT("Play");
    const bool bReading = bPlay && N->GetStage() == TEXT("Reading");
    const bool bComplete = bPlay && N->IsComplete();
    if (!bPlay)
    {
        UBorder* Veil = WidgetTree->ConstructWidget<UBorder>();
        Veil->SetBrushColor(FLinearColor(.012f, .024f, .034f, .8f));
        Veil->SetVisibility(ESlateVisibility::HitTestInvisible);
        Root->AddChildToOverlay(Veil);
    }

    USizeBox* Frame = WidgetTree->ConstructWidget<USizeBox>();
    Frame->SetMaxDesiredWidth(bPlay && !bReading && !bComplete ? 700.f : 1100.f);
    Frame->SetMaxDesiredHeight(620.f);
    UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetBrushColor(FLinearColor(.018f, .038f, .048f, bPlay ? .9f : .98f));
    Panel->SetPadding(FMargin(26, 20));
    UScrollBox* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    UVerticalBox* Content = WidgetTree->ConstructWidget<UVerticalBox>();
    Scroll->AddChild(Content);
    Panel->AddChild(Scroll);
    Frame->AddChild(Panel);
    UOverlaySlot* FrameSlot = Root->AddChildToOverlay(Frame);
    FrameSlot->SetHorizontalAlignment(bPlay && !bReading && !bComplete ? HAlign_Left : HAlign_Center);
    FrameSlot->SetVerticalAlignment(bReading ? VAlign_Bottom : bPlay && !bComplete ? VAlign_Top : VAlign_Center);
    FrameSlot->SetPadding(FMargin(24));

    if (Page == TEXT("Title"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "Edition", "말씀을 따라 예수님의 길 · Unreal"), 20, GospelGold);
        AddText(Content, NSLOCTEXT("GospelUI", "TempleTitle", "열두 살, 성전에서"), 40);
        AddRule(Content);
        AddText(Content, NSLOCTEXT("GospelUI", "PreviewScope", "나사렛의 출발부터 성전의 만남, 부모와의 귀향까지 같은 복음서 여정을 따라갑니다."));
        AddText(Content, NSLOCTEXT("GospelUI", "PreviewArtStatus", "이야기·진행 검증용 미리보기입니다. 인물과 공간은 임시 표현이며 영화 같은 실사·반실사 화면과 음악은 제작 중입니다."), 20, GospelMuted);
        AddButton(Content, NSLOCTEXT("GospelUI", "StartTemple", "성전 구간 새로 시작"), TEXT("Start"), N->IsReady(), true);
        AddButton(Content, NSLOCTEXT("GospelUI", "Continue", "이어하기"), TEXT("Continue"), N->CanContinue());
        AddText(Content, NSLOCTEXT("GospelUI", "IndependentSave", "이 미리보기의 진행은 Unity판과 기존 갈릴리 데모의 저장과 별도로 보관됩니다."), 18, GospelMuted);
    }
    else if (Page == TEXT("ConfirmNew"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "NewConfirmTitle", "성전 여정을 새로 시작할까요?"), 34);
        AddText(Content, NSLOCTEXT("GospelUI", "NewConfirmBody", "현재 Unreal 복음서 여정의 진행과 발견 기록을 새로 시작합니다. Unity판과 기존 갈릴리 데모의 저장은 유지됩니다."));
        AddButton(Content, NSLOCTEXT("GospelUI", "CancelNew", "기존 여정 유지"), TEXT("Menu"), true, true);
        AddButton(Content, NSLOCTEXT("GospelUI", "ConfirmStart", "성전 구간 새로 시작"), TEXT("ConfirmStart"));
    }
    else if (bPlay)
    {
        AddText(Content, N->GetAgeLabel(), 18, GospelGold);
        if (bComplete)
        {
            AddText(Content, NSLOCTEXT("GospelUI", "TempleComplete", "성전 구간을 마쳤습니다"), 34);
            AddRule(Content);
            AddText(Content, NSLOCTEXT("GospelUI", "TempleCompleteBody", "부모와 함께 나사렛으로 돌아온 기록까지 따라왔습니다. 발견한 말씀과 여정 기록을 다시 살펴볼 수 있습니다."));
            AddText(Content, NSLOCTEXT("GospelUI", "TempleCompleteScope", "탄생 서막과 성인 요단강 여정은 이번 성전 미리보기의 플레이 범위에 포함되지 않습니다."), 20, GospelMuted);
            AddButton(Content, NSLOCTEXT("GospelUI", "ReadDiscovered", "발견한 말씀 읽기 · M"), TEXT("Book"), true, true);
            AddButton(Content, NSLOCTEXT("GospelUI", "ReadJournal", "여정 기록 · J"), TEXT("Journal"));
            AddButton(Content, NSLOCTEXT("GospelUI", "SaveTitle", "저장하고 타이틀로"), TEXT("Title"));
        }
        else if (bReading)
        {
            const FDawnGospelBeat Beat = N->GetCurrentBeat();
            AddText(Content, Beat.SceneTitle, 30);
            AddText(Content, FText::Format(NSLOCTEXT("GospelUI", "ScenePlaceTime", "{0} · {1}"), Beat.Location, Beat.TimeLabel), 18, GospelMuted);
            AddRule(Content);
            AddText(Content, Beat.Speaker, 21, GospelGold);
            AddText(Content, Beat.Text, 26);
            AddText(Content, ContentKindLabel(Beat.Kind), 18, GospelGold);
            if (!Beat.Reference.IsEmpty()) AddText(Content, Beat.Reference, 18, GospelMuted);
            AddButton(Content, NSLOCTEXT("GospelUI", "AdvanceStory", "다음 이야기 · Enter / Space"), TEXT("Advance"), true, true);
            AddButton(Content, NSLOCTEXT("GospelUI", "BookWhileReading", "발견한 말씀 · M"), TEXT("Book"));
        }
        else
        {
            AddText(Content, N->GetCurrentQuest().Title, 29);
            AddText(Content, N->GetObjective(), 22);
            Prompt = AddText(Content, PC->GetInteractionPrompt(), 20, GospelGold);
            AddText(Content, NSLOCTEXT("GospelUI", "ExploreControls", "M 말씀 · J 여정 기록 · Esc 메뉴"), 17, GospelMuted);
            AddText(Content, NSLOCTEXT("GospelUI", "InPlayArtStatus", "개발용 공간 · 시각·음향 제작 중"), 16, GospelMuted);
        }
    }
    else if (Page == TEXT("Book"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "BookTitle", "발견한 말씀"), 36);
        AddText(Content, FText::Format(NSLOCTEXT("GospelUI", "FoundCount", "여정에서 발견한 본문 {0}개"), FText::AsNumber(N->GetDiscoveredCount())), 20, GospelGold);
        AddText(Content, NSLOCTEXT("GospelUI", "BookNotice", "사건을 마치면 그 본문이 여기에 남습니다. 책을 여는 것만으로 다음 여정이 진행되지는 않습니다."), 19, GospelMuted);
        AddRule(Content);
        const TArray<FDawnGospelReading> Readings = N->GetReadings();
        if (Readings.IsEmpty()) AddText(Content, NSLOCTEXT("GospelUI", "EmptyBook", "아직 발견한 본문이 없습니다. 현재 여정의 만남을 이어가세요."));
        for (const FDawnGospelReading& Reading : Readings)
        {
            AddText(Content, Reading.Title, 28);
            AddText(Content, Reading.Reference, 20, GospelGold);
            AddText(Content, Reading.Text, 24);
            AddText(Content, Reading.Source, 17, GospelMuted);
            if (!Reading.Context.IsEmpty())
            {
                AddText(Content, NSLOCTEXT("GospelUI", "ReadingContext", "본문을 살펴보는 해설"), 18, GospelGold);
                AddText(Content, Reading.Context, 20, GospelMuted);
            }
            AddRule(Content);
        }
        AddButton(Content, NSLOCTEXT("GospelUI", "Return", "돌아가기"), TEXT("Back"), true, true);
    }
    else if (Page == TEXT("Journal"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "JournalTitle", "여정 기록"), 36);
        AddText(Content, NSLOCTEXT("GospelUI", "JournalScope", "이번 성전 구간에서 지나온 사건과 현재 목적지를 기록합니다."), 20, GospelMuted);
        AddRule(Content);
        for (const FDawnGospelJournalEntry& Entry : N->GetJournal())
        {
            AddText(Content, FText::Format(Entry.bIsComplete ?
                NSLOCTEXT("GospelUI", "CompletedEntry", "마친 여정 · {0}") : NSLOCTEXT("GospelUI", "CurrentEntry", "현재 여정 · {0}"), Entry.Title),
                25, Entry.bIsCurrent ? GospelGold : GospelIvory);
            AddText(Content, Entry.Objective, 20, GospelMuted);
        }
        AddButton(Content, NSLOCTEXT("GospelUI", "Return", "돌아가기"), TEXT("Back"), true, true);
    }
    else if (Page == TEXT("Pause"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "PauseTitle", "잠시 머무르기"), 36);
        AddText(Content, N->GetObjective(), 22, GospelGold);
        AddRule(Content);
        AddButton(Content, NSLOCTEXT("GospelUI", "Resume", "여정으로 돌아가기"), TEXT("Back"), true, true);
        AddButton(Content, NSLOCTEXT("GospelUI", "Save", "현재 진행 저장"), TEXT("Save"));
        AddButton(Content, NSLOCTEXT("GospelUI", "ReadDiscovered", "발견한 말씀 읽기 · M"), TEXT("Book"));
        AddButton(Content, NSLOCTEXT("GospelUI", "ReadJournal", "여정 기록 · J"), TEXT("Journal"));
        AddButton(Content, NSLOCTEXT("GospelUI", "SaveTitle", "저장하고 타이틀로"), TEXT("Title"));
    }
    else if (Page == TEXT("UnsavedTitle"))
    {
        AddText(Content, NSLOCTEXT("GospelUI", "UnsavedTitle", "진행을 저장하지 못했습니다"), 34);
        AddText(Content, NSLOCTEXT("GospelUI", "UnsavedBody", "기존 저장 원본은 보존됐습니다. 현재 여정으로 돌아가거나 저장 없이 타이틀로 이동할 수 있습니다."));
        AddButton(Content, NSLOCTEXT("GospelUI", "Stay", "현재 여정으로 돌아가기"), TEXT("Back"), true, true);
        AddButton(Content, NSLOCTEXT("GospelUI", "LeaveWithoutSave", "저장 없이 타이틀로"), TEXT("LeaveTitle"));
    }

    const FText Message = PC->GetStatusMessage();
    if (!Message.IsEmpty()) AddText(Content, Message, 20, N->LastError.IsEmpty() ? GospelGold : FLinearColor(1, .62f, .48f, 1));
    if (!N->LastError.IsEmpty()) AddButton(Content, NSLOCTEXT("GospelUI", "RecoverBackup", "보존된 백업 복구 시도"), TEXT("Recover"));
}
void UDawnGospelWidget::RefreshPrompt()
{
    if (Prompt && Controller()) Prompt->SetText(Controller()->GetInteractionPrompt());
}
void UDawnGospelWidget::Dispatch(const FString& Action)
{
    if (Controller()) Controller()->HandleAction(Action);
}
FReply UDawnGospelWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    const FKey Key = Event.GetKey();
    FString Action;
    if (Key == EKeys::Escape) Action = TEXT("Menu");
    else if (Key == EKeys::Enter || Key == EKeys::SpaceBar) Action = TEXT("Advance");
    else if (Key == EKeys::E) Action = TEXT("Interact");
    else if (Key == EKeys::M) Action = TEXT("Book");
    else if (Key == EKeys::J) Action = TEXT("Journal");
    if (!Action.IsEmpty())
    {
        if (!Event.IsRepeat()) Dispatch(Action);
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, Event);
}
