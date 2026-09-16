#define MyAppName "Crelabel"
#define MyAppVersion "0.8.13"
#define MyAppPublisher "Prime Hand"
#define MyAppExeName "Crelabel.exe"

[Setup]
AppId={{F02E1B70-79DB-49DB-86C9-DBA5F043793A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Crelabel
DefaultGroupName=Crelabel
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=Crelabel-Setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=crelabel.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "drivers\NiimbotPrinterDriverInstaller-3.0.2.1.exe"; DestDir: "{app}\drivers"; Flags: ignoreversion
Source: "fonts\led_board-7.ttf"; DestDir: "{app}\fonts"; Flags: ignoreversion
Source: "assets\prime-logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\prime-logo.svg"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "dist\Crelabel.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Crelabel-Quick-Guide.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "vendor\lark-cli\lark-cli.exe"; DestDir: "{app}\runtime"; Flags: ignoreversion
Source: "vendor\lark-cli\LICENSE"; DestDir: "{app}\runtime"; DestName: "LARK_CLI_LICENSE.txt"; Flags: ignoreversion
Source: "drivers\ZebraDriverSetup.exe"; DestDir: "{app}\drivers"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\Crelabel"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Crelabel"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 Crelabel"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\drivers"
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\fonts"
Type: filesandordirs; Name: "{app}\assets"
