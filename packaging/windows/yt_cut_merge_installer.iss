#define MyAppName "YT Cut Merge GUI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Antonio Fiumara"
#define MyAppExeName "yt_cut_merge_gui.exe"

[Setup]
AppId={{9A86C0B5-5D85-4A1B-B5F7-0EACB9F0E111}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=yt_cut_merge_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Icone aggiuntive:"; Flags: unchecked

[Dirs]
Name: "{app}\video"

[Files]
Source: "dist\yt_cut_merge_gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Apri cartella video"; Filename: "explorer.exe"; Parameters: """{app}\video"""
Name: "{autoprograms}\{#MyAppName}\Apri cartella tools"; Filename: "explorer.exe"; Parameters: """{app}\tools"""
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia {#MyAppName}"; Flags: nowait postinstall skipifsilent
