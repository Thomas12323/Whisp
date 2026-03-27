# Whisp

Local speech-to-text overlay for Windows.

Lokales Speech-to-Text-Overlay fuer Windows.

## Deutsch

### Was ist Whisp?

Whisp ist ein lokales Diktier-Tool fuer Windows.  
Du haeltst `Ctrl + Shift + Space`, sprichst, laesst los, und Whisp fuegt den erkannten Text in die aktive Anwendung ein.

### Features

- vollstaendig lokal, keine Cloud
- Cohere Transcribe als Primaermodell
- faster-whisper als Backup
- globaler Hotkey fuer Aufnahme
- System-Tray fuer Modell, Sprache, Overlay-Position, Einstellungen und Autostart
- Live-Dashboard mit Mikrofonpegel, Status und Verlauf
- ZIP-Distribution statt `.exe`

### Voraussetzungen

- Windows 10 / 11
- Python 3.11
- bei der Installation "Add Python to PATH" aktivieren
- HuggingFace-Account fuer das Cohere-Modell
- ca. 4 GB freier Speicherplatz
- Mikrofon

### Installation

1. Die aktuelle ZIP aus den GitHub Releases herunterladen.
2. ZIP entpacken, z.B. nach `C:\Whisp`.
3. `setup.bat` ausfuehren.
4. Den HuggingFace-Login bzw. Token-Schritt abschliessen.
5. Whisp mit `overlay.bat` starten.

### Benutzung

- `Ctrl + Shift + Space` halten, um die Aufnahme zu starten
- `Space` loslassen, um die Aufnahme zu beenden
- Whisp transkribiert und fuegt den Text in das aktive Fenster ein

Funktioniert gut in Word, Outlook, Teams, Browser-Feldern, Notepad und VS Code.

### Updates

Du musst nichts deinstallieren.

Normales Update:

1. Neue ZIP herunterladen
2. Alte Dateien durch die neuen ersetzen
3. Whisp wieder mit `overlay.bat` starten

Falls sich Python-Abhaengigkeiten geaendert haben:

1. Dateien ersetzen
2. `setup.bat` nochmal ausfuehren
3. Danach `overlay.bat` starten

## English

### What is Whisp?

Whisp is a local dictation tool for Windows.  
Hold `Ctrl + Shift + Space`, speak, release the key, and Whisp inserts the transcribed text into the active app.

### Features

- fully local processing
- Cohere Transcribe as primary model
- faster-whisper as backup model
- global hotkey for recording
- system tray controls for model, language, overlay position, settings, and autostart
- live dashboard with microphone level, status, and transcription history
- ZIP-based distribution instead of `.exe`

### Requirements

- Windows 10 / 11
- Python 3.11
- "Add Python to PATH" enabled during installation
- HuggingFace account for the Cohere model
- about 4 GB free disk space
- microphone

### Installation

1. Download the latest ZIP from GitHub Releases.
2. Extract it somewhere, for example `C:\Whisp`.
3. Run `setup.bat`.
4. Complete the HuggingFace login/token step.
5. Start Whisp with `overlay.bat`.

### Usage

- Hold `Ctrl + Shift + Space` to start recording
- Release `Space` to stop recording
- Whisp transcribes and pastes the text into the active window

Works well in Word, Outlook, Teams, browser text fields, Notepad, and VS Code.

### Updating

You do not need to uninstall anything.

Normal update:

1. Download the new ZIP
2. Replace the old files with the new ones
3. Start Whisp again with `overlay.bat`

If Python dependencies changed:

1. Replace the files
2. Run `setup.bat` again
3. Start Whisp with `overlay.bat`

## Notes

- The first start can take longer because models may need to be downloaded or loaded.
- The tray menu is the main control center in everyday use.
- `setup.bat` is for setup and dependency refresh, not for every normal start.
