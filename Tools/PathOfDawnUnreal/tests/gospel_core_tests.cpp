#include "GospelState.h"
#include "GospelFixture.h"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>

namespace {
int assertions = 0;
void Check(bool value, const char* expression, int line) {
    ++assertions;
    if (!value) {
        std::cerr << "Gospel core failure at line " << line << ": " << expression << '\n';
        std::exit(1);
    }
}
#define CHECK(expression) Check(static_cast<bool>(expression), #expression, __LINE__)

bool SameState(const gospel::State& a, const gospel::State& b) {
    return a.schemaVersion == b.schemaVersion && a.campaignId == b.campaignId &&
        a.contentVersion == b.contentVersion && a.scopeStart == b.scopeStart &&
        a.scopeEnd == b.scopeEnd && a.questIndex == b.questIndex &&
        a.beatIndex == b.beatIndex && a.stage == b.stage && a.discovered == b.discovered;
}

void RejectRestore(gospel::Session& session, const gospel::State& invalid) {
    const auto before = session.Snapshot();
    const auto epoch = session.Generation();
    CHECK(!session.Restore(invalid));
    CHECK(!session.Error().empty());
    CHECK(SameState(before, session.Snapshot()));
    CHECK(epoch == session.Generation());
}

void RejectActionWithoutMutation(gospel::Session& session, bool result,
                                const gospel::State& before, std::uint64_t generation) {
    CHECK(!result);
    CHECK(!session.Error().empty());
    CHECK(SameState(before, session.Snapshot()));
    CHECK(generation == session.Generation());
}

void Journey(gospel::Session& session, const gospel::Campaign& campaign,
             bool preview, int expectedQuestCount, int expectedReadings) {
    CHECK(session.NewGame(preview));
    CHECK(session.IsTemplePreview() == preview);
    CHECK(session.Snapshot().discovered.empty());
    const int first = session.Snapshot().scopeStart;
    const int end = session.Snapshot().scopeEnd;
    CHECK(end - first == expectedQuestCount);
    std::vector<std::string> observed;
    for (int i = first; i < end; ++i) {
        const auto& quest = campaign.quests[static_cast<std::size_t>(i)];
        CHECK(session.CurrentQuest() != nullptr);
        CHECK(session.CurrentQuest()->id == quest.id);
        CHECK(session.Snapshot().questIndex == i);
        CHECK(session.Snapshot().beatIndex == 0);
        CHECK(session.Snapshot().discovered == observed);
        const auto beforeRead = session.Snapshot();
        if (quest.isPrologue) {
            CHECK(session.CurrentStage() == gospel::Stage::Reading);
        } else {
            CHECK(session.CurrentStage() == gospel::Stage::Travel);
            const auto generation = session.Generation();
            RejectActionWithoutMutation(session, session.Advance(), beforeRead, generation);
            RejectActionWithoutMutation(session, session.Talk(quest.npcId), beforeRead, generation);
            RejectActionWithoutMutation(session, session.Arrive("other-landmark", true), beforeRead, generation);
            RejectActionWithoutMutation(session, session.Arrive(quest.id, false), beforeRead, generation);
            CHECK(session.Arrive(quest.id, true));
            CHECK(session.CurrentStage() == gospel::Stage::Talk);
            CHECK(session.Snapshot().discovered == observed);
            const auto arrived = session.Snapshot();
            const auto arrivedGeneration = session.Generation();
            RejectActionWithoutMutation(session, session.Talk("other-character"), arrived, arrivedGeneration);
            CHECK(session.Talk(quest.npcId));
            CHECK(session.CurrentStage() == gospel::Stage::Reading);
        }
        for (std::size_t beat = 0; beat < quest.beatCount; ++beat) {
            CHECK(session.Snapshot().beatIndex == static_cast<int>(beat));
            CHECK(session.Snapshot().discovered == observed);
            if (!quest.readingId.empty()) CHECK(!session.HasReading(quest.readingId));
            // A fresh session can recover every actual story cursor without
            // awarding an early passage or replaying earlier completed events.
            gospel::Session recovered;
            CHECK(recovered.Configure(campaign));
            CHECK(recovered.Restore(session.Snapshot()));
            CHECK(SameState(recovered.Snapshot(), session.Snapshot()));
            // Opening the book/journal is read-only: callers inspect a copied
            // state and immutable campaign instead of advancing the journey.
            auto displayCopy = recovered.Snapshot();
            displayCopy.discovered.push_back("ui-copy-only");
            CHECK(SameState(recovered.Snapshot(), session.Snapshot()));
            const auto epoch = session.Generation();
            CHECK(session.Advance(epoch));
            const auto advanced = session.Snapshot();
            const auto newEpoch = session.Generation();
            RejectActionWithoutMutation(session, session.Advance(epoch), advanced, newEpoch);
        }
        if (!quest.readingId.empty()) observed.push_back(quest.readingId);
        CHECK(session.Snapshot().discovered == observed);
        CHECK(session.Snapshot().questIndex == i + 1);
    }
    CHECK(session.IsComplete());
    CHECK(session.CurrentQuest() == nullptr);
    CHECK(session.CurrentStage() == gospel::Stage::Complete);
    CHECK(session.Snapshot().beatIndex == 0);
    CHECK(static_cast<int>(session.Snapshot().discovered.size()) == expectedReadings);
    std::string error;
    CHECK(gospel::ValidateState(campaign, session.Snapshot(), error));
    const auto completed = session.Snapshot();
    const auto epoch = session.Generation();
    RejectActionWithoutMutation(session, session.Advance(), completed, epoch);
    RejectActionWithoutMutation(session, session.Arrive(campaign.quests.back().id, true), completed, epoch);
    RejectActionWithoutMutation(session, session.Talk(campaign.quests.back().npcId), completed, epoch);
}

void SaveMutations(const gospel::Campaign& campaign) {
    gospel::Session session;
    CHECK(session.Configure(campaign));
    CHECK(session.NewGame(true));
    const auto baseline = session.Snapshot();
    auto invalid = baseline;
    invalid.schemaVersion = 2; RejectRestore(session, invalid);
    invalid = baseline; invalid.campaignId += "-other"; RejectRestore(session, invalid);
    invalid = baseline; ++invalid.contentVersion; RejectRestore(session, invalid);
    invalid = baseline; invalid.scopeStart = -1; RejectRestore(session, invalid);
    invalid = baseline; ++invalid.scopeStart; RejectRestore(session, invalid);
    invalid = baseline; --invalid.scopeEnd; RejectRestore(session, invalid);
    invalid = baseline; invalid.scopeEnd = std::numeric_limits<int>::max(); RejectRestore(session, invalid);
    invalid = baseline; invalid.questIndex = baseline.scopeStart - 1; RejectRestore(session, invalid);
    invalid = baseline; invalid.questIndex = baseline.scopeEnd + 1; RejectRestore(session, invalid);
    invalid = baseline; invalid.beatIndex = -1; RejectRestore(session, invalid);
    invalid = baseline; invalid.beatIndex = 1; RejectRestore(session, invalid);
    invalid = baseline; invalid.stage = static_cast<gospel::Stage>(-1); RejectRestore(session, invalid);
    invalid = baseline; invalid.stage = gospel::Stage::Complete; RejectRestore(session, invalid);
    invalid = baseline; invalid.discovered = {"unknown-reading"}; RejectRestore(session, invalid);
    invalid = baseline;
    invalid.discovered = {campaign.quests.front().readingId}; RejectRestore(session, invalid);

    const auto* first = session.CurrentQuest();
    CHECK(first != nullptr);
    CHECK(session.Arrive(first->id, true));
    CHECK(session.Talk(first->npcId));
    auto duringReading = session.Snapshot();
    invalid = duringReading;
    invalid.beatIndex = static_cast<int>(first->beatCount); RejectRestore(session, invalid);
    invalid = duringReading; invalid.beatIndex = std::numeric_limits<int>::max(); RejectRestore(session, invalid);
    invalid = duringReading; invalid.stage = static_cast<gospel::Stage>(99); RejectRestore(session, invalid);

    // Obtain at least two genuine discoveries before testing deletion,
    // duplication and reordering of completed-passage records.
    while (session.Snapshot().discovered.size() < 2) {
        const auto* current = session.CurrentQuest();
        CHECK(current != nullptr);
        if (session.CurrentStage() == gospel::Stage::Travel) CHECK(session.Arrive(current->id, true));
        if (session.CurrentStage() == gospel::Stage::Talk) CHECK(session.Talk(current->npcId));
        CHECK(session.Advance());
    }
    auto withDiscoveries = session.Snapshot();
    invalid = withDiscoveries; invalid.discovered.pop_back(); RejectRestore(session, invalid);
    invalid = withDiscoveries; invalid.discovered.push_back(invalid.discovered.front()); RejectRestore(session, invalid);
    invalid = withDiscoveries; std::swap(invalid.discovered[0], invalid.discovered[1]); RejectRestore(session, invalid);
    invalid = withDiscoveries; invalid.discovered[0] = "unknown"; RejectRestore(session, invalid);
    invalid = withDiscoveries; invalid.discovered.push_back(campaign.quests.back().readingId); RejectRestore(session, invalid);

    while (!session.IsComplete()) {
        const auto* current = session.CurrentQuest();
        if (session.CurrentStage() == gospel::Stage::Travel) CHECK(session.Arrive(current->id, true));
        if (session.CurrentStage() == gospel::Stage::Talk) CHECK(session.Talk(current->npcId));
        CHECK(session.Advance());
    }
    auto finished = session.Snapshot();
    invalid = finished; invalid.stage = gospel::Stage::Reading; RejectRestore(session, invalid);
    invalid = finished; invalid.beatIndex = 1; RejectRestore(session, invalid);
    invalid = finished; invalid.questIndex = invalid.scopeEnd - 1; RejectRestore(session, invalid);

    CHECK(session.NewGame(false));
    const auto prologue = session.Snapshot();
    invalid = prologue; invalid.stage = gospel::Stage::Travel; RejectRestore(session, invalid);
    invalid = prologue; invalid.stage = gospel::Stage::Talk; RejectRestore(session, invalid);
    const auto oldGeneration = session.Generation();
    CHECK(session.Restore(finished));
    CHECK(!session.CallbackIsCurrent(oldGeneration));
}

void CampaignMutations(const gospel::Campaign& campaign) {
    gospel::Session session;
    CHECK(session.Configure(campaign));
    CHECK(session.Advance());
    const auto initial = session.Snapshot();
    const auto epoch = session.Generation();
    auto reject = [&](const gospel::Campaign& invalid) {
        CHECK(!session.Configure(invalid));
        CHECK(!session.Error().empty());
        CHECK(SameState(initial, session.Snapshot()));
        CHECK(epoch == session.Generation());
        CHECK(session.Definition().id == campaign.id);
    };
    auto invalid = campaign; invalid.id.clear(); reject(invalid);
    invalid = campaign; invalid.id = "untrusted/asset-path"; reject(invalid);
    invalid = campaign; invalid.contentVersion = 0; reject(invalid);
    invalid = campaign; invalid.quests.clear(); reject(invalid);
    invalid = campaign; invalid.quests[1].id = invalid.quests[0].id; reject(invalid);
    invalid = campaign; invalid.quests[0].beatCount = 0; reject(invalid);
    invalid = campaign; invalid.quests[0].beatCount = std::numeric_limits<std::size_t>::max(); reject(invalid);
    invalid = campaign; invalid.quests[11].npcId.clear(); reject(invalid);
    invalid = campaign; invalid.quests[12].chapterId = "baptism"; reject(invalid);
    invalid = campaign; invalid.quests.back().isPrologue = true; reject(invalid);
    invalid = campaign; invalid.quests.back().readingId = invalid.quests.front().readingId; reject(invalid);
    // Generic campaigns without temple remain valid, but preview requests must
    // fail transactionally instead of silently opening the full campaign.
    auto withoutTemple = campaign;
    for (auto& quest : withoutTemple.quests) if (quest.chapterId == "temple") quest.chapterId = "childhood";
    CHECK(session.Configure(withoutTemple));
    const auto full = session.Snapshot();
    const auto fullEpoch = session.Generation();
    RejectActionWithoutMutation(session, session.NewGame(true), full, fullEpoch);
}
} // namespace

int main() {
    const auto campaign = GospelFixture();
    CHECK(campaign.id == "gospel-pilgrimage");
    CHECK(campaign.quests.size() == 23);
    CHECK(campaign.quests.front().isPrologue);
    CHECK(campaign.quests[11].id == "nazareth-departure");
    CHECK(campaign.quests[18].id == "adult-jordan-road");
    int birthBeats = 0;
    for (const auto& quest : campaign.quests) if (quest.chapterId == "birth") birthBeats += static_cast<int>(quest.beatCount);
    CHECK(birthBeats == 51);
    gospel::Session session;
    CHECK(!session.NewGame());
    CHECK(session.CurrentQuest() == nullptr);
    CHECK(session.Configure(campaign));
    Journey(session, campaign, false, 23, 19);
    Journey(session, campaign, true, 7, 4);
    for (std::size_t i = 0; i < 11; ++i) CHECK(!session.HasReading(campaign.quests[i].readingId));
    SaveMutations(campaign);
    CampaignMutations(campaign);
    std::cout << "Gospel core passed " << assertions << " assertions against actual exported campaign; no Unreal execution.\n";
    return 0;
}
