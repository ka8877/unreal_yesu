#pragma once
// Engine-independent journal state for the Luke 2 rebuild. No rendered scene is
// certified by this implementation. The caller supplies actual scene events.
#include <array>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace Journey {
constexpr int SchemaVersion = 1;
constexpr int ContentVersion = 1;
enum class Event { Birth, Shepherds, Temple };
enum class Chapter { Birth, Temple };
enum class Checkpoint {
    Arrival, BirthWitnessed, BirthRecorded, ShepherdsWitnessed,
    BirthChapterComplete, TempleArrival, TempleWitnessed, TempleRecorded, Complete
};
enum class RecordState { Locked, Available, Written };
enum class LoadError { None, SchemaMismatch, ContentMismatch, InvalidState };

inline const char* EventId(Event event) {
    switch (event) {
    case Event::Birth: return "Birth";
    case Event::Shepherds: return "Shepherds";
    case Event::Temple: return "Temple";
    }
    return "";
}
inline bool ParseEvent(const std::string& id, Event& event) {
    if (id == "Birth") event=Event::Birth;
    else if (id == "Shepherds") event=Event::Shepherds;
    else if (id == "Temple") event=Event::Temple;
    else return false;
    return true;
}
inline const char* CheckpointId(Checkpoint checkpoint) {
    switch (checkpoint) {
    case Checkpoint::Arrival: return "Arrival";
    case Checkpoint::BirthWitnessed: return "BirthWitnessed";
    case Checkpoint::BirthRecorded: return "BirthRecorded";
    case Checkpoint::ShepherdsWitnessed: return "ShepherdsWitnessed";
    case Checkpoint::BirthChapterComplete: return "BirthChapterComplete";
    case Checkpoint::TempleArrival: return "TempleArrival";
    case Checkpoint::TempleWitnessed: return "TempleWitnessed";
    case Checkpoint::TempleRecorded: return "TempleRecorded";
    case Checkpoint::Complete: return "Complete";
    }
    return "";
}
inline bool ParseCheckpoint(const std::string& id, Checkpoint& checkpoint) {
    for (const auto value : {Checkpoint::Arrival, Checkpoint::BirthWitnessed,
         Checkpoint::BirthRecorded, Checkpoint::ShepherdsWitnessed,
         Checkpoint::BirthChapterComplete, Checkpoint::TempleArrival,
         Checkpoint::TempleWitnessed, Checkpoint::TempleRecorded, Checkpoint::Complete}) {
        if (id == CheckpointId(value)) { checkpoint=value; return true; }
    }
    return false;
}

struct Snapshot {
    int schemaVersion=SchemaVersion;
    int contentVersion=ContentVersion;
    bool started=false;
    Checkpoint checkpoint=Checkpoint::Arrival;
    std::set<std::string> experienced;
    std::set<std::string> written;
};

class Journal {
public:
    const Snapshot& State() const { return state; }
    std::uint64_t Epoch() const { return epoch; }
    void NewGame() { state=Snapshot{}; state.started=true; ++epoch; }

    RecordState GetRecordState(Event event) const {
        const std::string id=EventId(event);
        if (id.empty() || !state.started) return RecordState::Locked;
        if (state.written.count(id)) return RecordState::Written;
        if (state.experienced.count(id)) return RecordState::Available;
        return RecordState::Locked;
    }
    // Only these entries may be resolved into title/body text by a UI. Locked
    // events need not expose even their title, portrait, or scripture range.
    std::vector<Event> VisibleEntries() const {
        std::vector<Event> result;
        for (const auto event : {Event::Birth,Event::Shepherds,Event::Temple})
            if (GetRecordState(event)!=RecordState::Locked) result.push_back(event);
        return result;
    }
    Chapter GetChapter() const {
        switch (state.checkpoint) {
        case Checkpoint::TempleArrival: case Checkpoint::TempleWitnessed:
        case Checkpoint::TempleRecorded: case Checkpoint::Complete: return Chapter::Temple;
        default: return Chapter::Birth;
        }
    }
    // Both full playback and skip call this once with the epoch captured before
    // playback. A repeated/late completion cannot unlock the next scene.
    bool Experience(Event event, std::uint64_t expectedEpoch) {
        if (!state.started || expectedEpoch!=epoch) return false;
        if (event==Event::Birth && state.checkpoint==Checkpoint::Arrival)
            state.checkpoint=Checkpoint::BirthWitnessed;
        else if (event==Event::Shepherds && state.checkpoint==Checkpoint::BirthRecorded)
            state.checkpoint=Checkpoint::ShepherdsWitnessed;
        else if (event==Event::Temple && state.checkpoint==Checkpoint::TempleArrival)
            state.checkpoint=Checkpoint::TempleWitnessed;
        else return false;
        state.experienced.insert(EventId(event));
        ++epoch;
        return true;
    }
    bool Write(Event event) {
        if (GetRecordState(event)!=RecordState::Available) return false;
        if (event==Event::Birth && state.checkpoint==Checkpoint::BirthWitnessed)
            state.checkpoint=Checkpoint::BirthRecorded;
        else if (event==Event::Shepherds && state.checkpoint==Checkpoint::ShepherdsWitnessed)
            state.checkpoint=Checkpoint::BirthChapterComplete;
        else if (event==Event::Temple && state.checkpoint==Checkpoint::TempleWitnessed)
            state.checkpoint=Checkpoint::TempleRecorded;
        else return false;
        state.written.insert(EventId(event));
        ++epoch;
        return true;
    }
    bool BeginTemple() {
        if (!state.started || state.checkpoint!=Checkpoint::BirthChapterComplete) return false;
        state.checkpoint=Checkpoint::TempleArrival;
        ++epoch;
        return true;
    }
    bool CompleteDemo() {
        if (!state.started || state.checkpoint!=Checkpoint::TempleRecorded) return false;
        state.checkpoint=Checkpoint::Complete;
        ++epoch;
        return true;
    }
    LoadError Restore(const Snapshot& candidate) {
        if (candidate.schemaVersion!=SchemaVersion) return LoadError::SchemaMismatch;
        if (candidate.contentVersion!=ContentVersion) return LoadError::ContentMismatch;
        if (!Valid(candidate)) return LoadError::InvalidState;
        state=candidate; // independent value snapshot, never a mutable shared pointer
        ++epoch;
        return LoadError::None;
    }
    static bool Valid(const Snapshot& candidate) {
        // Derive exact allowed sets from the stable checkpoint, rejecting future
        // unlocks, unknown IDs, lost earlier records and impossible chapter jumps.
        std::set<std::string> experienced, written;
        switch (candidate.checkpoint) {
        case Checkpoint::Arrival: break;
        case Checkpoint::BirthWitnessed: experienced={"Birth"}; break;
        case Checkpoint::BirthRecorded: experienced=written={"Birth"}; break;
        case Checkpoint::ShepherdsWitnessed:
            experienced={"Birth","Shepherds"}; written={"Birth"}; break;
        case Checkpoint::BirthChapterComplete: case Checkpoint::TempleArrival:
            experienced=written={"Birth","Shepherds"}; break;
        case Checkpoint::TempleWitnessed:
            experienced={"Birth","Shepherds","Temple"}; written={"Birth","Shepherds"}; break;
        case Checkpoint::TempleRecorded: case Checkpoint::Complete:
            experienced=written={"Birth","Shepherds","Temple"}; break;
        default: return false;
        }
        return (candidate.started || candidate.checkpoint==Checkpoint::Arrival)
            && candidate.experienced==experienced && candidate.written==written;
    }
private:
    Snapshot state;
    std::uint64_t epoch=1; // transient; bump after load/new game/scene advancement
};
} // namespace Journey
