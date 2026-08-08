🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Vigila una o varias páginas de rúbrica (listados de artículos) de gazette-drouot.com y muestra una notificación de Windows por cada artículo nuevo o actualizado — haga clic en una notificación para abrirlo en su navegador predeterminado.

## Cómo funciona

- En cada ejecución, se analizan por completo las primeras `MAX_PAGES` páginas de listado de cada rúbrica configurada (no solo hasta encontrar un artículo "conocido" — las pruebas mostraron que la paginación del sitio no es fiablemente cronológica, así que detenerse antes podría pasar por alto noticias reales en silencio).
- Cada artículo encontrado se compara con el estado guardado (`state/<rubrique-key>.json`) por su id numérico **y** su fecha de publicación. Id nuevo → notifica. Id conocido pero con fecha distinta a la anterior → notifica de nuevo (probablemente el artículo fue republicado/editado). Un artículo sin fecha visible solo se notifica una vez y nunca se vuelve a comprobar.
- La primera ejecución de una rúbrica simplemente registra lo que hay actualmente como base, en silencio — sin avalancha de notificaciones por artículos preexistentes al instalar.
- Si aparecen más de `FLOOD_CAP` artículos nuevos/actualizados en una rúbrica en una sola ejecución, solo los primeros tienen notificación propia — el resto se agrupa en una notificación resumen de "N más".

## Configuración inicial

- **La VPN debe estar desactivada** mientras esto se ejecuta — Cloudflare fuerza un desafío interactivo en las IP de VPN que la automatización no puede resolver. Una IP doméstica normal pasa sin problemas.
- Requiere Microsoft Edge instalado (usa su Edge del sistema mediante el `channel="msedge"` de Playwright, sin necesidad de descargar un navegador aparte).
- `pip install -r requirements.txt`

## Configuración

**`gazette_watcher/config.py` es el único archivo a editar** para todo: qué páginas vigilar, con qué frecuencia comprobar, qué tan profundo analizar, límites de notificación, tiempos de espera de alertas, etc. — cada ajuste tiene un comentario explicativo (o edítelos desde la pestaña Configuración del panel de control, vea abajo). Tras cualquier cambio ahí, tendrá efecto en la siguiente ejecución, **excepto** `POLL_INTERVAL_MINUTES`, que también requiere volver a hacer clic en **Instalar** en el panel de control para actualizar la tarea real del Programador de tareas de Windows con el nuevo intervalo.

## Panel de control (GUI)

**Esta es la aplicación** — un único `.exe` autónomo, sin necesidad de instalar Python por separado ni de archivos de script en la máquina que lo ejecute. Una ventana de escritorio para todo: instalar / activar / desactivar / desinstalar la tarea programada (mediante la API nativa del Programador de tareas directamente, sin PowerShell), y un panel de configuración (con "Restablecer valores predeterminados" si algo se estropea) en lugar de editar el archivo de configuración a mano. El icono de la bandera cambia el idioma de la interfaz (inglés, 中文, español, हिन्दी, العربية, português, русский, français, 日本語, alemán — sigue por defecto el idioma de Windows, y si no es compatible usa inglés); el icono sol/luna alterna claro/oscuro (sigue por defecto el tema de Windows). Ambas elecciones se guardan en `gui_prefs.json`.

**Si solo tiene el `.exe`:** haga doble clic en `GazetteDrouotWatcher.exe` — no hay nada más que instalar. Debe estar directamente en esta carpeta del proyecto, junto a `gazette_watcher/`, etc. Haga clic en **Instalar** en la ventana para registrar la tarea programada — a partir de ahí, la comprobación se hace automáticamente en segundo plano, con el intervalo definido en `config.py`, sin que esta ventana (ni la aplicación) necesite permanecer abierta, y se inicia sola de nuevo tras cada reinicio del PC.

**Si lo ejecuta desde el código fuente:** haga doble clic en `main.pyw` (Windows ejecuta los archivos `.pyw` mediante `pythonw.exe`, sin ventana de consola), o:
```
pythonw.exe main.pyw
```

**Para compilar el `.exe` usted mismo** (está excluido de git — no se sube al repositorio, reconstrúyalo o descárguelo de una Release):
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
Luego copie `dist/GazetteDrouotWatcher.exe` a la raíz del proyecto (junto a `main.pyw`) y elimine los restos de `build/`, `dist/` y `*.spec`.

## Ejecución manual

`main.pyw --watch` (o el equivalente `GazetteDrouotWatcher.exe --watch`) es lo que realmente llama la tarea programada — ejecuta una comprobación y termina, sin interfaz. También equivale a:
```
python -m gazette_watcher.watcher
```

## Si algo falla

Existen dos notificaciones de alerta distintas, cada una limitada a un máximo de una por `ALERT_COOLDOWN_HOURS` (config.py) para que un problema continuo no sature con una notificación en cada ejecución:

- **"blocked by Cloudflare"** — la protección antibots del sitio interceptó la solicitud. Casi siempre se soluciona desactivando una VPN.
- **"needs an update"** — una página cargó bien pero su HTML ya no coincide con lo que este script espera. Lo más probable es que gazette-drouot.com haya cambiado el diseño de sus páginas y los selectores del scraper (`gazette_watcher/scraper.py`) necesiten actualizarse para coincidir.

`logs/watcher.log` tiene el detalle completo de cada ejecución — revíselo primero si las notificaciones dejan de aparecer.

## Probar sin tocar el sitio real

`test/` contiene un pequeño entorno de pruebas con un sitio falso local, para probar la lógica de scraping/notificación de forma aislada, sin sobrecargar el sitio real ni depender de su contenido en vivo. Vea `test/README.md`.

## Añadir otra página para vigilar

Añada otra entrada a `RUBRIQUES` en `config.py` — mientras la página use la misma estructura de tarjeta `div.articleResume`, no es necesario cambiar nada más.
