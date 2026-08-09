🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

Surveille une ou plusieurs pages de rubrique (listes d'articles) de gazette-drouot.com et affiche une notification Windows pour chaque article nouveau ou mis à jour — cliquez sur une notification pour l'ouvrir dans votre navigateur par défaut.

## Fonctionnement

- À chaque exécution, les `MAX_PAGES` premières pages de chaque rubrique configurée sont entièrement analysées (pas seulement jusqu'à ce qu'un article « connu » soit trouvé — les tests ont montré que la pagination du site n'est pas fiable chronologiquement, un arrêt anticipé pourrait donc silencieusement manquer de vraies nouveautés).
- Chaque article trouvé est comparé à l'état enregistré (`state/<rubrique-key>.json`, sous `%LOCALAPPDATA%\GazetteDrouotWatcher\`) par son identifiant numérique **et** sa date de publication. Nouvel id → notification. Id connu mais date différente de la dernière fois → notification à nouveau (l'article a probablement été republié/modifié). Un article sans date affichée n'est notifié qu'une seule fois, puis jamais revérifié.
- La première exécution pour une rubrique se contente d'enregistrer ce qui est présent comme référence, silencieusement — pas d'avalanche de notifications pour des articles préexistants à l'installation.
- Si plus de `FLOOD_CAP` articles nouveaux/modifiés apparaissent sur une rubrique en une seule exécution, seuls les premiers ont leur propre notification — le reste est regroupé en une notification récapitulative « N articles de plus ».

## Installation

- **Le VPN doit être désactivé** pendant l'exécution — Cloudflare impose un défi interactif aux IP de VPN que l'automatisation ne peut pas résoudre. Une IP domestique classique passe sans problème.
- Nécessite Microsoft Edge installé (utilise votre Edge système via le `channel="msedge"` de Playwright, aucun téléchargement de navigateur séparé n'est nécessaire).
- `pip install -r requirements.txt`

## Configuration

**`config.py` est le fichier unique à modifier** pour tout : quelles pages surveiller, la fréquence de vérification, la profondeur d'analyse, les limites de notification, les délais d'alerte, etc. — chaque paramètre a un commentaire explicatif (ou modifiez-les via l'onglet Paramètres du panneau de configuration, voir ci-dessous). Il se trouve dans `%LOCALAPPDATA%\GazetteDrouotWatcher\config.py` (créé automatiquement à cet endroit au premier lancement — pas à côté du `.exe`), de sorte qu'il survit au déplacement ou au remplacement du `.exe` lui-même. Après toute modification, le changement prend effet à la prochaine exécution, **sauf** `POLL_INTERVAL_MINUTES`, qui nécessite aussi de cliquer de nouveau sur **Installer** dans le panneau de configuration pour mettre à jour la tâche planifiée Windows avec le nouvel intervalle.

## Panneau de configuration (GUI)

**C'est l'application** — un seul `.exe` autonome, aucune installation Python séparée ni fichiers de script nécessaires sur la machine qui l'exécute. Une fenêtre de bureau pour tout : installer / activer / désactiver / désinstaller la tâche planifiée (via l'API native du Planificateur de tâches directement, sans PowerShell), et un panneau de paramètres (avec un « Réinitialiser aux valeurs par défaut » en cas de problème) au lieu de modifier le fichier de configuration à la main. L'icône du drapeau change la langue de l'interface (anglais, 中文, español, हिन्दी, العربية, português, русский, français, 日本語, allemand — suit par défaut la langue de Windows, revient à l'anglais sinon) ; l'icône soleil/lune bascule entre clair/sombre (suit par défaut le thème de Windows). Les deux choix sont conservés dans `%LOCALAPPDATA%\GazetteDrouotWatcher\gui_prefs.json`.

**Si vous avez juste le `.exe` :** double-cliquez sur `GazetteDrouotWatcher.exe` — rien d'autre à installer, et rien d'autre nécessaire à côté. Il est entièrement autonome : `config.py`, `gui_prefs.json`, `state/` et `logs/` sont tous créés sous `%LOCALAPPDATA%\GazetteDrouotWatcher\` au premier lancement, pas à côté du `.exe` lui-même, si bien qu'il ne disperse jamais de fichiers dans le dossier depuis lequel il est exécuté. Cliquez sur **Installer** dans la fenêtre pour enregistrer la tâche planifiée — à partir de là, la vérification se fait automatiquement en arrière-plan, à l'intervalle défini dans `config.py`, sans que cette fenêtre (ni l'application) n'ait besoin de rester ouverte, et elle redémarre d'elle-même à chaque redémarrage du PC.

**En lançant depuis les sources :** double-cliquez sur `main.pyw` (Windows lance les fichiers `.pyw` via `pythonw.exe`, pas de fenêtre de console), ou :
```
pythonw.exe main.pyw
```

**Pour construire le `.exe` vous-même** (il est exclu de git — pas commité dans les sources, reconstruisez-le ou récupérez-le depuis une Release) :
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
Copiez ensuite `dist/GazetteDrouotWatcher.exe` à la racine du projet (à côté de `main.pyw`) et supprimez les dossiers/fichiers restants `build/`, `dist/` et `*.spec`.

## Exécution manuelle

`main.pyw --watch` (ou l'équivalent `GazetteDrouotWatcher.exe --watch`) est ce que la tâche planifiée appelle réellement — exécute une vérification puis se termine, sans interface. C'est aussi équivalent à :
```
python -m gazette_watcher.watcher
```

## En cas de problème

Deux notifications d'alerte distinctes existent, chacune limitée à une fois maximum par `ALERT_COOLDOWN_HOURS` (config.py) pour qu'un problème persistant ne spamme pas une notification à chaque exécution :

- **« blocked by Cloudflare »** — la protection anti-robots du site a intercepté la requête. Presque toujours résolu en désactivant un VPN.
- **« needs an update »** — une page s'est chargée normalement mais son HTML ne correspond plus à ce que ce script attend. gazette-drouot.com a probablement changé la mise en page de ses pages, et les sélecteurs du scraper (`gazette_watcher/scraper.py`) doivent être mis à jour en conséquence.

`%LOCALAPPDATA%\GazetteDrouotWatcher\logs\watcher.log` contient le détail complet de chaque exécution — à consulter en premier si les notifications s'arrêtent.

## Tester sans toucher au vrai site

`test/` contient un petit environnement de test avec un faux site local, pour tester la logique de scraping/notification isolément, sans solliciter le vrai site ni dépendre de son contenu en direct. Voir `test/README.md`.

## Ajouter une autre page à surveiller

Ajoutez une nouvelle entrée à `RUBRIQUES` dans `config.py` — tant que la page utilise la même structure de carte `div.articleResume`, rien d'autre n'a besoin de changer.
