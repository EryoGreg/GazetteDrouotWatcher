🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Beobachtet eine oder mehrere Rubrikseiten (Artikellisten) von gazette-drouot.com und zeigt für jeden neuen oder aktualisierten Artikel eine Windows-Benachrichtigung an — klicken Sie auf eine Benachrichtigung, um sie im Standardbrowser zu öffnen.

## Funktionsweise

- Bei jedem Durchlauf werden die ersten `MAX_PAGES` Listenseiten jeder konfigurierten Rubrik vollständig durchsucht (nicht nur bis ein "bekannter" Artikel gefunden wird — Tests zeigten, dass die Paginierung der Website nicht zuverlässig chronologisch ist, ein früher Abbruch könnte also echte Neuigkeiten übersehen).
- Jeder gefundene Artikel wird anhand seiner numerischen ID **und** seines Veröffentlichungsdatums mit dem gespeicherten Zustand (`state/<rubrique-key>.json`) verglichen. Neue ID → Benachrichtigung. Bekannte ID, aber anderes Datum als zuvor → erneute Benachrichtigung (der Artikel wurde wahrscheinlich neu veröffentlicht/bearbeitet). Ein Artikel ohne angezeigtes Datum wird nur einmal benachrichtigt und danach nie wieder geprüft.
- Der erste Durchlauf für eine Rubrik zeichnet lediglich den aktuellen Stand als Ausgangsbasis auf, still — keine Benachrichtigungsflut für bereits vorhandene Artikel bei der Installation.
- Wenn in einem Durchlauf mehr als `FLOOD_CAP` neue/aktualisierte Artikel in einer Rubrik auftauchen, erhalten nur die ersten eine eigene Benachrichtigung — der Rest wird zu einer Sammelbenachrichtigung "N weitere neue Beiträge" zusammengefasst.

## Einrichtung

- **VPN muss deaktiviert sein**, während dies läuft — Cloudflare erzwingt bei VPN-IPs eine interaktive Prüfung, die die Automatisierung nicht lösen kann. Eine normale Heim-IP läuft problemlos durch.
- Erfordert installiertes Microsoft Edge (nutzt Ihren System-Edge über Playwrights `channel="msedge"`, kein separater Browser-Download nötig).
- `pip install -r requirements.txt`

## Konfiguration

**`gazette_watcher/config.py` ist die einzige zu bearbeitende Datei** für alles: welche Seiten beobachtet werden, wie oft geprüft wird, wie tief gescannt wird, Benachrichtigungsgrenzen, Warnungs-Abklingzeiten usw. — jede Einstellung hat einen erklärenden Kommentar. Nach einer Änderung dort wirkt sie beim nächsten Durchlauf, **außer** `POLL_INTERVAL_MINUTES`, wofür zusätzlich `install_task.ps1` einmal erneut ausgeführt werden muss, um den eigentlichen Windows-Aufgabenplanung-Task zu aktualisieren.

## Bedienfeld (GUI)

Ein Desktop-Fenster für alles Folgende, ohne PowerShell oder config.py direkt anzufassen: geplanten Task installieren / aktivieren / deaktivieren / deinstallieren, sowie ein Einstellungsbereich (mit "Auf Standardwerte zurücksetzen", falls etwas schiefgeht) statt die Konfigurationsdatei von Hand zu bearbeiten. Das Flaggen-Symbol wechselt die Oberflächensprache (Englisch, 中文, Español, हिन्दी, العربية, Português, Русский, Français, 日本語, Deutsch — folgt standardmäßig der Windows-Oberflächensprache, sonst Englisch als Rückfall); das Sonne/Mond-Symbol wechselt zwischen hell/dunkel (folgt standardmäßig dem Windows-Design). Beide Einstellungen werden in `gui_prefs.json` gespeichert.

**Falls Sie nur die `.exe` haben:** Doppelklicken Sie auf `GazetteDrouotWatcherGUI.exe` — nichts weiter zu installieren. Sie muss sich direkt in diesem Projektordner befinden, neben `gazette_watcher/`, `install_task.ps1` usw.

**Stattdessen aus dem Quellcode ausführen:** Doppelklicken Sie auf `gui.pyw` (Windows führt `.pyw`-Dateien über `pythonw.exe` aus, kein Konsolenfenster), oder:
```
pythonw.exe gui.pyw
```

**Um die `.exe` selbst zu erstellen** (sie ist per gitignore ausgeschlossen — nicht im Quellcode enthalten, selbst neu bauen oder aus einer Release herunterladen):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcherGUI --icon icon.ico gui.pyw
```
Kopieren Sie anschließend `dist/GazetteDrouotWatcherGUI.exe` in das Projektstammverzeichnis (neben `gui.pyw`) und löschen Sie die Überbleibsel `build/`, `dist/` und `*.spec`.

## Manueller Durchlauf

```
python -m gazette_watcher.watcher
```

## Zeitplanung

Führen Sie `install_task.ps1` aus, um einen "GazetteDrouotWatcher"-Task in der Aufgabenplanung zu registrieren, der im in `config.py` festgelegten Intervall läuft, solange Sie angemeldet sind. Führen Sie es jederzeit erneut aus (z. B. nach Änderung von `POLL_INTERVAL_MINUTES`), um den bereits registrierten Task zu aktualisieren.

```
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

Einmal sofort zum Testen ausführen:
```
powershell -Command "Start-ScheduledTask -TaskName GazetteDrouotWatcher"
```

Entfernen mit `uninstall_task.ps1`:
```
powershell -ExecutionPolicy Bypass -File uninstall_task.ps1
```

## Wenn etwas schiefgeht

Es gibt zwei unterschiedliche Warnbenachrichtigungen, jede auf höchstens eine pro `ALERT_COOLDOWN_HOURS` (config.py) begrenzt, damit ein andauerndes Problem nicht bei jedem Durchlauf eine Benachrichtigung auslöst:

- **"blocked by Cloudflare"** — der Bot-Schutz der Website hat die Anfrage abgefangen. Fast immer durch Deaktivieren eines VPN behoben.
- **"needs an update"** — eine Seite wurde zwar geladen, aber ihr HTML entspricht nicht mehr dem, was dieses Skript erwartet. Höchstwahrscheinlich hat gazette-drouot.com sein Seitenlayout geändert, und die Selektoren des Scrapers (`gazette_watcher/scraper.py`) müssen entsprechend aktualisiert werden.

`logs/watcher.log` enthält alle Details zu jedem Durchlauf — hier zuerst nachsehen, falls Benachrichtigungen ausbleiben.

## Testen, ohne die echte Website zu belasten

`test/` enthält eine kleine lokale Fake-Site-Testumgebung, um die Scraping-/Benachrichtigungslogik isoliert zu testen, ohne die echte Website zu belasten oder von ihren aktuellen Inhalten abhängig zu sein. Siehe `test/README.md`.

## Eine weitere zu beobachtende Seite hinzufügen

Fügen Sie einen weiteren Eintrag zu `RUBRIQUES` in `config.py` hinzu — solange die Seite dasselbe `div.articleResume`-Kartenlayout verwendet, muss sonst nichts geändert werden.
