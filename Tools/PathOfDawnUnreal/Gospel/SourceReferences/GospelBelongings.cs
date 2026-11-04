using System;
using System.Collections.Generic;

namespace PathOfDawn.Core
{
    public sealed class GospelBelonging
    {
        public readonly string Id, Name, Category, Description, Detail;
        public GospelBelonging(string id,string name,string category,string description,string detail)
        {Id=id;Name=name;Category=category;Description=description;Detail=detail;}
    }

    /// <summary>Game props for exploring the learning space; never additional biblical testimony.</summary>
    public static class GospelBelongings
    {
        public const string LampId="travel-lamp";
        public static IReadOnlyList<GospelBelonging> All { get; }=Array.AsReadOnly(new[] {
            new GospelBelonging("linen-tunic","아마포 튜닉","의복 · 착용 중","가볍고 넉넉한 여행용 튜닉.","현재 인물의 의상입니다. 전투 능력치나 성경 사건에 영향을 주지 않습니다."),
            new GospelBelonging("leather-sandals","가죽 샌들","신발 · 착용 중","돌바닥과 흙길을 걷는 데 쓰는 샌들.","걷기·달리기·점프는 실제 이동 조작에 연결됩니다. Shift로 달리고 Space로 점프합니다."),
            new GospelBelonging("water-skin","여행 물주머니","여행 소품","가죽끈을 묶어 휴대하는 작은 물주머니.","이 체험판은 성경을 따라 걷는 학습 여정입니다. 갈증 수치나 소모 효과는 없습니다."),
            new GospelBelonging(LampId,"토기 등잔","장착 가능한 도구","기름과 심지를 담는 작고 따뜻한 불빛.","켜면 인물 앞에 실제 등잔과 불빛이 나타납니다. 장착 여부는 현재 여정에 저장됩니다."),
            new GospelBelonging("reading-notes","말씀 수첩","학습 도구","지금까지 읽은 말씀을 모아 보는 수첩.","읽기를 마친 본문만 말씀 기록에 남습니다. 수첩을 열어 정확한 구절을 다시 읽을 수 있습니다."),
            new GospelBelonging("courtyard-map","성전의 뜰 안내도","학습 도구","현재 위치와 다음 대화 장소를 표시하는 안내도.","게임 속 이동을 돕는 개략도입니다. 성전의 고고학적 실측 복원도는 아닙니다.")
        });
        public static GospelBelonging Find(string id)
        {foreach(var item in All)if(item.Id==id)return item;throw new ArgumentException("알 수 없는 소지품입니다.",nameof(id));}
        public static bool IsValidUtility(string id)=>string.IsNullOrEmpty(id)||id==LampId;
    }
}
