#include "DawnGospelGameMode.h"
#include "DawnGospelCharacter.h"
#include "DawnGospelController.h"

ADawnGospelGameMode::ADawnGospelGameMode()
{
    DefaultPawnClass = ADawnGospelCharacter::StaticClass();
    PlayerControllerClass = ADawnGospelController::StaticClass();
}
