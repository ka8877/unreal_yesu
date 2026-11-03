#include "JourneyJournal.h"
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

using namespace Journey;
static int checks=0;
static void require(bool condition,const char* message) {
    ++checks;
    if (!condition) { std::cerr<<"FAIL: "<<message<<'\n';std::exit(1); }
}
static bool same(const Snapshot& a,const Snapshot& b) {
    return a.schemaVersion==b.schemaVersion && a.contentVersion==b.contentVersion
        && a.started==b.started && a.checkpoint==b.checkpoint
        && a.experienced==b.experienced && a.written==b.written;
}
int main() {
    Event event=Event::Birth;
    for (auto value:{Event::Birth,Event::Shepherds,Event::Temple}) {
        require(ParseEvent(EventId(value),event)&&event==value,"event ID roundtrip");
    }
    require(!ParseEvent("Temple_Sermon",event),"unknown event rejected");
    require(!ParseEvent("",event),"empty event rejected");
    require(std::string(EventId(static_cast<Event>(999))).empty(),"invalid enum has no ID");
    Checkpoint checkpoint=Checkpoint::Arrival;
    for (auto value:{Checkpoint::Arrival,Checkpoint::BirthWitnessed,Checkpoint::BirthRecorded,
         Checkpoint::ShepherdsWitnessed,Checkpoint::BirthChapterComplete,
         Checkpoint::TempleArrival,Checkpoint::TempleWitnessed,
         Checkpoint::TempleRecorded,Checkpoint::Complete}) {
        require(ParseCheckpoint(CheckpointId(value),checkpoint)&&checkpoint==value,"checkpoint stable ID roundtrip");
    }
    require(!ParseCheckpoint("OmittedPresentation",checkpoint),"omitted scene cannot become checkpoint");
    Journal journal;
    require(!journal.State().started,"no active session initially");
    require(journal.VisibleEntries().empty(),"initial book empty");
    require(!journal.Experience(Event::Birth,journal.Epoch()),"no scene completion before new game");
    require(!journal.Write(Event::Birth),"cannot write unseen event");
    journal.NewGame();
    require(journal.State().started,"new game starts session");
    require(journal.GetChapter()==Chapter::Birth,"birth chapter initially");
    const auto openingEpoch=journal.Epoch();
    const Snapshot initial=journal.State();
    std::vector<Snapshot> snapshots{initial};
    require(!journal.BeginTemple(),"cannot skip first chapter");
    require(!journal.CompleteDemo(),"cannot end unplayed demo");
    require(!journal.Experience(Event::Temple,openingEpoch),"future scene rejected");
    require(!journal.Experience(Event::Shepherds,openingEpoch),"shepherds gated behind birth record");
    require(journal.Experience(Event::Birth,openingEpoch),"opening completion unlocks birth only");
    snapshots.push_back(journal.State());
    require(journal.GetRecordState(Event::Birth)==RecordState::Available,"available before writing");
    require(journal.VisibleEntries()==std::vector<Event>{Event::Birth},"future titles/bodies not eligible for UI");
    require(!journal.State().written.count("Birth"),"unlock does not auto-write");
    require(!journal.Experience(Event::Birth,openingEpoch),"skip and playback cannot double-apply");
    require(!journal.Experience(Event::Shepherds,openingEpoch),"old opening callback cannot finish next scene");
    require(!journal.Write(Event::Temple),"future write rejected");
    require(!journal.BeginTemple(),"unwritten birth cannot trigger time transition");
    require(journal.Write(Event::Birth),"explicit user action writes birth");
    snapshots.push_back(journal.State());
    require(!journal.Write(Event::Birth),"record write idempotent");
    require(journal.GetRecordState(Event::Birth)==RecordState::Written,"written state");
    require(initial.experienced.empty()&&initial.written.empty(),"snapshots independent values");
    require(!journal.BeginTemple(),"shepherd event still required");
    const auto shepherdEpoch=journal.Epoch();
    require(journal.Experience(Event::Shepherds,shepherdEpoch),"visit unlocks shepherd record");
    snapshots.push_back(journal.State());
    require(journal.VisibleEntries().size()==2,"only past/current entries visible");
    require(!journal.BeginTemple(),"unwritten shepherd event gates chapter");
    require(journal.Write(Event::Shepherds),"write shepherd summary");
    snapshots.push_back(journal.State());
    require(journal.State().checkpoint==Checkpoint::BirthChapterComplete,"birth section checkpoint");
    require(journal.BeginTemple(),"explicit time transition");
    snapshots.push_back(journal.State());
    require(journal.GetChapter()==Chapter::Temple,"temple chapter active");
    require(journal.GetRecordState(Event::Temple)==RecordState::Locked,"transition does not witness temple");
    require(journal.State().experienced.size()==2,"omitted middle passage not marked experienced");
    require(!journal.BeginTemple(),"repeated transition rejected");
    require(!journal.Experience(Event::Temple,shepherdEpoch),"prior chapter async callback rejected");
    require(journal.Experience(Event::Temple,journal.Epoch()),"temple observed");
    snapshots.push_back(journal.State());
    require(journal.VisibleEntries().size()==3,"three entries eligible after three experiences");
    require(!journal.CompleteDemo(),"last page must be explicitly written");
    require(journal.Write(Event::Temple),"final record written");
    snapshots.push_back(journal.State());
    require(journal.CompleteDemo(),"demo complete after all three records");
    snapshots.push_back(journal.State());
    require(!journal.CompleteDemo(),"finish idempotent");
    require(journal.State().written.size()==3,"exactly three pages");
    require(!journal.Experience(static_cast<Event>(999),journal.Epoch()),"unknown enum rejected");

    // Resume each stable checkpoint into an entirely different Journal instance.
    for (const auto& saved:snapshots) {
        Journal resumed;
        const auto previousEpoch=resumed.Epoch();
        require(Journal::Valid(saved),"every authored checkpoint consistent");
        require(resumed.Restore(saved)==LoadError::None,"value checkpoint accepted in new instance");
        require(same(resumed.State(),saved),"resume restores all progress sets/checkpoint");
        require(resumed.Epoch()!=previousEpoch,"resume invalidates old callbacks");
        require(resumed.VisibleEntries().size()==saved.experienced.size(),"resume does not reveal future entries");
    }
    auto before=journal.State();
    const auto beforeEpoch=journal.Epoch();
    auto damaged=before; damaged.schemaVersion=99;
    require(journal.Restore(damaged)==LoadError::SchemaMismatch,"save schema mismatch rejected");
    damaged=before;damaged.contentVersion=99;
    require(journal.Restore(damaged)==LoadError::ContentMismatch,"content mismatch rejected");
    std::vector<Snapshot> corrupt;
    damaged=initial;damaged.experienced={"Temple"};corrupt.push_back(damaged);
    damaged=initial;damaged.written={"Birth"};corrupt.push_back(damaged);
    damaged=initial;damaged.experienced={"Circumcision"};corrupt.push_back(damaged);
    damaged=snapshots[1];damaged.written={"Birth"};corrupt.push_back(damaged);
    damaged=before;damaged.started=false;corrupt.push_back(damaged);
    damaged=before;damaged.checkpoint=static_cast<Checkpoint>(999);corrupt.push_back(damaged);
    damaged=before;damaged.written.erase("Birth");corrupt.push_back(damaged);
    damaged=before;damaged.experienced.insert("FourthEnding");corrupt.push_back(damaged);
    for (const auto& broken:corrupt) {
        require(journal.Restore(broken)==LoadError::InvalidState,"impossible save rejected");
        require(same(journal.State(),before),"invalid restore leaves current session untouched");
        require(journal.Epoch()==beforeEpoch,"failed restore leaves callback epoch untouched");
    }
    journal.NewGame();
    require(journal.VisibleEntries().empty(),"new game starts a new empty journal");
    require(journal.State().checkpoint==Checkpoint::Arrival,"new game checkpoint reset");
    require(!journal.Experience(Event::Birth,beforeEpoch),"previous-session callback cannot unlock new book");
    std::cout<<"PASS "<<checks<<" Journey journal assertions. Portable logic only; no Unreal, USaveGame disk or visual execution.\n";
}
