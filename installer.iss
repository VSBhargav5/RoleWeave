; RoleWeave per-user Windows x64 delivery. Compile via build_installer.py.
#ifndef AppVersion
  #error AppVersion is required
#endif
[Setup]
AppId={{5E91607C-895F-4A78-B731-F05B0DA9E644}
AppName=RoleWeave
AppVersion={#AppVersion}
AppPublisher=Bhargav Vasireddy
DefaultDirName={localappdata}\Programs\RoleWeave
DefaultGroupName=RoleWeave
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=out
OutputBaseFilename=RoleWeave-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\RoleWeave.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
DisableProgramGroupPage=yes
[Files]
Source: "out\portable\RoleWeave\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\RoleWeave"; Filename: "{app}\RoleWeave.exe"
; No Run, UninstallDelete, or data-directory entries: launch is deliberate,
; and the application-managed LOCALAPPDATA\RoleWeave database is retained.
