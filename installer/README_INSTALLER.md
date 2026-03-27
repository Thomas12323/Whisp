# Whisp Installer bauen

## Einmalige Vorbereitung

### 1. Inno Setup installieren
https://jrsoftware.org/isdl.php → kostenlos, ~5 MB

### 2. Python Embeddable herunterladen
https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip

ZIP entpacken nach: `installer/python/`

### 3. Icon + Grafiken kopieren
```
copy inference\assets\whisp.ico installer\assets\whisp.ico
```

Für die Installer-Grafiken (optional, sonst Standard-Inno-Look):
- `installer/assets/logo_installer.bmp` — 164×314 px (linke Seite im Wizard)
- `installer/assets/logo_small.bmp`    — 55×55 px (oben rechts)

### 4. Installer bauen
Inno Setup öffnen → `installer/whisp_setup.iss` öffnen → Compile (F9)

Output: `dist/whisp_setup_1.0.0.exe`

---

## Update veröffentlichen

1. Version in `whisp_setup.iss` erhöhen (`#define AppVersion "1.0.1"`)
2. Neue .exe bauen
3. Nutzer führt neue .exe aus — Settings + Modell bleiben erhalten

---

## Was der Installer macht

1. Begrüßungs-Screen mit Whisp-Branding
2. Installationspfad wählen (`%LOCALAPPDATA%\Whisp`)
3. Desktop-Verknüpfung + Autostart optional
4. Dateien kopieren (App + Python Embeddable)
5. venv erstellen + pip install (einmalig ~2 Min.)
6. Optional: Cohere-Modell herunterladen (~4 GB)
7. Whisp starten

## Deinstallation
Einstellungen → Apps → Whisp → Deinstallieren
(oder `%LOCALAPPDATA%\Whisp\unins000.exe`)
