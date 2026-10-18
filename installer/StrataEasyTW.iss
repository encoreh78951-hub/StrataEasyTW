; Candidate release. Installs only this guide, never deletes Strata or models.
#define AppVersion "1.3.0-rc1"
[Setup]
AppId={{02A55F2E-FF41-45AE-95AB-9CE735F96AC9}
AppName=Strata Easy TW（非官方）
AppVersion={#AppVersion}
AppPublisher=Strata Easy TW contributors
DefaultDirName={localappdata}\Programs\StrataEasyTW
DefaultGroupName=Strata Easy TW
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\release
OutputBaseFilename=StrataEasyTW-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
InfoBeforeFile=release-notice.txt
UninstallDisplayIcon={app}\StrataEasyTW.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "zhTW"; MessagesFile: "ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; GroupDescription: "捷徑"; Flags: unchecked

[Files]
Source: "..\dist\StrataEasyTW\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Strata Easy TW"; Filename: "{app}\StrataEasyTW.exe"
Name: "{group}\離線展示"; Filename: "{app}\StrataEasyTW.exe"; Parameters: "--demo"
Name: "{autodesktop}\Strata Easy TW"; Filename: "{app}\StrataEasyTW.exe"; Tasks: desktopicon
Name: "{group}\解除安裝導覽器"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\StrataEasyTW.exe"; Parameters: "--demo"; Description: "開啟離線展示（不安裝模型）"; Flags: nowait postinstall skipifsilent unchecked

[CustomMessages]
zhTW.UninstallProgram=解除安裝 %1
