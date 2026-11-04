#include "DawnGospelData.h"

const FDawnGospelReading* UDawnGospelData::FindReading(FName Id) const
{
    return Readings.FindByPredicate([Id](const FDawnGospelReading& Reading) { return Reading.Id == Id; });
}

const FDawnGospelQuest* UDawnGospelData::FindQuest(FName Id) const
{
    return Quests.FindByPredicate([Id](const FDawnGospelQuest& Quest) { return Quest.Id == Id; });
}

FString UDawnGospelData::ValidationError() const
{
    FString Error;
    Validate(Error);
    return Error;
}

bool UDawnGospelData::Validate(FString& Error) const
{
    Error.Reset();
    auto Reject = [&Error](const FString& Message) { Error = Message; return false; };
    if (SchemaVersion != 1 || CampaignId != TEXT("gospel-pilgrimage") || ContentVersion != 1)
        return Reject(TEXT("Unsupported Gospel campaign identity or version."));
    if (SourceRepository != TEXT("ka8877/firstgame") || SourceCommit.Len() != 40)
        return Reject(TEXT("Missing pinned Unity source provenance."));
    for (TCHAR Character : SourceCommit)
        if (!FChar::IsHexDigit(Character)) return Reject(TEXT("Invalid Unity commit identifier."));
    if (Title.IsEmpty() || ScopeNote.IsEmpty() || Quests.Num() != 23 || Readings.Num() != 19)
        return Reject(TEXT("The version-one campaign must contain its title, scope, 23 quests and 19 readings."));

    TSet<FName> ReadingIds;
    for (const FDawnGospelReading& Reading : Readings)
    {
        if (Reading.Id.IsNone() || ReadingIds.Contains(Reading.Id) || Reading.Title.IsEmpty() ||
            Reading.Reference.IsEmpty() || Reading.Text.IsEmpty() || Reading.Source.IsEmpty())
            return Reject(TEXT("Missing, duplicate or unsourced scripture reading."));
        ReadingIds.Add(Reading.Id);
    }

    TSet<FName> QuestIds;
    TSet<FName> BeatIds;
    TSet<FName> ReferencedReadings;
    int32 BirthBeats = 0;
    for (int32 Index = 0; Index < Quests.Num(); ++Index)
    {
        const FDawnGospelQuest& Quest = Quests[Index];
        const FName ExpectedChapter = Index < 11 ? FName(TEXT("birth")) :
                                      Index < 18 ? FName(TEXT("temple")) : FName(TEXT("baptism"));
        if (Quest.Id.IsNone() || QuestIds.Contains(Quest.Id) || Quest.ChapterId != ExpectedChapter ||
            Quest.bIsPrologue != (ExpectedChapter == TEXT("birth")) || Quest.Title.IsEmpty() ||
            Quest.Objective.IsEmpty() || Quest.NpcId.IsNone() || Quest.NpcName.IsEmpty() || Quest.Beats.IsEmpty())
            return Reject(TEXT("Invalid quest identity, chronology, target or dialogue."));
        QuestIds.Add(Quest.Id);
        if (!Quest.ReadingId.IsNone())
        {
            if (!ReadingIds.Contains(Quest.ReadingId) || ReferencedReadings.Contains(Quest.ReadingId))
                return Reject(TEXT("An event has a missing or repeated reading reward."));
            ReferencedReadings.Add(Quest.ReadingId);
        }
        if (Quest.bIsPrologue) BirthBeats += Quest.Beats.Num();
        for (int32 BeatIndex = 0; BeatIndex < Quest.Beats.Num(); ++BeatIndex)
        {
            const FDawnGospelBeat& Beat = Quest.Beats[BeatIndex];
            const FString StableKey = Quest.Id.ToString() + FString::Printf(TEXT(":%d"), BeatIndex);
            if (Beat.Id != FName(*StableKey) || BeatIds.Contains(Beat.Id) || Beat.VoiceKey != StableKey ||
                Beat.Text.IsEmpty() || Beat.Speaker.IsEmpty() || Beat.SceneTitle.IsEmpty() ||
                Beat.Location.IsEmpty() || Beat.TimeLabel.IsEmpty() || Beat.MusicRole.IsEmpty())
                return Reject(TEXT("Invalid or incomplete story beat."));
            if (Beat.Kind != TEXT("Scripture") && Beat.Kind != TEXT("Summary") && Beat.Kind != TEXT("Dramatization"))
                return Reject(TEXT("Every beat must distinguish scripture, summary and dramatization."));
            if (Beat.Kind == TEXT("Scripture") && Beat.Reference.IsEmpty())
                return Reject(TEXT("A direct scripture quotation has no reference."));
            BeatIds.Add(Beat.Id);
        }
    }
    if (ReferencedReadings.Num() != Readings.Num() || BirthBeats != 51)
        return Reject(TEXT("The imported campaign omitted readings or changed the 51-beat Nativity prologue."));
    return true;
}
