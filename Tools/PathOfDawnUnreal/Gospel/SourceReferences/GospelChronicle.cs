using System;
using System.Collections.Generic;
using System.Linq;

namespace PathOfDawn.Core
{
    public enum GospelQuestStage { Travel, Talk, Reading, Complete }

    [Serializable] public sealed class GospelChronicleSave
    {
        public int version, questIndex, dialoguePage;
        // Optional presentation cursor. Older schema-one JSON omits it and
        // resumes at the first detail of the same saved legacy dialogue page.
        public int storyDetailPage;
        public GospelQuestStage stage = GospelQuestStage.Reading;
        public bool importedCompletedJourney;
        public List<string> inheritedReadings = new List<string>();
        public List<string> discoveredReadings = new List<string>();
        public GospelChronicleSave Copy() => new GospelChronicleSave {
            version=version,questIndex=questIndex,dialoguePage=dialoguePage,storyDetailPage=storyDetailPage,stage=stage,
            importedCompletedJourney=importedCompletedJourney,
            inheritedReadings=inheritedReadings==null?null:new List<string>(inheritedReadings),
            discoveredReadings=discoveredReadings==null?null:new List<string>(discoveredReadings)
        };
    }

    public sealed class GospelBookPage
    {
        public int Number { get; }
        public bool IsDiscovered { get; }
        public GospelReading Reading { get; }
        public string Title => Reading == null ? "" : Reading.Title;
        public string Reference => Reading == null ? "" : Reading.Reference;
        public string Text => Reading == null ? "" : Reading.Text;
        public string ReadingId => Reading == null ? "" : Reading.Id;
        internal GospelBookPage(int number,GospelReading reading,bool discovered)
        { Number=number;IsDiscovered=discovered;Reading=discovered?reading:null; }
    }

    public sealed class GospelQuestJournalEntry
    {
        public string Id { get; }
        public string Title { get; }
        public string Objective { get; }
        public bool IsComplete { get; }
        public bool IsCurrent { get; }
        internal GospelQuestJournalEntry(GospelChronicleQuest quest,bool complete,bool current)
        { Id=quest.Id;Title=quest.Title;Objective=quest.Objective;IsComplete=complete;IsCurrent=current; }
    }

    /// <summary>Ordered story objectives. Visiting or opening a conversation is
    /// not scripture discovery: completing the event records its passage.</summary>
    public sealed class GospelChronicle
    {
        public const float InteractionRadius=2.25f;
        readonly GospelChronicleSave state;
        internal GospelChronicle(GospelChronicleSave state) { this.state=state; }
        public GospelChronicleQuest CurrentQuest => IsComplete?null:GospelChronicleCatalog.Quests[state.questIndex];
        public GospelQuestStage Stage => state.stage;
        public int QuestIndex => state.questIndex;
        public int QuestCount => GospelChronicleCatalog.Quests.Count;
        public bool IsComplete => state.questIndex==QuestCount;
        public string ChapterId => IsComplete?"baptism":CurrentQuest.ChapterId;
        public bool IsAdult => ChapterId=="baptism";
        public string AgeLabel => ChapterId=="birth"?"탄생과 아기 때의 기록":IsAdult?"공생애 시작 · 삼십세쯤":"열두 살 · 유월절의 여정";
        public int DialogueIndex => state.dialoguePage;
        public int DialogueCount => CurrentQuest==null?0:CurrentQuest.Dialogue.Count;
        public int StoryDetailIndex => state.storyDetailPage;
        public int StoryBeatIndex => IsComplete?0:GospelStorybookCatalog.GetStoryBeatIndex(CurrentQuest,DialogueIndex,StoryDetailIndex);
        public int StoryBeatCount => IsComplete?0:GospelStorybookCatalog.GetStoryBeatCount(CurrentQuest);
        public string StoryVoiceKey => IsComplete?"":CurrentQuest.Id+":"+StoryBeatIndex;
        public string CurrentStoryReference => IsComplete?"":GospelStorybookCatalog.GetDetail(CurrentQuest,DialogueIndex,StoryDetailIndex).Reference;
        public GospelDialogueTurn CurrentDialogue => Stage==GospelQuestStage.Reading?CurrentQuest.Dialogue[state.dialoguePage]:null;
        public GospelReading CurrentReading => Stage==GospelQuestStage.Reading?CurrentQuest.Reading:null;
        public GospelStorybookScene CurrentStoryScene => IsComplete?null:GospelStorybookCatalog.GetCurrentScene(this);
        public GospelDialogueTurn CurrentStoryBeat => GospelStorybookCatalog.GetBeat(this);
        public int DiscoveredCount => state.discoveredReadings.Count;
        public int TotalReadings => GospelChronicleCatalog.Readings.Count;
        public bool HasReading(string id) => !string.IsNullOrEmpty(id)&&state.discoveredReadings.Contains(id);
        public IReadOnlyList<GospelBookPage> BookPages => GospelChronicleCatalog.Readings.Select((r,i)=>new GospelBookPage(i+1,r,HasReading(r.Id))).ToList().AsReadOnly();
        public IReadOnlyList<GospelQuestJournalEntry> Journal => GospelChronicleCatalog.Quests.Take(Math.Min(state.questIndex+1,QuestCount))
            .Select((q,i)=>new { quest=q,index=i })
            .Where(x=>!state.importedCompletedJourney||x.index>=GospelChronicleCatalog.FirstAdultQuest||x.quest.Reading==null||HasReading(x.quest.Reading.Id))
            .Select(x=>new GospelQuestJournalEntry(x.quest,x.index<state.questIndex,x.index==state.questIndex)).ToList().AsReadOnly();

        internal static GospelChronicleSave Import(IReadOnlyList<string> inherited,bool completed)
        {
            var save=new GospelChronicleSave { version=1,inheritedReadings=new List<string>(inherited),discoveredReadings=new List<string>(inherited),importedCompletedJourney=completed };
            if(completed)save.questIndex=GospelChronicleCatalog.FirstAdultQuest;
            var journey=new GospelChronicle(save);journey.SelectNextQuest();return save;
        }

        void SelectNextQuest()
        {
            // Imported discoveries retain their original IDs. Do not make the
            // player read an already completed reading a second time to advance.
            while(state.questIndex<QuestCount)
            {
                var q=GospelChronicleCatalog.Quests[state.questIndex];
                if(q.Reading!=null&&state.inheritedReadings.Contains(q.Reading.Id))state.questIndex++;
                else break;
            }
            state.dialoguePage=0;
            state.storyDetailPage=0;
            state.stage=IsComplete?GospelQuestStage.Complete:CurrentQuest.IsPrologue?GospelQuestStage.Reading:GospelQuestStage.Travel;
        }

        public bool TryArrive(string landmarkId,float playerX,out string message)
        {
            if(IsComplete) {message="요단의 기록까지 여정을 마쳤습니다.";return false;}
            if(Stage!=GospelQuestStage.Travel) {message="현재 만남을 이어가세요.";return false;}
            if(float.IsNaN(playerX)||float.IsInfinity(playerX)||landmarkId!=CurrentQuest.LandmarkId||Math.Abs(playerX-CurrentQuest.X)>InteractionRadius)
            {message=CurrentQuest.Objective;return false;}
            state.stage=GospelQuestStage.Talk;message=CurrentQuest.NpcName+"에게 말을 걸어 보세요.";return true;
        }

        public bool TryTalk(string npcId,out string message)
        {
            if(IsComplete||Stage!=GospelQuestStage.Talk) {message="먼저 현재 목적지에 도착해야 합니다.";return false;}
            if(npcId!=CurrentQuest.NpcId) {message=CurrentQuest.NpcName+"와 현재 여정을 이야기하세요.";return false;}
            state.stage=GospelQuestStage.Reading;state.dialoguePage=0;state.storyDetailPage=0;message=CurrentQuest.Title;return true;
        }

        public bool AdvanceDialogue()
        {
            if(IsComplete||Stage!=GospelQuestStage.Reading)return false;
            state.storyDetailPage=0;
            if(state.dialoguePage+1<DialogueCount) {state.dialoguePage++;return true;}
            var reading=CurrentQuest.Reading;
            if(reading!=null&&!HasReading(reading.Id))state.discoveredReadings.Add(reading.Id);
            state.questIndex++;SelectNextQuest();return true;
        }

        /// <summary>The story-completion boundary. The returned acquisition is
        /// new exactly once; displaying/opening the Bible never calls this API.</summary>
        public bool AdvanceStory(out GospelReading acquired)
        {
            acquired=null;
            if(IsComplete||Stage!=GospelQuestStage.Reading)return false;
            var details=GospelStorybookCatalog.GetDetails(CurrentQuest,DialogueIndex);
            if(state.storyDetailPage+1<details.Count)
            {state.storyDetailPage++;return true;}
            var reading=CurrentReading;
            bool alreadyFound=reading!=null&&HasReading(reading.Id);
            if(!AdvanceDialogue())return false;
            if(reading!=null&&!alreadyFound&&HasReading(reading.Id))acquired=reading;
            return true;
        }

        internal static void Validate(GospelChronicleSave save,IReadOnlyList<string> inherited,bool completedLegacy)
        {
            if(save.version!=1||save.questIndex<0||save.questIndex>GospelChronicleCatalog.Quests.Count||!Enum.IsDefined(typeof(GospelQuestStage),save.stage)
                ||save.discoveredReadings==null||save.inheritedReadings==null||save.inheritedReadings.Count!=inherited.Count
                ||!save.inheritedReadings.SequenceEqual(inherited)||save.discoveredReadings.Distinct().Count()!=save.discoveredReadings.Count)
                throw new ArgumentException("생애 여정의 저장 범위 또는 계승한 말씀이 잘못되었습니다.");
            if(save.importedCompletedJourney&&(!completedLegacy||save.questIndex<GospelChronicleCatalog.FirstAdultQuest))
                throw new ArgumentException("완료한 이전 여정의 이어하기 정보가 잘못되었습니다.");
            var known=new HashSet<string>(GospelChronicleCatalog.Readings.Select(r=>r.Id));
            if(save.discoveredReadings.Any(id=>!known.Contains(id)))throw new ArgumentException("발견하지 않은 말씀의 식별자가 있습니다.");
            var expected=new List<string>(inherited);
            for(int i=0;i<save.questIndex;i++)
            {
                if(save.importedCompletedJourney&&i<GospelChronicleCatalog.FirstAdultQuest)continue;
                var reading=GospelChronicleCatalog.Quests[i].Reading;
                if(reading!=null&&!expected.Contains(reading.Id))expected.Add(reading.Id);
            }
            if(!save.discoveredReadings.SequenceEqual(expected))throw new ArgumentException("발견한 말씀과 완료한 여정의 순서가 일치하지 않습니다.");
            bool finished=save.questIndex==GospelChronicleCatalog.Quests.Count;
            if(finished!=(save.stage==GospelQuestStage.Complete))throw new ArgumentException("생애 여정의 완료 상태가 일치하지 않습니다.");
            if(finished)
            {if(save.dialoguePage!=0||save.storyDetailPage!=0)throw new ArgumentException("완료한 여정에 열린 대화가 있습니다.");return;}
            var quest=GospelChronicleCatalog.Quests[save.questIndex];
            if(quest.IsPrologue&&save.stage!=GospelQuestStage.Reading)throw new ArgumentException("탄생 도입의 장면 상태가 잘못되었습니다.");
            if(save.dialoguePage<0||(save.stage==GospelQuestStage.Reading?save.dialoguePage>=quest.Dialogue.Count:save.dialoguePage!=0))
                throw new ArgumentException("생애 여정의 대화 위치가 잘못되었습니다.");
            if(save.storyDetailPage<0||(save.stage==GospelQuestStage.Reading?
                save.storyDetailPage>=GospelStorybookCatalog.GetDetails(quest,save.dialoguePage).Count:save.storyDetailPage!=0))
                throw new ArgumentException("이야기의 세부 장면 위치가 잘못되었습니다.");
        }
    }
}
