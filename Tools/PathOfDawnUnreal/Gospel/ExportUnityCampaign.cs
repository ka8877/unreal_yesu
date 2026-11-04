// This executable evaluates the byte-exact Unity catalogs in SourceReferences.
// It never implements an alternate copy of the story or Unity's progression.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Encodings.Web;
using System.Text.Json;
using PathOfDawn.Core;

internal static class ExportUnityCampaign
{
    internal const string SourceCommit = "808d8d1e1eeed908d8925398f80c7173653ef364";

    private static object ExportQuest(GospelChronicleQuest quest)
    {
        var beats = new List<object>();
        int index = 0;
        for (int legacyIndex = 0; legacyIndex < quest.Dialogue.Count; legacyIndex++)
        {
            foreach (var detail in GospelStorybookCatalog.GetDetails(quest, legacyIndex))
            {
                var turn = detail.Turn;
                var scene = detail.Scene ?? GospelStorybookCatalog.GetScene(quest);
                string id = quest.Id + ":" + index++;
                beats.Add(new {
                    Id = id,
                    Speaker = turn.Speaker,
                    Text = turn.Text,
                    Kind = turn.IsVerbatim ? "Scripture" : turn.IsDramatized ? "Dramatization" : "Summary",
                    Reference = detail.Reference,
                    VoiceKey = id,
                    SceneTitle = scene.Title,
                    Location = scene.Location,
                    TimeLabel = scene.TimeLabel,
                    MusicRole = scene.MusicRole
                });
            }
        }
        if (beats.Count != GospelStorybookCatalog.GetStoryBeatCount(quest))
            throw new InvalidOperationException("Unity beat count disagrees for " + quest.Id);
        return new {
            Id = quest.Id,
            ChapterId = quest.ChapterId,
            Title = quest.Title,
            Objective = quest.Objective,
            NpcId = quest.NpcId,
            NpcName = quest.NpcName,
            ReadingId = quest.ReadingId,
            IsPrologue = quest.IsPrologue,
            Beats = beats
        };
    }

    private static void VerifyOriginalUnityProgression()
    {
        var journey = GospelJourney.New();
        journey.EnableChronicle();
        var chronicle = journey.Chronicle;
        int expectedDiscoveries = 0;
        foreach (var quest in GospelChronicleCatalog.Quests)
        {
            if (chronicle.CurrentQuest.Id != quest.Id)
                throw new InvalidOperationException("Unity objective order changed at " + quest.Id);
            string message;
            if (!quest.IsPrologue)
            {
                if (!chronicle.TryArrive(quest.LandmarkId, quest.X, out message)
                    || !chronicle.TryTalk(quest.NpcId, out message))
                    throw new InvalidOperationException("Unity interaction failed at " + quest.Id);
            }
            int steps = 0;
            while (!chronicle.IsComplete && chronicle.CurrentQuest.Id == quest.Id)
            {
                int before = chronicle.DiscoveredCount;
                bool last = steps + 1 == GospelStorybookCatalog.GetStoryBeatCount(quest);
                GospelReading acquired;
                if (!chronicle.AdvanceStory(out acquired))
                    throw new InvalidOperationException("Unity story advance failed at " + quest.Id);
                if (!last && (acquired != null || chronicle.DiscoveredCount != before))
                    throw new InvalidOperationException("Unity discovered a passage before story completion");
                steps++;
            }
            if (steps != GospelStorybookCatalog.GetStoryBeatCount(quest))
                throw new InvalidOperationException("Unity progression and flattened beat count disagree");
            if (quest.Reading != null) expectedDiscoveries++;
            if (chronicle.DiscoveredCount != expectedDiscoveries)
                throw new InvalidOperationException("Unity passage completion differs from export");
        }
        if (!chronicle.IsComplete || expectedDiscoveries != GospelChronicleCatalog.Readings.Count)
            throw new InvalidOperationException("Unity campaign did not finish");
    }

    public static int Main()
    {
        VerifyOriginalUnityProgression();
        var document = new {
            SchemaVersion = 1,
            CampaignId = "gospel-pilgrimage",
            ContentVersion = 1,
            Title = "말씀을 따라 예수님의 길",
            ScopeNote = GospelStorybookCatalog.Scope + " " + GospelChronicleCatalog.HistoricalNote,
            Source = new { Repository = "ka8877/firstgame", Commit = SourceCommit },
            Readings = GospelChronicleCatalog.Readings.Select(reading => new {
                Id = reading.Id,
                Title = reading.Title,
                Reference = reading.Reference,
                Text = reading.Text,
                Source = GospelCatalog.Attribution + " · " + reading.SourceUrl,
                Context = reading.Context
            }).ToArray(),
            Quests = GospelChronicleCatalog.Quests.Select(ExportQuest).ToArray()
        };
        Console.OutputEncoding = new System.Text.UTF8Encoding(false);
        Console.WriteLine(JsonSerializer.Serialize(document, new JsonSerializerOptions {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            WriteIndented = true
        }));
        return 0;
    }
}
