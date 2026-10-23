using UnrealBuildTool;
public class PathOfDawnUnreal : ModuleRules
{
    public PathOfDawnUnreal(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        CppStandard = CppStandardVersion.Cpp20;
        PublicIncludePaths.Add(ModuleDirectory);
        PublicDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
            "UMG", "Slate", "SlateCore", "CinematicCamera", "LevelSequence", "MovieScene"
        });
        PrivateDependencyModuleNames.AddRange(new string[] { "Json", "JsonUtilities", "ApplicationCore" });
        // No editor-only dependencies in the runtime module.
    }
}
