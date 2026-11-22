# DB Export Tool

Outil desktop permettant de **récupérer des données depuis des bases de données** (PostgreSQL, MySQL, SQL Server) selon une fréquence (manuelle, hebdomadaire, mensuelle, trimestrielle) et de les **déposer automatiquement dans des dossiers SharePoint**, au format CSV configurable.

---

## Table des matières

1. [Présentation](#1-présentation)
2. [Prérequis](#2-prérequis)
3. [Installation](#3-installation)
4. [Lancement](#4-lancement)
5. [Premiers pas (configuration initiale)](#5-premiers-pas-configuration-initiale)
6. [Onglet Connexions](#6-onglet-connexions)
7. [Onglet Dossiers SharePoint](#7-onglet-dossiers-sharepoint)
8. [Onglet Récupérations](#8-onglet-récupérations)
9. [Variables dans les requêtes SQL](#9-variables-dans-les-requêtes-sql)
10. [Onglet Exécution](#10-onglet-exécution)
11. [Onglet Historique](#11-onglet-historique)
12. [Onglet Paramètres](#12-onglet-paramètres)
13. [Planification automatique](#13-planification-automatique)
14. [Notifications par email](#14-notifications-par-email)
15. [Format CSV d'export](#15-format-csv-dexport)
16. [Structure du projet](#16-structure-du-projet)
17. [Raccourcis clavier](#17-raccourcis-clavier)
18. [Dépannage (FAQ)](#18-dépannage-faq)
19. [Packaging en exécutable](#19-packaging-en-exécutable)

---

## 1. Présentation

DB Export Tool est une application desktop (Tkinter) qui permet à un utilisateur non-développeur de :

- **Configurer des connexions** à des bases de données PostgreSQL, MySQL ou SQL Server.
- **Définir des récupérations** : pour chaque récupération, on associe une connexion, un script SQL (fichier `.sql`), un dossier SharePoint cible et une fréquence.
- **Exécuter manuellement** une récupération : le SQL est lancé, le résultat est exporté en CSV, puis uploadé dans SharePoint.
- **Planifier automatiquement** les récupérations (hebdomadaire, mensuelle, trimestrielle) via APScheduler.
- **Tracer** toutes les exécutions (date, lignes, statut, durée, fichier généré).
- **Notifier** par email en cas de succès/échec.

L'interface est en français et utilise un thème moderne (Sun Valley).

---

## 2. Prérequis

### Compatibilité multi-plateforme

L'application est **compatible Windows, Linux et macOS**. Le code utilise exclusivement des bibliothèques Python portables (`os.path`, `pathlib` implicite via `os.path.join`) et des dépendances qui fournissent des wheels pour les trois plateformes.

| Plateforme | Statut | Notes |
|---|---|---|
| Windows 10/11 | ✅ Supporté | Lancement via `.venv\Scripts\python.exe` |
| Linux (Ubuntu, Debian, Fedora, etc.) | ✅ Supporté | Nécessite un serveur X (X11 ou Wayland avec XWayland) |
| macOS (10.15+) | ✅ Supporté | Lancement via `.venv/bin/python` |

- **Python 3.10 ou supérieur** (recommandé : 3.12).
- Un **affichage graphique** (natif sous Windows/macOS, X11/Wayland sous Linux).
- Accès réseau aux bases de données cibles et à SharePoint (si utilisé).
- Pour SQL Server : aucune dépendance système supplémentaire (le driver `pymssql` est pur Python et fournit des wheels pour les 3 OS).

Vérifier la version de Python :

```bash
python --version
```

---

## 3. Installation

### 3.1. Extraire le projet

Décompressez l'archive `db_export_tool.zip` dans un dossier de votre choix, par exemple :

```bash
unzip db_export_tool.zip -d ~/db_export_tool
cd ~/db_export_tool
```

### 3.2. Créer un environnement virtuel

**Linux / macOS :**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell) :**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (cmd) :**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3.3. Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Les dépendances installées sont :

| Package | Rôle |
|---|---|
| `sv-ttk` | Thème moderne Tkinter |
| `argon2-cffi` | Hashing de mots de passe (login applicatif) |
| `cryptography` | Chiffrement réversible des secrets (mots de passe DB, secrets SharePoint) |
| `aiosmtplib` | Envoi d'emails (notifications) |
| `requests` | Client HTTP (Microsoft Graph / SharePoint) |
| `psycopg2-binary` | Driver PostgreSQL |
| `pymysql` | Driver MySQL |
| `pymssql` | Driver SQL Server |
| `APScheduler` | Planification automatique des récupérations |

> `tkinter` et `sqlite3` sont inclus dans Python (bibliothèque standard), rien à installer.

---

## 4. Lancement

Depuis le dossier du projet, avec le venv activé :

```bash
python app.py
```

Ou sans activer le venv :

**Linux / macOS :**

```bash
.venv/bin/python app.py
```

**Windows :**

```cmd
.venv\Scripts\python.exe app.py
```

La fenêtre principale s'ouvre avec 6 onglets : **Connexions**, **SharePoint**, **Récupérations**, **Exécution**, **Historique**, **Paramètres**.

---

## 5. Premiers pas (configuration initiale)

L'application est mono-utilisateur et stocke ses données dans `db_tool/app_data/tool.db` (SQLite). Au premier lancement, la base est créée automatiquement.

### Étape 1 — Créer une connexion à une base de données

1. Ouvrir l'onglet **Connexions**.
2. Cliquer sur **Nouvelle connexion**.
3. Remplir les champs :
   - **Nom** : un nom parlant (ex: `Prod PostgreSQL`).
   - **Type** : `postgres`, `mysql` ou `mssql`.
   - **Hôte** : adresse du serveur (ex: `db.example.com`).
   - **Port** : laisser vide pour la valeur par défaut (5432 / 3306 / 1433).
   - **Base** : nom de la base de données.
   - **Utilisateur** : compte de lecture.
   - **Mot de passe** : mot de passe du compte.
4. Cliquer sur **Enregistrer**.
5. Sélectionner la connexion et cliquer sur **Tester** pour vérifier.

> Le mot de passe est stocké chiffré (réversible) pour permettre les exécutions automatiques.

### Étape 2 — Créer un dossier SharePoint (optionnel)

Si vous souhaitez déposer les exports dans SharePoint :

1. Ouvrir l'onglet **Dossiers SharePoint**.
2. Cliquer sur **Nouveau dossier**.
3. Remplir :
   - **Nom** : nom d'affichage.
   - **URL du site** : ex. `https://tenant.sharepoint.com/sites/MonSite`.
   - **Drive ID** : optionnel (laisser vide pour utiliser le drive par défaut du site).
   - **Chemin dossier** : chemin dans la bibliothèque (ex: `/Exports`).
   - **Mode auth** : `app` (recommandé) ou `oauth`.
   - **Tenant ID**, **Client ID**, **Client secret** : identifiants de l'application Azure AD (voir section 7).
4. Cliquer sur **Enregistrer**.
5. Sélectionner le dossier et cliquer sur **Tester** pour vérifier la connexion Graph.

### Étape 3 — Créer une récupération

1. Ouvrir l'onglet **Récupérations**.
2. Cliquer sur **Nouvelle récupération**.
3. Remplir :
   - **Nom** : ex. `Ventes mensuelles`.
   - **Connexion** : choisir la connexion créée à l'étape 1.
   - **Script SQL** : cliquer sur **Parcourir** et sélectionner un fichier `.sql`.
   - **Dossier SharePoint** : choisir un dossier (ou `(aucun)` pour un export local uniquement).
   - **Fréquence** : `manual`, `weekly`, `monthly` ou `quarterly`.
   - **Chemin SP (optionnel)** : sous-chemin dans le dossier SharePoint.
4. Cliquer sur **Enregistrer**.

### Étape 4 — Exécuter

1. Ouvrir l'onglet **Exécution**.
2. Sélectionner la récupération.
3. Cliquer sur **Exécuter...** : une boîte de dialogue s'ouvre avec les variables détectées (modifiables) et un aperçu du SQL résolu.
4. Cliquer sur **Exécuter**.

Le résultat apparaît dans l'onglet **Historique**.

---

## 6. Onglet Connexions

Gère les connexions aux bases de données.

| Bouton | Action |
|---|---|
| **Nouvelle connexion** | Ouvre un formulaire de création |
| **Modifier** | Modifie la connexion sélectionnée |
| **Supprimer** | Supprime la connexion (et ses récupérations associées) |
| **Tester** | Tente une connexion réelle à la base (thread d'arrière-plan, progressbar) |
| **Rafraîchir** | Recharge la liste |

**Types supportés :** `postgres`, `mysql`, `mssql`.

**Ports par défaut :** PostgreSQL 5432, MySQL 3306, SQL Server 1433.

---

## 7. Onglet Dossiers SharePoint

Gère les dossiers SharePoint cibles.

### Configuration Azure AD (app registration)

Pour utiliser SharePoint, il faut créer une application dans Azure AD :

1. Aller sur [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**.
2. Nommer l'application (ex. `DB Export Tool`), compte dans ce répertoire uniquement.
3. Dans **Certificates & secrets**, créer un **Client secret** (noter la valeur).
4. Dans **API permissions**, ajouter **Microsoft Graph** → **Application permissions** → `Sites.ReadWrite.All` (et `Files.ReadWrite.All` si nécessaire).
5. Cliquer sur **Grant admin consent**.
6. Noter le **Tenant ID**, **Client ID** et le **Client secret**.

Renseigner ces valeurs dans le formulaire "Nouveau dossier SharePoint" (mode auth = `app`).

### Champs du formulaire

| Champ | Description |
|---|---|
| Nom | Nom d'affichage |
| URL du site | `https://tenant.sharepoint.com/sites/MonSite` |
| Drive ID | Optionnel (drive par défaut si vide) |
| Chemin dossier | Chemin dans la bibliothèque (`/Exports`) |
| Mode auth | `app` (client secret) ou `oauth` |
| Tenant ID | ID du tenant Azure AD |
| Client ID | ID de l'application |
| Client secret | Secret de l'application (stocké chiffré) |

---

## 8. Onglet Récupérations

Gère les récupérations (requêtes planifiées).

| Colonne | Description |
|---|---|
| id | Identifiant |
| name | Nom de la récupération |
| connection | Connexion associée |
| script_path | Chemin du fichier `.sql` |
| sharepoint_folder | Dossier SharePoint cible |
| frequency | `manual`, `weekly`, `monthly`, `quarterly` |
| status | `pending`, `success`, `error`, `partial` |
| last_execution | Date de la dernière exécution |

**Bouton Variables** : ouvre le gestionnaire de variables personnalisées pour la récupération sélectionnée (voir section 9).

---

## 9. Variables dans les requêtes SQL

Les scripts SQL peuvent contenir des placeholders `{{nom}}` ou `{{nom:format}}` qui sont résolus à l'exécution.

### Variables automatiques

Calculées selon la fréquence et la date du jour :

| Variable | Description |
|---|---|
| `today` | Date du jour (YYYY-MM-DD) |
| `yesterday` | Hier |
| `tomorrow` | Demain |
| `now` | Date/heure courante (ISO) |
| `timestamp` | Horodatage compact (YYYYMMDD_HHMMSS) |
| `week_start` / `week_end` | Début/fin de la semaine courante |
| `month_start` / `month_end` | Début/fin du mois courant |
| `year_start` / `year_end` | Début/fin de l'année courante |
| `period_start` / `period_end` | Période précédente selon la fréquence (semaine/mois/trimestre précédent) |
| `period_label` | Libellé de la période (`YYYY-MM-DD_YYYY-MM-DD`) |
| `recovery_name` | Nom de la récupération |
| `connection_name` | Nom de la connexion |

### Variables personnalisées

Définies par récupération via le bouton **Variables**. Champs :

- **Nom** : nom de la variable (utilisé dans `{{nom}}`).
- **Type** : `text` ou `date`.
- **Valeur** : la valeur (pour une date, format ISO `YYYY-MM-DD`).
- **Format** : format strftime pour les dates (ex: `%d/%m/%Y`).

### Syntaxe dans le SQL

```sql
SELECT * FROM ventes
WHERE date_vente >= '{{period_start}}'
  AND date_vente <= '{{period_end}}'
  AND categorie = '{{categorie}}';
```

> **Important** : mettez les quotes vous-même autour des placeholders (`'{{period_start}}'`), car la substitution injecte la valeur brute.

### Format personnalisé

```
{{today:%d/%m/%Y}}   -- affiche la date au format jj/mm/aaaa
```

### Aperçu et surcharge

Dans l'onglet **Exécution**, la boîte de dialogue affiche toutes les variables détectées avec leurs valeurs par défaut (modifiables pour ce run uniquement) et un aperçu du SQL résolu avant exécution.

---

## 10. Onglet Exécution

Permet de lancer manuellement une récupération.

1. Sélectionner la récupération dans la liste déroulante.
2. Cliquer sur **Exécuter...**.
3. Dans la boîte de dialogue :
   - Modifier les valeurs des variables si besoin.
   - Cliquer sur **Aperçu** pour voir le SQL résolu.
   - Cliquer sur **Exécuter** pour lancer.
4. Le résultat s'affiche dans l'onglet **Historique**.

La progressbar dans la barre de statut indique l'avancement.

---

## 11. Onglet Historique

Liste toutes les exécutions passées.

| Colonne | Description |
|---|---|
| id | Identifiant de l'exécution |
| recovery_id | Récupération concernée |
| date_execution | Date/heure de l'exécution |
| lignes_exportees | Nombre de lignes exportées |
| statut | `success`, `error`, `partial` |
| duree_ms | Durée en millisecondes |
| csv_filename | Nom du fichier CSV généré |

Cliquer sur l'en-tête d'une colonne pour trier.

---

## 12. Onglet Paramètres

### Format CSV

| Paramètre | Options | Défaut |
|---|---|---|
| Séparateur | `,`, `;`, tab, `\|` | `,` |
| Encodage | `utf-8`, `utf-8-sig` (BOM Excel), `latin-1`, `cp1252` | `utf-8-sig` |
| En-tête | oui / non | oui |
| Quoting | `minimal`, `all`, `nonnumeric`, `none` | `minimal` |
| Fin de ligne | LF / CRLF | LF |

Ces paramètres s'appliquent à toutes les prochaines exécutions.

### Notifications par email (SMTP)

| Champ | Description |
|---|---|
| Serveur SMTP | ex. `smtp.gmail.com` |
| Port | ex. `587` |
| Utilisateur | compte SMTP |
| Mot de passe | mot de passe SMTP (stocké chiffré) |
| Expéditeur | adresse d'envoi |
| Destinataire | adresse de réception |
| TLS | oui / non |
| Notifier si erreur | oui / non |
| Notifier si succès | oui / non |

Bouton **Tester l'envoi** : envoie un email de test.

### Thème

Bouton **Thème clair/sombre** dans le header pour basculer entre les deux thèmes (préférence sauvegardée).

---

## 13. Planification automatique

L'application utilise APScheduler (BackgroundScheduler) pour exécuter automatiquement les récupérations selon leur fréquence.

### Activation

Dans la **barre de statut** (en bas de la fenêtre) :
- Régler l'**heure** (0-23).
- Cliquer sur **Activer/Désactiver planification**.

La planification est persistée dans `app_settings` (`schedule_enabled`, `schedule_hour`).

### Triggers cron

| Fréquence | Déclenchement |
|---|---|
| `weekly` | Tous les lundis à l'heure configurée |
| `monthly` | Le 1er de chaque mois à l'heure configurée |
| `quarterly` | Le 1er janvier, avril, juillet, octobre à l'heure configurée |

### Rattrapage

Au démarrage de l'application, les exécutions manquées (si l'app était fermée) sont rattrapées (une par récupération).

### Paramètres

- `misfire_grace_time` : 1 heure (une exécution manquée de moins d'1h est rattrapée).
- `coalesce` : activé (si plusieurs exécutions manquées, une seule est exécutée).
- `max_instances` : 1 (pas d'exécutions parallèles pour la même récupération).

### Important

La planification **ne fonctionne que si l'application reste ouverte**. Pour une exécution même app fermée, il faudrait passer à une planification externe (cron / Task Scheduler) — non implémenté.

---

## 14. Notifications par email

- Mode : **email uniquement** (SMTP).
- Déclenchement : à la fin de chaque exécution **planifiée** (APScheduler).
- Contenu : nom de la récupération, statut, détails (lignes, CSV, erreur éventuelle).
- Configurable : notifier si erreur et/ou si succès.

Les exécutions manuelles (onglet Exécution) n'envoient pas d'email (l'utilisateur voit le résultat dans l'UI).

---

## 15. Format CSV d'export

Les exports sont écrits dans `db_tool/app_data/exports/` avec le nom `{nom_recuperation}_{timestamp}.csv`.

Le format est configurable (voir section 12). Si un dossier SharePoint est configuré, le fichier est uploadé via Microsoft Graph.

### Colonnes du CSV

Les colonnes correspondent aux colonnes retournées par la requête SQL (ordre préservé).

---

## 16. Structure du projet

```
db_export_tool/
├── app.py                      # Point d'entrée
├── requirements.txt            # Dépendances
├── SPEC.md                     # Spécification technique
├── README.md                   # Ce fichier
├── logo.png                    # Logo de l'application
├── db_tool/
│   ├── __init__.py             # Version
│   ├── config.py               # Hashing (Argon2) + chiffrement (Fernet)
│   ├── database.py             # SQLite : schéma + CRUD
│   ├── models.py               # Dataclasses
│   ├── connectors/             # Drivers DB
│   │   ├── base.py
│   │   ├── postgres.py
│   │   ├── mysql.py
│   │   ├── mssql.py
│   │   └── __init__.py
│   ├── sharepoint/             # Intégration SharePoint
│   │   ├── graph.py
│   │   └── __init__.py
│   ├── services/               # Logique métier
│   │   ├── executor.py         # Exécution d'une récupération
│   │   ├── scheduler.py        # Calcul de next_execution
│   │   ├── scheduler_service.py# APScheduler
│   │   ├── variables.py        # Résolution des variables SQL
│   │   ├── notifications.py    # Emails
│   │   └── __init__.py
│   └── ui/                     # Interface Tkinter
│       ├── main.py             # Fenêtre principale
│       ├── connections_tab.py
│       ├── sharepoint_tab.py
│       ├── recoveries_tab.py
│       ├── execution_tab.py
│       ├── history_tab.py
│       ├── settings_tab.py
│       ├── tooltip.py
│       ├── tree_sort.py
│       └── __init__.py
└── db_tool/app_data/           # Données locales (DB, exports, clé)
    ├── tool.db
    ├── .secret.key
    └── exports/
```

---

## 17. Raccourcis clavier

| Raccourci | Action |
|---|---|
| `Ctrl+Q` | Quitter l'application |
| `F5` | Rafraîchir tous les onglets |

---

## 18. Dépannage (FAQ)

### L'application ne démarre pas

- Vérifier que Python 3.10+ est installé : `python --version`.
- Vérifier que le venv est activé ou utiliser `.venv/bin/python app.py`.
- Vérifier les dépendances : `pip install -r requirements.txt`.

### Erreur "No module named 'sv_ttk'"

Le thème n'est pas installé. Lancer : `pip install sv-ttk`.

### Test de connexion échoue

- Vérifier l'hôte, le port, la base, l'utilisateur et le mot de passe.
- Vérifier que le serveur DB accepte les connexions distantes (firewall).
- Pour PostgreSQL : vérifier `pg_hba.conf`.
- Pour SQL Server : vérifier que TCP/IP est activé et que le port 1433 est ouvert.

### Test SharePoint échoue

- Vérifier le Tenant ID, Client ID et Client secret.
- Vérifier que l'admin consent a été accordé pour les permissions Graph.
- Vérifier l'URL du site (format `https://tenant.sharepoint.com/sites/Site`).
- Vérifier que l'application a les permissions `Sites.ReadWrite.All`.

### L'export CSV est vide

- Vérifier que la requête SQL retourne des résultats.
- Vérifier les variables (`{{...}}`) : une variable inconnue reste telle quelle dans le SQL et peut causer une erreur.
- Consulter l'onglet Historique pour le statut et l'erreur.

### La planification ne se déclenche pas

- Vérifier que l'application reste ouverte.
- Vérifier que la planification est activée (barre de statut).
- Vérifier l'heure configurée.
- Les récupérations doivent avoir une fréquence ≠ `manual`.

### Les emails ne sont pas envoyés

- Vérifier la configuration SMTP dans l'onglet Paramètres.
- Utiliser le bouton **Tester l'envoi**.
- Vérifier que "Notifier si erreur/succès" est activé.
- Vérifier les identifiants et le port (587 avec TLS, 465 sans).

### Où sont stockées les données ?

- Base SQLite : `db_tool/app_data/tool.db`.
- Exports CSV : `db_tool/app_data/exports/`.
- Clé de chiffrement : `db_tool/app_data/.secret.key`.

> **Attention** : ne pas partager le fichier `.secret.key` ni la base `tool.db` (ils contiennent des secrets chiffrés).

---

## 19. Packaging en exécutable

Pour créer un exécutable autonome (sans Python installé) :

**Linux / macOS :**

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "db_tool:db_tool" --add-data "logo.png:." app.py
```

**Windows (cmd ou PowerShell) :**

```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "db_tool;db_tool" --add-data "logo.png;." app.py
```

> Note : le séparateur de `--add-data` est `:` sous Linux/macOS et `;` sous Windows.

L'exécutable sera dans le dossier `dist/`.

### Build automatique via GitHub Actions

Un workflow (`.github/workflows/build-windows.yml`) est fourni pour builder automatiquement un `.exe` sur un runner Windows :

1. Pousser le code sur GitHub (branche `main` ou `master`).
2. Le workflow se déclenche automatiquement (ou manuellement via **Actions** → **Run workflow**).
3. Télécharger l'artefact `DBExportTool-Windows` depuis l'onglet **Actions** → **Artifacts**.

Le fichier `build.bat` est aussi fourni pour un build local sur Windows (double-clic).

> Note : le packaging n'a pas été testé. Des ajustements peuvent être nécessaires (chemins de données, etc.).

---

## Licence

Projet personnel — usage libre.
