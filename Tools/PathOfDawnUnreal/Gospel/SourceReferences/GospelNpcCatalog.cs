using System;
using System.Collections.Generic;

namespace PathOfDawn.Core
{
    public sealed class GospelNpcDefinition
    {
        public string Id { get; }
        public string Name { get; }
        public string Portrait { get; }
        public string Role { get; }
        public string Greeting { get; }
        public IReadOnlyList<GospelNpcTopic> Topics { get; }
        public GospelNpcDefinition(string id,string name,string portrait,string role,string greeting,params GospelNpcTopic[] topics)
        { Id=id;Name=name;Portrait=portrait;Role=role;Greeting=greeting;Topics=Array.AsReadOnly(topics); }
    }
    public sealed class GospelNpcTopic
    {
        public string Id { get; }
        public string Title { get; }
        public string ReadingId { get; }
        public string Introduction { get; }
        public string Reflection { get; }
        public GospelNpcTopic(string id,string title,string reading,string introduction,string reflection)
        { Id=id;Title=title;ReadingId=reading;Introduction=introduction;Reflection=reflection; }
    }

    /// <summary>Repeatable study conversations never award or skip the ordered Gospel readings.</summary>
    public static class GospelNpcCatalog
    {
        static GospelNpcTopic Topic(string id,string title,string reading,string intro,string reflection)
            =>new GospelNpcTopic(id,title,reading,intro,reflection);
        static readonly GospelNpcDefinition[] npcs={
            new GospelNpcDefinition("temple-guide","성전 길잡이","teacher","유월절 여정 안내",
                "예루살렘의 성전 뜰에 오셨군요. 이 여정에서는 누가복음의 기록을 한 장면씩 따라 읽습니다. 무엇이 궁금한가요?",
                Topic("passover","유월절에 왜 예루살렘에 왔나요?","temple-passover",
                    "누가는 부모가 해마다 유월절에 예루살렘으로 갔다고 기록합니다. 예수님이 열두 살이 되셨을 때의 여정이지요.",
                    "아래의 본문에서 나이와 절기, 장소를 찾아보세요. 다음 기록은 선생들 가운데 계신 예수님으로 이어집니다."),
                Topic("good-news","탄생의 소식을 다시 듣고 싶어요","birth-good-news",
                    "이야기의 시작에는 목자들에게 전해진 기쁜 소식이 있습니다. 누가복음은 구주가 나셨다는 천사의 소식을 기록합니다.",
                    "천사의 말과 게임의 해설을 구분해 읽어 보세요. 본문은 아래에 그대로 놓여 있습니다.")),
            new GospelNpcDefinition("teacher-reading","율법 선생","teacher","성전에서 말씀 읽기",
                "말씀을 천천히 살펴봅시다. 이곳의 대화는 본문을 이해하도록 돕는 학습 대화입니다.",
                Topic("listening","예수님은 성전에서 무엇을 하셨나요?","temple-teachers",
                    "누가는 예수님께서 선생들 가운데 앉아 듣기도 하시고 묻기도 하셨다고 기록합니다.",
                    "구체적으로 어떤 질문을 하셨는지는 이 구절에 적혀 있지 않습니다. 기록된 행동과 반응부터 살펴보세요."),
                Topic("growing","지혜가 자란다는 말씀은 무엇인가요?","temple-nazareth",
                    "성전의 만남 뒤에는 나사렛으로 돌아가신 기록과 성장의 말씀이 이어집니다.",
                    "누가복음 2장 52절의 지혜와 키, 하나님과 사람이라는 표현을 함께 읽어 보세요.")),
            new GospelNpcDefinition("teacher-listening","성전의 선생","teacher","본문과 질문 나누기",
                "본문을 읽고 질문을 나누어 볼까요? 기록되지 않은 대답을 새 성경 말씀으로 만들지는 않습니다.",
                Topic("wonder","사람들은 왜 놀랐나요?","temple-teachers",
                    "본문은 듣는 사람들이 예수님의 지혜와 대답을 놀랍게 여겼다고 전합니다.",
                    "성경이 무엇을 기록했고 무엇을 기록하지 않았는지 나누어 생각해 보세요."),
                Topic("father-house","‘내 아버지 집’이라는 말씀이 궁금해요","temple-parents",
                    "마리아와 예수님의 대화는 누가복음 2장 48절부터 나옵니다. 직접 하신 말씀을 본문에서 읽을 수 있습니다.",
                    "이어서 부모가 그 말씀을 깨닫지 못했다는 기록도 함께 읽어 보세요.")),
            new GospelNpcDefinition("mary","마리아","mary","부모와 예수님의 만남",
                "기록된 말씀을 함께 돌아볼까요? 마음에 간직했다는 표현을 따라 읽어 보세요.",
                Topic("found","예수님을 찾은 장면을 읽고 싶어요","temple-parents",
                    "누가복음은 부모가 놀랐고, 마리아가 근심하며 찾았던 마음을 전했다고 기록합니다.",
                    "아래 48절과 49절에서 마리아의 말과 예수님의 대답을 차례대로 읽어 보세요."),
                Topic("remember","마음에 간직한 말씀을 듣고 싶어요","birth-remembered",
                    "탄생의 기록에서도 마리아가 모든 말을 마음에 지켜 생각했다는 구절이 나옵니다.",
                    "목자들의 반응과 마리아의 반응이 어떻게 기록되어 있는지 본문에서 찾아보세요.")),
            new GospelNpcDefinition("joseph","요셉","joseph","가족의 여정",
                "함께 걸어온 여정을 되짚어 볼까요? 성경의 기록을 읽고 다음 장면으로 나아갑시다.",
                Topic("family-trip","가족의 예루살렘 여정이 궁금해요","temple-passover",
                    "예수님의 부모는 유월절을 지키러 예루살렘으로 올라갔습니다. 열두 살 때의 사건이 이 여정의 본문입니다.",
                    "부모가 예수님이 예루살렘에 머무셨다는 것을 알지 못했다는 부분까지 이어 읽어 보세요."),
                Topic("nazareth","나사렛으로 돌아간 뒤에는요?","temple-nazareth",
                    "누가는 예수님이 부모와 함께 나사렛으로 내려가 순종하여 받드셨다고 전합니다.",
                    "첫 여정은 이 성장의 기록에서 마칩니다. 이후 공생애는 다음 장에서 다룰 부분입니다."))
        };
        public static IReadOnlyList<GospelNpcDefinition> All { get; }=Array.AsReadOnly(npcs);
        public static GospelNpcDefinition Get(string id)
        { foreach(var npc in npcs)if(npc.Id==id)return npc;throw new ArgumentException("알 수 없는 대화 인물: "+id); }
        public static bool CanGuide(string npcId,string objectiveId)
        {
            Get(npcId);
            switch(objectiveId)
            {
                case "temple-gate":return npcId=="temple-guide";
                case "teachers":return npcId=="teacher-reading"||npcId=="teacher-listening";
                case "parents":return npcId=="mary"||npcId=="joseph";
                case "nazareth-gate":return npcId=="joseph";
                default:return false;
            }
        }
        public static bool TryBeginStory(GospelJourney journey,string npcId,out string message)
        {
            if(journey==null)throw new ArgumentNullException(nameof(journey));
            Get(npcId);
            if(journey.Phase!=GospelPhase.Exploring)
            {message=journey.IsComplete?"첫 여정을 마쳤습니다. 말씀 기록에서 다시 읽을 수 있습니다.":"현재 대화를 먼저 마쳐 주세요.";return false;}
            if(!CanGuide(npcId,journey.CurrentObjective.Id))
            {message=journey.CurrentObjective.Prompt;return false;}
            return journey.TryInteract(journey.CurrentObjective.Id,out message);
        }
        public static GospelNpcTopic GetTopic(string npcId,string topicId)
        { foreach(var topic in Get(npcId).Topics)if(topic.Id==topicId)return topic;throw new ArgumentException("알 수 없는 대화 주제: "+topicId); }
        public static IReadOnlyList<GospelDialogueTurn> ForTopic(string npcId,string topicId)
        {
            var npc=Get(npcId);var topic=GetTopic(npcId,topicId);var reading=GospelCatalog.GetReading(topic.ReadingId);
            string first=reading.Text.Split('\n')[0];int space=first.IndexOf(' ');
            string quotation=space>=0?first.Substring(space+1):first;
            return Array.AsReadOnly(new[]{new GospelDialogueTurn(npc.Name,npc.Portrait,topic.Introduction),
                new GospelDialogueTurn("복음서의 기록",npc.Portrait,quotation,true),
                new GospelDialogueTurn(npc.Name,npc.Portrait,topic.Reflection)});
        }
    }
}
