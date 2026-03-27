; ============================================================
;  Whisp — Inno Setup Script
;  Erstellt: whisp_setup.exe
;
;  Voraussetzungen zum Bauen:
;    1. Inno Setup 6+ installieren (jrsoftware.org/isdl.php)
;    2. whisp.ico in installer\assets\ kopieren
;    3. Diese Datei kompilieren: ISCC.exe whisp_setup.iss
;
;  Hinweis: Nutzt System-Python (py.exe) — kein Python bundeln nötig.
;  Empfehlung für Nutzer ohne Python: Python 3.11 vorher installieren.
; ============================================================

#define AppName    "Whisp"
#define AppVersion "1.0.0"
#define AppPublisher "Whisp"
#define AppURL     "https://whisp.app"
#define AppExeName "whisp_launcher.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=whisp_setup_{#AppVersion}
SetupIconFile=assets\whisp.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\assets\whisp.ico
DisableProgramGroupPage=yes

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked
Name: "autostart";   Description: "Whisp mit Windows starten";      GroupDescription: "Systemstart:"; Flags: unchecked

[Dirs]
Name: "{app}"
Name: "{app}\inference"
Name: "{app}\inference\assets"
Name: "{app}\assets"

[Files]
; App-Dateien
Source: "..\inference\overlay.py";         DestDir: "{app}\inference"
Source: "..\inference\settings.py";        DestDir: "{app}\inference"
Source: "..\inference\settings_window.py"; DestDir: "{app}\inference"
Source: "..\inference\dashboard.py";       DestDir: "{app}\inference"
Source: "..\inference\hf_login.py";        DestDir: "{app}\inference"
Source: "..\inference\server.py";          DestDir: "{app}\inference"
Source: "..\inference\requirements.txt";   DestDir: "{app}\inference"
Source: "..\inference\assets\whisp.ico";   DestDir: "{app}\inference\assets"
Source: "..\inference\assets\whisp.ico";   DestDir: "{app}\assets"

; Installer-Hilfsskripte
Source: "whisp_install.py";   DestDir: "{app}"
Source: "whisp_download.py";  DestDir: "{app}"

; Launcher
Source: "whisp_launcher.bat"; DestDir: "{app}"

[Icons]
Name: "{group}\Whisp";                       Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\whisp.ico"
Name: "{group}\{cm:UninstallProgram,Whisp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Whisp";                 Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\whisp.ico"; Tasks: desktopicon
Name: "{userstartup}\Whisp";                 Filename: "{app}\{#AppExeName}"; Tasks: autostart

[Run]
; venv erstellen + Dependencies installieren (nutzt System-Python via py.exe)
Filename: "py.exe"; \
    Parameters: "-3 ""{app}\whisp_install.py"" ""{app}"""; \
    WorkingDir: "{app}"; \
    StatusMsg: "Abhängigkeiten werden installiert (einmalig ~5 Min.)..."; \
    Flags: runhidden waituntilterminated

; Optional: Modell herunterladen
Filename: "{app}\inference\venv\Scripts\pythonw.exe"; \
    Parameters: """{app}\whisp_download.py"" ""{app}"""; \
    WorkingDir: "{app}"; \
    StatusMsg: "Cohere-Modell wird heruntergeladen (~4 GB)..."; \
    Flags: waituntilterminated; \
    Check: ShouldDownloadModel

; Whisp starten
Filename: "{app}\{#AppExeName}"; \
    Description: "Whisp jetzt starten"; \
    Flags: nowait postinstall skipifsilent shellexec

[Code]
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('py.exe', '-3 --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
            and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  if not IsPythonInstalled() then begin
    MsgBox(
      'Python 3 wurde nicht gefunden.' + #13#10 + #13#10 +
      'Bitte installiere Python 3.11 von python.org und führe dieses Setup erneut aus.' + #13#10 + #13#10 +
      'Wichtig: "Add Python to PATH" beim Installieren aktivieren!',
      mbError, MB_OK
    );
    Result := False;
  end else
    Result := True;
end;

function ShouldDownloadModel(): Boolean;
begin
  Result := MsgBox(
    'Soll das Cohere-Modell jetzt heruntergeladen werden?' + #13#10 +
    'Größe: ~4 GB — wird einmalig gespeichert.' + #13#10 + #13#10 +
    'Du kannst das auch später über das Tray-Menü nachholen.',
    mbConfirmation, MB_YESNO
  ) = IDYES;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    if MsgBox(
      'Sollen die heruntergeladenen Modelle (~4 GB) ebenfalls gelöscht werden?',
      mbConfirmation, MB_YESNO
    ) = IDYES then begin
      DelTree(ExpandConstant('{%USERPROFILE}\.cache\huggingface'), True, True, True);
    end;
  end;
end;
