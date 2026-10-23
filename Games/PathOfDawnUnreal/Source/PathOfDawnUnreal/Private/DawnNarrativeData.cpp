#include "DawnNarrativeData.h"
#include "Core/DawnState.h"
const FDawnDialogueNode* UDawnNarrativeData::Find(FName Id) const
{
    return Nodes.FindByPredicate([Id](const FDawnDialogueNode& Node){ return Node.Id == Id; });
}
bool UDawnNarrativeData::Validate(FString& Error) const
{
    if(ContentVersion != dawn::ContentVersion) { Error=TEXT("Unsupported narrative content version."); return false; }
    TSet<FName> Ids;
    for(const FDawnDialogueNode& Node:Nodes)
    {
        if(Node.Id.IsNone() || Node.Text.IsEmpty() || Ids.Contains(Node.Id)) { Error=TEXT("Empty/duplicate narrative node or text."); return false; }
        Ids.Add(Node.Id);
        if(Node.ContentKind.IsEmpty() || Node.ScriptureReference.IsEmpty() || Node.SourceNote.IsEmpty()) { Error=TEXT("Missing narrative provenance."); return false; }
    }
    for(const FDawnDialogueNode& Node:Nodes)
    {
        if(!Node.NextNode.IsNone() && !Ids.Contains(Node.NextNode)) { Error=TEXT("Missing next narrative node: ")+Node.NextNode.ToString(); return false; }
        for(const FDawnChoice& Choice:Node.Choices)
            if(Choice.Text.IsEmpty() || (!Ids.Contains(Choice.NextNode) && Choice.NextNode!=TEXT("Outcome_Stay"))) { Error=TEXT("Invalid choice target/text."); return false; }
    }
    for(FName Required : {FName(TEXT("Intro_Arrival")),FName(TEXT("Explore")),FName(TEXT("Choice_01")),FName(TEXT("Choice_02")),FName(TEXT("Task_HelpNet")),FName(TEXT("Task_ObserveShore")),FName(TEXT("Task_ReturnToSimon")),FName(TEXT("Task_Departure")),FName(TEXT("Ending_Together")),FName(TEXT("Ending_Witness")),FName(TEXT("Ending_Departure"))})
        if(!Ids.Contains(Required)){Error=TEXT("Missing required narrative node: ")+Required.ToString();return false;}
    for(FName ChoiceId : {FName(TEXT("Choice_01")), FName(TEXT("Choice_02"))})
        if(Find(ChoiceId)->Choices.Num()!=2){Error=TEXT("Each choice must have exactly two options.");return false;}
    return true;
}
