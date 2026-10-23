using UnrealBuildTool;
public class PathOfDawnUnrealEditor : ModuleRules
{
    public PathOfDawnUnrealEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "PathOfDawnUnreal" });
        PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "AssetRegistry", "SlateCore" });
    }
}
