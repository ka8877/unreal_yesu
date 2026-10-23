using UnrealBuildTool;
public class PathOfDawnUnrealTarget : TargetRules
{
    public PathOfDawnUnrealTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        // Match the installed UE 5.8 shared build environment.
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("PathOfDawnUnreal");
    }
}
