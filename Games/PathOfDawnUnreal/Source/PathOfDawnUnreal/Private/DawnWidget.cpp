#include "DawnWidget.h"
#include "DawnPlayerController.h"
#include "DawnPlayerSettings.h"
#include "DawnNarrativeSubsystem.h"
#include "DawnNarrativeData.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Components/Image.h"
#include "Components/ScaleBox.h"
#include "Components/SizeBox.h"
#include "Components/ScrollBox.h"
#include "Engine/Font.h"
#include "Engine/Texture2D.h"
#include "InputCoreTypes.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"

namespace {
const FLinearColor DawnIvory(.94f,.91f,.82f,1.f);
const FLinearColor DawnGold(.76f,.59f,.34f,1.f);
const FLinearColor DawnMuted(.58f,.66f,.65f,1.f);
const FLinearColor DawnInk(.018f,.035f,.043f,1.f);

FSlateBrush SolidBrush(const FLinearColor& Color)
{
    FSlateBrush Brush;
    Brush.DrawAs=ESlateBrushDrawType::Image;
    Brush.ImageSize=FVector2D(1,1);
    Brush.TintColor=Color;
    return Brush;
}

// The ramp lives in UMG, so the illustration stays clean and can be reused.
// All decorative layers ignore pointer input. No external material is required.
void AddSideShade(UWidgetTree* Tree,UOverlay* Root)
{
    UHorizontalBox* Ramp=Tree->ConstructWidget<UHorizontalBox>();
    Ramp->SetVisibility(ESlateVisibility::HitTestInvisible);
    constexpr int32 StripCount=64;
    for (int32 Index=0;Index<StripCount;++Index)
    {
        const float Position=(Index+.5f)/StripCount;
        const float Blend=FMath::Clamp((Position-.23f)/.49f,0.f,1.f);
        const float Smooth=Blend*Blend*(3.f-2.f*Blend);
        UImage* Shade=Tree->ConstructWidget<UImage>();
        Shade->SetBrush(SolidBrush(FLinearColor(DawnInk.R,DawnInk.G,DawnInk.B,.98f-.92f*Smooth)));
        Ramp->AddChildToHorizontalBox(Shade)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    }
    Root->AddChildToOverlay(Ramp);
}

FText LabelForMemory(FName Id)
{
    if (Id==TEXT("Net") || Id==TEXT("Memory_Net")) return NSLOCTEXT("DawnUI","UI_d9212673c411","그물 · 누군가의 밤이 남긴 매듭");
    if (Id==TEXT("Boat") || Id==TEXT("Memory_Boat")) return NSLOCTEXT("DawnUI","UI_dcb7775b745e","작은 배 · 다시 물 위로 나아갈 자리");
    if (Id==TEXT("Stone") || Id==TEXT("Memory_Stone")) return NSLOCTEXT("DawnUI","UI_ca40f79ab0d6","물가의 돌 · 새벽을 기다린 흔적");
    if (Id==TEXT("Memory_Shore")) return NSLOCTEXT("DawnUI","UI_e640c119e507","물가의 흔적 · 다른 자리에서 바라본 아침");
    if (Id==TEXT("Memory_SharedWork")) return NSLOCTEXT("DawnUI","UI_b2288ec6d2ad","함께 묶은 매듭 · 말보다 먼저 내민 손");
    if (Id==TEXT("Memory_Together") || Id==TEXT("Memory_Ending_Together")) return NSLOCTEXT("DawnUI","UI_3f4428568fed","함께한 아침 · 시몬 곁에 머문 기억");
    if (Id==TEXT("Memory_Witness") || Id==TEXT("Memory_Ending_Witness")) return NSLOCTEXT("DawnUI","UI_1aa9305840d3","호숫가의 증인 · 물빛에 남은 기억");
    if (Id==TEXT("Memory_Departure") || Id==TEXT("Memory_Ending_Departure")) return NSLOCTEXT("DawnUI","UI_4fd349683402","아직 걷지 않은 길 · 마음에 담고 떠난 기억");
    return NSLOCTEXT("DawnUI","UI_dba1da04d38c","새로운 아침의 기억");
}
FText ChoiceSummary(UDawnNarrativeSubsystem* N)
{
    FString Result;
    for (FName Id:N->GetChoiceHistory())
    {
        if (Id==TEXT("Choice1_A")) Result+=NSLOCTEXT("DawnUI","History1A","첫 선택: 시몬의 그물 정리를 도왔다.\n").ToString();
        if (Id==TEXT("Choice1_B")) Result+=NSLOCTEXT("DawnUI","History1B","첫 선택: 물가에 남겨진 흔적을 살폈다.\n").ToString();
        if (Id==TEXT("Choice2_A")) Result+=NSLOCTEXT("DawnUI","History2A","두 번째 선택: 시몬 곁에 남았다.").ToString();
        if (Id==TEXT("Choice2_B")) Result+=NSLOCTEXT("DawnUI","History2B","두 번째 선택: 마을로 발걸음을 돌렸다.").ToString();
    }
    return FText::FromString(Result);
}
FText EndingLabel(FName Id)
{
    if (Id==TEXT("Ending_Together")) return NSLOCTEXT("DawnUI","UI_c7405734a2bc","함께한 아침");
    if (Id==TEXT("Ending_Witness")) return NSLOCTEXT("DawnUI","UI_022f237d3ec0","호숫가의 증인");
    if (Id==TEXT("Ending_Departure")) return NSLOCTEXT("DawnUI","UI_bb97ed49a243","아직 걷지 않은 길");
    return FText::FromName(Id);
}
}
void UDawnActionButton::SetAction(UDawnWidget* InOwner,const FString& InAction)
{
    Owner=InOwner; Action=InAction;
    OnClicked.AddDynamic(this,&UDawnActionButton::Dispatch);
}
void UDawnActionButton::Dispatch() { if (Owner) Owner->Dispatch(Action); }
ADawnPlayerController* UDawnWidget::PC() const { return Cast<ADawnPlayerController>(GetOwningPlayer()); }
TSharedRef<SWidget> UDawnWidget::RebuildWidget()
{
    if (!WidgetTree) WidgetTree=NewObject<UWidgetTree>(this,TEXT("WidgetTree"));
    if (!WidgetTree->RootWidget) WidgetTree->RootWidget=WidgetTree->ConstructWidget<UOverlay>(UOverlay::StaticClass(),TEXT("DawnRoot"));
    return Super::RebuildWidget();
}
void UDawnWidget::NativeConstruct()
{
    Super::NativeConstruct();
    SetIsFocusable(true);
    KoreanFont=LoadObject<UFont>(nullptr,TEXT("/Game/PathOfDawn/UI/F_Korean.F_Korean"));
    Refresh();
}
UTextBlock* UDawnWidget::AddText(UVerticalBox* Box,const FText& Text,int32 Size,FLinearColor Color)
{
    UTextBlock* W=WidgetTree->ConstructWidget<UTextBlock>();
    W->SetText(Text);
    W->SetAutoWrapText(true);
    W->SetColorAndOpacity(Color);
    const float Scale=UDawnPlayerSettings::Get() ? UDawnPlayerSettings::Get()->TextScale : 1.f;
    FSlateFontInfo Font= W->GetFont();
    if (KoreanFont) Font.FontObject=KoreanFont;
    Font.Size=FMath::RoundToInt(Size*Scale);
    W->SetFont(Font);
    W->SetLineHeightPercentage(1.35f);
    UVerticalBoxSlot* TextSlot=Box->AddChildToVerticalBox(W);
    TextSlot->SetPadding(FMargin(0,3,0,7));
    return W;
}
UDawnActionButton* UDawnWidget::AddButton(UVerticalBox* Box,const FText& Label,const FString& Action,bool bEnabled,bool bPrimary)
{
    UDawnActionButton* Button=WidgetTree->ConstructWidget<UDawnActionButton>();
    Button->SetAction(this,Action);
    Button->SetIsEnabled(bEnabled);
    FButtonStyle Style=Button->GetStyle();
    Style.SetNormal(SolidBrush(bPrimary?FLinearColor(.37f,.28f,.15f,.95f):FLinearColor(.065f,.115f,.125f,.80f)));
    Style.SetHovered(SolidBrush(bPrimary?FLinearColor(.51f,.39f,.21f,1.f):FLinearColor(.16f,.235f,.235f,.98f)));
    Style.SetPressed(SolidBrush(FLinearColor(.24f,.32f,.30f,1.f)));
    Style.SetDisabled(SolidBrush(FLinearColor(.045f,.07f,.075f,.45f)));
    Style.SetNormalPadding(FMargin(18,8));
    Style.SetPressedPadding(FMargin(19,9,17,7));
    Button->SetStyle(Style);
    Button->SetBackgroundColor(FLinearColor::White);
    UVerticalBox* Contents=WidgetTree->ConstructWidget<UVerticalBox>();
    UTextBlock* Text=AddText(Contents,Label,22,bEnabled?DawnIvory:DawnMuted);
    if (UVerticalBoxSlot* LabelSlot=Cast<UVerticalBoxSlot>(Text->Slot)) LabelSlot->SetPadding(FMargin(0));
    Text->SetJustification(ETextJustify::Left);
    Button->AddChild(Contents);
    Box->AddChildToVerticalBox(Button)->SetPadding(FMargin(0,4,0,4));
    ActionButtons.Add(Button);
    return Button;
}
void UDawnWidget::AddImage(UVerticalBox* Box,UTexture2D* Texture,float Height)
{
    if (!Texture) return;
    USizeBox* Size=WidgetTree->ConstructWidget<USizeBox>();
    Size->SetHeightOverride(Height);
    UBorder* Frame=WidgetTree->ConstructWidget<UBorder>();
    Frame->SetBrushColor(FLinearColor(.24f,.29f,.27f,1.f));
    Frame->SetPadding(FMargin(1));
    UScaleBox* Scale=WidgetTree->ConstructWidget<UScaleBox>();
    Scale->SetStretch(EStretch::ScaleToFit);
    UImage* Image=WidgetTree->ConstructWidget<UImage>();
    Image->SetBrushFromTexture(Texture,true);
    Scale->AddChild(Image); Frame->AddChild(Scale); Size->AddChild(Frame); Box->AddChildToVerticalBox(Size);
}
void UDawnWidget::AddSpace(UVerticalBox* Box,float Height)
{
    USizeBox* Space=WidgetTree->ConstructWidget<USizeBox>();
    Space->SetHeightOverride(Height);
    Box->AddChildToVerticalBox(Space);
}
void UDawnWidget::AddRule(UVerticalBox* Box,float Width)
{
    USizeBox* RuleSize=WidgetTree->ConstructWidget<USizeBox>();
    RuleSize->SetWidthOverride(Width); RuleSize->SetHeightOverride(2);
    UBorder* Rule=WidgetTree->ConstructWidget<UBorder>();
    Rule->SetPadding(FMargin(0)); Rule->SetBrushColor(DawnGold);
    RuleSize->AddChild(Rule);
    UVerticalBoxSlot* RuleSlot=Box->AddChildToVerticalBox(RuleSize);
    RuleSlot->SetHorizontalAlignment(HAlign_Left); RuleSlot->SetPadding(FMargin(0,12,0,16));
}
void UDawnWidget::Refresh()
{
    if (!PC()) return;
    UDawnNarrativeSubsystem* N=PC()->GetNarrative();
    if (!N) return;
    ActionButtons.Empty(); Prompt=nullptr; Objective=nullptr; NavigationHint=nullptr;
    UOverlay* Root=Cast<UOverlay>(WidgetTree->RootWidget);
    if (!Root) return;
    Root->ClearChildren();
    FName Page=PC()->GetPage(), Stage=N->GetStage();
    const bool bTitle=Page==TEXT("Title");
    const bool bPlay=Page==TEXT("Play");
    const bool bIntro=bPlay && Stage==TEXT("Intro");
    const bool bEnding=bPlay && Stage==TEXT("Ending");
    const bool bDialogue=bPlay && (Stage==TEXT("Dialogue") || Stage==TEXT("Choice1") || Stage==TEXT("Choice2") || Stage==TEXT("Scene"));
    FDawnDialogueNode Node=N->GetCurrentNode();
    UTexture2D* Background=nullptr;
    if (bTitle) Background=LoadObject<UTexture2D>(nullptr,TEXT("/Game/PathOfDawn/Illustrations/IL_Title_Dawn.IL_Title_Dawn"));
    if (bIntro && PC()->IsArrivalIllustrationVisible()) Background=LoadObject<UTexture2D>(nullptr,TEXT("/Game/PathOfDawn/Illustrations/IL_Arrival.IL_Arrival"));
    if (bEnding || (bDialogue && !Node.Illustration.IsNull())) Background=Node.Illustration.LoadSynchronous();
    Root->SetClipping(EWidgetClipping::ClipToBounds);
    Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    if (Background)
    {
        UScaleBox* Frame=WidgetTree->ConstructWidget<UScaleBox>();
        Frame->SetStretch(EStretch::ScaleToFill);
        Frame->SetVisibility(ESlateVisibility::HitTestInvisible);
        UImage* Image=WidgetTree->ConstructWidget<UImage>();
        Image->SetBrushFromTexture(Background,true);
        Frame->AddChild(Image); Root->AddChildToOverlay(Frame);
    }
    if (bTitle || bEnding || bIntro) AddSideShade(WidgetTree,Root);
    else if (!bPlay)
    {
        UBorder* Veil=WidgetTree->ConstructWidget<UBorder>();
        Veil->SetBrushColor(FLinearColor(DawnInk.R,DawnInk.G,DawnInk.B,.68f));
        Veil->SetVisibility(ESlateVisibility::HitTestInvisible);
        Root->AddChildToOverlay(Veil);
    }
    // Artwork fills the viewport; controls remain inside a 16:9 safe area.
    // Large text is allowed to scroll rather than clipping a choice offscreen.
    UScaleBox* CanvasScale=WidgetTree->ConstructWidget<UScaleBox>();
    CanvasScale->SetStretch(EStretch::ScaleToFit);
    CanvasScale->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    USizeBox* CanvasSize=WidgetTree->ConstructWidget<USizeBox>();
    CanvasSize->SetWidthOverride(1600); CanvasSize->SetHeightOverride(900);
    UOverlay* Canvas=WidgetTree->ConstructWidget<UOverlay>();
    Canvas->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    CanvasSize->AddChild(Canvas); CanvasScale->AddChild(CanvasSize); Root->AddChildToOverlay(CanvasScale);
    UVerticalBox* Badge=WidgetTree->ConstructWidget<UVerticalBox>();
    Badge->SetVisibility(ESlateVisibility::HitTestInvisible);
    AddText(Badge,FText::FromString(TEXT("새벽의 길  /  ")+PC()->GetBuildId()),14,DawnMuted);
    UOverlaySlot* BadgeSlot=Canvas->AddChildToOverlay(Badge);
    BadgeSlot->SetHorizontalAlignment(HAlign_Right); BadgeSlot->SetVerticalAlignment(VAlign_Top); BadgeSlot->SetPadding(FMargin(32,22));
    if (bPlay && (Stage==TEXT("Explore") || Stage==TEXT("Task")))
    {
        UBorder* Hud=WidgetTree->ConstructWidget<UBorder>();
        Hud->SetBrushColor(FLinearColor(DawnInk.R,DawnInk.G,DawnInk.B,.83f)); Hud->SetPadding(FMargin(22,18));
        UVerticalBox* Info=WidgetTree->ConstructWidget<UVerticalBox>();
        AddText(Info,NSLOCTEXT("DawnUI","V8_FirstChapter","첫 번째 이야기  /  갈릴리"),15,DawnGold);
        Objective=AddText(Info,N->GetObjective(),22,DawnIvory);
        NavigationHint=AddText(Info,PC()->GetNavigationHint(),18,DawnMuted);
        USizeBox* InfoWidth=WidgetTree->ConstructWidget<USizeBox>();
        InfoWidth->SetWidthOverride(455); InfoWidth->AddChild(Info); Hud->AddChild(InfoWidth);
        UOverlaySlot* HudSlot=Canvas->AddChildToOverlay(Hud);
        HudSlot->SetHorizontalAlignment(HAlign_Left); HudSlot->SetVerticalAlignment(VAlign_Top); HudSlot->SetPadding(FMargin(32));
        if (!N->LastError.IsEmpty()) AddText(Info,N->LastError,18,FLinearColor(1,.55f,.45f));

        UVerticalBox* Interaction=WidgetTree->ConstructWidget<UVerticalBox>();
        Prompt=AddText(Interaction,PC()->GetInteractionPrompt(),25,DawnIvory);
        Prompt->SetJustification(ETextJustify::Center);
        Prompt->SetShadowOffset(FVector2D(1,2)); Prompt->SetShadowColorAndOpacity(FLinearColor(0,0,0,.95f));
        USizeBox* PromptWidth=WidgetTree->ConstructWidget<USizeBox>();
        PromptWidth->SetWidthOverride(720); PromptWidth->AddChild(Interaction);
        UOverlaySlot* PromptSlot=Canvas->AddChildToOverlay(PromptWidth);
        PromptSlot->SetHorizontalAlignment(HAlign_Center); PromptSlot->SetVerticalAlignment(VAlign_Bottom); PromptSlot->SetPadding(FMargin(0,0,0,116));

        UVerticalBox* Controls=WidgetTree->ConstructWidget<UVerticalBox>();
        UTextBlock* ControlsText=AddText(Controls,NSLOCTEXT("DawnUI","UI_c0c37e108242","WASD 이동   마우스 시점   E 상호작용   Esc 메뉴"),17,DawnIvory);
        ControlsText->SetShadowOffset(FVector2D(1,1)); ControlsText->SetShadowColorAndOpacity(FLinearColor::Black);
        UOverlaySlot* ControlsSlot=Canvas->AddChildToOverlay(Controls);
        ControlsSlot->SetHorizontalAlignment(HAlign_Left); ControlsSlot->SetVerticalAlignment(VAlign_Bottom); ControlsSlot->SetPadding(FMargin(32,0,0,28));
        UVerticalBox* MenuBox=WidgetTree->ConstructWidget<UVerticalBox>();
        AddButton(MenuBox,NSLOCTEXT("DawnUI","V8_ExploreMenu","기록과 회귀  ·  Esc"),TEXT("Menu"));
        UOverlaySlot* MenuSlot=Canvas->AddChildToOverlay(MenuBox);
        MenuSlot->SetHorizontalAlignment(HAlign_Right); MenuSlot->SetVerticalAlignment(VAlign_Bottom); MenuSlot->SetPadding(FMargin(0,0,32,24));
        return;
    }
    const FText Notice=NSLOCTEXT("DawnUI","UI_ee0fe03a877d","성경의 사건을 바탕으로 구성한 창작 서사입니다. 여행자의 존재, 선택과 시간 회귀는 허구입니다.");
    UBorder* Panel=WidgetTree->ConstructWidget<UBorder>();
    Panel->SetBrushColor((bTitle || bEnding || bIntro)?FLinearColor::Transparent:FLinearColor(DawnInk.R,DawnInk.G,DawnInk.B,.96f));
    Panel->SetPadding((bTitle || bEnding || bIntro)?FMargin(0):FMargin(30,22));
    USizeBox* PanelSize=WidgetTree->ConstructWidget<USizeBox>();
    PanelSize->SetWidthOverride(bTitle?510.f:(bEnding?580.f:(bIntro?590.f:(bDialogue?1390.f:870.f))));
    PanelSize->SetMaxDesiredHeight(bTitle?730.f:(bEnding?760.f:(bIntro?490.f:(bDialogue?470.f:740.f))));
    UScrollBox* Scroll=WidgetTree->ConstructWidget<UScrollBox>();
    UVerticalBox* Content=WidgetTree->ConstructWidget<UVerticalBox>();
    Scroll->AddChild(Content); PanelSize->AddChild(Scroll); Panel->AddChild(PanelSize);
    UOverlaySlot* PanelSlot=Canvas->AddChildToOverlay(Panel);
    PanelSlot->SetHorizontalAlignment((bTitle || bEnding || bIntro)?HAlign_Left:HAlign_Center);
    PanelSlot->SetVerticalAlignment((bDialogue || bIntro)?VAlign_Bottom:VAlign_Center);
    PanelSlot->SetPadding(bTitle?FMargin(80,44,0,120):(bEnding?FMargin(80,64,0,64):(bIntro?FMargin(80,0,0,96):FMargin(30))));
    if (bTitle)
    {
        AddText(Content,NSLOCTEXT("DawnUI","V8_TitleEyebrow","서사 어드벤처  /  첫 번째 이야기"),16,DawnGold);
        AddSpace(Content,12);
        AddText(Content,NSLOCTEXT("DawnUI","UI_54a9e24a476b","새벽의 길"),78,DawnIvory);
        AddText(Content,NSLOCTEXT("DawnUI","UI_8cb09720b5ec","갈릴리의 첫 아침"),28,DawnIvory);
        AddRule(Content,80);
        AddText(Content,NSLOCTEXT("DawnUI","V8_TitleInvitation","먼 시간의 호숫가,\n당신이 함께한 순간이 기억으로 남습니다."),21,DawnMuted);
        AddSpace(Content,12);
        AddButton(Content,NSLOCTEXT("DawnUI","V8_NewJourney","새 게임  ·  여정 시작"),TEXT("New"),true,true);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_4459ec31d675","이어하기"),TEXT("Continue"),N->CanContinue());
        AddButton(Content,NSLOCTEXT("DawnUI","UI_c14a567ea996","설정"),TEXT("Settings"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_5091d8fd2c59","제작 및 각색 기록"),TEXT("Credits"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_c67ed36ba334","게임 종료"),TEXT("Quit"));
        AddSpace(Content,8);
        AddText(Content,NSLOCTEXT("DawnUI","V8_NewKeepsMemories","새 게임을 시작해도 발견한 기억은 간직합니다."),16,DawnMuted);
        UVerticalBox* Footnote=WidgetTree->ConstructWidget<UVerticalBox>();
        AddText(Footnote,Notice,15,DawnMuted);
        USizeBox* FootnoteSize=WidgetTree->ConstructWidget<USizeBox>();
        FootnoteSize->SetWidthOverride(680); FootnoteSize->AddChild(Footnote);
        UOverlaySlot* FootnoteSlot=Canvas->AddChildToOverlay(FootnoteSize);
        FootnoteSlot->SetHorizontalAlignment(HAlign_Left); FootnoteSlot->SetVerticalAlignment(VAlign_Bottom); FootnoteSlot->SetPadding(FMargin(80,0,0,24));
    }
    else if (bIntro)
    {
        AddText(Content,NSLOCTEXT("DawnUI","V8_ArrivalEyebrow","갈릴리 호숫가  /  동트기 전"),17,DawnGold);
        AddText(Content,NSLOCTEXT("DawnUI","UI_031d1171445c","첫 아침"),52,DawnIvory);
        AddRule(Content);
        AddText(Content,NSLOCTEXT("DawnUI","UI_f99b12ab8375","먼 도시의 소음이 사라지고, 발밑에 차가운 모래가 닿았다. 물 위에 아직 이름 붙이지 못한 빛이 번진다."),26,DawnIvory);
        AddSpace(Content,12);
        AddText(Content,Notice,17,DawnMuted);
        AddText(Content,NSLOCTEXT("DawnUI","UI_443ac2e0ea93","잠시 후 호숫가에서 여행이 시작됩니다."),17,DawnMuted);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_af5649d81ef7","도입 건너뛰기 · Enter"),TEXT("Skip"));
    }
    else if (bEnding)
    {
        AddText(Content,NSLOCTEXT("DawnUI","V8_EndingEyebrow","아침의 기록  /  당신이 머문 자리"),17,DawnGold);
        AddText(Content,EndingLabel(N->GetEndingId()),43,DawnIvory);
        AddRule(Content);
        AddText(Content,Node.Text,25,DawnIvory);
        AddSpace(Content,12);
        AddText(Content,NSLOCTEXT("DawnUI","V8_ChoicesHeading","이 아침의 발자취"),17,DawnGold);
        AddText(Content,ChoiceSummary(N),20,DawnMuted);
        AddText(Content,FText::Format(NSLOCTEXT("DawnUI","V8_EndingState","밧줄 {0}개 · 시몬과 함께한 정도 {1} · 기억 {2}개"),FText::AsNumber(N->GetItemCount(TEXT("Rope"))),FText::AsNumber(N->GetRelationship(TEXT("Simon"))),FText::AsNumber(N->GetMemories().Num())),17,DawnMuted);
        AddText(Content,NSLOCTEXT("DawnUI","UI_9abd80166f6d","결과는 믿음의 점수가 아니라, 여행자가 바라본 자리의 차이입니다."),17,DawnMuted);
        AddSpace(Content,12);
        AddButton(Content,NSLOCTEXT("DawnUI","V8_ReturnFirstChoice","첫 선택 전으로 회귀  ·  CP01"),TEXT("CP01"),N->HasCheckpoint(TEXT("CP01")),true);
        AddButton(Content,NSLOCTEXT("DawnUI","V8_ReturnSecondChoice","두 번째 선택 전으로 회귀  ·  CP02"),TEXT("CP02"),N->HasCheckpoint(TEXT("CP02")));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_6f2e8bb38199","발견한 기억과 결과 기록"),TEXT("Records"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_aac22ec10c28","타이틀로 돌아가기"),TEXT("Title"));
    }
    else if (bDialogue)
    {
        UHorizontalBox* DialogueRow=WidgetTree->ConstructWidget<UHorizontalBox>(); Content->AddChildToVerticalBox(DialogueRow);
        UTexture2D* Portrait=Node.Portrait.LoadSynchronous();
        if (Portrait)
        {
            UVerticalBox* PortraitBox=WidgetTree->ConstructWidget<UVerticalBox>();
            AddImage(PortraitBox,Portrait,300);
            USizeBox* PortraitSize=WidgetTree->ConstructWidget<USizeBox>();
            PortraitSize->SetWidthOverride(225); PortraitSize->AddChild(PortraitBox);
            UHorizontalBoxSlot* PortraitSlot=DialogueRow->AddChildToHorizontalBox(PortraitSize);
            PortraitSlot->SetPadding(FMargin(0,3,30,0)); PortraitSlot->SetVerticalAlignment(VAlign_Top);
        }
        UVerticalBox* TextBox=WidgetTree->ConstructWidget<UVerticalBox>();
        DialogueRow->AddChildToHorizontalBox(TextBox)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        AddText(TextBox,Node.Speaker,24,DawnGold);
        UTextBlock* DialogueText=AddText(TextBox,Node.Text,27,DawnIvory);
        DialogueText->SetWrapTextAt(1000);
        AddSpace(TextBox,4);
        AddText(TextBox,FText::FromString(Node.ScriptureReference+TEXT(" · ")+Node.ContentKind),15,DawnMuted);
        if (!Node.DisplayNote.IsEmpty()) AddText(TextBox,Node.DisplayNote,16,DawnMuted);
        if (!Node.Choices.IsEmpty())
        {
            AddSpace(TextBox,8);
            for (int32 ChoiceIndex=0;ChoiceIndex<Node.Choices.Num();++ChoiceIndex)
                AddButton(TextBox,FText::Format(NSLOCTEXT("DawnUI","V8_ChoiceLabel","{0}  /  {1}"),FText::AsNumber(ChoiceIndex+1),Node.Choices[ChoiceIndex].Text),FString::Printf(TEXT("Choice%d"),ChoiceIndex));
        }
        AddSpace(TextBox,6);
        UHorizontalBox* DialogueActions=WidgetTree->ConstructWidget<UHorizontalBox>(); TextBox->AddChildToVerticalBox(DialogueActions);
        UVerticalBox* ProgressActions=WidgetTree->ConstructWidget<UVerticalBox>();
        UHorizontalBoxSlot* ProgressSlot=DialogueActions->AddChildToHorizontalBox(ProgressActions);
        ProgressSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); ProgressSlot->SetPadding(FMargin(0,0,12,0));
        if (Node.Choices.IsEmpty()) AddButton(ProgressActions,NSLOCTEXT("DawnUI","UI_cad217f59a18","계속 · Enter"),TEXT("Advance"),true,true);
        if (Stage==TEXT("Scene") && N->HasSeenScene(TEXT("Scene"))) AddButton(ProgressActions,NSLOCTEXT("DawnUI","UI_49434c5bce5d","이미 본 장면 건너뛰기"),TEXT("Skip"));
        UVerticalBox* DialogueMenu=WidgetTree->ConstructWidget<UVerticalBox>();
        DialogueActions->AddChildToHorizontalBox(DialogueMenu)->SetVerticalAlignment(VAlign_Bottom);
        AddButton(DialogueMenu,NSLOCTEXT("DawnUI","V8_DialogueMenu","메뉴 · Esc"),TEXT("Menu"));
    }
    else if (Page==TEXT("Menu"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","UI_d7587b15f035","잠시 머무르기"),39);
        AddRule(Content);
        AddText(Content,N->GetObjective(),24);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_b33643fea416","이야기로 돌아가기"),TEXT("BackPlay"),true,true);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_414bd5102c60","CP01로 회귀"),TEXT("CP01"),N->HasCheckpoint(TEXT("CP01")));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_996bf94d9ff5","CP02로 회귀"),TEXT("CP02"),N->HasCheckpoint(TEXT("CP02")));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_fb04b87ffb82","발견한 기억과 결과"),TEXT("Records"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_c14a567ea996","설정"),TEXT("Settings"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_1f1712acff27","저장"),TEXT("Save"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_aac22ec10c28","타이틀로 돌아가기"),TEXT("Title"));
    }
    else if (Page==TEXT("Records"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","UI_91981a91c29d","사라지지 않는 기억"),38);
        AddRule(Content);
        AddText(Content,Notice,20);
        AddText(Content,NSLOCTEXT("DawnUI","UI_ae10108c60cd","발견한 단서"),27,FLinearColor(.92f,.77f,.5f));
        if (N->GetMemories().IsEmpty()) AddText(Content,NSLOCTEXT("DawnUI","UI_f7ffcced9235","아직 기록된 기억이 없습니다."),22);
        for (FName Id:N->GetMemories()) AddText(Content,LabelForMemory(Id),22);
        AddText(Content,NSLOCTEXT("DawnUI","UI_59ef6bf31626","다시 만날 아침"),27,FLinearColor(.92f,.77f,.5f));
        for (FName Id:N->GetSeenEndings()) AddText(Content,EndingLabel(Id),22);
        AddText(Content,ChoiceSummary(N),22);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_9a7b9f55be19","기억 전체 초기화…"),TEXT("ResetConfirm"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_1a7f31cadb8c","돌아가기"),TEXT("Back"));
    }
    else if (Page==TEXT("Settings"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","UI_c14a567ea996","설정"),38);
        AddRule(Content);
        if (UDawnPlayerSettings* S=UDawnPlayerSettings::Get())
        {
            struct Row { const TCHAR* Id; FText Label; float Value; };
            for (const Row& R: {Row{TEXT("Master"),NSLOCTEXT("DawnUI","SettingMaster","전체 음량"),S->MasterVolume},Row{TEXT("Music"),NSLOCTEXT("DawnUI","SettingMusic","음악 음량"),S->MusicVolume},Row{TEXT("Effects"),NSLOCTEXT("DawnUI","SettingEffects","환경·효과음 음량"),S->EffectsVolume},Row{TEXT("Text"),NSLOCTEXT("DawnUI","SettingText","글자 크기"),S->TextScale},Row{TEXT("Camera"),NSLOCTEXT("DawnUI","SettingCamera","카메라 감도"),S->CameraSensitivity}})
            {
                AddText(Content,FText::Format(NSLOCTEXT("DawnUI","SettingValue","{0}  {1}%"),R.Label,FText::AsNumber(FMath::RoundToInt(R.Value*100))),23);
                UHorizontalBox* SettingActions=WidgetTree->ConstructWidget<UHorizontalBox>();
                Content->AddChildToVerticalBox(SettingActions)->SetPadding(FMargin(0,0,0,12));
                UVerticalBox* Decrease=WidgetTree->ConstructWidget<UVerticalBox>();
                UHorizontalBoxSlot* DecreaseSlot=SettingActions->AddChildToHorizontalBox(Decrease);
                DecreaseSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); DecreaseSlot->SetPadding(FMargin(0,0,8,0));
                UVerticalBox* Increase=WidgetTree->ConstructWidget<UVerticalBox>();
                SettingActions->AddChildToHorizontalBox(Increase)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
                AddButton(Decrease,NSLOCTEXT("DawnUI","UI_de226cb9a9a7","− 줄이기"),FString(TEXT("Setting-"))+R.Id);
                AddButton(Increase,NSLOCTEXT("DawnUI","UI_63310b47e372","+ 늘리기"),FString(TEXT("Setting+"))+R.Id);
            }
            AddText(Content,NSLOCTEXT("DawnUI","UI_cad5561b8068","이 데모에는 음악 트랙이 없습니다. 음악 음량은 이후 추가되는 트랙에 적용됩니다."),19);
            AddButton(Content,FText::FromString(S->GetOverallScalabilityLevel()<2?TEXT("화질: 낮음 → 높음"):TEXT("화질: 높음 → 낮음")),TEXT("Setting+Quality"));
            AddButton(Content,NSLOCTEXT("DawnUI","UI_29e450007c12","창 모드 / 테두리 없는 전체화면 전환"),TEXT("Setting+Window"));
        }
        AddButton(Content,NSLOCTEXT("DawnUI","UI_1a7f31cadb8c","돌아가기"),TEXT("Back"));
    }
    else if (Page==TEXT("UnsavedTitle"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","SaveFailedTitle","진행을 저장하지 못했습니다"),36);
        AddText(Content,NSLOCTEXT("DawnUI","SaveFailedBody","타이틀로 돌아갈 수 있지만 이번 진행은 종료 후 복구되지 않을 수 있습니다. 기존 정상 저장 파일은 유지됩니다."),25);
        AddButton(Content,NSLOCTEXT("DawnUI","StayHere","돌아가서 계속하기"),TEXT("Back"));
        AddButton(Content,NSLOCTEXT("DawnUI","LeaveWithoutSave","저장하지 않고 타이틀로"),TEXT("LeaveTitle"));
    }
    else if (Page==TEXT("ResetConfirm"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","UI_5fb0698ee4f7","발견한 기억을 지울까요?"),36);
        AddText(Content,NSLOCTEXT("DawnUI","UI_62640a1f772e","현재 진행과 체크포인트는 유지됩니다. 발견한 단서와 결과 기록만 지워집니다. 새 게임을 시작할 때는 기억이 지워지지 않습니다."),25);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_19b2d19bc141","취소"),TEXT("Records"));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_b86e9d144658","기억과 결과 기록 초기화"),TEXT("ResetMemories"));
    }
    else if (Page==TEXT("Credits"))
    {
        AddText(Content,NSLOCTEXT("DawnUI","UI_4555ae24e226","새벽의 길: 갈릴리의 첫 아침"),35);
        AddRule(Content);
        AddText(Content,Notice,24);
        AddText(Content,NSLOCTEXT("DawnUI","UI_853ca2c84ec7","참고: 누가복음 5:1–11. 본문의 사건 순서를 바탕으로 직접 쓴 한국어 요약을 사용합니다. 여행자, 조사 사물, 선택, 회귀, 인물과 여행자의 대화는 창작입니다. 예수님의 외모는 역사적으로 확인된 초상이 아닙니다."),24);
        AddText(Content,NSLOCTEXT("DawnUI","UI_6948d153d09a","예수님이 시몬의 배에서 가르치신 뒤 깊은 곳으로 나아가도록 이끄시는 사건을 압축합니다. 많은 군중과 두 번째 배의 동료, 야고보와 요한은 화면 밖의 요약으로 남겨 둡니다. 플레이어의 선택이 성경의 결말을 바꾸지는 않습니다."),24);
        AddText(Content,NSLOCTEXT("DawnUI","V8_ArtCredits","원화와 인물·의상은 이 데모를 위해 창작적으로 재현했습니다. 환경음은 직접 제작했으며, 한국어 글꼴은 OFL 라이선스에 따라 사용합니다."),22);
        AddButton(Content,NSLOCTEXT("DawnUI","UI_1a7f31cadb8c","돌아가기"),TEXT("Back"));
    }
    if (!N->LastError.IsEmpty())
    {
        AddText(Content,N->LastError,21,FLinearColor(1,.55f,.45f));
        AddButton(Content,NSLOCTEXT("DawnUI","UI_1072b7563165","백업 저장 복구 시도"),TEXT("Recover"));
    }
}
void UDawnWidget::RefreshPrompt()
{
    if (PC() && Prompt) Prompt->SetText(PC()->GetInteractionPrompt());
    if (PC() && NavigationHint) NavigationHint->SetText(PC()->GetNavigationHint());
    if (PC() && Objective && PC()->GetNarrative()) Objective->SetText(PC()->GetNarrative()->GetObjective());
}
void UDawnWidget::Dispatch(const FString& Action) { if (PC()) PC()->HandleUIAction(Action); }
FReply UDawnWidget::NativeOnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    if (Event.IsRepeat()) return FReply::Handled();
    if (Event.GetKey()==EKeys::Escape) { Dispatch(TEXT("Menu")); return FReply::Handled(); }
    if (Event.GetKey()==EKeys::Enter || Event.GetKey()==EKeys::SpaceBar) { Dispatch(TEXT("Advance")); return FReply::Handled(); }
    if (Event.GetKey()==EKeys::One) { Dispatch(TEXT("Choice0")); return FReply::Handled(); }
    if (Event.GetKey()==EKeys::Two) { Dispatch(TEXT("Choice1")); return FReply::Handled(); }
    return Super::NativeOnKeyDown(Geometry,Event);
}
