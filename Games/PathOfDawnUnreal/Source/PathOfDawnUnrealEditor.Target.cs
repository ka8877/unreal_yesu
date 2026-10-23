using UnrealBuildTool;
public class PathOfDawnUnrealEditorTarget : TargetRules
{
    public PathOfDawnUnrealEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        // Match UnrealEditor instead of overriding its shared build products.
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("PathOfDawnUnreal");
        ExtraModuleNames.Add("PathOfDawnUnrealEditor");
    }
}
