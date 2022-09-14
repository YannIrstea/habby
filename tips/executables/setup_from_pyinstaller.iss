; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "HABBY"
#define MyAppVersion "1.5.5"
#define MyAppPublisher "INRAE EDF OFB"
#define MyAppURL "https://habby.wiki.inrae.fr/"
#define MyAppExeName "habby.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{7503A26E-B0AA-4E9A-A803-7698E8A6FD73}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=C:\habby_dev\habby\file_dep\Licence_CeCILL_V2.1-fr.txt
InfoBeforeFile=C:\habby_dev\habby\tips\executables\disclamer.txt
OutputDir=C:\habby_dev\habby\build\pyinstaller
OutputBaseFilename=HABBY-setup-64
Compression=lzma
SolidCompression=yes
ChangesAssociations=yes
SetupIconFile=C:\habby_dev\habby\file_dep\habby_icon.ico
UninstallDisplayIcon=C:\habby_dev\habby\file_dep\habby_icon.ico
PrivilegesRequiredOverridesAllowed=dialog


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "C:\habby_dev\habby\build\pyinstaller\habby\habby.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\habby_dev\habby\build\pyinstaller\habby\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{commonprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: ".habby";                             ValueData: "{#MyAppName}";          Flags: uninsdeletevalue; ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}";                     ValueData: "Program {#MyAppName}";  Flags: uninsdeletekey;   ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\DefaultIcon";             ValueData: "{app}\file_dep\habby_icon.ico";               ValueType: string;  ValueName: ""
Root: HKCR; Subkey: "{#MyAppName}\shell\open\command";  ValueData: """{app}\{#MyAppExeName}"" ""%1""";  ValueType: string;  ValueName: ""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\INRAE_EDF_OFB\HABBY\user_settings"

[InstallDelete]
Type: filesandordirs; Name: "{localappdata}\INRAE_EDF_OFB\HABBY\user_settings"
