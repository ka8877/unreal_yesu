using System;
using System.Collections.Generic;

namespace PathOfDawn.Core
{
    public sealed class GospelDialogueTurn
    {
        public string Speaker { get; }
        public string PortraitKey { get; }
        public string Text { get; }
        public bool IsVerbatim { get; }
        public bool IsDramatized { get; }
        public string Label => IsVerbatim ? "성경 직접 인용 · 개역한글" : IsDramatized ? "게임을 위한 극화 · 성경 직접 인용 아님" : "학습 안내 · 본문 요약";
        public GospelDialogueTurn(string speaker, string portrait, string text, bool verbatim = false, bool dramatized = false)
        { Speaker = speaker; PortraitKey = portrait; Text = text; IsVerbatim = verbatim; IsDramatized = !verbatim&&dramatized; }
    }

    /// <summary>Quoted speech is extracted from the existing verified passage, never invented.</summary>
    public static class GospelConversations
    {
        static GospelDialogueTurn Guide(string text, string portrait = "teacher", string speaker = "말씀 길잡이")
            => new GospelDialogueTurn(speaker, portrait, text);
        static GospelDialogueTurn Quote(string reading, int verse, string speaker, string portrait,
            string after = null, string before = null)
        {
            string prefix = verse + " ";
            foreach (string line in GospelCatalog.GetReading(reading).Text.Split('\n'))
                if (line.StartsWith(prefix, StringComparison.Ordinal))
                {
                    string value = line.Substring(prefix.Length);
                    if (after != null) value = value.Substring(value.IndexOf(after, StringComparison.Ordinal) + after.Length);
                    if (before != null) value = value.Substring(0, value.LastIndexOf(before, StringComparison.Ordinal));
                    return new GospelDialogueTurn(speaker, portrait, value, true);
                }
            throw new ArgumentException("Missing verified verse: " + reading + ":" + verse);
        }
        static readonly IReadOnlyDictionary<string, IReadOnlyList<GospelDialogueTurn>> conversations =
            new Dictionary<string, IReadOnlyList<GospelDialogueTurn>>
            {
                ["birth-manger"] = Array.AsReadOnly(new[] { Guide(GospelCatalog.GetReading("birth-manger").Context, "mary") }),
                ["birth-good-news"] = Array.AsReadOnly(new[] { Guide(GospelCatalog.GetReading("birth-good-news").Context, "joseph") }),
                ["birth-remembered"] = Array.AsReadOnly(new[] { Guide(GospelCatalog.GetReading("birth-remembered").Context, "mary") }),
                ["temple-passover"] = Array.AsReadOnly(new[] {
                    Guide("누가는 예수님의 부모가 해마다 유월절에 예루살렘으로 갔다고 기록합니다. 이번 여정의 예수님은 열두 살입니다.", "teacher", "성전 길잡이"),
                    Guide("절기를 마치고 돌아갈 때, 예수님은 예루살렘에 머무셨습니다. 부모는 이를 알지 못했습니다. 선생들이 있는 곳에서 다음 기록을 살펴보세요.", "teacher", "성전 길잡이") }),
                ["temple-teachers"] = Array.AsReadOnly(new[] {
                    Guide("부모는 예수님을 찾으러 예루살렘으로 돌아옵니다. 사흘 후 성전에서 만났을 때, 예수님은 선생들 가운데 앉아 계셨습니다.", "teacher", "율법 선생"),
                    Quote("temple-teachers",46,"복음서의 기록","teacher"),
                    Quote("temple-teachers",47,"복음서의 기록","jesus"),
                    Guide("어떤 질문과 대답이 오갔는지는 이 본문에 기록되어 있지 않습니다. 기록된 만남에 이어, 마리아와 예수님의 대화를 들어보세요.") }),
                ["temple-parents"] = Array.AsReadOnly(new[] {
                    Quote("temple-parents",48,"마리아","mary","그 모친은 가로되 "),
                    Quote("temple-parents",49,"예수님","jesus","예수께서 가라사대 "," 하시니"),
                    Quote("temple-parents",50,"복음서의 기록","joseph"),
                    Guide("예수님은 ‘내 아버지 집’을 말씀하셨습니다. 누가는 부모가 이 말씀을 깨닫지 못했다고 기록합니다. 이 대목을 지금 모두 이해했다고 바꾸지 않고 본문 그대로 기억해 보세요.","mary") }),
                ["temple-nazareth"] = Array.AsReadOnly(new[] {
                    Quote("temple-nazareth",51,"복음서의 기록","mary"),
                    Quote("temple-nazareth",52,"복음서의 기록","jesus"),
                    Guide("첫 여정은 여기에서 마칩니다. 나사렛에서 성장하신 이후의 세례와 공생애는 다음 장으로 이어질 예정입니다. 읽은 본문은 성경 기록에서 다시 볼 수 있습니다.","joseph") })
            };
        public static IReadOnlyList<GospelDialogueTurn> ForReading(string id)
            => conversations.TryGetValue(id, out var turns) ? turns : throw new ArgumentException("Unknown conversation: " + id);
    }
}
