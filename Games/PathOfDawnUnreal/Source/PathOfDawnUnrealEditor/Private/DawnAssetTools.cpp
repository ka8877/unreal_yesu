#include "DawnAssetTools.h"
#include "DawnNarrativeData.h"
#include "Engine/Font.h"
#include "Engine/FontFace.h"
#include "Fonts/CompositeFont.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "Modules/ModuleManager.h"
IMPLEMENT_MODULE(FDefaultModuleImpl, PathOfDawnUnrealEditor)

UFont* UDawnAssetTools::CreateCompositeFont(UFontFace* Face, const FString& PackagePath)
{
    if (!Face || !FPackageName::IsValidLongPackageName(PackagePath)) return nullptr;
    const FString Name = FPackageName::GetLongPackageAssetName(PackagePath);
    if (UFont* Existing = LoadObject<UFont>(nullptr, *(PackagePath + TEXT(".") + Name))) return Existing;
    // Do not overwrite any existing package (including an asset of the wrong type).
    if (FPackageName::DoesPackageExist(PackagePath)) return nullptr;
    UPackage* Package = CreatePackage(*PackagePath);
    UFont* Font = NewObject<UFont>(Package, *Name, RF_Public | RF_Standalone);
    Font->FontCacheType = EFontCacheType::Runtime;
    FTypefaceEntry RegularTypeface;
    RegularTypeface.Name = FName(TEXT("Regular"));
    RegularTypeface.Font = FFontData(Face, 0);
    Font->GetMutableInternalCompositeFont().DefaultTypeface.Fonts.Add(MoveTemp(RegularTypeface));
    FAssetRegistryModule::AssetCreated(Font);
    Font->MarkPackageDirty();
    FSavePackageArgs Args;
    Args.TopLevelFlags = RF_Public | RF_Standalone;
    Args.SaveFlags = SAVE_NoError;
    const FString Filename = FPackageName::LongPackageNameToFilename(PackagePath, FPackageName::GetAssetPackageExtension());
    return UPackage::SavePackage(Package, Font, *Filename, Args) ? Font : nullptr;
}
FString UDawnAssetTools::ValidateNarrative(UDawnNarrativeData* Data)
{
    if (!Data) return TEXT("Narrative data asset is null");
    FString Error;
    Data->Validate(Error);
    return Error;
}

FText UDawnAssetTools::LocalizedText(const FString& Key, const FString& Value)
{
    return FText::ChangeKey(TEXT("PathOfDawn"), Key, FText::FromString(Value));
}

bool UDawnAssetTools::HasRuntimeFont(UFont* Font)
{
    return Font && Font->FontCacheType == EFontCacheType::Runtime && Font->GetInternalCompositeFont().DefaultTypeface.Fonts.Num() > 0;
}
