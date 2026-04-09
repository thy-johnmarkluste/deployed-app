; ThyWeb installer for PyInstaller onedir outputs
; Expected build folders:
;   dist\ThyWeb\ThyWeb.exe
;   dist\ThyWebSetup\ThyWebSetup.exe (optional)

[Setup]
AppId={{2E0C45C6-9A43-4F4E-95F7-7D67E7D9E2A1}
AppName=ThyWeb
AppVersion=1.0.1
AppPublisher=ThyWeb
DefaultDirName={autopf}\ThyWeb
DefaultGroupName=ThyWeb
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=ThyWeb-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\ThyWeb\ThyWeb.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Main app (required)
Source: "dist\ThyWeb\*"; DestDir: "{app}\ThyWeb"; Flags: recursesubdirs createallsubdirs ignoreversion
; Runtime env file (optional)
Source: ".env"; DestDir: "{app}\ThyWeb"; Flags: ignoreversion skipifsourcedoesntexist
; Setup utility app (optional) - comment out if not built
Source: "dist\ThyWebSetup\*"; DestDir: "{app}\ThyWebSetup"; Flags: recursesubdirs createallsubdirs ignoreversion skipifsourcedoesntexist
Source: ".env"; DestDir: "{app}\ThyWebSetup"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\ThyWeb\ThyWeb"; Filename: "{app}\ThyWeb\ThyWeb.exe"
Name: "{autoprograms}\ThyWeb\ThyWeb Setup"; Filename: "{app}\ThyWebSetup\ThyWebSetup.exe"; Check: FileExists(ExpandConstant('{app}\ThyWebSetup\ThyWebSetup.exe'))
Name: "{autodesktop}\ThyWeb"; Filename: "{app}\ThyWeb\ThyWeb.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ThyWebSetup\ThyWebSetup.exe"; Description: "Run first-time setup"; Flags: nowait postinstall skipifsilent; Check: FileExists(ExpandConstant('{app}\ThyWebSetup\ThyWebSetup.exe'))
Filename: "{app}\ThyWeb\ThyWeb.exe"; Description: "Launch ThyWeb"; Flags: nowait postinstall skipifsilent; Check: not FileExists(ExpandConstant('{app}\ThyWebSetup\ThyWebSetup.exe'))

[UninstallDelete]
Type: filesandordirs; Name: "{app}\ThyWeb"
Type: filesandordirs; Name: "{app}\ThyWebSetup"
