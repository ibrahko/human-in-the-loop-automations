# Automatisations avec un humain dans la boucle

[English](README.md) · **Français**

Deux petites automatisations [n8n](https://n8n.io) qui fonctionnent et qui utilisent un modèle d'IA **sans lui laisser la décision**. Chacune est livrée avec ses garde-fous, les chiffres qui montrent si elle vaut la peine d'être gardée, et une règle pour l'arrêter.

| Projet | Ce qu'il automatise | Ce qui reste humain |
|---|---|---|
| [Tri des offres d'emploi](job-offer-triage/README.fr.md) | Lit chaque matin des flux publics d'offres d'emploi, fait noter par Gemini chaque nouvelle offre selon des critères écrits, envoie un résumé classé sur Telegram | La décision de postuler. L'IA ne fait que classer. |
| [Assistant support](support-assistant/README.fr.md) | Classe chaque demande client et rédige un brouillon de réponse | Chaque réponse. Les remboursements, les réclamations et les brouillons à risque vont à une personne, sans brouillon. |

## La méthode

Ces workflows suivent une seule liste de contrôle, décrite dans [GUARDRAILS.fr.md](GUARDRAILS.fr.md) :

1. **Décider ce que l'IA ne doit jamais faire.** Dans ces workflows, elle n'envoie rien, ne postule à rien, ne rembourse rien et ne promet rien.
2. **Vérifier chaque réponse de l'IA avant de l'utiliser.** Les réponses doivent respecter un schéma JSON, et les réponses incohérentes sont rejetées. Un appel qui échoue est quand même enregistré, jamais perdu en silence.
3. **Garder une personne responsable là où est le risque.** Les cas sensibles vont directement à un humain, et les autres attendent une décision humaine.
4. **Mesurer par rapport à l'humain.** Chaque projet a un rapport hebdomadaire qui compare l'IA à ce que les personnes ont réellement décidé.
5. **Écrire à l'avance la règle d'arrêt.** Chaque rapport hebdomadaire affiche **PAUSE** quand l'IA ne correspond plus aux décisions humaines : le taux d'accord pour les offres d'emploi, le taux de rejet pour les brouillons.

## Démarrage rapide (Windows, macOS ou Linux)

**Première fois ? Suivez [SETUP.fr.md](SETUP.fr.md) : chaque clic, dans l'ordre, avec les pièges habituels.**

Il vous faut [Docker Desktop](https://www.docker.com/products/docker-desktop/), une [clé API Gemini](https://aistudio.google.com/apikey) gratuite et un bot Telegram (créé en deux minutes avec [@BotFather](https://t.me/BotFather)).

```bash
git clone https://github.com/ibrahko/human-in-the-loop-automations.git
cd human-in-the-loop-automations
docker compose up -d        # then wait until http://localhost:5678 opens in your browser
docker compose exec n8n n8n import:workflow --separate --input=/import/job-offer-triage
docker compose exec n8n n8n import:workflow --separate --input=/import/support-assistant
```

Ouvrez ensuite http://localhost:5678, créez votre compte et suivez les étapes de configuration du README de chaque projet. Elles couvrent les identifiants, le nœud `Config` et la création unique des tables.

Les planifications utilisent le fuseau horaire défini dans `docker-compose.yml` (`Africa/Bamako`). Changez-y `GENERIC_TIMEZONE` et `TZ` si vous vivez ailleurs.

## Comment c'est testé

Les sept workflows sont testés de bout en bout sur une vraie instance n8n (2.40.7), en local et sur GitHub Actions. Gemini, Telegram et les flux RSS sont remplacés par un serveur factice local (`tests/mock_server.py`). Les 17 tests de bout en bout, plus un test unitaire de la liste des mots à risque, couvrent :

- **Tri des offres d'emploi :**
  - les doublons, les offres trop anciennes et les offres hors sujet sont écartés avant tout appel à l'IA ;
  - les titres contenant `&`, `<`, `>` ou `_` sont échappés, pour que le message Telegram ne puisse pas être cassé ;
  - les réponses de l'IA mal formées, vides, incohérentes ou en échec sont signalées, et aucune n'arrête l'exécution ;
  - il y a un seul résumé par exécution et rien n'est renvoyé deux fois ;
  - la limite par exécution est respectée ;
  - le rapport se met en pause quand le taux d'accord baisse.
- **Assistant support :**
  - les vrais formulaires sont publiés et remplis comme le ferait un navigateur ; le client ne voit jamais le formulaire de relecture ;
  - les brouillons attendent un humain ; le lien de relecture exige son jeton à usage unique, ne fonctionne qu'une fois et enregistre "as is" (tel quel), "edited" (modifié) ou "rejected" (rejeté) ;
  - une réponse vide n'est jamais envoyée ;
  - les remboursements, les promesses à risque, une confiance trop faible, une panne de l'IA et les brouillons suspendus vont à une personne ;
  - le rapport suspend les brouillons quand trop de brouillons sont rejetés.

```bash
npm install -g n8n@2.40.7   # Node.js 24
bash tests/run_all.sh       # bash: Linux, macOS, or WSL / Git Bash on Windows
```

Les fichiers JSON des workflows sont générés à partir de `build/build.py` et des scripts de `build/js/`, pour que la logique puisse être lue et relue comme du code. Après une modification, lancez `python build/build.py`.

## Auteur

**Ibrahima Koné**, ingénieur back-end Python et IA, Bamako, Mali
[GitHub](https://github.com/ibrahko) · [LinkedIn](https://www.linkedin.com/in/ibrahima-koné-632006a1)

## Licence

MIT © 2026 Ibrahima Koné
