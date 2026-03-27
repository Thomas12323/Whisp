# Whisp

Local speech-to-text overlay for Windows with a global hotkey, tray controls, live microphone monitoring, and ZIP-based releases.

Lokales Speech-to-Text-Overlay fuer Windows mit globalem Hotkey, Tray-Steuerung, Live-Mikrofonanzeige und ZIP-basierten Releases.

## English

### What is Whisp?

Whisp is a local dictation tool for Windows.

You hold `Ctrl + Shift + Space`, speak, release the key, and Whisp inserts the transcribed text into the active app.

Main features:

- fully local processing
- Cohere Transcribe as primary model
- faster-whisper as backup model
- system tray controls for model, language, overlay position, settings, and autostart
- live dashboard with microphone level, status, and transcription history
- ZIP-based distribution instead of `.exe`, to avoid Smart App Control blocking

### Requirements

- Windows 10 / 11
- Python 3.11
- "Add Python to PATH" enabled during installation
- HuggingFace account for the gated Cohere model
- about 4 GB free disk space for the first model download
- microphone

### Installation

1. Download the latest ZIP from GitHub Releases
2. Extract it somewhere, for example `C:\Whisp`
3. Run `setup.bat`
4. Follow the HuggingFace login/token steps
5. Start Whisp with `overlay.bat`

### Usage

- Hold `Ctrl + Shift + Space` to start recording
- Release `Space` to stop recording
- Whisp transcribes and pastes the text into the active window

Works well in apps like Word, Outlook, Teams, browser text fields, Notepad, and VS Code.

### Updating

There is no installer to remove.

For most updates:

1. Download the new ZIP
2. Replace the old files with the new ones
3. Start Whisp again with `overlay.bat`

If dependencies changed:

1. Replace the files
2. Run `setup.bat` again
3. Start Whisp with `overlay.bat`

### Release workflow

Create a release ZIP locally:

```bat
release.bat 1.0.0
```

Then tag and push:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Upload the generated ZIP from `dist\` to GitHub Releases.

## Deutsch

### Was ist Whisp?

Whisp ist ein lokales Diktier-Tool fuer Windows.

Du haeltst `Ctrl + Shift + Space`, sprichst, laesst los, und Whisp fuegt den erkannten Text in die aktive Anwendung ein.

Wichtige Funktionen:

- vollstaendig lokale Verarbeitung
- Cohere Transcribe als Primaermodell
- faster-whisper als Backup
- System-Tray fuer Modell, Sprache, Overlay-Position, Einstellungen und Autostart
- Live-Dashboard mit Mikrofonpegel, Status und Verlauf
- ZIP-Distribution statt `.exe`, damit Windows Smart App Control nichts blockiert

### Voraussetzungen

- Windows 10 / 11
- Python 3.11
- bei der Installation "Add Python to PATH" aktivieren
- HuggingFace-Account fuer das geschuetzte Cohere-Modell
- ca. 4 GB freier Speicher fuer den ersten Model-Download
- Mikrofon

### Installation

1. Die aktuelle ZIP aus den GitHub Releases herunterladen
2. ZIP entpacken, z.B. nach `C:\Whisp`
3. `setup.bat` ausfuehren
4. Den HuggingFace-Login bzw. Token-Schritt abschliessen
5. Whisp mit `overlay.bat` starten

### Benutzung

- `Ctrl + Shift + Space` halten, um die Aufnahme zu starten
- `Space` loslassen, um die Aufnahme zu beenden
- Whisp transkribiert und fuegt den Text in das aktive Fenster ein

Funktioniert gut in Word, Outlook, Teams, Browser-Feldern, Notepad und VS Code.

### Updates

Du musst nichts deinstallieren.

Fuer die meisten Updates gilt:

1. neue ZIP herunterladen
2. alte Dateien durch die neuen ersetzen
3. Whisp wieder mit `overlay.bat` starten

Falls sich Python-Abhaengigkeiten geaendert haben:

1. Dateien ersetzen
2. `setup.bat` nochmal ausfuehren
3. danach `overlay.bat` starten

### Release-Workflow

Release-ZIP lokal bauen:

```bat
release.bat 1.0.0
```

Danach taggen und pushen:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Die ZIP aus `dist\` anschliessend in GitHub Releases hochladen.

## Notes

- The first start can take longer because models may be loaded or downloaded.
- The tray menu is the main control center for everyday use.
- `setup.bat` is for setup and dependency refresh, not for every normal start.
