#include "JourneyJournalData.h"
#include "Core/JourneyJournal.h"

const FJourneyJournalEntry* UJourneyJournalData::Find(FName Id) const
{
    return Entries.FindByPredicate([Id](const FJourneyJournalEntry& Entry) { return Entry.Id == Id; });
}

bool UJourneyJournalData::Validate(FString& Error) const
{
    if (ContentVersion != Journey::ContentVersion || Entries.Num() != 3)
    {
        Error = TEXT("The Luke 2 journal requires content version 1 and exactly three entries.");
        return false;
    }
    const TMap<FName, FString> Required = {
        {FName(TEXT("Birth")), TEXT("Luke 2:1-7")},
        {FName(TEXT("Shepherds")), TEXT("Luke 2:8-20")},
        {FName(TEXT("Temple")), TEXT("Luke 2:41-52")}
    };
    TSet<FName> Seen;
    for (const FJourneyJournalEntry& Entry : Entries)
    {
        const FString* Reference = Required.Find(Entry.Id);
        const FName ExpectedChapter = Entry.Id == FName(TEXT("Temple")) ? FName(TEXT("Temple")) : FName(TEXT("Birth"));
        if (!Reference || Seen.Contains(Entry.Id) || Entry.ChapterId != ExpectedChapter ||
            Entry.Title.IsEmpty() || Entry.Summary.IsEmpty() || Entry.SourceNote.IsEmpty() ||
            Entry.People.IsEmpty() || Entry.Places.IsEmpty() || Entry.ScriptureReferences.Num() != 1 ||
            Entry.ScriptureReferences[0] != *Reference || Entry.TextKind != EJourneyTextKind::Summary)
        {
            // No translation/license has been selected: direct quotations cannot
            // silently enter this version of the game through a DataAsset edit.
            Error = TEXT("Invalid, duplicate or unlicensed journal entry: ") + Entry.Id.ToString();
            return false;
        }
        Seen.Add(Entry.Id);
    }
    Error.Empty();
    return true;
}

bool UJourneyJournalData::IsSceneReady(FName Id) const
{
    const FJourneyJournalEntry* Entry = Find(Id);
    return Entry && Entry->bSceneReady;
}
