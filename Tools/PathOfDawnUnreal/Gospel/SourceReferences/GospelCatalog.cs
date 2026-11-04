using System;
using System.Collections.Generic;

namespace PathOfDawn.Core
{
    public sealed class GospelReading
    {
        public string Id { get; }
        public string Title { get; }
        public string Reference { get; }
        public string Text { get; }
        public string Context { get; }
        public string Translation => "개역한글";
        readonly string sourceUrl;
        public string SourceUrl => string.IsNullOrEmpty(sourceUrl) ? GospelCatalog.ScriptureSource : sourceUrl;
        public GospelReading(string id, string title, string reference, string text, string context, string sourceUrl = null)
        { Id = id; Title = title; Reference = reference; Text = text; Context = context; this.sourceUrl = sourceUrl; }
    }

    public sealed class GospelObjective
    {
        public string Id { get; }
        public string Title { get; }
        public string Prompt { get; }
        public string ReadingId { get; }
        public GospelObjective(string id, string title, string prompt, string readingId)
        { Id = id; Title = title; Prompt = prompt; ReadingId = readingId; }
    }

    public sealed class GospelEpisode
    {
        public string Id { get; }
        public string Title { get; }
        public string Reference { get; }
        public string AgeLabel { get; }
        public bool IsPlayable { get; }
        public GospelEpisode(string id, string title, string reference, string ageLabel, bool playable = false)
        { Id = id; Title = title; Reference = reference; AgeLabel = ageLabel; IsPlayable = playable; }
    }

    /// <summary>Scripture quotations and game instructions are separate, explicitly named fields.</summary>
    public static class GospelCatalog
    {
        public const string ScriptureSource = "https://www.bskorea.or.kr/bible/korbibReadpage.php?version=HAN&book=luk&chap=2";
        public const string Attribution = "성경전서 개역한글판 · 대한성서공회";
        public const string ChronologyNote = "복음서의 기록을 함께 살펴보기 위한 장 순서입니다. 각 복음서의 배열 차이와 기록되지 않은 이동·건축 세부는 성경 본문과 구분합니다.";

        static readonly GospelReading[] readings =
        {
            new GospelReading("birth-manger", "베들레헴의 탄생", "누가복음 2:6–7",
                "6 거기 있을 그 때에 해산할 날이 차서\n7 맏아들을 낳아 강보로 싸서 구유에 뉘었으니 이는 사관에 있을 곳이 없음이러라",
                "요셉과 마리아는 호적하러 나사렛에서 베들레헴으로 올라갑니다. 예수님의 탄생을 누가복음의 기록으로 따라갑니다."),
            new GospelReading("birth-good-news", "큰 기쁨의 소식", "누가복음 2:10–11",
                "10 천사가 이르되 무서워 말라 보라 내가 온 백성에게 미칠 큰 기쁨의 좋은 소식을 너희에게 전하노라\n11 오늘날 다윗의 동네에 너희를 위하여 구주가 나셨으니 곧 그리스도 주시니라",
                "목자들에게 탄생의 소식이 전해집니다. 구유의 아기를 찾아가는 기록은 누가복음 2:8–18에서 함께 읽을 수 있습니다."),
            new GospelReading("birth-remembered", "마음에 간직한 말씀", "누가복음 2:19–20",
                "19 마리아는 이 모든 말을 마음에 지키어 생각하니라\n20 목자가 자기들에게 이르던 바와 같이 듣고 본 그 모든 것을 인하여 하나님께 영광을 돌리고 찬송하며 돌아가니라",
                "탄생의 기록을 마치고 열두 살 예수님의 성전 방문으로 넘어갑니다. 이 구간에서 빠진 시간은 누가복음 2:21–40의 할례·성전 봉헌·나사렛에서의 성장 기록으로 연결됩니다."),
            new GospelReading("temple-passover", "유월절의 예루살렘", "누가복음 2:41–43",
                "41 그 부모가 해마다 유월절을 당하면 예루살렘으로 가더니\n42 예수께서 열 두살 될 때에 저희가 이 절기의 전례를 좇아 올라갔다가\n43 그 날들을 마치고 돌아갈 때에 아이 예수는 예루살렘에 머무셨더라 그 부모는 이를 알지 못하고",
                "열두 살 예수님은 유월절을 지키러 예루살렘에 올라오십니다. 성전 문으로 걸어가 이번 기록의 시작을 읽어 보세요."),
            new GospelReading("temple-teachers", "선생들 가운데", "누가복음 2:46–47",
                "46 사흘 후에 성전에서 만난즉 그가 선생들 중에 앉으사 저희에게 듣기도 하시며 묻기도 하시니\n47 듣는 자가 다 그 지혜와 대답을 기이히 여기더라",
                "부모는 예수님을 찾다가 사흘 후 성전에서 만납니다. 예수님은 선생들 가운데 앉아 듣기도 하시고 묻기도 하십니다. 앞선 찾음의 기록은 누가복음 2:44–45에 나옵니다."),
            new GospelReading("temple-parents", "내 아버지 집", "누가복음 2:48–50",
                "48 그 부모가 보고 놀라며 그 모친은 가로되 아이야 어찌하여 우리에게 이렇게 하였느냐 보라 네 아버지와 내가 근심하여 너를 찾았노라\n49 예수께서 가라사대 어찌하여 나를 찾으셨나이까 내가 내 아버지 집에 있어야 될 줄을 알지 못하셨나이까 하시니\n50 양친이 그 하신 말씀을 깨닫지 못하더라",
                "마리아는 근심하며 찾았던 마음을 전합니다. 예수님께서 말씀하신 내 아버지 집을 본문에서 살펴보세요."),
            new GospelReading("temple-nazareth", "나사렛으로", "누가복음 2:51–52",
                "51 예수께서 한가지로 내려가사 나사렛에 이르러 순종하여 받드시더라 그 모친은 이 모든 말을 마음에 두니라\n52 예수는 그 지혜와 그 키가 자라가며 하나님과 사람에게 더 사랑스러워 가시더라",
                "예수님은 부모와 함께 나사렛으로 내려가십니다. 돌아가는 길에서 첫 여정을 마치고, 읽은 말씀을 기록에서 다시 살펴보세요.")
        };

        public static IReadOnlyList<GospelReading> Readings { get; } = Array.AsReadOnly(readings);
        public static IReadOnlyList<GospelReading> PrologueReadings { get; } = Array.AsReadOnly(new[] { readings[0], readings[1], readings[2] });
        public static IReadOnlyList<GospelObjective> Objectives { get; } = Array.AsReadOnly(new[]
        {
            new GospelObjective("temple-gate", "성전으로 들어가기", "성전 문으로 걸어가 말씀을 읽으세요.", "temple-passover"),
            new GospelObjective("teachers", "선생들 가운데", "선생들이 있는 곳으로 가서 말씀을 읽으세요.", "temple-teachers"),
            new GospelObjective("parents", "부모와의 만남", "마리아와 요셉이 있는 곳에서 말씀을 읽으세요.", "temple-parents"),
            new GospelObjective("nazareth-gate", "나사렛으로 돌아가기", "나사렛으로 향하는 문에서 첫 여정을 마치세요.", "temple-nazareth")
        });
        public static IReadOnlyList<GospelEpisode> Episodes { get; } = Array.AsReadOnly(new[]
        {
            new GospelEpisode("birth", "예수님의 탄생", "눅 2:1–20 · 마 1:18–25", "탄생", true),
            new GospelEpisode("temple", "성전의 소년", "눅 2:41–52", "열두 살", true),
            new GospelEpisode("baptism", "요단강의 세례", "마 3:13–17 · 눅 3:21–23", "삼십 세쯤"),
            new GospelEpisode("wilderness", "광야의 시험", "마 4:1–11 · 눅 4:1–13", "공생애 시작"),
            new GospelEpisode("disciples", "제자들을 부르심", "요 1:35–51 · 막 1:16–20", "공생애"),
            new GospelEpisode("cana", "가나의 혼인 잔치", "요 2:1–11", "공생애"),
            new GospelEpisode("kingdom", "하나님 나라를 전하심", "막 1:14–15 · 눅 4:16–30", "공생애"),
            new GospelEpisode("sermon", "산 위의 가르침", "마 5–7장", "공생애"),
            new GospelEpisode("healing", "치유와 용서", "막 2:1–12", "공생애"),
            new GospelEpisode("parables", "비유로 가르치심", "마 13장", "공생애"),
            new GospelEpisode("feeding", "오천 명을 먹이심", "막 6:30–44 · 요 6:1–15", "공생애"),
            new GospelEpisode("sea", "물 위를 걸으심", "막 6:45–52", "공생애"),
            new GospelEpisode("confession", "베드로의 고백", "막 8:27–38", "공생애"),
            new GospelEpisode("transfiguration", "변화산", "막 9:2–13", "공생애"),
            new GospelEpisode("lazarus", "나사로를 살리심", "요 11:1–44", "예루살렘 입성 전"),
            new GospelEpisode("jerusalem", "예루살렘 입성", "마 21:1–11 · 요 12:12–19", "마지막 주간"),
            new GospelEpisode("temple-cleansing", "성전을 깨끗하게 하심", "막 11:15–19", "마지막 주간"),
            new GospelEpisode("supper", "마지막 만찬", "눅 22:7–20", "마지막 주간"),
            new GospelEpisode("gethsemane", "겟세마네의 기도와 체포", "눅 22:39–53", "수난"),
            new GospelEpisode("trial", "심문과 재판", "눅 22:54–23:25", "수난"),
            new GospelEpisode("cross", "십자가", "눅 23:26–49 · 요 19:16–30", "수난"),
            new GospelEpisode("burial", "무덤에 모심", "눅 23:50–56", "수난"),
            new GospelEpisode("resurrection", "부활의 아침", "눅 24:1–12 · 요 20:1–18", "부활"),
            new GospelEpisode("emmaus", "엠마오로 가는 길", "눅 24:13–35", "부활 이후"),
            new GospelEpisode("risen-disciples", "제자들에게 나타나심", "눅 24:36–49 · 요 21:1–23", "부활 이후"),
            new GospelEpisode("ascension", "승천", "눅 24:50–53 · 행 1:6–11", "부활 이후")
        });

        public static GospelReading GetReading(string id)
        {
            foreach (var reading in readings) if (reading.Id == id) return reading;
            throw new ArgumentException("알 수 없는 말씀 식별자입니다: " + id, nameof(id));
        }
    }
}
