#include "DawnGameMode.h"
#include "DawnPlayerCharacter.h"
#include "DawnPlayerController.h"

ADawnGameMode::ADawnGameMode()
{
    DefaultPawnClass = ADawnPlayerCharacter::StaticClass();
    PlayerControllerClass = ADawnPlayerController::StaticClass();
}
