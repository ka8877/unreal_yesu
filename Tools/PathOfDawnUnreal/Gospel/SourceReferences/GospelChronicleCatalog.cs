using System;
using System.Collections.Generic;
using System.Linq;

namespace PathOfDawn.Core
{
    public sealed class GospelChronicleQuest
    {
        public string Id { get; }
        public string ChapterId { get; }
        public string Title { get; }
        public string Objective { get; }
        public string NpcId { get; }
        public string NpcName { get; }
        public string Portrait { get; }
        public string LandmarkId => Id;
        public float X { get; }
        public bool IsPrologue => ChapterId=="birth";
        public GospelReading Reading { get; }
        public string ReadingId => Reading==null?"":Reading.Id;
        public IReadOnlyList<GospelDialogueTurn> Dialogue { get; }
        public GospelChronicleQuest(string id,string chapter,string title,string objective,string npc,string name,string portrait,float x,GospelReading reading,params GospelDialogueTurn[] dialogue)
        { Id=id;ChapterId=chapter;Title=title;Objective=objective;NpcId=npc;NpcName=name;Portrait=portrait;X=x;Reading=reading;Dialogue=Array.AsReadOnly(dialogue); }
    }

    public static class GospelChronicleCatalog
    {
        public const string Revision="gospel-chronicle-2026-10-29";
        public const int FirstAdultQuest=18;
        public const string HistoricalNote="복음서에 기록된 사건을 따라가는 학습 여정입니다. 지형·이동 거리·길 안내 대화는 게임을 위한 극화이며, 기록되지 않은 예수님의 발언을 성경 말씀으로 만들지 않습니다.";
        static GospelDialogueTurn Summary(string text,string portrait="teacher") => new GospelDialogueTurn("복음서의 이야기",portrait,text);
        static GospelDialogueTurn Direction(string name,string portrait,string text) => new GospelDialogueTurn(name,portrait,text,false,true);
        static GospelDialogueTurn Quote(GospelReading reading,string portrait="teacher") => new GospelDialogueTurn("성경의 기록",portrait,reading.Text,true);
        static GospelReading Reading(string id)
        {
            foreach(var reading in GospelChronicleScripture.Readings)if(reading.Id==id)return reading;
            return GospelStudyCatalog.GetReading(id);
        }
        static GospelChronicleQuest Birth(string id,string summary,string portrait="mary")
        {
            var r=Reading(id);
            return new GospelChronicleQuest("birth-"+id,"birth",r.Title,"탄생에서 이어지는 이야기를 따라가세요.","narrator","복음서의 이야기",portrait,0,r,Summary(summary,portrait),Quote(r,portrait));
        }
        static GospelChronicleQuest World(string id,string chapter,string title,string objective,string npc,string name,string portrait,float x,string reading,params GospelDialogueTurn[] dialogue)
            => new GospelChronicleQuest(id,chapter,title,objective,npc,name,portrait,x,reading==null?null:Reading(reading),dialogue);

        public static IReadOnlyList<GospelChronicleQuest> Quests { get; }=Array.AsReadOnly(new[] {
            Birth("road-bethlehem","누가는 호적 명령 때문에 요셉과 마리아가 나사렛에서 베들레헴으로 올라갔다고 전합니다. 탄생의 기록은 이 여행에서 시작됩니다.","joseph"),
            Birth("birth-manger","베들레헴에 있을 때 해산할 날이 차서 아기가 태어났습니다. 마리아는 아기를 강보로 싸서 구유에 뉘었습니다."),
            Birth("night-shepherds","그 지경에서 밤에 양 떼를 지키던 목자들 곁에 주의 사자가 나타났습니다. 평범하던 밤이 소식을 듣는 밤으로 바뀝니다.","teacher"),
            Birth("birth-good-news","두려워하는 목자들에게 천사는 큰 기쁨의 소식을 전합니다. 본문은 아기를 구주, 그리스도 주라고 부릅니다.","teacher"),
            Birth("manger-witnesses","목자들은 베들레헴으로 가서 아기를 찾고, 들었던 소식을 전했습니다. 듣고 찾아가 보고 알리는 행동이 이어집니다.","teacher"),
            Birth("birth-remembered","마리아는 들은 말을 마음에 지켜 생각했습니다. 목자들은 하나님께 영광을 돌리고 찬송하며 돌아갔습니다."),
            Birth("name-jesus","팔 일이 되어 아기의 이름을 예수라 하였습니다. 나중에 예수가 된 별개의 인물이 아니라, 탄생 때부터 이어지는 한 생애의 기록입니다."),
            Birth("temple-dedication","부모는 모세의 법을 따라 아기를 데리고 예루살렘으로 올라갔습니다. 아기 때의 성전 방문과 이후 열두 살의 방문은 서로 다른 사건입니다.","joseph"),
            Birth("simeon-peace","시므온은 아기를 안고 하나님을 찬송했습니다. 그의 찬송은 이방을 비추는 빛과 이스라엘의 영광을 말합니다.","teacher"),
            Birth("anna-thanksgiving","성전에는 안나도 있었습니다. 안나는 하나님께 감사하며 예루살렘의 구속을 바라는 사람들에게 아기에 관하여 말했습니다.","teacher"),
            Birth("nazareth-growth","가족은 나사렛으로 돌아갔고 아기는 자랐습니다. 그 사이의 모든 날은 기록되어 있지 않습니다. 다음 장에서 직접 움직이는 예수님은 열두 살입니다.","joseph"),
            World("nazareth-departure","temple","유월절 길을 준비하며","나사렛 길목에서 요셉과 출발 준비를 이야기하세요.","joseph","요셉","joseph",-27,null,
                Summary("누가는 부모가 해마다 유월절에 예루살렘으로 갔다고 기록합니다. 예수님이 열두 살이 되던 해, 그 절기의 전례를 따라 올라갑니다."),
                Direction("요셉","joseph","여행길에서는 함께 걷는 이들을 놓치지 않도록 살펴보자. 준비가 되면 샘가 길목에 있는 마리아에게 가 보렴.")),
            World("pilgrim-spring","temple","함께 오르는 길","샘가 길목으로 걸어가 마리아와 여정의 목적을 이야기하세요.","mary","마리아","mary",-12,null,
                Summary("이 여정의 목적은 유월절을 지키러 예루살렘에 올라가는 것입니다. 실제 이동 거리와 쉬는 장소는 성경에 상세히 기록되어 있지 않습니다."),
                Direction("마리아","mary","이 길을 지나면 성전 뜰로 이어진단다. 길을 잘 살피며 성전 길잡이가 있는 곳까지 가 보자.")),
            World("festival-courtyard","temple","예루살렘의 절기","성전 뜰의 길잡이에게 유월절의 기록을 들으세요.","temple-guide","성전 길잡이","teacher",2,"temple-passover",
                Summary("절기에 예루살렘으로 올라온 기록을 읽습니다. 절기의 날들이 지난 뒤, 부모는 예수님이 예루살렘에 머무셨다는 것을 알지 못하고 돌아갑니다."),
                Quote(Reading("temple-passover")),
                Summary("다음 장면은 절기가 지난 뒤의 성전입니다. 누가는 부모가 동행 중에 있는 줄로 생각했다가 예수님을 찾으러 돌아왔다고 전합니다.")),
            World("listening-court","temple","듣고 묻는 자리","회랑에서 성전의 선생을 만나 대화하세요.","teacher-listening","성전의 선생","teacher",11,null,
                Direction("성전의 선생","teacher","먼저 이야기를 듣고, 기록에 어떤 말이 남아 있는지 함께 살펴봅시다. 안쪽 선생들이 있는 자리로 오세요."),
                Summary("예수님이 구체적으로 어떤 질문을 하셨는지는 이 본문에 적혀 있지 않습니다. 새 질문을 예수님의 실제 말씀으로 대신하지 않고, 누가가 기록한 행동을 따라갑니다.")),
            World("teachers-circle","temple","선생들 가운데","안쪽 뜰의 율법 선생을 만나 성전의 이야기를 이어가세요.","teacher-reading","율법 선생","teacher",18,"temple-teachers",
                Summary("사흘 후 부모는 성전에서 예수님을 만났습니다. 예수님은 선생들 가운데 앉아 듣기도 하시고 묻기도 하셨습니다."),
                Quote(Reading("temple-teachers")),
                Summary("듣는 사람들은 그 지혜와 대답을 기이하게 여겼습니다. 이제 부모가 예수님을 찾은 자리로 갑니다.")),
            World("parents-reunite","temple","근심 끝의 만남","성전으로 찾아온 부모와 함께 마리아의 말을 들으세요.","mary","마리아","mary",25,"temple-parents",
                GospelConversations.ForReading("temple-parents").ToArray()),
            World("nazareth-return","temple","나사렛으로 함께","귀향길의 요셉을 만나 성장의 기록을 간직하세요.","joseph","요셉","joseph",34,"temple-nazareth",
                Quote(Reading("temple-nazareth"),"joseph"),
                Summary("예수님은 부모와 함께 나사렛으로 내려가 순종하여 받드셨습니다. 성경은 성장하셨다고 전하지만 이후의 모든 해를 상세히 기록하지 않습니다."),
                Summary("다음 장은 공생애의 시작 무렵 요단에서 이어집니다. 누가가 말하는 나이는 '삼십세쯤'입니다. 기록되지 않은 세월을 임의의 사건으로 채우지 않습니다.")),
            World("adult-jordan-road","baptism","요단으로 향하는 길","성인이 된 예수님으로 요단 길목의 안내자를 만나세요.","jordan-guide","요단 길잡이","teacher",-26,null,
                Summary("이제 공생애가 시작되는 무렵입니다. 마태는 예수님이 갈릴리에서 요단강으로 와서 요한에게 세례를 받으려 하셨다고 전합니다."),
                Direction("요단 길잡이","teacher","강가에 세례 요한이 있습니다. 나무 그늘을 지나 강가의 만남으로 걸어가 보세요.")),
            World("john-calling","baptism","요단에서 들리는 외침","요단 부근에서 세례 요한의 사역에 관한 기록을 들으세요.","john-baptist","세례 요한","teacher",-12,"john-jordan",
                Summary("누가는 하나님의 말씀이 빈 들에서 요한에게 임했다고 기록합니다. 요한은 요단강 부근에서 회개의 세례를 전파합니다."),
                Quote(Reading("john-jordan"))),
            World("baptism-request","baptism","모든 의를 이루는 길","세례 자리에서 요한을 만나 이야기를 이어가세요.","john-baptist","세례 요한","teacher",2,"baptism-request",
                Summary("요한은 자신이 예수님께 세례를 받아야 한다고 말하며 만류합니다. 예수님의 대답과 요한의 허락을 마태복음의 문장 그대로 읽습니다."),
                Quote(Reading("baptism-request"),"jesus")),
            World("baptism-water","baptism","물에서 올라오시다","강가의 다음 만남에서 세례 후의 기록을 살펴보세요.","jordan-witness","강가의 기록 안내자","teacher",19,"baptism-water",
                Summary("마태는 예수님이 세례를 받으시고 물에서 올라오실 때의 일을 전합니다. 여기서는 마태복음의 하늘 음성을 다른 복음서의 표현과 섞지 않습니다."),
                Quote(Reading("baptism-water"),"jesus")),
            World("ministry-beginning","baptism","공생애의 문턱","강가 길 끝에서 공생애 시작의 나이를 기록한 말씀을 발견하세요.","journey-narrator","여정의 기록자","teacher",34,"ministry-thirty",
                Summary("누가는 예수님이 가르치심을 시작할 때 삼십세쯤 되셨다고 기록합니다. 이는 대략적인 나이이며 세례 날의 정확한 생일을 알려 주는 문장은 아닙니다."),
                Quote(Reading("ministry-thirty"),"jesus"),
                Summary("이번 여정은 요단의 세례와 공생애의 시작에서 마칩니다. 이후의 사역·십자가·부활·승천은 이번 장에 포함되지 않습니다. 발견한 말씀은 성경 책에 남아 다시 읽을 수 있습니다."))
        });

        public static IReadOnlyList<GospelReading> Readings { get; }=Quests.Where(q=>q.Reading!=null).Select(q=>q.Reading).ToList().AsReadOnly();
        public static GospelReading GetReading(string id) => Readings.FirstOrDefault(r=>r.Id==id)??throw new ArgumentException("알 수 없는 생애 말씀: "+id);
    }
}
