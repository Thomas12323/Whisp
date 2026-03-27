# Whisp Overlay

Systemweites Diktierwerkzeug fuer Windows. Laeuft vollstaendig lokal, ohne Cloud, ohne dass Daten den PC verlassen.

**Primaermodell:** [Cohere Transcribe](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026) (2B Parameter, Apache 2.0)  
**Backup:** `faster-whisper`

## Release-Modell

Whisp wird ueber **GitHub Releases als ZIP** verteilt.

Es gibt bewusst **keinen `.exe`-Installer mehr**, weil Windows Smart App Control den unsignierten Installer blockiert hat. Der empfohlene Endnutzerpfad ist deshalb:

1. ZIP aus GitHub Releases herunterladen
2. ZIP entpacken
3. `setup.bat` einmal ausfuehren
4. danach `overlay.bat` starten

Der Ordner `installer/` ist nur noch Altbestand aus dem verworfenen EXE-Ansatz und wird fuer normale Releases nicht mehr benoetigt.

## Voraussetzungen

- Windows 10 / 11
- Python 3.11 von [python.org/downloads](https://www.python.org/downloads/)
- Bei der Installation unbedingt **"Add Python to PATH"** aktivieren
- HuggingFace-Account von [huggingface.co/join](https://huggingface.co/join)
- Ca. 4 GB freier Speicherplatz fuer das Cohere-Modell
- Mikrofon

## Installation

1. ZIP entpacken, z.B. nach `C:\Whisp`
2. `setup.bat` starten
3. Beim HuggingFace-Schritt:
   - [Cohere-Modellseite](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026) oeffnen
   - "Access repository" bestaetigen
   - [Token-Seite](https://huggingface.co/settings/tokens) oeffnen
   - Read-Token erzeugen
   - Token im Setup eingeben

## Starten

`overlay.bat` starten.

Beim ersten Start wird das Cohere-Modell einmalig heruntergeladen. Danach erscheint unten am Bildschirm sinngemaess:

> Whisp bereit (cohere)

Ab dann laeuft Whisp im System-Tray.

## Bedienung

| Aktion | Beschreibung |
|---|---|
| `Ctrl` + `Shift` + `Space` halten | Aufnahme startet |
| `Space` loslassen | Aufnahme stoppt, Transkription laeuft |
| Automatisch | Text wird ins aktive Fenster eingefuegt |

Funktioniert in Word, Outlook, Teams, Browsern, Notepad, VS Code und allgemein ueberall dort, wo man tippen kann.

## Gesprochene Satzzeichen

| Gesprochen | Ergebnis |
|---|---|
| `Komma` | `,` |
| `Punkt` | `.` |
| `Fragezeichen` | `?` |
| `Ausrufezeichen` | `!` |
| `Doppelpunkt` | `:` |
| `Neue Zeile` | Zeilenumbruch |
| `Neuer Absatz` | Absatz |

## Tray-Menue

```text
Modell    >  Cohere Transcribe
            faster-whisper

Sprache   >  Auto-Erkennung
            Deutsch
            Englisch
            Spanisch
            Franzoesisch
            Italienisch

Autostart
Dashboard oeffnen
Einstellungen
Beenden
```

## GitHub Release bauen

```bat
release.bat 1.0.0
git tag v1.0.0
git push origin v1.0.0
```

Die ZIP in `dist/` ist das Artefakt fuer GitHub Releases.

## Entwicklerhinweis

Die Next.js-App in `src/` und der lokale Server in `inference/server.py` sind Entwicklungs- und Vergleichswerkzeuge. Fuer normale Tester reicht der ZIP-Pfad mit `setup.bat` und `overlay.bat`.

## Fehlersuche

**Overlay erscheint nicht / kein Text wird eingefuegt**

- Konsolenfenster pruefen
- `overlay.bat` verwenden, nicht direkt `overlay.py`

**Cohere wird nicht geladen**

- Login pruefen:
  `inference\venv\Scripts\python -c "from huggingface_hub import whoami; print(whoami())"`
- Zugriff auf das Cohere-Modell auf HuggingFace akzeptieren

**Hotkey reagiert nicht**

- pruefen, ob ein anderes Programm `Ctrl+Shift+Space` belegt
- kurz in Notepad testen
