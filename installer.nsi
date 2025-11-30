!include "LogicLib.nsh"
!include "MUI2.nsh"
!define MUI_ICON "Icon.ico"
!define MUI_UNICON "Icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "inslogo.bmp"

Outfile "PixelScript+ Setup.exe"
Name "PixelScript+ V1.4"
InstallDir "$PROGRAMFILES\PixelScript+"
RequestExecutionLevel admin

; --- Modern UI Pages ---
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "Licence.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch PixelScript+"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchPixelScript
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; --- Language Files ---
!insertmacro MUI_LANGUAGE "English"

Section "Install"
    SetOutPath "$INSTDIR"
    File "dist\PixelScript.exe"
    File "Licence.txt"
    WriteUninstaller "$INSTDIR\\Uninstall.exe"
    CreateShortCut "$DESKTOP\PixelScript+.lnk" "$INSTDIR\PixelScript.exe"
SectionEnd

!include "nsDialogs.nsh"

Section "Uninstall"
    Delete "$INSTDIR\PixelScript.exe"
    Delete "$INSTDIR\Licence.txt"
    Delete "$DESKTOP\PixelScript+.lnk"
    RMDir "$INSTDIR"
SectionEnd

Function LaunchPixelScript
    Exec "$INSTDIR\PixelScript.exe"
FunctionEnd

