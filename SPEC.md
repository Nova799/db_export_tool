# DB Export Tool — Spécification & Plan

## 1. Idée de base

Outil desktop qui permet de **récupérer des données de tables de bases de données** (PostgreSQL, MySQL, SQL Server) selon une fréquence (hebdomadaire, mensuelle, trimestrielle) et de les **déposer dans des dossiers SharePoint**.

L'utilisateur configure lui-même :
- les **connexions** aux bases de données (host, port, db, user, password),
- les **récupérations** (recovery) : nom, connexion associée, script SQL à exécuter, dossier SharePoint cible, fréquence,
- les **dossiers SharePoint** cibles (site, drive/bibliothèque, chemin) avec leurs informations de connexion.

Chaque exécution est tracée (date, lignes exportées, statut, durée, fichier CSV généré).

## 2. État actuel du projet (diagnostic)

### Ce qui existe déjà
- `__init__.py` : version 1.0.0, description alignée avec l'idée.
- `config.py` : hashing Argon2 des mots de passe (connexions DB).
- `database.py` : SQLite locale avec 3 tables :
  - `connections` (id, name, type, host, port, database, username, password_hash, created_at, last_test)
  - `recoveries` (id, name, connection_id, script_path, sharepoint_path, frequency, last_execution, next_execution, status)
  - `executions` (id, recovery_id, date_execution, lignes_exportees, statut, duree_ms, csv_filename)
- `app.py` (racine) : fenêtre Tkinter placeholder listant les fonctionnalités prévues.
- `requirements.txt` : tkinter, argon2-cffi, aiosmtplib, requests, sqlite3.

### Ce qui manque vs l'idée
| Besoin de l'idée | État actuel | Écart |
|---|---|---|
| Connexions PG/MySQL/SQL Server | Schéma + placeholder test | Aucun driver réel, test_connection factice |
| Scripts SQL par récupération | Champ `script_path` (chemin fichier) | Pas d'UI pour créer/éditer, pas d'exécution réelle |
| Fréquence hebdo/mensuel/trimestriel | Champ `frequency` (texte libre) | Pas de scheduler, pas de calcul de `next_execution` |
| Dossier SharePoint cible | Champ `sharepoint_path` (texte) | Pas d'abstraction "dossier SharePoint" avec site/drive/chemin, pas d'upload |
| Auth SharePoint | — | Pas d'intégration Graph API |
| Export CSV | — | Non implémenté |
| Historique exécutions | Table existe | Pas d'UI, pas d'écriture réelle |
| UI CRUD | Fenêtre placeholder | Rien |
| Planification automatique | — | Non implémenté |
| Notifications email | aiosmtplib prévu | Non utilisé |

### Points de vigilance
- `test_connection` remplacé par de vrais tests via les connecteurs.
- Table `sharepoint_folders` ajoutée (site, drive, chemin, auth).
- Pas de table `users` : l'app est supposée mono-utilisateur desktop.
- Drivers SQL Server : `pyodbc` non installé (nécessite unixodbc-dev) ; alternative `pymssql`. À décider.
- **Décision** : les mots de passe de connexion DB et les secrets SharePoint sont stockés de façon réversible (Fernet) dans les colonnes historiques `password_hash` / `client_secret_hash`, car ils doivent être réutilisés pour les exécutions automatiques. Le hashing Argon2 reste pour un éventuel login applicatif.

## 2b. Compatibilité multi-plateforme

L'application est conçue pour fonctionner sur **Windows, Linux et macOS** sans modification du code :

- **Chemins** : utilisation exclusive de `os.path.join` et `os.path.dirname(os.path.abspath(__file__))`. Aucun chemin absolu codé en dur.
- **GUI** : Tkinter (bibliothèque standard) + `sv-ttk` (wheels pour les 3 OS).
- **Drivers DB** : `psycopg2-binary`, `pymysql`, `pymssql` fournissent des wheels pour Windows, Linux et macOS (pas de compilation requise).
- **Dépendances** : `cryptography`, `argon2-cffi`, `aiosmtplib`, `requests`, `APScheduler` sont toutes disponibles sur les 3 plateformes.
- **Chiffrement** : `os.chmod` est un no-op sur Windows mais ne lève pas d'erreur.
- **Dialogues fichier** : `tkinter.filedialog` utilise les dialogues natifs de chaque OS.
- **Icône** : `iconphoto` avec PNG fonctionne sur les 3 OS (Tk 8.6+).
- **Threading** : `threading` est standard.

### Différences à documenter pour l'utilisateur

| Élément | Windows | Linux | macOS |
|---|---|---|---|
| Activation venv | `.venv\Scripts\activate.bat` | `source .venv/bin/activate` | `source .venv/bin/activate` |
| Lancement | `.venv\Scripts\python.exe app.py` | `.venv/bin/python app.py` | `.venv/bin/python app.py` |
| PyInstaller `--add-data` | séparateur `;` | séparateur `:` | séparateur `:` |
| Affichage | natif | X11/Wayland (XWayland) | natif |

### Points de vigilance

- Sur macOS, l'application peut nécessiter d'être lancée depuis un terminal pour voir les logs stderr.
- Sur Linux Wayland pur (sans XWayland), Tkinter peut ne pas fonctionner ; installer `python3-tk` si nécessaire.
- Le packaging PyInstaller n'a pas été testé sur toutes les plateformes.

## 3. Architecture proposée

```
db_tool/
  __init__.py
  config.py              # hashing, settings, chemins
  database.py            # SQLite + CRUD (schéma étendu)
  models.py              # dataclasses
  connectors/
    base.py              # interface BaseConnector
    postgres.py          # psycopg2
    mysql.py             # pymysql
    mssql.py             # pyodbc ou pymssql (import conditionnel)
    factory.py           # get_connector(type, config)
  sharepoint/
    base.py              # interface BaseSharePointClient
    graph.py             # Microsoft Graph (app registration / OAuth)
  services/
    executor.py          # run recovery : SQL -> rows -> CSV -> upload SP
    scheduler.py          # calcul next_execution + déclenchement (APScheduler)
  ui/
    main.py              # fenêtre principale + navigation
    connections.py       # CRUD connexions + test
    recoveries.py        # CRUD récupérations
    sharepoint_folders.py# CRUD dossiers SharePoint
    history.py           # historique exécutions
  app.py                 # entry point desktop
```

Couche de données : SQLite locale (app_data/tool.db). Couche métier découplée de l'UI pour être testable.

## 4. Schéma de données étendu (proposition)

```sql
-- existant, inchangé
connections (...)
recoveries (..., sharepoint_folder_id INTEGER FK -> sharepoint_folders.id)
executions (...)
-- nouveaux
sharepoint_folders (
  id, name, site_url, drive_id, folder_path,
  auth_mode ('app' | 'oauth'), tenant_id, client_id,
  client_secret_hash, created_at, last_test
)
app_settings (key, value)   -- ex: dossier d'export local, smtp, etc.
```

Les scripts SQL restent des **fichiers .sql sur disque** (choix utilisateur) ; `recoveries.script_path` pointe vers le fichier. L'UI permet de sélectionner/créer le fichier.

## 5. Authentification SharePoint — options

1. **App registration (client secret)** : application Azure AD avec permissions `Sites.ReadWrite.All`. Simple pour un outil automatisé ; le secret est stocké haché/chiffré localement. Recommandé pour démarrer.
2. **OAuth2 utilisateur (device code)** : l'utilisateur se connecte avec son compte Microsoft ; plus sécurisé, flux interactif.
3. **Les deux** : app registration par défaut + option OAuth.

> À décider selon le contexte IT (admin Azure disponible ?). L'abstraction `BaseSharePointClient` permet de changer sans toucher au reste.

## 6. Roadmap par étapes

- **Étape 0** (fait) : diagnostic + spec + squelette de dossiers.
- **Étape 1** (fait) : CRUD connexions + test de connexion réel (Postgres/MySQL/MSSQL) + UI Tkinter.
- **Étape 2** (fait) : CRUD dossiers SharePoint + abstraction client Graph (test de connexion).
- **Étape 3** (fait) : CRUD récupérations liées à connexion + dossier SP + script .sql.
- **Étape 4** (fait) : Exécution manuelle d'une récupération : run SQL, export CSV, upload SharePoint.
- **Étape 5** (fait) : Historique des exécutions + UI.
- **Étape 6** (fait) : calcul de `next_execution` + planification automatique APScheduler (BackgroundScheduler, cron hebdo/mensuel/trimestriel, rattrapage au démarrage, UI on/off).
- **Étape 7** (à faire) : notifications email + packaging (PyInstaller) + tests.
- **Étape 2** : CRUD dossiers SharePoint (modèle + UI) + abstraction client Graph (mock d'abord).
- **Étape 3** : CRUD récupérations liées à connexion + dossier SP + script .sql.
- **Étape 4** : Exécution manuelle d'une récupération : run SQL, export CSV, upload SharePoint (Graph réel).
- **Étape 5** : Historique des exécutions + UI.
- **Étape 6** : Planification (APScheduler) + calcul next_execution + fréquences.
- **Étape 7** : Notifications email + packaging (PyInstaller) + tests.

## 7. Choix techniques retenus
- UI : Tkinter (déjà prévu, standard).
- DB locale : SQLite (déjà en place).
- Drivers DB : psycopg2 (PG), pymysql (MySQL), pyodbc/pymssql (SQL Server, optionnel).
- SharePoint : Microsoft Graph via `requests` (pas de SDK lourd).
- Planification : APScheduler (à installer).
- Packaging : PyInstaller (plus tard).

## 8. Variables de dates dans les requêtes SQL

Les scripts SQL peuvent contenir des placeholders `{{nom_variable}}` qui sont résolus à l'exécution.

Variables automatiques (calculées selon la fréquence et la date du jour) :
- Dates simples : `today`, `yesterday`, `tomorrow`, `now`, `timestamp`
- Semaine : `week_start`, `week_end`
- Mois : `month_start`, `month_end`
- Année : `year_start`, `year_end`
- Période liée à la fréquence : `period_start`, `period_end`, `period_label`
- Contexte : `recovery_name`, `connection_name`

Variables personnalisées : définissables par récupération (nom, type text/date, valeur, format strftime pour les dates). Stockées dans `recovery_variables`.

Résolution : substitution textuelle avec échappement des quotes simples. Format de date modifiable via `{{nom:format}}` (ex: `{{today:%d/%m/%Y}}`).

L'UI d'exécution permet de surcharger les valeurs pour un run donné et d'afficher un aperçu du SQL résolu avant exécution.

## 9. Planification automatique (APScheduler)

- `BackgroundScheduler` lancé dans un thread d'arrière-plan au démarrage (si activé dans les paramètres).
- Triggers cron : hebdo = lundi à l'heure configurée ; mensuel = 1er du mois ; trimestriel = 1er jan/avr/juil/oct.
- `misfire_grace_time=3600s`, `coalesce=True`, `max_instances=1`.
- Au démarrage : reprogrammation de toutes les récupérations actives + rattrapage des exécutions manquées (une par récupération).
- Activation/désactivation via la barre de statut de l'UI ; heure configurable (0-23h).
- Persistance légère : reconstruction au démarrage depuis la table `recoveries` (pas de JobStore DB). Paramètres stockés dans `app_settings` (`schedule_enabled`, `schedule_hour`).
- Arrêt propre à la fermeture de la fenêtre.

## 10. Paramètres d'export CSV

Configurables depuis l'onglet Paramètres (stockés dans `app_settings`) :
- Séparateur : `,`, `;`, tab, `|`
- Encodage : utf-8, utf-8-sig (BOM Excel), latin-1, cp1252
- En-tête : oui/non
- Quoting : minimal, all, nonnumeric, none
- Fin de ligne : LF ou CRLF

## 11. Notifications

- Mode : email uniquement (SMTP).
- Paramètres dans `app_settings` : smtp_host, smtp_port, smtp_user, smtp_password (chiffré), smtp_from, smtp_to, smtp_use_tls, notify_on_error, notify_on_success.
- Déclenchement : à la fin de chaque exécution planifiée (APScheduler). Bouton "Tester l'envoi" dans l'UI.
- Bibliothèque : aiosmtplib.

## 12. Questions ouvertes
- SQL Server : pyodbc (nécessite installation système) ou pymssql ?
- Mono ou multi-utilisateur ? (actuellement mono desktop)
- Format d'export : CSV uniquement ou aussi Excel/JSON ?
- Notifications : email uniquement ou aussi Teams/Slack ?
