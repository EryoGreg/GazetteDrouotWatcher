🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Beobachtet eine oder mehrere Rubrikseiten (Artikellisten) von gazette-drouot.com und zeigt für jeden neuen oder aktualisierten Artikel eine Windows-Benachrichtigung an — klicken Sie auf eine Benachrichtigung, um sie im Standardbrowser zu öffnen.

## Funktionsweise

- Bei jedem Durchlauf werden die ersten `MAX_PAGES` Listenseiten jeder konfigurierten Rubrik vollständig durchsucht (nicht nur bis ein "bekannter" Artikel gefunden wird — Tests zeigten, dass die Paginierung der Website nicht zuverlässig chronologisch ist, ein früher Abbruch könnte also echte Neuigkeiten übersehen).
- Jeder gefundene Artikel wird anhand seiner numerischen ID **und** seines Veröffentlichungsdatums mit dem gespeicherten Zustand (`state/<rubrique-key>.json`, unter `%LOCALAPPDATA%\GazetteDrouotWatcher\`) verglichen. Neue ID → Benachrichtigung. Bekannte ID, aber anderes Datum als zuvor → erneute Benachrichtigung (der Artikel wurde wahrscheinlich neu veröffentlicht/bearbeitet). Ein Artikel ohne angezeigtes Datum wird nur einmal benachrichtigt und danach nie wieder geprüft.
- Der erste Durchlauf für eine Rubrik zeichnet lediglich den aktuellen Stand als Ausgangsbasis auf, still — keine Benachrichtigungsflut für bereits vorhandene Artikel bei der Installation.
- Wenn in einem Durchlauf mehr als `FLOOD_CAP` neue/aktualisierte Artikel in einer Rubrik auftauchen, erhalten nur die ersten eine eigene Benachrichtigung — der Rest wird zu einer Sammelbenachrichtigung "N weitere neue Beiträge" zusammengefasst.

## Einrichtung

- **VPN muss deaktiviert sein**, während dies läuft — Cloudflare erzwingt bei VPN-IPs eine interaktive Prüfung, die die Automatisierung nicht lösen kann. Eine normale Heim-IP läuft problemlos durch.
- Erfordert installiertes Microsoft Edge (nutzt Ihren System-Edge über Playwrights `channel="msedge"`, kein separater Browser-Download nötig).
- `pip install -r requirements.txt`

## Konfiguration

**`config.py` ist die einzige zu bearbeitende Datei** für alles: welche Seiten beobachtet werden, wie oft geprüft wird, wie tief gescannt wird, Benachrichtigungsgrenzen, Warnungs-Abklingzeiten usw. — jede Einstellung hat einen erklärenden Kommentar (oder bearbeiten Sie sie über den Einstellungen-Tab des Bedienfelds, siehe unten). Sie befindet sich unter `%LOCALAPPDATA%\GazetteDrouotWatcher\config.py` (dort beim ersten Start automatisch angelegt — nicht neben der `.exe`), sodass sie das Verschieben oder Ersetzen der `.exe` selbst übersteht. Nach einer Änderung dort wirkt sie beim nächsten Durchlauf, **außer** `POLL_INTERVAL_MINUTES`, wofür zusätzlich erneut auf **Installieren** im Bedienfeld geklickt werden muss, um den eigentlichen Windows-Aufgabenplanung-Task mit dem neuen Intervall zu aktualisieren.

## Bedienfeld (GUI)

**Das ist die Anwendung** — eine einzige, eigenständige `.exe`, keine separate Python-Installation oder Skriptdateien auf dem ausführenden Rechner nötig. Ein Desktop-Fenster für alles: geplanten Task installieren / aktivieren / deaktivieren / deinstallieren (direkt über die native Aufgabenplanung-API, ohne PowerShell), sowie ein Einstellungsbereich (mit "Auf Standardwerte zurücksetzen", falls etwas schiefgeht) statt die Konfigurationsdatei von Hand zu bearbeiten. Das Flaggen-Symbol wechselt die Oberflächensprache (Englisch, 中文, Español, हिन्दी, العربية, Português, Русский, Français, 日本語, Deutsch — folgt standardmäßig der Windows-Oberflächensprache, sonst Englisch als Rückfall); das Sonne/Mond-Symbol wechselt zwischen hell/dunkel (folgt standardmäßig dem Windows-Design). Beide Einstellungen werden in `%LOCALAPPDATA%\GazetteDrouotWatcher\gui_prefs.json` gespeichert.

**Falls Sie nur die `.exe` haben:** Doppelklicken Sie auf `GazetteDrouotWatcher.exe` — nichts weiter zu installieren, und nichts weiter nötig daneben. Sie ist vollständig eigenständig: `config.py`, `gui_prefs.json`, `state/` und `logs/` werden alle beim ersten Start unter `%LOCALAPPDATA%\GazetteDrouotWatcher\` angelegt, nicht neben der `.exe` selbst, sodass sie nie Dateien in dem Ordner verstreut, aus dem sie ausgeführt wird. Klicken Sie im Fenster auf **Installieren**, um den geplanten Task zu registrieren — von da an läuft die Prüfung automatisch im Hintergrund, im in `config.py` festgelegten Intervall, ohne dass dieses Fenster (oder die App überhaupt) geöffnet bleiben muss, und startet sich nach jedem PC-Neustart selbst neu.

**Stattdessen aus dem Quellcode ausführen:** Doppelklicken Sie auf `main.pyw` (Windows führt `.pyw`-Dateien über `pythonw.exe` aus, kein Konsolenfenster), oder:
```
pythonw.exe main.pyw
```

**Um die `.exe` selbst zu erstellen** (sie ist per gitignore ausgeschlossen — nicht im Quellcode enthalten, selbst neu bauen oder aus einer Release herunterladen):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
Kopieren Sie anschließend `dist/GazetteDrouotWatcher.exe` in das Projektstammverzeichnis (neben `main.pyw`) und löschen Sie die Überbleibsel `build/`, `dist/` und `*.spec`.

## Manueller Durchlauf

`main.pyw --watch` (oder gleichbedeutend `GazetteDrouotWatcher.exe --watch`) ist das, was der geplante Task tatsächlich aufruft — führt eine Prüfung aus und beendet sich, ohne Oberfläche. Das entspricht auch:
```
python -m gazette_watcher.watcher
```

## Wenn etwas schiefgeht

Es gibt zwei unterschiedliche Warnbenachrichtigungen, jede auf höchstens eine pro `ALERT_COOLDOWN_HOURS` (config.py) begrenzt, damit ein andauerndes Problem nicht bei jedem Durchlauf eine Benachrichtigung auslöst:

- **"blocked by Cloudflare"** — der Bot-Schutz der Website hat die Anfrage abgefangen. Fast immer durch Deaktivieren eines VPN behoben.
- **"needs an update"** — eine Seite wurde zwar geladen, aber ihr HTML entspricht nicht mehr dem, was dieses Skript erwartet. Höchstwahrscheinlich hat gazette-drouot.com sein Seitenlayout geändert, und die Selektoren des Scrapers (`gazette_watcher/scraper.py`) müssen entsprechend aktualisiert werden.

`%LOCALAPPDATA%\GazetteDrouotWatcher\logs\watcher.log` enthält alle Details zu jedem Durchlauf — hier zuerst nachsehen, falls Benachrichtigungen ausbleiben.

## Testen, ohne die echte Website zu belasten

`test/` enthält eine kleine lokale Fake-Site-Testumgebung, um die Scraping-/Benachrichtigungslogik isoliert zu testen, ohne die echte Website zu belasten oder von ihren aktuellen Inhalten abhängig zu sein. Siehe `test/README.md`.

## Eine weitere zu beobachtende Seite hinzufügen

Fügen Sie einen weiteren Eintrag zu `RUBRIQUES` in `config.py` hinzu — solange die Seite dasselbe `div.articleResume`-Kartenlayout verwendet, muss sonst nichts geändert werden.
