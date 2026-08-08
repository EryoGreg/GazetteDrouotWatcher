"""
Translations for gui.pyw's UI text.

LANGUAGES lists the supported languages (code, flag emoji, native name).
TRANSLATIONS[lang_code] maps a short key to that language's text for every
piece of UI copy. English is the fallback: t() falls back to English for
any key a language is missing, so a partial/future translation never
crashes or shows a blank string.

Some values contain {placeholders} filled in via .format(**kwargs) at call
time (e.g. an action name or an underlying error message) — keep the same
placeholder names across every language's version of that key.
"""

LANGUAGES = [
    ("en", "🇬🇧", "English"),
    ("zh", "🇨🇳", "中文"),
    ("es", "🇪🇸", "Español"),
    ("hi", "🇮🇳", "हिन्दी"),
    ("ar", "🇸🇦", "العربية"),
    ("pt", "🇵🇹", "Português"),
    ("ru", "🇷🇺", "Русский"),
    ("fr", "🇫🇷", "Français"),
    ("ja", "🇯🇵", "日本語"),
    ("de", "🇩🇪", "Deutsch"),
]
_SUPPORTED_CODES = {code for code, _flag, _name in LANGUAGES}

TRANSLATIONS = {
    "en": {
        "window_title_suffix": "control panel",
        "description": (
            "Gazette Drouot Watcher polls gazette-drouot.com's rubrique (article "
            "listing) pages on a timer and fires a Windows notification for each "
            "new or updated article — click a notification to open it in your "
            "default browser."
        ),
        "author_prefix": "Author:",
        "section_task": "Scheduled task",
        "task_note": (
            "Once installed, this runs on its own in the background on the interval set below — you don't "
            "need to keep this window (or the app) open, and it starts itself automatically after every "
            "PC restart. Use Enable/Disable here rather than Windows' own Task Scheduler app to pause it."
        ),
        "status_label": "Status:",
        "status_checking": "checking...",
        "status_not_installed": "Not installed",
        "status_ready": "Installed and enabled",
        "status_disabled": "Disabled",
        "btn_refresh": "Refresh",
        "btn_install": "Install",
        "btn_enable": "Enable",
        "btn_disable": "Disable",
        "btn_uninstall": "Uninstall",
        "log_ok": "OK",
        "log_failed": "FAILED",
        "log_permission_hint": "Looks like a permissions problem.",
        "dlg_admin_needed_body": (
            "{action} needs administrator rights on this PC.\n\n"
            "Relaunch this control panel as Administrator and retry?"
        ),
        "diag_not_installed": (
            "The scheduled task isn't installed yet, so there's nothing to "
            "enable/disable. Click Install first, then try again."
        ),
        "diag_python_not_found": (
            "install_task.ps1 can't find Python at the location it expects.\n\n"
            "Open install_task.ps1 in a text editor and update the $PythonExe "
            "line to match where Python is actually installed on this PC."
        ),
        "diag_config_unreadable": (
            "config.py couldn't be read to determine the check interval — it "
            "may have been edited into an invalid state.\n\n"
            "Try 'Reset to defaults' in the Settings section below, then "
            "click Install again."
        ),
        "dlg_action_failed_body": "{action} failed:\n\n{detail}",
        "section_settings": "Settings",
        "field_poll_interval_label": "Check interval (minutes)",
        "field_poll_interval_desc": "How often each page is checked. Whole minutes only.",
        "field_max_pages_label": "Pages scanned per check",
        "field_max_pages_desc": "How many listing pages deep to look, every single run. Whole number.",
        "field_page_delay_label": "Delay between page fetches (seconds)",
        "field_page_delay_desc": "Politeness pause between the page requests within one run. Decimals allowed (e.g. 1.5 or 1,5).",
        "field_max_seen_label": "Remembered articles per page (max)",
        "field_max_seen_desc": "How many already-seen article ids are kept in memory per page. Whole number.",
        "field_flood_cap_label": "Max individual notifications per run",
        "field_flood_cap_desc": "Beyond this many new articles at once, the rest collapse into one summary notification. Whole number.",
        "field_notif_gap_label": "Gap between notifications (seconds)",
        "field_notif_gap_desc": "Delay between showing each individual notification. Whole number.",
        "field_alert_cooldown_label": "Problem-alert cooldown (hours)",
        "field_alert_cooldown_desc": "Minimum time between repeats of the same 'something's wrong' alert. Decimals allowed (e.g. 1.5 or 1,5).",
        "field_headless_label": "Run browser invisibly",
        "field_headless_desc": "Off makes the browser window visible during each check — useful for debugging.",
        "field_browser_label": "Browser used",
        "field_browser_desc": (
            "msedge or chrome (and their -beta/-dev/-canary variants) drive your real installed browser directly. "
            "firefox uses Playwright's own bundled Firefox, not your installed one — run "
            "'playwright install firefox' once before using it. Opera, Brave, Vivaldi, Safari and other "
            "less-mainstream browsers aren't supported — Playwright doesn't know how to drive them."
        ),
        "pages_to_watch": "Pages to watch",
        "btn_add_page": "Add page",
        "rubrique_key": "key",
        "rubrique_label": "label",
        "rubrique_url": "url",
        "btn_save": "Save",
        "btn_reload": "Reload (discard changes)",
        "btn_reset_defaults": "Reset to defaults",
        "err_invalid_page_title": "Invalid page",
        "err_invalid_page_body": "Every page needs a key, label, and url — remove any blank row.",
        "err_invalid_pages_title": "Invalid pages",
        "err_invalid_pages_body": "At least one page to watch is required.",
        "err_invalid_value_title": "Invalid value",
        "err_invalid_value_body": "'{label}' needs {kind}, got: {raw}",
        "kind_int": "a whole number",
        "kind_float": "a decimal number",
        "err_load_failed_title": "Load failed",
        "err_load_failed_body": "Couldn't read config.py:\n\n{error}",
        "log_loaded_settings": "Loaded current settings.",
        "err_save_failed_title": "Save failed",
        "err_save_failed_body": "Nothing was written:\n\n{error}",
        "log_saved_settings": "Saved settings.",
        "dlg_saved_title": "Saved",
        "dlg_saved_body": (
            "Settings saved. Takes effect on the next run — if you changed the "
            "check interval, click Install above once to update the scheduled task."
        ),
        "dlg_reset_confirm_title": "Reset to defaults",
        "dlg_reset_confirm_body": "This restores every setting below to its factory default. Continue?",
        "err_reset_failed_title": "Reset failed",
        "err_reset_failed_body": "Nothing was written:\n\n{error}",
        "log_reset_settings": "Reset settings to defaults.",
        "dlg_reset_done_title": "Reset",
        "dlg_reset_done_body": "Settings restored to defaults.",
        "section_log": "Action log",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Language",
    },
    "fr": {
        "window_title_suffix": "panneau de configuration",
        "description": (
            "Gazette Drouot Watcher interroge périodiquement les pages de rubrique "
            "(listes d'articles) de gazette-drouot.com et affiche une notification "
            "Windows pour chaque article nouveau ou mis à jour — cliquez sur une "
            "notification pour l'ouvrir dans votre navigateur par défaut."
        ),
        "author_prefix": "Auteur :",
        "section_task": "Tâche planifiée",
        "task_note": (
            "Une fois installée, cette tâche tourne seule en arrière-plan selon l'intervalle défini ci-dessous — "
            "inutile de garder cette fenêtre (ou l'application) ouverte, et elle démarre automatiquement à chaque "
            "redémarrage du PC. Utilisez Activer/Désactiver ici plutôt que le Planificateur de tâches de Windows."
        ),
        "status_label": "Statut :",
        "status_checking": "vérification...",
        "status_not_installed": "Non installée",
        "status_ready": "Installée et activée",
        "status_disabled": "Désactivée",
        "btn_refresh": "Actualiser",
        "btn_install": "Installer",
        "btn_enable": "Activer",
        "btn_disable": "Désactiver",
        "btn_uninstall": "Désinstaller",
        "log_ok": "OK",
        "log_failed": "ÉCHEC",
        "log_permission_hint": "Cela ressemble à un problème de permissions.",
        "dlg_admin_needed_body": (
            "{action} nécessite les droits administrateur sur ce PC.\n\n"
            "Relancer ce panneau de configuration en tant qu'administrateur et réessayer ?"
        ),
        "diag_not_installed": (
            "La tâche planifiée n'est pas encore installée, il n'y a donc rien à "
            "activer/désactiver. Cliquez d'abord sur Installer, puis réessayez."
        ),
        "diag_python_not_found": (
            "install_task.ps1 ne trouve pas Python à l'emplacement attendu.\n\n"
            "Ouvrez install_task.ps1 dans un éditeur de texte et corrigez la ligne "
            "$PythonExe pour qu'elle corresponde à l'emplacement réel de Python sur ce PC."
        ),
        "diag_config_unreadable": (
            "config.py n'a pas pu être lu pour déterminer l'intervalle de vérification — "
            "il a peut-être été modifié dans un état invalide.\n\n"
            "Essayez « Réinitialiser aux valeurs par défaut » dans la section Paramètres "
            "ci-dessous, puis cliquez de nouveau sur Installer."
        ),
        "dlg_action_failed_body": "{action} a échoué :\n\n{detail}",
        "section_settings": "Paramètres",
        "field_poll_interval_label": "Intervalle de vérification (minutes)",
        "field_poll_interval_desc": "Fréquence de vérification de chaque page. Minutes entières uniquement.",
        "field_max_pages_label": "Pages analysées par vérification",
        "field_max_pages_desc": "Nombre de pages de liste à examiner en profondeur, à chaque exécution. Nombre entier.",
        "field_page_delay_label": "Délai entre les pages (secondes)",
        "field_page_delay_desc": "Pause de courtoisie entre les requêtes de page au sein d'une même exécution. Décimales acceptées (ex. 1.5 ou 1,5).",
        "field_max_seen_label": "Articles mémorisés par page (max)",
        "field_max_seen_desc": "Nombre d'identifiants d'articles déjà vus conservés en mémoire par page. Nombre entier.",
        "field_flood_cap_label": "Notifications individuelles max par exécution",
        "field_flood_cap_desc": "Au-delà de ce nombre de nouveaux articles à la fois, le reste est regroupé en une seule notification récapitulative. Nombre entier.",
        "field_notif_gap_label": "Intervalle entre notifications (secondes)",
        "field_notif_gap_desc": "Délai entre l'affichage de chaque notification individuelle. Nombre entier.",
        "field_alert_cooldown_label": "Délai entre alertes de problème (heures)",
        "field_alert_cooldown_desc": "Temps minimum entre deux répétitions de la même alerte « problème ». Décimales acceptées (ex. 1.5 ou 1,5).",
        "field_headless_label": "Exécuter le navigateur en invisible",
        "field_headless_desc": "Désactivé rend la fenêtre du navigateur visible pendant chaque vérification — utile pour le débogage.",
        "field_browser_label": "Navigateur utilisé",
        "field_browser_desc": (
            "msedge ou chrome (et leurs variantes -beta/-dev/-canary) pilotent directement votre navigateur réellement installé. "
            "firefox utilise le Firefox intégré à Playwright, pas celui installé sur votre PC — exécutez "
            "« playwright install firefox » une fois avant de l'utiliser. Opera, Brave, Vivaldi, Safari et autres "
            "navigateurs moins courants ne sont pas pris en charge — Playwright ne sait pas les piloter."
        ),
        "pages_to_watch": "Pages surveillées",
        "btn_add_page": "Ajouter une page",
        "rubrique_key": "clé",
        "rubrique_label": "libellé",
        "rubrique_url": "url",
        "btn_save": "Enregistrer",
        "btn_reload": "Recharger (annuler les modifications)",
        "btn_reset_defaults": "Réinitialiser aux valeurs par défaut",
        "err_invalid_page_title": "Page invalide",
        "err_invalid_page_body": "Chaque page nécessite une clé, un libellé et une url — supprimez toute ligne vide.",
        "err_invalid_pages_title": "Pages invalides",
        "err_invalid_pages_body": "Au moins une page à surveiller est requise.",
        "err_invalid_value_title": "Valeur invalide",
        "err_invalid_value_body": "« {label} » nécessite {kind}, reçu : {raw}",
        "kind_int": "un nombre entier",
        "kind_float": "un nombre décimal",
        "err_load_failed_title": "Échec du chargement",
        "err_load_failed_body": "Impossible de lire config.py :\n\n{error}",
        "log_loaded_settings": "Paramètres actuels chargés.",
        "err_save_failed_title": "Échec de l'enregistrement",
        "err_save_failed_body": "Rien n'a été écrit :\n\n{error}",
        "log_saved_settings": "Paramètres enregistrés.",
        "dlg_saved_title": "Enregistré",
        "dlg_saved_body": (
            "Paramètres enregistrés. Prend effet à la prochaine exécution — si vous avez modifié "
            "l'intervalle de vérification, cliquez sur Installer ci-dessus pour mettre à jour la tâche planifiée."
        ),
        "dlg_reset_confirm_title": "Réinitialiser aux valeurs par défaut",
        "dlg_reset_confirm_body": "Cela restaure tous les paramètres ci-dessous à leur valeur d'origine. Continuer ?",
        "err_reset_failed_title": "Échec de la réinitialisation",
        "err_reset_failed_body": "Rien n'a été écrit :\n\n{error}",
        "log_reset_settings": "Paramètres réinitialisés aux valeurs par défaut.",
        "dlg_reset_done_title": "Réinitialisation",
        "dlg_reset_done_body": "Paramètres restaurés aux valeurs par défaut.",
        "section_log": "Journal des actions",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Langue",
    },
    "es": {
        "window_title_suffix": "panel de control",
        "description": (
            "Gazette Drouot Watcher consulta periódicamente las páginas de rúbrica "
            "(listados de artículos) de gazette-drouot.com y muestra una notificación "
            "de Windows por cada artículo nuevo o actualizado — haga clic en una "
            "notificación para abrirlo en su navegador predeterminado."
        ),
        "author_prefix": "Autor:",
        "section_task": "Tarea programada",
        "task_note": (
            "Una vez instalada, se ejecuta sola en segundo plano según el intervalo definido abajo — no es "
            "necesario mantener esta ventana (ni la app) abierta, y se inicia automáticamente tras cada "
            "reinicio del PC. Use Activar/Desactivar aquí en lugar del Programador de tareas de Windows."
        ),
        "status_label": "Estado:",
        "status_checking": "comprobando...",
        "status_not_installed": "No instalada",
        "status_ready": "Instalada y activada",
        "status_disabled": "Desactivada",
        "btn_refresh": "Actualizar",
        "btn_install": "Instalar",
        "btn_enable": "Activar",
        "btn_disable": "Desactivar",
        "btn_uninstall": "Desinstalar",
        "log_ok": "OK",
        "log_failed": "FALLÓ",
        "log_permission_hint": "Parece un problema de permisos.",
        "dlg_admin_needed_body": (
            "{action} requiere permisos de administrador en este PC.\n\n"
            "¿Reiniciar este panel de control como administrador y volver a intentarlo?"
        ),
        "diag_not_installed": (
            "La tarea programada aún no está instalada, así que no hay nada que "
            "activar/desactivar. Haga clic en Instalar primero y vuelva a intentarlo."
        ),
        "diag_python_not_found": (
            "install_task.ps1 no encuentra Python en la ubicación esperada.\n\n"
            "Abra install_task.ps1 en un editor de texto y actualice la línea "
            "$PythonExe para que coincida con la ubicación real de Python en este PC."
        ),
        "diag_config_unreadable": (
            "No se pudo leer config.py para determinar el intervalo de comprobación — "
            "puede haberse editado a un estado inválido.\n\n"
            "Pruebe 'Restablecer valores predeterminados' en la sección Configuración "
            "de abajo y vuelva a hacer clic en Instalar."
        ),
        "dlg_action_failed_body": "{action} falló:\n\n{detail}",
        "section_settings": "Configuración",
        "field_poll_interval_label": "Intervalo de comprobación (minutos)",
        "field_poll_interval_desc": "Con qué frecuencia se comprueba cada página. Solo minutos enteros.",
        "field_max_pages_label": "Páginas analizadas por comprobación",
        "field_max_pages_desc": "Cuántas páginas de listado revisar en cada ejecución. Número entero.",
        "field_page_delay_label": "Retraso entre páginas (segundos)",
        "field_page_delay_desc": "Pausa de cortesía entre las solicitudes de página en una misma ejecución. Se admiten decimales (p. ej. 1.5 o 1,5).",
        "field_max_seen_label": "Artículos recordados por página (máx.)",
        "field_max_seen_desc": "Cuántos ids de artículos ya vistos se guardan en memoria por página. Número entero.",
        "field_flood_cap_label": "Notificaciones individuales máx. por ejecución",
        "field_flood_cap_desc": "Más allá de esta cantidad de artículos nuevos a la vez, el resto se agrupa en una notificación resumen. Número entero.",
        "field_notif_gap_label": "Intervalo entre notificaciones (segundos)",
        "field_notif_gap_desc": "Retraso entre cada notificación individual. Número entero.",
        "field_alert_cooldown_label": "Espera entre alertas de problemas (horas)",
        "field_alert_cooldown_desc": "Tiempo mínimo entre repeticiones de la misma alerta de 'algo va mal'. Se admiten decimales (p. ej. 1.5 o 1,5).",
        "field_headless_label": "Ejecutar el navegador de forma invisible",
        "field_headless_desc": "Desactivado hace visible la ventana del navegador durante cada comprobación — útil para depurar.",
        "field_browser_label": "Navegador usado",
        "field_browser_desc": (
            "msedge o chrome (y sus variantes -beta/-dev/-canary) controlan directamente su navegador instalado. "
            "firefox usa el Firefox integrado de Playwright, no el instalado en su PC — ejecute "
            "'playwright install firefox' una vez antes de usarlo. Opera, Brave, Vivaldi, Safari y otros "
            "navegadores menos comunes no son compatibles — Playwright no sabe controlarlos."
        ),
        "pages_to_watch": "Páginas vigiladas",
        "btn_add_page": "Añadir página",
        "rubrique_key": "clave",
        "rubrique_label": "etiqueta",
        "rubrique_url": "url",
        "btn_save": "Guardar",
        "btn_reload": "Recargar (descartar cambios)",
        "btn_reset_defaults": "Restablecer valores predeterminados",
        "err_invalid_page_title": "Página inválida",
        "err_invalid_page_body": "Cada página necesita una clave, etiqueta y url — elimine cualquier fila vacía.",
        "err_invalid_pages_title": "Páginas inválidas",
        "err_invalid_pages_body": "Se requiere al menos una página para vigilar.",
        "err_invalid_value_title": "Valor inválido",
        "err_invalid_value_body": "'{label}' necesita {kind}, se recibió: {raw}",
        "kind_int": "un número entero",
        "kind_float": "un número decimal",
        "err_load_failed_title": "Error al cargar",
        "err_load_failed_body": "No se pudo leer config.py:\n\n{error}",
        "log_loaded_settings": "Configuración actual cargada.",
        "err_save_failed_title": "Error al guardar",
        "err_save_failed_body": "No se escribió nada:\n\n{error}",
        "log_saved_settings": "Configuración guardada.",
        "dlg_saved_title": "Guardado",
        "dlg_saved_body": (
            "Configuración guardada. Tendrá efecto en la próxima ejecución — si cambió el "
            "intervalo de comprobación, haga clic en Instalar arriba para actualizar la tarea programada."
        ),
        "dlg_reset_confirm_title": "Restablecer valores predeterminados",
        "dlg_reset_confirm_body": "Esto restaura todos los valores de abajo a su valor de fábrica. ¿Continuar?",
        "err_reset_failed_title": "Error al restablecer",
        "err_reset_failed_body": "No se escribió nada:\n\n{error}",
        "log_reset_settings": "Configuración restablecida a valores predeterminados.",
        "dlg_reset_done_title": "Restablecido",
        "dlg_reset_done_body": "Configuración restaurada a los valores predeterminados.",
        "section_log": "Registro de acciones",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Idioma",
    },
    "de": {
        "window_title_suffix": "Bedienfeld",
        "description": (
            "Gazette Drouot Watcher ruft regelmäßig die Rubrikseiten (Artikellisten) "
            "von gazette-drouot.com ab und zeigt für jeden neuen oder aktualisierten "
            "Artikel eine Windows-Benachrichtigung an — klicken Sie auf eine "
            "Benachrichtigung, um den Artikel im Standardbrowser zu öffnen."
        ),
        "author_prefix": "Autor:",
        "section_task": "Geplanter Task",
        "task_note": (
            "Nach der Installation läuft dies selbstständig im Hintergrund im unten festgelegten Intervall — "
            "dieses Fenster (oder die App) muss nicht geöffnet bleiben, und es startet nach jedem PC-Neustart "
            "automatisch. Verwenden Sie Aktivieren/Deaktivieren hier statt der Windows-Aufgabenplanung."
        ),
        "status_label": "Status:",
        "status_checking": "wird geprüft...",
        "status_not_installed": "Nicht installiert",
        "status_ready": "Installiert und aktiviert",
        "status_disabled": "Deaktiviert",
        "btn_refresh": "Aktualisieren",
        "btn_install": "Installieren",
        "btn_enable": "Aktivieren",
        "btn_disable": "Deaktivieren",
        "btn_uninstall": "Deinstallieren",
        "log_ok": "OK",
        "log_failed": "FEHLGESCHLAGEN",
        "log_permission_hint": "Sieht nach einem Berechtigungsproblem aus.",
        "dlg_admin_needed_body": (
            "{action} benötigt Administratorrechte auf diesem PC.\n\n"
            "Dieses Bedienfeld als Administrator neu starten und erneut versuchen?"
        ),
        "diag_not_installed": (
            "Der geplante Task ist noch nicht installiert, daher gibt es nichts zu "
            "aktivieren/deaktivieren. Zuerst auf Installieren klicken, dann erneut versuchen."
        ),
        "diag_python_not_found": (
            "install_task.ps1 findet Python nicht am erwarteten Ort.\n\n"
            "Öffnen Sie install_task.ps1 in einem Texteditor und passen Sie die "
            "$PythonExe-Zeile an den tatsächlichen Python-Installationsort auf diesem PC an."
        ),
        "diag_config_unreadable": (
            "config.py konnte nicht gelesen werden, um das Prüfintervall zu bestimmen — "
            "sie wurde möglicherweise in einen ungültigen Zustand bearbeitet.\n\n"
            "Versuchen Sie 'Auf Standardwerte zurücksetzen' im Bereich Einstellungen "
            "unten und klicken Sie dann erneut auf Installieren."
        ),
        "dlg_action_failed_body": "{action} fehlgeschlagen:\n\n{detail}",
        "section_settings": "Einstellungen",
        "field_poll_interval_label": "Prüfintervall (Minuten)",
        "field_poll_interval_desc": "Wie oft jede Seite geprüft wird. Nur ganze Minuten.",
        "field_max_pages_label": "Seiten pro Prüfung durchsucht",
        "field_max_pages_desc": "Wie viele Listenseiten bei jedem Durchlauf durchsucht werden. Ganze Zahl.",
        "field_page_delay_label": "Verzögerung zwischen Seitenabrufen (Sekunden)",
        "field_page_delay_desc": "Höflichkeitspause zwischen den Seitenanfragen innerhalb eines Durchlaufs. Dezimalzahlen erlaubt (z. B. 1.5 oder 1,5).",
        "field_max_seen_label": "Gespeicherte Artikel pro Seite (max.)",
        "field_max_seen_desc": "Wie viele bereits gesehene Artikel-IDs pro Seite im Speicher behalten werden. Ganze Zahl.",
        "field_flood_cap_label": "Max. einzelne Benachrichtigungen pro Durchlauf",
        "field_flood_cap_desc": "Über diese Anzahl neuer Artikel auf einmal hinaus wird der Rest zu einer Sammelbenachrichtigung zusammengefasst. Ganze Zahl.",
        "field_notif_gap_label": "Abstand zwischen Benachrichtigungen (Sekunden)",
        "field_notif_gap_desc": "Verzögerung zwischen der Anzeige jeder einzelnen Benachrichtigung. Ganze Zahl.",
        "field_alert_cooldown_label": "Abklingzeit für Problem-Warnungen (Stunden)",
        "field_alert_cooldown_desc": "Mindestzeit zwischen Wiederholungen derselben 'Problem'-Warnung. Dezimalzahlen erlaubt (z. B. 1.5 oder 1,5).",
        "field_headless_label": "Browser unsichtbar ausführen",
        "field_headless_desc": "Aus macht das Browserfenster während jeder Prüfung sichtbar — nützlich zum Debuggen.",
        "field_browser_label": "Verwendeter Browser",
        "field_browser_desc": (
            "msedge oder chrome (und deren -beta/-dev/-canary-Varianten) steuern direkt Ihren echten installierten Browser. "
            "firefox nutzt Playwrights eigenes gebündeltes Firefox, nicht Ihr installiertes — führen Sie einmalig "
            "'playwright install firefox' aus, bevor Sie es verwenden. Opera, Brave, Vivaldi, Safari und andere "
            "weniger verbreitete Browser werden nicht unterstützt — Playwright kann sie nicht steuern."
        ),
        "pages_to_watch": "Beobachtete Seiten",
        "btn_add_page": "Seite hinzufügen",
        "rubrique_key": "Schlüssel",
        "rubrique_label": "Bezeichnung",
        "rubrique_url": "url",
        "btn_save": "Speichern",
        "btn_reload": "Neu laden (Änderungen verwerfen)",
        "btn_reset_defaults": "Auf Standardwerte zurücksetzen",
        "err_invalid_page_title": "Ungültige Seite",
        "err_invalid_page_body": "Jede Seite braucht einen Schlüssel, eine Bezeichnung und eine url — leere Zeilen entfernen.",
        "err_invalid_pages_title": "Ungültige Seiten",
        "err_invalid_pages_body": "Mindestens eine zu beobachtende Seite ist erforderlich.",
        "err_invalid_value_title": "Ungültiger Wert",
        "err_invalid_value_body": "'{label}' benötigt {kind}, erhalten: {raw}",
        "kind_int": "eine ganze Zahl",
        "kind_float": "eine Dezimalzahl",
        "err_load_failed_title": "Laden fehlgeschlagen",
        "err_load_failed_body": "config.py konnte nicht gelesen werden:\n\n{error}",
        "log_loaded_settings": "Aktuelle Einstellungen geladen.",
        "err_save_failed_title": "Speichern fehlgeschlagen",
        "err_save_failed_body": "Es wurde nichts geschrieben:\n\n{error}",
        "log_saved_settings": "Einstellungen gespeichert.",
        "dlg_saved_title": "Gespeichert",
        "dlg_saved_body": (
            "Einstellungen gespeichert. Wird beim nächsten Durchlauf wirksam — falls Sie das "
            "Prüfintervall geändert haben, oben auf Installieren klicken, um den geplanten Task zu aktualisieren."
        ),
        "dlg_reset_confirm_title": "Auf Standardwerte zurücksetzen",
        "dlg_reset_confirm_body": "Dadurch werden alle Einstellungen unten auf die Werkseinstellungen zurückgesetzt. Fortfahren?",
        "err_reset_failed_title": "Zurücksetzen fehlgeschlagen",
        "err_reset_failed_body": "Es wurde nichts geschrieben:\n\n{error}",
        "log_reset_settings": "Einstellungen auf Standardwerte zurückgesetzt.",
        "dlg_reset_done_title": "Zurückgesetzt",
        "dlg_reset_done_body": "Einstellungen auf Standardwerte zurückgesetzt.",
        "section_log": "Aktionsprotokoll",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Sprache",
    },
    "pt": {
        "window_title_suffix": "painel de controlo",
        "description": (
            "O Gazette Drouot Watcher consulta periodicamente as páginas de rubrica "
            "(listas de artigos) do gazette-drouot.com e mostra uma notificação do "
            "Windows para cada artigo novo ou atualizado — clique numa notificação "
            "para o abrir no seu navegador predefinido."
        ),
        "author_prefix": "Autor:",
        "section_task": "Tarefa agendada",
        "task_note": (
            "Depois de instalada, esta tarefa corre sozinha em segundo plano no intervalo definido abaixo — "
            "não precisa manter esta janela (nem a aplicação) aberta, e inicia-se automaticamente após cada "
            "reinício do PC. Use Ativar/Desativar aqui em vez do Agendador de Tarefas do Windows."
        ),
        "status_label": "Estado:",
        "status_checking": "a verificar...",
        "status_not_installed": "Não instalada",
        "status_ready": "Instalada e ativada",
        "status_disabled": "Desativada",
        "btn_refresh": "Atualizar",
        "btn_install": "Instalar",
        "btn_enable": "Ativar",
        "btn_disable": "Desativar",
        "btn_uninstall": "Desinstalar",
        "log_ok": "OK",
        "log_failed": "FALHOU",
        "log_permission_hint": "Parece um problema de permissões.",
        "dlg_admin_needed_body": (
            "{action} requer direitos de administrador neste PC.\n\n"
            "Reiniciar este painel de controlo como administrador e tentar novamente?"
        ),
        "diag_not_installed": (
            "A tarefa agendada ainda não está instalada, por isso não há nada para "
            "ativar/desativar. Clique primeiro em Instalar e tente novamente."
        ),
        "diag_python_not_found": (
            "O install_task.ps1 não encontra o Python no local esperado.\n\n"
            "Abra o install_task.ps1 num editor de texto e atualize a linha "
            "$PythonExe para corresponder ao local real do Python neste PC."
        ),
        "diag_config_unreadable": (
            "Não foi possível ler o config.py para determinar o intervalo de verificação — "
            "pode ter sido editado para um estado inválido.\n\n"
            "Experimente 'Repor predefinições' na secção Definições abaixo e clique "
            "novamente em Instalar."
        ),
        "dlg_action_failed_body": "{action} falhou:\n\n{detail}",
        "section_settings": "Definições",
        "field_poll_interval_label": "Intervalo de verificação (minutos)",
        "field_poll_interval_desc": "Com que frequência cada página é verificada. Apenas minutos inteiros.",
        "field_max_pages_label": "Páginas analisadas por verificação",
        "field_max_pages_desc": "Quantas páginas de listagem verificar em profundidade, em cada execução. Número inteiro.",
        "field_page_delay_label": "Atraso entre páginas (segundos)",
        "field_page_delay_desc": "Pausa de cortesia entre os pedidos de página numa mesma execução. Decimais permitidos (ex. 1.5 ou 1,5).",
        "field_max_seen_label": "Artigos memorizados por página (máx.)",
        "field_max_seen_desc": "Quantos ids de artigos já vistos são mantidos em memória por página. Número inteiro.",
        "field_flood_cap_label": "Notificações individuais máx. por execução",
        "field_flood_cap_desc": "Além desta quantidade de novos artigos de uma vez, o resto é agrupado numa notificação-resumo. Número inteiro.",
        "field_notif_gap_label": "Intervalo entre notificações (segundos)",
        "field_notif_gap_desc": "Atraso entre a exibição de cada notificação individual. Número inteiro.",
        "field_alert_cooldown_label": "Intervalo entre alertas de problema (horas)",
        "field_alert_cooldown_desc": "Tempo mínimo entre repetições do mesmo alerta de 'algo está errado'. Decimais permitidos (ex. 1.5 ou 1,5).",
        "field_headless_label": "Executar o navegador de forma invisível",
        "field_headless_desc": "Desativado torna a janela do navegador visível durante cada verificação — útil para depuração.",
        "field_browser_label": "Navegador utilizado",
        "field_browser_desc": (
            "msedge ou chrome (e as suas variantes -beta/-dev/-canary) controlam diretamente o seu navegador instalado. "
            "firefox usa o Firefox integrado do Playwright, não o instalado no seu PC — execute "
            "'playwright install firefox' uma vez antes de o usar. Opera, Brave, Vivaldi, Safari e outros "
            "navegadores menos comuns não são suportados — o Playwright não sabe controlá-los."
        ),
        "pages_to_watch": "Páginas vigiadas",
        "btn_add_page": "Adicionar página",
        "rubrique_key": "chave",
        "rubrique_label": "rótulo",
        "rubrique_url": "url",
        "btn_save": "Guardar",
        "btn_reload": "Recarregar (descartar alterações)",
        "btn_reset_defaults": "Repor predefinições",
        "err_invalid_page_title": "Página inválida",
        "err_invalid_page_body": "Cada página precisa de uma chave, um rótulo e um url — remova qualquer linha vazia.",
        "err_invalid_pages_title": "Páginas inválidas",
        "err_invalid_pages_body": "É necessária pelo menos uma página para vigiar.",
        "err_invalid_value_title": "Valor inválido",
        "err_invalid_value_body": "'{label}' precisa de {kind}, recebido: {raw}",
        "kind_int": "um número inteiro",
        "kind_float": "um número decimal",
        "err_load_failed_title": "Falha ao carregar",
        "err_load_failed_body": "Não foi possível ler o config.py:\n\n{error}",
        "log_loaded_settings": "Definições atuais carregadas.",
        "err_save_failed_title": "Falha ao guardar",
        "err_save_failed_body": "Nada foi escrito:\n\n{error}",
        "log_saved_settings": "Definições guardadas.",
        "dlg_saved_title": "Guardado",
        "dlg_saved_body": (
            "Definições guardadas. Terá efeito na próxima execução — se alterou o "
            "intervalo de verificação, clique em Instalar acima para atualizar a tarefa agendada."
        ),
        "dlg_reset_confirm_title": "Repor predefinições",
        "dlg_reset_confirm_body": "Isto repõe todas as definições abaixo para os valores de fábrica. Continuar?",
        "err_reset_failed_title": "Falha ao repor",
        "err_reset_failed_body": "Nada foi escrito:\n\n{error}",
        "log_reset_settings": "Definições repostas para os valores predefinidos.",
        "dlg_reset_done_title": "Reposto",
        "dlg_reset_done_body": "Definições repostas para os valores predefinidos.",
        "section_log": "Registo de ações",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Idioma",
    },
    "ru": {
        "window_title_suffix": "панель управления",
        "description": (
            "Gazette Drouot Watcher периодически опрашивает страницы рубрик "
            "(списки статей) на gazette-drouot.com и показывает уведомление "
            "Windows для каждой новой или обновлённой статьи — щёлкните "
            "уведомление, чтобы открыть её в браузере по умолчанию."
        ),
        "author_prefix": "Автор:",
        "section_task": "Запланированная задача",
        "task_note": (
            "После установки задача работает самостоятельно в фоне с заданным ниже интервалом — не нужно "
            "держать это окно (или приложение) открытым, она запускается автоматически после каждой "
            "перезагрузки ПК. Используйте Включить/Отключить здесь, а не Планировщик заданий Windows."
        ),
        "status_label": "Статус:",
        "status_checking": "проверка...",
        "status_not_installed": "Не установлена",
        "status_ready": "Установлена и включена",
        "status_disabled": "Отключена",
        "btn_refresh": "Обновить",
        "btn_install": "Установить",
        "btn_enable": "Включить",
        "btn_disable": "Отключить",
        "btn_uninstall": "Удалить",
        "log_ok": "OK",
        "log_failed": "ОШИБКА",
        "log_permission_hint": "Похоже на проблему с правами доступа.",
        "dlg_admin_needed_body": (
            "{action} требует прав администратора на этом ПК.\n\n"
            "Перезапустить панель управления от имени администратора и повторить?"
        ),
        "diag_not_installed": (
            "Запланированная задача ещё не установлена, поэтому включать/отключать "
            "нечего. Сначала нажмите «Установить», затем повторите попытку."
        ),
        "diag_python_not_found": (
            "install_task.ps1 не может найти Python в ожидаемом месте.\n\n"
            "Откройте install_task.ps1 в текстовом редакторе и исправьте строку "
            "$PythonExe в соответствии с реальным расположением Python на этом ПК."
        ),
        "diag_config_unreadable": (
            "Не удалось прочитать config.py, чтобы определить интервал проверки — "
            "возможно, файл был изменён и стал недействительным.\n\n"
            "Попробуйте «Сбросить настройки» в разделе «Настройки» ниже, затем "
            "снова нажмите «Установить»."
        ),
        "dlg_action_failed_body": "{action}: ошибка\n\n{detail}",
        "section_settings": "Настройки",
        "field_poll_interval_label": "Интервал проверки (минуты)",
        "field_poll_interval_desc": "Как часто проверяется каждая страница. Только целые минуты.",
        "field_max_pages_label": "Страниц за одну проверку",
        "field_max_pages_desc": "Сколько страниц списка просматривать при каждом запуске. Целое число.",
        "field_page_delay_label": "Задержка между страницами (секунды)",
        "field_page_delay_desc": "Пауза вежливости между запросами страниц в рамках одного запуска. Допустимы дробные значения (напр. 1.5 или 1,5).",
        "field_max_seen_label": "Запоминаемых статей на страницу (макс.)",
        "field_max_seen_desc": "Сколько id уже просмотренных статей хранится в памяти для каждой страницы. Целое число.",
        "field_flood_cap_label": "Макс. отдельных уведомлений за запуск",
        "field_flood_cap_desc": "Сверх этого числа новых статей за раз остальные объединяются в одно сводное уведомление. Целое число.",
        "field_notif_gap_label": "Интервал между уведомлениями (секунды)",
        "field_notif_gap_desc": "Задержка перед показом каждого отдельного уведомления. Целое число.",
        "field_alert_cooldown_label": "Пауза между предупреждениями о проблемах (часы)",
        "field_alert_cooldown_desc": "Минимальное время между повторами одного и того же предупреждения. Допустимы дробные значения (напр. 1.5 или 1,5).",
        "field_headless_label": "Запускать браузер невидимо",
        "field_headless_desc": "Отключено — окно браузера будет видно при каждой проверке, полезно для отладки.",
        "field_browser_label": "Используемый браузер",
        "field_browser_desc": (
            "msedge или chrome (и их варианты -beta/-dev/-canary) напрямую управляют вашим установленным браузером. "
            "firefox использует собственную сборку Firefox от Playwright, а не установленный на ПК — перед "
            "использованием один раз выполните 'playwright install firefox'. Opera, Brave, Vivaldi, Safari и другие "
            "менее распространённые браузеры не поддерживаются — Playwright не умеет ими управлять."
        ),
        "pages_to_watch": "Отслеживаемые страницы",
        "btn_add_page": "Добавить страницу",
        "rubrique_key": "ключ",
        "rubrique_label": "название",
        "rubrique_url": "url",
        "btn_save": "Сохранить",
        "btn_reload": "Перезагрузить (отменить изменения)",
        "btn_reset_defaults": "Сбросить настройки",
        "err_invalid_page_title": "Некорректная страница",
        "err_invalid_page_body": "Каждой странице нужны ключ, название и url — удалите пустые строки.",
        "err_invalid_pages_title": "Некорректные страницы",
        "err_invalid_pages_body": "Нужна хотя бы одна отслеживаемая страница.",
        "err_invalid_value_title": "Некорректное значение",
        "err_invalid_value_body": "«{label}» требует {kind}, получено: {raw}",
        "kind_int": "целое число",
        "kind_float": "дробное число",
        "err_load_failed_title": "Ошибка загрузки",
        "err_load_failed_body": "Не удалось прочитать config.py:\n\n{error}",
        "log_loaded_settings": "Текущие настройки загружены.",
        "err_save_failed_title": "Ошибка сохранения",
        "err_save_failed_body": "Ничего не было записано:\n\n{error}",
        "log_saved_settings": "Настройки сохранены.",
        "dlg_saved_title": "Сохранено",
        "dlg_saved_body": (
            "Настройки сохранены. Вступят в силу при следующем запуске — если вы изменили "
            "интервал проверки, нажмите «Установить» выше, чтобы обновить запланированную задачу."
        ),
        "dlg_reset_confirm_title": "Сбросить настройки",
        "dlg_reset_confirm_body": "Это восстановит все настройки ниже к заводским значениям. Продолжить?",
        "err_reset_failed_title": "Ошибка сброса",
        "err_reset_failed_body": "Ничего не было записано:\n\n{error}",
        "log_reset_settings": "Настройки сброшены к значениям по умолчанию.",
        "dlg_reset_done_title": "Сброшено",
        "dlg_reset_done_body": "Настройки восстановлены к значениям по умолчанию.",
        "section_log": "Журнал действий",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "Язык",
    },
    "zh": {
        "window_title_suffix": "控制面板",
        "description": (
            "Gazette Drouot Watcher 会定期轮询 gazette-drouot.com 的栏目"
            "（文章列表）页面，每当有新文章或文章更新时都会发送一条 Windows 通知"
            "——点击通知即可在默认浏览器中打开该文章。"
        ),
        "author_prefix": "作者：",
        "section_task": "计划任务",
        "task_note": (
            "安装后，程序会按下方设定的间隔在后台自行运行——无需保持此窗口（或应用）打开，"
            "并且每次电脑重启后会自动启动。请使用此处的启用/禁用按钮，而不是 Windows 自带的"
            "任务计划程序。"
        ),
        "status_label": "状态：",
        "status_checking": "检查中……",
        "status_not_installed": "未安装",
        "status_ready": "已安装并已启用",
        "status_disabled": "已禁用",
        "btn_refresh": "刷新",
        "btn_install": "安装",
        "btn_enable": "启用",
        "btn_disable": "禁用",
        "btn_uninstall": "卸载",
        "log_ok": "成功",
        "log_failed": "失败",
        "log_permission_hint": "看起来是权限问题。",
        "dlg_admin_needed_body": (
            "{action} 需要此电脑的管理员权限。\n\n"
            "是否以管理员身份重新启动此控制面板并重试？"
        ),
        "diag_not_installed": (
            "计划任务尚未安装，因此没有可启用/禁用的内容。"
            "请先点击“安装”，然后重试。"
        ),
        "diag_python_not_found": (
            "install_task.ps1 在预期位置找不到 Python。\n\n"
            "请在文本编辑器中打开 install_task.ps1，并将 $PythonExe 这一行"
            "改为此电脑上 Python 的实际安装路径。"
        ),
        "diag_config_unreadable": (
            "无法读取 config.py 以确定检查间隔——该文件可能被编辑成了无效状态。\n\n"
            "请尝试点击下方“设置”区域中的“恢复默认设置”，然后再次点击“安装”。"
        ),
        "dlg_action_failed_body": "{action} 失败：\n\n{detail}",
        "section_settings": "设置",
        "field_poll_interval_label": "检查间隔（分钟）",
        "field_poll_interval_desc": "每个页面的检查频率，仅限整数分钟。",
        "field_max_pages_label": "每次检查扫描的页数",
        "field_max_pages_desc": "每次运行深入查看多少个列表页。整数。",
        "field_page_delay_label": "页面请求间隔（秒）",
        "field_page_delay_desc": "同一次运行中各页面请求之间的礼貌性停顿。允许小数（例如 1.5 或 1,5）。",
        "field_max_seen_label": "每页记忆的文章数上限",
        "field_max_seen_desc": "每个页面在内存中保留多少个已见过的文章 ID。整数。",
        "field_flood_cap_label": "每次运行的最大单独通知数",
        "field_flood_cap_desc": "超过这个数量的新文章将合并为一条汇总通知，而不是逐条发送。整数。",
        "field_notif_gap_label": "通知之间的间隔（秒）",
        "field_notif_gap_desc": "每条单独通知显示之间的延迟。整数。",
        "field_alert_cooldown_label": "问题提醒冷却时间（小时）",
        "field_alert_cooldown_desc": "同一条“出现问题”提醒之间的最短间隔。允许小数（例如 1.5 或 1,5）。",
        "field_headless_label": "以无窗口方式运行浏览器",
        "field_headless_desc": "关闭后，每次检查时浏览器窗口都会可见——便于调试。",
        "field_browser_label": "使用的浏览器",
        "field_browser_desc": (
            "msedge 或 chrome（及其 -beta/-dev/-canary 变体）会直接驱动您电脑上实际安装的浏览器。"
            "firefox 使用 Playwright 自带的 Firefox 构建版本，而非您安装的版本——首次使用前请先运行一次"
            "“playwright install firefox”。Opera、Brave、Vivaldi、Safari 等较小众的浏览器不受支持——"
            "Playwright 无法驱动它们。"
        ),
        "pages_to_watch": "监控的页面",
        "btn_add_page": "添加页面",
        "rubrique_key": "键（key）",
        "rubrique_label": "名称",
        "rubrique_url": "网址",
        "btn_save": "保存",
        "btn_reload": "重新加载（放弃更改）",
        "btn_reset_defaults": "恢复默认设置",
        "err_invalid_page_title": "页面无效",
        "err_invalid_page_body": "每个页面都需要键、名称和网址——请删除任何空白行。",
        "err_invalid_pages_title": "页面无效",
        "err_invalid_pages_body": "至少需要一个要监控的页面。",
        "err_invalid_value_title": "值无效",
        "err_invalid_value_body": "“{label}”需要{kind}，但输入的是：{raw}",
        "kind_int": "一个整数",
        "kind_float": "一个小数",
        "err_load_failed_title": "加载失败",
        "err_load_failed_body": "无法读取 config.py：\n\n{error}",
        "log_loaded_settings": "已加载当前设置。",
        "err_save_failed_title": "保存失败",
        "err_save_failed_body": "未写入任何内容：\n\n{error}",
        "log_saved_settings": "设置已保存。",
        "dlg_saved_title": "已保存",
        "dlg_saved_body": (
            "设置已保存，将在下次运行时生效——如果您修改了检查间隔，"
            "请点击上方的“安装”以更新计划任务。"
        ),
        "dlg_reset_confirm_title": "恢复默认设置",
        "dlg_reset_confirm_body": "这将把下方所有设置恢复为出厂默认值。是否继续？",
        "err_reset_failed_title": "恢复失败",
        "err_reset_failed_body": "未写入任何内容：\n\n{error}",
        "log_reset_settings": "设置已恢复为默认值。",
        "dlg_reset_done_title": "已恢复",
        "dlg_reset_done_body": "设置已恢复为默认值。",
        "section_log": "操作日志",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "语言",
    },
    "ja": {
        "window_title_suffix": "コントロールパネル",
        "description": (
            "Gazette Drouot Watcher は gazette-drouot.com のルブリック（記事一覧）"
            "ページを定期的に確認し、新着または更新された記事があるたびに "
            "Windows 通知を表示します——通知をクリックすると既定のブラウザーで開きます。"
        ),
        "author_prefix": "作者：",
        "section_task": "スケジュールされたタスク",
        "task_note": (
            "インストール後は、下記の間隔で自動的にバックグラウンドで実行されます——このウィンドウ"
            "（やアプリ）を開いたままにする必要はなく、PC の再起動後も自動的に起動します。停止するには"
            "Windows の「タスク スケジューラ」ではなく、こちらの有効化/無効化ボタンを使ってください。"
        ),
        "status_label": "状態：",
        "status_checking": "確認中...",
        "status_not_installed": "未インストール",
        "status_ready": "インストール済み・有効",
        "status_disabled": "無効",
        "btn_refresh": "更新",
        "btn_install": "インストール",
        "btn_enable": "有効化",
        "btn_disable": "無効化",
        "btn_uninstall": "アンインストール",
        "log_ok": "OK",
        "log_failed": "失敗",
        "log_permission_hint": "権限の問題のようです。",
        "dlg_admin_needed_body": (
            "{action} にはこの PC の管理者権限が必要です。\n\n"
            "このコントロールパネルを管理者として再起動して再試行しますか？"
        ),
        "diag_not_installed": (
            "スケジュールされたタスクはまだインストールされていないため、"
            "有効化/無効化できるものがありません。まず「インストール」をクリックしてから再試行してください。"
        ),
        "diag_python_not_found": (
            "install_task.ps1 が想定した場所に Python を見つけられません。\n\n"
            "テキストエディタで install_task.ps1 を開き、$PythonExe の行をこの PC の"
            "実際の Python インストール場所に合わせて修正してください。"
        ),
        "diag_config_unreadable": (
            "確認間隔を判断するための config.py を読み込めませんでした——無効な状態に"
            "編集された可能性があります。\n\n"
            "下記の「設定」セクションで「既定値に戻す」を試してから、再度「インストール」を"
            "クリックしてください。"
        ),
        "dlg_action_failed_body": "{action} に失敗しました：\n\n{detail}",
        "section_settings": "設定",
        "field_poll_interval_label": "確認間隔（分）",
        "field_poll_interval_desc": "各ページを確認する頻度。分単位の整数のみ。",
        "field_max_pages_label": "1回の確認でスキャンするページ数",
        "field_max_pages_desc": "毎回の実行でどれだけ深く一覧ページを確認するか。整数。",
        "field_page_delay_label": "ページ取得間の遅延（秒）",
        "field_page_delay_desc": "1回の実行内でのページリクエスト間の礼儀的な間隔。小数可（例：1.5 または 1,5）。",
        "field_max_seen_label": "ページごとに記憶する記事数（上限）",
        "field_max_seen_desc": "ページごとにメモリに保持する既知の記事IDの数。整数。",
        "field_flood_cap_label": "1回の実行あたりの個別通知の最大数",
        "field_flood_cap_desc": "この件数を超える新着記事は、まとめて1件のサマリー通知になります。整数。",
        "field_notif_gap_label": "通知間の間隔（秒）",
        "field_notif_gap_desc": "個別の通知を表示する間隔。整数。",
        "field_alert_cooldown_label": "問題通知のクールダウン（時間）",
        "field_alert_cooldown_desc": "同じ「問題発生」通知を繰り返す間隔の最小値。小数可（例：1.5 または 1,5）。",
        "field_headless_label": "ブラウザーを非表示で実行",
        "field_headless_desc": "オフにすると、確認のたびにブラウザーウィンドウが表示されます——デバッグに便利です。",
        "field_browser_label": "使用するブラウザー",
        "field_browser_desc": (
            "msedge や chrome（およびその -beta/-dev/-canary バリアント）は、実際にインストールされている"
            "ブラウザーを直接操作します。firefox は Playwright にバンドルされた Firefox を使用し、"
            "インストール済みのものではありません——使用前に一度「playwright install firefox」を"
            "実行してください。Opera、Brave、Vivaldi、Safari などのあまり一般的でないブラウザーは"
            "サポートされていません——Playwright はこれらを操作する方法を知りません。"
        ),
        "pages_to_watch": "監視するページ",
        "btn_add_page": "ページを追加",
        "rubrique_key": "キー",
        "rubrique_label": "ラベル",
        "rubrique_url": "URL",
        "btn_save": "保存",
        "btn_reload": "再読み込み（変更を破棄）",
        "btn_reset_defaults": "既定値に戻す",
        "err_invalid_page_title": "無効なページ",
        "err_invalid_page_body": "各ページにはキー、ラベル、URLが必要です——空の行を削除してください。",
        "err_invalid_pages_title": "無効なページ",
        "err_invalid_pages_body": "監視するページが少なくとも1つ必要です。",
        "err_invalid_value_title": "無効な値",
        "err_invalid_value_body": "「{label}」には{kind}が必要ですが、入力値は「{raw}」でした",
        "kind_int": "整数",
        "kind_float": "小数",
        "err_load_failed_title": "読み込み失敗",
        "err_load_failed_body": "config.py を読み込めませんでした：\n\n{error}",
        "log_loaded_settings": "現在の設定を読み込みました。",
        "err_save_failed_title": "保存失敗",
        "err_save_failed_body": "何も書き込まれませんでした：\n\n{error}",
        "log_saved_settings": "設定を保存しました。",
        "dlg_saved_title": "保存しました",
        "dlg_saved_body": (
            "設定を保存しました。次回の実行時に反映されます——確認間隔を変更した場合は、"
            "上の「インストール」をクリックしてスケジュールされたタスクを更新してください。"
        ),
        "dlg_reset_confirm_title": "既定値に戻す",
        "dlg_reset_confirm_body": "以下のすべての設定を工場出荷時の値に戻します。続行しますか？",
        "err_reset_failed_title": "リセット失敗",
        "err_reset_failed_body": "何も書き込まれませんでした：\n\n{error}",
        "log_reset_settings": "設定を既定値にリセットしました。",
        "dlg_reset_done_title": "リセット完了",
        "dlg_reset_done_body": "設定を既定値に戻しました。",
        "section_log": "操作ログ",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "言語",
    },
    "hi": {
        "window_title_suffix": "नियंत्रण पैनल",
        "description": (
            "Gazette Drouot Watcher gazette-drouot.com के रुब्रीक (लेख सूची) पेजों को "
            "समय-समय पर जाँचता है और हर नए या अपडेट किए गए लेख के लिए एक Windows "
            "सूचना दिखाता है — सूचना पर क्लिक करके उसे अपने डिफ़ॉल्ट ब्राउज़र में खोलें।"
        ),
        "author_prefix": "लेखक:",
        "section_task": "अनुसूचित कार्य",
        "task_note": (
            "इंस्टॉल होने के बाद, यह नीचे दिए गए अंतराल पर पृष्ठभूमि में स्वतः चलता रहता है — इस विंडो "
            "(या ऐप) को खुला रखने की ज़रूरत नहीं है, और हर PC पुनरारंभ के बाद यह स्वयं शुरू हो जाता है। "
            "इसे रोकने के लिए Windows के अपने टास्क शेड्यूलर के बजाय यहाँ के सक्षम/अक्षम बटन का उपयोग करें।"
        ),
        "status_label": "स्थिति:",
        "status_checking": "जाँच हो रही है...",
        "status_not_installed": "इंस्टॉल नहीं है",
        "status_ready": "इंस्टॉल और सक्षम",
        "status_disabled": "अक्षम",
        "btn_refresh": "रीफ्रेश करें",
        "btn_install": "इंस्टॉल करें",
        "btn_enable": "सक्षम करें",
        "btn_disable": "अक्षम करें",
        "btn_uninstall": "अनइंस्टॉल करें",
        "log_ok": "ठीक है",
        "log_failed": "विफल",
        "log_permission_hint": "यह अनुमति संबंधी समस्या लगती है।",
        "dlg_admin_needed_body": (
            "{action} के लिए इस PC पर व्यवस्थापक अधिकार आवश्यक हैं।\n\n"
            "क्या इस नियंत्रण पैनल को व्यवस्थापक के रूप में फिर से लॉन्च करके पुनः प्रयास करें?"
        ),
        "diag_not_installed": (
            "अनुसूचित कार्य अभी तक इंस्टॉल नहीं है, इसलिए सक्षम/अक्षम करने के लिए कुछ नहीं है। "
            "पहले 'इंस्टॉल करें' पर क्लिक करें, फिर पुनः प्रयास करें।"
        ),
        "diag_python_not_found": (
            "install_task.ps1 को अपेक्षित स्थान पर Python नहीं मिल रहा।\n\n"
            "install_task.ps1 को टेक्स्ट एडिटर में खोलें और $PythonExe वाली लाइन को इस PC पर "
            "Python के वास्तविक इंस्टॉल स्थान से मेल खाने के लिए अपडेट करें।"
        ),
        "diag_config_unreadable": (
            "जाँच अंतराल तय करने के लिए config.py नहीं पढ़ा जा सका — हो सकता है इसे संपादित करके "
            "अमान्य स्थिति में डाल दिया गया हो।\n\n"
            "नीचे सेटिंग्स सेक्शन में 'डिफ़ॉल्ट पर रीसेट करें' आज़माएँ, फिर दोबारा 'इंस्टॉल करें' पर क्लिक करें।"
        ),
        "dlg_action_failed_body": "{action} विफल रहा:\n\n{detail}",
        "section_settings": "सेटिंग्स",
        "field_poll_interval_label": "जाँच अंतराल (मिनट)",
        "field_poll_interval_desc": "हर पेज कितनी बार जाँचा जाता है। केवल पूर्ण मिनट।",
        "field_max_pages_label": "प्रति जाँच स्कैन किए गए पेज",
        "field_max_pages_desc": "हर बार कितने लिस्टिंग पेज गहराई से देखे जाएँ। पूर्ण संख्या।",
        "field_page_delay_label": "पेज फ़ेच के बीच देरी (सेकंड)",
        "field_page_delay_desc": "एक ही रन के भीतर पेज अनुरोधों के बीच शिष्टाचार विराम। दशमलव मान्य (जैसे 1.5 या 1,5)।",
        "field_max_seen_label": "प्रति पेज याद रखे गए लेख (अधिकतम)",
        "field_max_seen_desc": "प्रति पेज मेमोरी में कितने पहले देखे गए लेख id रखे जाएँ। पूर्ण संख्या।",
        "field_flood_cap_label": "प्रति रन अधिकतम अलग सूचनाएँ",
        "field_flood_cap_desc": "एक साथ इतने नए लेखों से अधिक होने पर बाकी को एक सारांश सूचना में मिला दिया जाता है। पूर्ण संख्या।",
        "field_notif_gap_label": "सूचनाओं के बीच अंतराल (सेकंड)",
        "field_notif_gap_desc": "हर अलग सूचना दिखाने के बीच की देरी। पूर्ण संख्या।",
        "field_alert_cooldown_label": "समस्या-चेतावनी कूलडाउन (घंटे)",
        "field_alert_cooldown_desc": "एक ही 'कुछ गड़बड़ है' चेतावनी की पुनरावृत्तियों के बीच न्यूनतम समय। दशमलव मान्य (जैसे 1.5 या 1,5)।",
        "field_headless_label": "ब्राउज़र को अदृश्य रूप से चलाएँ",
        "field_headless_desc": "बंद होने पर हर जाँच के दौरान ब्राउज़र विंडो दिखाई देगी — डीबगिंग के लिए उपयोगी।",
        "field_browser_label": "उपयोग किया गया ब्राउज़र",
        "field_browser_desc": (
            "msedge या chrome (और उनके -beta/-dev/-canary संस्करण) आपके वास्तविक इंस्टॉल किए गए ब्राउज़र को "
            "सीधे चलाते हैं। firefox Playwright के अपने बंडल किए गए Firefox का उपयोग करता है, आपके इंस्टॉल किए "
            "गए का नहीं — उपयोग से पहले एक बार 'playwright install firefox' चलाएँ। Opera, Brave, Vivaldi, "
            "Safari और अन्य कम प्रचलित ब्राउज़र समर्थित नहीं हैं — Playwright को उन्हें चलाना नहीं आता।"
        ),
        "pages_to_watch": "देखे जा रहे पेज",
        "btn_add_page": "पेज जोड़ें",
        "rubrique_key": "key",
        "rubrique_label": "लेबल",
        "rubrique_url": "url",
        "btn_save": "सहेजें",
        "btn_reload": "पुनः लोड करें (परिवर्तन छोड़ें)",
        "btn_reset_defaults": "डिफ़ॉल्ट पर रीसेट करें",
        "err_invalid_page_title": "अमान्य पेज",
        "err_invalid_page_body": "हर पेज के लिए key, लेबल और url ज़रूरी है — कोई भी खाली पंक्ति हटाएँ।",
        "err_invalid_pages_title": "अमान्य पेज",
        "err_invalid_pages_body": "देखने के लिए कम से कम एक पेज आवश्यक है।",
        "err_invalid_value_title": "अमान्य मान",
        "err_invalid_value_body": "'{label}' के लिए {kind} चाहिए, मिला: {raw}",
        "kind_int": "एक पूर्ण संख्या",
        "kind_float": "एक दशमलव संख्या",
        "err_load_failed_title": "लोड विफल",
        "err_load_failed_body": "config.py नहीं पढ़ा जा सका:\n\n{error}",
        "log_loaded_settings": "वर्तमान सेटिंग्स लोड हो गईं।",
        "err_save_failed_title": "सहेजना विफल",
        "err_save_failed_body": "कुछ भी नहीं लिखा गया:\n\n{error}",
        "log_saved_settings": "सेटिंग्स सहेजी गईं।",
        "dlg_saved_title": "सहेजा गया",
        "dlg_saved_body": (
            "सेटिंग्स सहेज ली गई हैं। अगली बार चलने पर लागू होंगी — यदि आपने जाँच अंतराल बदला है, "
            "तो अनुसूचित कार्य अपडेट करने के लिए ऊपर 'इंस्टॉल करें' पर क्लिक करें।"
        ),
        "dlg_reset_confirm_title": "डिफ़ॉल्ट पर रीसेट करें",
        "dlg_reset_confirm_body": "यह नीचे की सभी सेटिंग्स को उनके फ़ैक्टरी डिफ़ॉल्ट पर पुनर्स्थापित कर देगा। जारी रखें?",
        "err_reset_failed_title": "रीसेट विफल",
        "err_reset_failed_body": "कुछ भी नहीं लिखा गया:\n\n{error}",
        "log_reset_settings": "सेटिंग्स डिफ़ॉल्ट पर रीसेट कर दी गईं।",
        "dlg_reset_done_title": "रीसेट हो गया",
        "dlg_reset_done_body": "सेटिंग्स डिफ़ॉल्ट पर पुनर्स्थापित कर दी गई हैं।",
        "section_log": "कार्रवाई लॉग",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "भाषा",
    },
    "ar": {
        "window_title_suffix": "لوحة التحكم",
        "description": (
            "يقوم Gazette Drouot Watcher باستطلاع صفحات الأقسام (قوائم المقالات) "
            "في gazette-drouot.com بشكل دوري، ويعرض إشعار Windows لكل مقال جديد "
            "أو محدَّث — انقر على الإشعار لفتحه في متصفحك الافتراضي."
        ),
        "author_prefix": "المؤلف:",
        "section_task": "المهمة المجدولة",
        "task_note": (
            "بعد التثبيت، تعمل هذه المهمة بمفردها في الخلفية حسب الفاصل الزمني المحدد أدناه — لا حاجة لإبقاء "
            "هذه النافذة (أو التطبيق) مفتوحة، وتبدأ تلقائيًا بعد كل إعادة تشغيل للجهاز. استخدم أزرار "
            "التفعيل/التعطيل هنا بدلاً من جدولة المهام في Windows."
        ),
        "status_label": "الحالة:",
        "status_checking": "جارٍ التحقق...",
        "status_not_installed": "غير مثبّتة",
        "status_ready": "مثبتة ومفعّلة",
        "status_disabled": "معطّلة",
        "btn_refresh": "تحديث",
        "btn_install": "تثبيت",
        "btn_enable": "تفعيل",
        "btn_disable": "تعطيل",
        "btn_uninstall": "إلغاء التثبيت",
        "log_ok": "تم",
        "log_failed": "فشل",
        "log_permission_hint": "يبدو أنها مشكلة في الأذونات.",
        "dlg_admin_needed_body": (
            "يتطلب {action} صلاحيات المسؤول على هذا الجهاز.\n\n"
            "هل تريد إعادة تشغيل لوحة التحكم هذه كمسؤول والمحاولة مرة أخرى؟"
        ),
        "diag_not_installed": (
            "المهمة المجدولة غير مثبّتة بعد، لذا لا يوجد ما يمكن تفعيله أو تعطيله. "
            "انقر أولاً على 'تثبيت'، ثم أعد المحاولة."
        ),
        "diag_python_not_found": (
            "لا يستطيع install_task.ps1 العثور على Python في الموقع المتوقع.\n\n"
            "افتح install_task.ps1 في محرر نصوص وحدّث سطر $PythonExe ليطابق "
            "موقع تثبيت Python الفعلي على هذا الجهاز."
        ),
        "diag_config_unreadable": (
            "تعذّرت قراءة config.py لتحديد فاصل التحقق — ربما تم تعديله إلى حالة غير صالحة.\n\n"
            "جرّب 'إعادة التعيين إلى الإعدادات الافتراضية' في قسم الإعدادات أدناه، ثم انقر "
            "مرة أخرى على 'تثبيت'."
        ),
        "dlg_action_failed_body": "فشل {action}:\n\n{detail}",
        "section_settings": "الإعدادات",
        "field_poll_interval_label": "فاصل التحقق (بالدقائق)",
        "field_poll_interval_desc": "عدد مرات التحقق من كل صفحة. دقائق كاملة فقط.",
        "field_max_pages_label": "عدد الصفحات المفحوصة في كل تحقق",
        "field_max_pages_desc": "عدد صفحات القائمة التي يتم فحصها بعمق في كل تشغيل. رقم صحيح.",
        "field_page_delay_label": "التأخير بين طلبات الصفحات (بالثواني)",
        "field_page_delay_desc": "فترة توقف مهذبة بين طلبات الصفحات ضمن نفس التشغيل. تُقبل الكسور العشرية (مثل 1.5 أو 1,5).",
        "field_max_seen_label": "المقالات المحفوظة لكل صفحة (الحد الأقصى)",
        "field_max_seen_desc": "عدد معرّفات المقالات المشاهدة مسبقًا المحفوظة في الذاكرة لكل صفحة. رقم صحيح.",
        "field_flood_cap_label": "الحد الأقصى للإشعارات الفردية لكل تشغيل",
        "field_flood_cap_desc": "بعد هذا العدد من المقالات الجديدة دفعة واحدة، يتم تجميع الباقي في إشعار ملخّص واحد. رقم صحيح.",
        "field_notif_gap_label": "الفاصل بين الإشعارات (بالثواني)",
        "field_notif_gap_desc": "التأخير بين عرض كل إشعار فردي. رقم صحيح.",
        "field_alert_cooldown_label": "فترة تهدئة تنبيهات المشاكل (بالساعات)",
        "field_alert_cooldown_desc": "أقل وقت بين تكرارات نفس تنبيه 'هناك مشكلة'. تُقبل الكسور العشرية (مثل 1.5 أو 1,5).",
        "field_headless_label": "تشغيل المتصفح بشكل غير مرئي",
        "field_headless_desc": "عند الإيقاف، ستكون نافذة المتصفح مرئية أثناء كل تحقق — مفيد لأغراض التصحيح.",
        "field_browser_label": "المتصفح المستخدم",
        "field_browser_desc": (
            "يقوم msedge أو chrome (وإصداراتهما -beta/-dev/-canary) بتشغيل متصفحك المثبت فعليًا مباشرة. "
            "يستخدم firefox نسخة Firefox المدمجة الخاصة بـ Playwright، وليست النسخة المثبتة لديك — شغّل "
            "'playwright install firefox' مرة واحدة قبل استخدامه. المتصفحات الأقل شيوعًا مثل Opera وBrave "
            "وVivaldi وSafari غير مدعومة — لا يعرف Playwright كيفية تشغيلها."
        ),
        "pages_to_watch": "الصفحات المُراقَبة",
        "btn_add_page": "إضافة صفحة",
        "rubrique_key": "المفتاح",
        "rubrique_label": "التسمية",
        "rubrique_url": "الرابط",
        "btn_save": "حفظ",
        "btn_reload": "إعادة التحميل (تجاهل التغييرات)",
        "btn_reset_defaults": "إعادة التعيين إلى الإعدادات الافتراضية",
        "err_invalid_page_title": "صفحة غير صالحة",
        "err_invalid_page_body": "تحتاج كل صفحة إلى مفتاح وتسمية ورابط — احذف أي صف فارغ.",
        "err_invalid_pages_title": "صفحات غير صالحة",
        "err_invalid_pages_body": "يلزم وجود صفحة واحدة على الأقل للمراقبة.",
        "err_invalid_value_title": "قيمة غير صالحة",
        "err_invalid_value_body": "يحتاج '{label}' إلى {kind}، والقيمة المُدخلة: {raw}",
        "kind_int": "رقم صحيح",
        "kind_float": "رقم عشري",
        "err_load_failed_title": "فشل التحميل",
        "err_load_failed_body": "تعذّرت قراءة config.py:\n\n{error}",
        "log_loaded_settings": "تم تحميل الإعدادات الحالية.",
        "err_save_failed_title": "فشل الحفظ",
        "err_save_failed_body": "لم يتم كتابة أي شيء:\n\n{error}",
        "log_saved_settings": "تم حفظ الإعدادات.",
        "dlg_saved_title": "تم الحفظ",
        "dlg_saved_body": (
            "تم حفظ الإعدادات. ستصبح سارية في التشغيل التالي — إذا غيّرت فاصل التحقق، "
            "انقر على 'تثبيت' أعلاه لتحديث المهمة المجدولة."
        ),
        "dlg_reset_confirm_title": "إعادة التعيين إلى الإعدادات الافتراضية",
        "dlg_reset_confirm_body": "سيؤدي هذا إلى إعادة جميع الإعدادات أدناه إلى قيمها الافتراضية. المتابعة؟",
        "err_reset_failed_title": "فشلت إعادة التعيين",
        "err_reset_failed_body": "لم يتم كتابة أي شيء:\n\n{error}",
        "log_reset_settings": "تمت إعادة تعيين الإعدادات إلى الوضع الافتراضي.",
        "dlg_reset_done_title": "تمت إعادة التعيين",
        "dlg_reset_done_body": "تمت استعادة الإعدادات الافتراضية.",
        "section_log": "سجل الإجراءات",
        "log_action_dashes": "--- {action} ---",
        "language_menu_title": "اللغة",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Looks up `key` in `lang`'s translation dict, falling back to English
    if either the language or the specific key is missing. Any **kwargs are
    used to .format() placeholders in the resulting string."""
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    text = table.get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def detect_os_language() -> str:
    """Best-effort detection of the Windows UI language, mapped to one of
    our supported codes — falls back to English if detection fails or the
    detected language isn't one we support."""
    try:
        import ctypes
        import locale

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        win_locale = locale.windows_locale.get(lcid, "")
        code = win_locale.split("_")[0].lower()
        return code if code in _SUPPORTED_CODES else "en"
    except Exception:
        return "en"
