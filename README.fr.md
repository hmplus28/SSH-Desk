<div align="center">

**Gestionnaire professionnel de connexions SSH pour Ubuntu — GUI + CLI, un moteur partagé.**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · [فارسی](README.fa.md) · [العربية](README.ar.md) · [简体中文](README.zh.md) · [Русский](README.ru.md) · [Español](README.es.md) · **Français**

</div>

SSH Desk est un produit réel et installable (pas un prototype) pour gérer tous vos serveurs SSH : les mots de passe sont stockés **uniquement** dans GNOME Keyring (Secret Service), le moteur SSH est le **OpenSSH du système**, et le terminal intégré est une **vraie PTY** (vim/nano, couleurs, Ctrl+C, redimensionnement — tout fonctionne réellement).

- 🖥️ **Interface graphique** (PySide6) : thèmes sombre/clair, persan/anglais (RTL complet), onglets de terminal réels, gestionnaire de fichiers SFTP, tunnels, clés, historique
- ⌨️ **CLI** (Typer) : fonctionne **sans** la GUI ; nom de commande configurable (`sss`, `cnc`, `sshgo`, …) ; complétion bash/zsh incluant les alias de serveurs
- 🔐 **Sécurité d'abord** : vérification stricte des host keys avec boîte de dialogue d'empreinte ; les secrets n'atteignent jamais la base de données/logs/argv ; sans `sshpass` ni `StrictHostKeyChecking=no`
- 🌐 **Résistant aux coupures réseau** : chaîne de miroirs PyPI (officiel → ArvanCloud (Iran) → TUNA → Aliyun → Tencent) et installation entièrement hors ligne via `install.sh --offline`

📄 **[Guide utilisateur complet (PDF, en français)](docs/SSH-Desk-User-Guide-fr.pdf)** — 16 pages illustrées : installation hors ligne, référence CLI complète, terminal, SFTP, tunnels et modèle de sécurité. Le guide existe aussi en 6 autres langues : [English](docs/SSH-Desk-User-Guide-en.pdf) · [فارسی](docs/SSH-Desk-User-Guide-fa.pdf) · [العربية](docs/SSH-Desk-User-Guide-ar.pdf) · [简体中文](docs/SSH-Desk-User-Guide-zh.pdf) · [Русский](docs/SSH-Desk-User-Guide-ru.pdf) · [Español](docs/SSH-Desk-User-Guide-es.pdf)

---

## Démarrage rapide

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

Ensuite :

```bash
ssh-desk          # interface graphique
sss add           # ajouter le premier serveur
sss prod          # connexion (shell interactif dans votre terminal)
```

Paquet DEB et installation manuelle : [docs/INSTALLATION.md](docs/INSTALLATION.md).
Réseau faible ou coupé : `bash scripts/download_wheels.sh --mirror-name ir` puis `bash scripts/install.sh --offline`.

## La CLI en 30 secondes

```bash
sss                      # résumé + astuces
sss list                 # tableau des serveurs
sss add                  # assistant interactif (ou --alias/--host/...)
sss info prod            # détails complets
sss test prod            # test de connectivité
sss prod                 # shell interactif au chemin par défaut
sss prod nginx           # connexion à un chemin enregistré
sss prod /etc/nginx      # connexion à un chemin absolu
sss prod --exec "uptime" # exécuter une commande (rien n'est enregistré)
sss prod --user ubuntu --port 2222   # substitution pour cette exécution
sss history              # historique des connexions
sss current              # sessions actives + tunnels en cours
sss tunnel db            # démarrer un tunnel nommé (survit au terminal)
sss config cli-name cnc  # renommer la commande au niveau du système
sss --help               # référence complète
```

## Fonctionnalités

| Domaine | Ce qui fonctionne |
| --- | --- |
| Serveurs | CRUD, alias uniques, groupes, tags, favoris, duplication, recherche/tri/filtres |
| Authentification | Mot de passe (Keyring), clé privée (+phrase dans Keyring), agent SSH, interactive |
| Chemins | Chemin par défaut + chemins enregistrés nommés (`sss prod nginx`), quoting sûr |
| Terminal | Vraie PTY (OpenSSH), multi-onglets, couleurs, vim/nano, redimensionnement, copier/coller |
| Fichiers | Gestionnaire SFTP à deux volets : upload/download/mkdir/renommage/chmod/édition/suppression + transfert serveur↔serveur |
| Clés | Génération Ed25519/RSA/ECDSA au format OpenSSH, import, empreinte, export de clé publique, guide `ssh-copy-id` |
| Tunnels | Local / Remote / SOCKS dynamique, démarrage/arrêt, démon détaché, suivi d'état |
| Jump hosts | `ProxyCommand` via `ssh -W` au travers de tout serveur enregistré (chaînes imbriquées) |
| Commandes | Commandes enregistrées par serveur ou globales, confirmation pour les dangereuses |
| Historique | Connexion/déconnexion, durée, statut, erreurs (sans contenu du terminal ni mots de passe) |
| Import/Export | Import de `~/.ssh/config` avec aperçu et déduplication, sauvegarde/restauration TOML (secrets optionnels) |

## Modèle de sécurité (version courte)

1. Les mots de passe/phrases vivent **uniquement** dans le Secret Service (GNOME Keyring) ; la BD ne stocke qu'une référence non secrète.
2. OpenSSH reçoit les secrets via un **helper askpass** durci — jamais en argv, jamais en variable d'environnement, jamais via sshpass.
3. La vérification des host keys est forcée (`StrictHostKeyChecking=yes`) : inconnue → dialogue d'empreinte ; modifiée → avertissement fort.
4. Fichiers de base de données/config en `0600`/`0700` ; logs assainis ; aucun démon root.

Détails complets : [docs/SECURITY.md](docs/SECURITY.md).

## Développement

```bash
pip install -e .[dev]
pytest          # 54 tests
ruff check .    # clean
```

Architecture et internes : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## Prérequis

- Ubuntu 22.04 / 24.04+ (ou toute distribution basée sur Debian)
- Python 3.10+ (3.12 recommandé), `openssh-client`
- GNOME Keyring pour le stockage des mots de passe (`sudo apt install gnome-keyring`)

## Licence

MIT — voir [LICENSE](LICENSE).
