#pragma once
// Engine-independent ordered Gospel journey. Unreal and portable tests use this
// exact state machine; presentation and book inspection never award discoveries.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace gospel {
constexpr int SaveSchemaVersion = 1;
enum class Stage { Travel = 0, Talk = 1, Reading = 2, Complete = 3 };

struct Quest {
    std::string id;
    std::string chapterId;
    std::string npcId;
    std::string readingId;
    bool isPrologue = false;
    std::size_t beatCount = 0;
};

struct Campaign {
    std::string id;
    int contentVersion = 1;
    std::vector<Quest> quests;
};

struct State {
    int schemaVersion = SaveSchemaVersion;
    std::string campaignId;
    int contentVersion = 1;
    int scopeStart = 0;
    int scopeEnd = 0;  // Exclusive. A preview never claims preceding discoveries.
    int questIndex = 0;
    int beatIndex = 0;
    Stage stage = Stage::Complete;
    std::vector<std::string> discovered;
};

inline bool ValidId(const std::string& id) {
    if (id.empty() || id.size() > 128) return false;
    for (const unsigned char c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_' ||
              c == ':' || c == '.')) return false;
    }
    return true;
}

inline bool ValidateCampaign(const Campaign& campaign, std::string& error) {
    error.clear();
    if (!ValidId(campaign.id) || campaign.contentVersion < 1 ||
        campaign.quests.empty() || campaign.quests.size() > 4096) {
        error = "Invalid campaign identity, version or quest count.";
        return false;
    }
    std::set<std::string> questIds;
    std::set<std::string> readingIds;
    std::set<std::string> closedChapters;
    std::string chapter;
    bool leftPrologue = false;
    for (const Quest& quest : campaign.quests) {
        if (!ValidId(quest.id) || !ValidId(quest.chapterId) ||
            !ValidId(quest.npcId) ||
            (!quest.readingId.empty() && !ValidId(quest.readingId)) ||
            quest.beatCount == 0 ||
            quest.beatCount > static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
            !questIds.insert(quest.id).second ||
            (!quest.readingId.empty() && !readingIds.insert(quest.readingId).second)) {
            error = "Invalid, duplicate or empty quest, passage or dialogue definition.";
            return false;
        }
        if (quest.chapterId != chapter) {
            if (closedChapters.count(quest.chapterId) != 0) {
                error = "Campaign chapters must form contiguous ranges.";
                return false;
            }
            if (!chapter.empty()) closedChapters.insert(chapter);
            chapter = quest.chapterId;
        }
        if (quest.isPrologue && leftPrologue) {
            error = "Prologue quests must precede world travel.";
            return false;
        }
        if (!quest.isPrologue) leftPrologue = true;
    }
    return true;
}

inline bool TempleScope(const Campaign& campaign, int& start, int& end) {
    start = -1;
    end = -1;
    for (std::size_t i = 0; i < campaign.quests.size(); ++i) {
        if (campaign.quests[i].chapterId == "temple") {
            if (start < 0) start = static_cast<int>(i);
            end = static_cast<int>(i) + 1;
        }
    }
    if (start < 0) return false;
    for (int i = start; i < end; ++i) {
        if (campaign.quests[static_cast<std::size_t>(i)].chapterId != "temple") return false;
    }
    return true;
}

inline bool ValidateState(const Campaign& campaign, const State& state, std::string& error) {
    if (!ValidateCampaign(campaign, error)) return false;
    if (state.schemaVersion != SaveSchemaVersion || state.campaignId != campaign.id ||
        state.contentVersion != campaign.contentVersion) {
        error = "Save schema or campaign version does not match this content.";
        return false;
    }
    const int count = static_cast<int>(campaign.quests.size());
    int templeStart = -1, templeEnd = -1;
    const bool templeExists = TempleScope(campaign, templeStart, templeEnd);
    const bool fullScope = state.scopeStart == 0 && state.scopeEnd == count;
    const bool previewScope = templeExists && state.scopeStart == templeStart && state.scopeEnd == templeEnd;
    if ((!fullScope && !previewScope) || state.scopeStart < 0 ||
        state.scopeEnd <= state.scopeStart || state.scopeEnd > count ||
        state.questIndex < state.scopeStart || state.questIndex > state.scopeEnd) {
        error = "Save has an invalid campaign or preview range.";
        return false;
    }
    const bool complete = state.questIndex == state.scopeEnd;
    if (complete) {
        if (state.stage != Stage::Complete || state.beatIndex != 0) {
            error = "A completed journey must have a closed dialogue cursor.";
            return false;
        }
    } else {
        const Quest& quest = campaign.quests[static_cast<std::size_t>(state.questIndex)];
        switch (state.stage) {
        case Stage::Travel:
        case Stage::Talk:
            if (quest.isPrologue || state.beatIndex != 0) {
                error = "Travel and talk require a world quest with a closed dialogue cursor.";
                return false;
            }
            break;
        case Stage::Reading:
            if (state.beatIndex < 0 || static_cast<std::size_t>(state.beatIndex) >= quest.beatCount) {
                error = "Saved dialogue cursor is outside the current event.";
                return false;
            }
            break;
        default:
            error = "An unfinished journey has an invalid stage.";
            return false;
        }
    }
    std::vector<std::string> expected;
    for (int i = state.scopeStart; i < state.questIndex; ++i) {
        const std::string& id = campaign.quests[static_cast<std::size_t>(i)].readingId;
        if (!id.empty()) expected.push_back(id);
    }
    if (state.discovered != expected) {
        error = "Discovered passages do not match completed events in this journey.";
        return false;
    }
    error.clear();
    return true;
}

class Session {
public:
    // A successful configuration starts a valid full campaign. A rejected new
    // definition leaves both the previous campaign and its current save intact.
    bool Configure(const Campaign& campaign) {
        std::string error;
        if (!ValidateCampaign(campaign, error)) return Fail(std::move(error));
        campaign_ = campaign;
        configured_ = true;
        return NewGame(false);
    }

    bool NewGame(bool templePreview = false) {
        if (!configured_) return Fail("Campaign content has not been configured.");
        State candidate;
        candidate.campaignId = campaign_.id;
        candidate.contentVersion = campaign_.contentVersion;
        candidate.scopeEnd = static_cast<int>(campaign_.quests.size());
        if (templePreview && !TempleScope(campaign_, candidate.scopeStart, candidate.scopeEnd))
            return Fail("This campaign has no contiguous temple preview.");
        candidate.questIndex = candidate.scopeStart;
        SelectStage(candidate);
        return Commit(std::move(candidate));
    }

    bool Restore(const State& state) {
        if (!configured_) return Fail("Campaign content has not been configured.");
        return Commit(state);
    }

    State Snapshot() const { return state_; }
    const Campaign& Definition() const { return campaign_; }
    bool IsConfigured() const { return configured_; }
    const Quest* CurrentQuest() const {
        if (!configured_ || IsComplete()) return nullptr;
        return &campaign_.quests[static_cast<std::size_t>(state_.questIndex)];
    }
    Stage CurrentStage() const { return state_.stage; }
    bool IsComplete() const { return !configured_ || state_.questIndex == state_.scopeEnd; }
    bool IsTemplePreview() const {
        return configured_ && (state_.scopeStart != 0 || state_.scopeEnd != static_cast<int>(campaign_.quests.size()));
    }
    bool HasReading(const std::string& id) const {
        return std::find(state_.discovered.begin(), state_.discovered.end(), id) != state_.discovered.end();
    }
    const std::string& Error() const { return error_; }
    std::uint64_t Generation() const { return generation_; }
    bool CallbackIsCurrent(std::uint64_t generation) const { return configured_ && generation == generation_; }
    bool Validate(const State& state, std::string& error) const {
        if (!configured_) { error = "Campaign content has not been configured."; return false; }
        return ValidateState(campaign_, state, error);
    }

    // The world adapter owns geometry and supplies a verified proximity result.
    // Merely visiting another landmark or interacting with another NPC cannot
    // advance the authoritative objective.
    bool Arrive(const std::string& questId, bool withinRange) {
        const Quest* quest = CurrentQuest();
        if (!quest || state_.stage != Stage::Travel || questId != quest->id || !withinRange)
            return Fail("Reach the current objective before starting this encounter.");
        State candidate = state_;
        candidate.stage = Stage::Talk;
        return Commit(std::move(candidate));
    }

    bool Talk(const std::string& npcId) {
        const Quest* quest = CurrentQuest();
        if (!quest || state_.stage != Stage::Talk || npcId != quest->npcId)
            return Fail("Speak to the current objective's character after arriving.");
        State candidate = state_;
        candidate.stage = Stage::Reading;
        return Commit(std::move(candidate));
    }

    bool Advance() {
        const Quest* quest = CurrentQuest();
        if (!quest || state_.stage != Stage::Reading)
            return Fail("There is no current story dialogue to advance.");
        State candidate = state_;
        if (static_cast<std::size_t>(candidate.beatIndex) + 1 < quest->beatCount) {
            ++candidate.beatIndex;
        } else {
            if (!quest->readingId.empty()) candidate.discovered.push_back(quest->readingId);
            ++candidate.questIndex;
            candidate.beatIndex = 0;
            SelectStage(candidate);
        }
        return Commit(std::move(candidate));
    }

    bool Advance(std::uint64_t expectedGeneration) {
        if (!CallbackIsCurrent(expectedGeneration)) return Fail("The story callback is stale.");
        return Advance();
    }

private:
    Campaign campaign_;
    State state_;
    bool configured_ = false;
    std::uint64_t generation_ = 0;
    std::string error_;

    void SelectStage(State& state) const {
        state.beatIndex = 0;
        state.stage = state.questIndex == state.scopeEnd ? Stage::Complete :
            campaign_.quests[static_cast<std::size_t>(state.questIndex)].isPrologue ? Stage::Reading : Stage::Travel;
    }
    bool Fail(std::string error) { error_ = std::move(error); return false; }
    bool Commit(State candidate) {
        std::string error;
        if (!ValidateState(campaign_, candidate, error)) return Fail(std::move(error));
        state_ = std::move(candidate);
        ++generation_;
        error_.clear();
        return true;
    }
};
} // namespace gospel
