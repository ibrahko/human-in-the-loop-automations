# Installation pas à pas (Windows)

[English](SETUP.md) · **Français**

Chaque clic, dans l'ordre. Ce guide a été écrit en faisant vraiment l'installation : il signale donc les endroits où l'on bloque souvent. Comptez environ 45 minutes la première fois.

## 0. Ce qu'il vous faut

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), installé et **lancé** (l'icône de la baleine dans la barre des tâches ne bouge plus).
- Un compte Google, pour obtenir une clé API Gemini gratuite.
- Telegram sur votre téléphone ou votre ordinateur. [Telegram Web](https://web.telegram.org) fonctionne aussi.
- Git, seulement si vous voulez télécharger le projet avec `git clone`.

## 1. Démarrer n8n

1. Ouvrez un terminal (PowerShell) dans le dossier du projet, celui qui contient `docker-compose.yml`.
2. Lancez :
   ```
   docker compose up -d
   ```
3. Attendez que http://localhost:5678 s'ouvre dans votre navigateur. Le premier démarrage peut prendre une minute.
4. Créez votre compte n8n. Il reste sur votre ordinateur.
5. **Si une fenêtre "Connect a model" apparaît** (l'assistant de n8n, qui demande une clé Anthropic), fermez-la avec le ✕. Ces workflows n'en ont pas besoin, et c'est un service payant.

## 2. Importer les six workflows

1. Dans le même terminal, lancez :
   ```
   docker compose exec n8n n8n import:workflow --separate --input=/import/job-offer-triage
   docker compose exec n8n n8n import:workflow --separate --input=/import/support-assistant
   ```
2. Chaque commande doit afficher `Successfully imported 3 workflows`.
3. Rechargez la page de n8n. Dans **Overview → Workflows** (vue d'ensemble → workflows), vous voyez maintenant six workflows : trois qui commencent par "Job offers" et trois par "Support".

> ⚠️ **Importer à nouveau remplace les workflows.** Vos choix d'identifiants et vos valeurs dans **Config** sont perdus. Refaites les étapes 6 et 8 après chaque nouvel import. Vos tables de données et vos identifiants eux-mêmes sont conservés.

## 3. Créer la clé Gemini

1. Allez sur https://aistudio.google.com/apikey et connectez-vous avec votre compte Google.
2. Cliquez sur **Create API key** (créer une clé API) et copiez la clé. Elle commence en général par `AIza`.
3. Ne la partagez jamais. Si vous pensez qu'elle a fuité, supprimez-la sur la même page et créez-en une nouvelle.

## 4. Ajouter la clé Gemini dans n8n

1. Dans n8n, allez dans **Overview → Credentials → Create credential** (vue d'ensemble → identifiants → créer un identifiant).
2. Cherchez **Header Auth** (authentification par en-tête) et sélectionnez-le.
3. Remplissez les champs :
   - **Name** : `x-goog-api-key` (exactement ceci ; c'est le nom attendu par Google) ;
   - **Value** : votre clé Gemini ;
   - **Allowed HTTP Request Domains** (domaines autorisés) : choisissez **Specific Domains**, puis dans **Allowed Domains** tapez `generativelanguage.googleapis.com`. Votre clé ne pourra alors être envoyée qu'à Google.
4. Facultatif : cliquez sur le titre "Header Auth account" en haut à gauche et renommez-le `Gemini API key`.
5. Cliquez sur **Save** (enregistrer).

## 5. Créer le bot Telegram

1. Dans Telegram, ouvrez **@BotFather** et envoyez `/newbot`.
2. Donnez-lui un nom d'affichage, par exemple `My alerts`.
3. Donnez-lui ensuite un nom d'utilisateur qui se termine par `bot`, par exemple `my_alerts_bot`.
4. BotFather répond avec un **jeton** (token), du type `123456789:AA…`. Copiez-le et gardez-le secret.
5. Dans n8n, allez dans **Credentials → Create credential → Telegram API**, collez le jeton dans **Access Token**, puis cliquez sur **Save**. Vous devez voir "Connection tested successfully" (connexion testée avec succès).
6. **Trouver votre chat id.** C'est le numéro dont le bot a besoin pour savoir à qui écrire.
   1. Ouvrez une conversation avec votre nouveau bot et envoyez-lui un message quelconque, par exemple "hello". **Le bot ne répond pas. C'est normal** : il n'envoie que les messages que les workflows lui donnent.
   2. Dans votre navigateur, ouvrez `https://api.telegram.org/botYOUR_TOKEN/getUpdates`. Remplacez `YOUR_TOKEN` par le jeton, et écrivez `bot` juste avant, sans espace.
   3. Cherchez `"chat":{"id":` dans la page. Le nombre qui suit est votre chat id.
   4. Si vous ne voyez que `{"ok":true,"result":[]}`, envoyez un autre message au bot et rechargez la page.
   5. L'identifiant d'un groupe commence par `-`.

## 6. Configurer "Job offers — 1. Triage"

1. Ouvrez **Job offers — 0. Create the table** et cliquez une fois sur **Execute workflow** (exécuter le workflow). Dans **Overview → Data tables**, une table appelée `job_offers` apparaît.
2. Ouvrez **Job offers — 1. Triage with human approval**.
3. **Config** :
   1. Double-cliquez sur le nœud.
   2. Remplacez `PUT_YOUR_TELEGRAM_CHAT_ID_HERE` par votre chat id. Gardez les guillemets, comme ceci : `"7000000000"`.
   3. Si vous le souhaitez, ajustez `criteria`, le texte qui vous décrit à Gemini, et `keywords`.
   4. Fermez le nœud.
4. **Ask Gemini for a score** (demander une note à Gemini) : double-cliquez sur le nœud. Dans **Header Auth**, le champ du bas, choisissez votre identifiant Gemini, puis fermez le nœud.
5. **Send the digest on Telegram** (envoyer le résumé sur Telegram) : double-cliquez sur le nœud. Dans **Credential to connect with** (identifiant à utiliser), choisissez votre identifiant Telegram, puis fermez le nœud.
6. Appuyez sur **Ctrl+S** pour enregistrer.
7. Cliquez sur **Execute workflow** en bas du canevas. N'utilisez pas **Execute step** (exécuter l'étape) à l'intérieur d'un nœud : cela lance un seul nœud, sans ses données d'entrée.
8. Attendez une à deux minutes. Gemini est appelé une fois toutes les 5 secondes pour rester dans le quota gratuit.
9. **Résultat attendu :**
   - tous les nœuds passent au vert ;
   - vous recevez un message Telegram qui commence par **"Job offers: N new"**.

Si un nœud passe au rouge, cliquez dessus et lisez le message. Causes fréquentes :

| Symptôme | Solution |
|---|---|
| Offres marquées `error` avec "404" ou "model not found" | Le nom du modèle dans **Config** n'existe plus. Choisissez un modèle Flash actuel sur https://ai.google.dev/gemini-api/docs/models. |
| Offres marquées `error` avec "429" | Quota gratuit atteint. Baissez `max_offers_per_run` ou attendez le lendemain. |
| Nœud Telegram rouge avec "chat not found" | Mauvais chat id, ou vous n'avez jamais envoyé de message au bot. |
| Rien n'est envoyé du tout | Normal s'il n'y a pas de nouvelle offre : le workflow n'envoie que lorsqu'il y a du nouveau. |

## 7. Le faire tourner chaque matin

1. Dans **Job offers — 1. Triage**, cliquez sur **Publish** (publier) en haut à droite. Le workflow tourne désormais les jours de semaine à 08:00, dans le fuseau horaire défini dans `docker-compose.yml`.
2. Ouvrez **Job offers — 2. Weekly report**.
3. Renseignez votre chat id dans son **Config**.
4. Choisissez l'identifiant Telegram dans **Send the report on Telegram** (envoyer le rapport sur Telegram).
5. Enregistrez, puis cliquez sur **Publish**. Il tourne le lundi à 09:00.
6. n8n ne tourne que si Docker Desktop est lancé. Si l'ordinateur est éteint à 08:00, cette exécution est sautée. L'exécution suivante reprend les offres, tant qu'elles sont encore dans la limite de `max_age_days`.

## 8. Votre rôle : décider

1. Ouvrez **Overview → Data tables → job_offers**.
2. Pour chaque offre que vous avez lue, tapez `apply` ou `skip` dans la colonne `human_decision`.
3. Ce sont ces décisions que le rapport du lundi compare à l'IA. Après 20 décisions, il vous dit si l'on peut se fier au classement de l'IA.

## 9. Configurer l'assistant support

1. Lancez une fois **Support — 0. Create the table**.
2. Ouvrez **Support — 1. Intake and approval**.
3. Choisissez vos identifiants dans trois nœuds :
   - **Ask Gemini to classify and draft** (demander à Gemini de classer et de rédiger) : l'identifiant Gemini ;
   - **Ask a human to approve** (demander la validation d'un humain) : l'identifiant Telegram ;
   - **Hand over to a human** (passer la main à un humain) : l'identifiant Telegram.
4. Dans **Config** :
   - renseignez `telegram_chat_id` ;
   - renseignez `company_name` ;
   - laissez `drafting_enabled` à `true`.
5. Enregistrez, puis cliquez sur **Publish**.
6. Ouvrez le formulaire sur http://localhost:5678/form/support et envoyez une demande de test, par exemple "Hello, where is my order?".
7. Sur Telegram, vous recevez le brouillon avec un lien de relecture.
   - Ouvrez le lien **sur l'ordinateur qui fait tourner n8n**, car il pointe vers `localhost`.
   - Choisissez *Send as is* (envoyer tel quel), *Send my edited version* (envoyer ma version modifiée) ou *Reject* (rejeter).
8. Essayez aussi une demande de remboursement, par exemple "I want a refund". Elle doit arriver comme "needs a person" (à traiter par une personne), sans brouillon.
9. Dans **Support — 2. Weekly report**, renseignez le chat id, choisissez l'identifiant Telegram, puis cliquez sur **Publish**.

## 10. Passer à une nouvelle version

1. Récupérez les nouveaux fichiers, avec `git pull` ou en copiant le nouveau dossier.
2. Relancez les deux commandes d'import de l'étape 2.
3. Refaites les étapes 6.3 à 6.6, 7.3 à 7.4 et 9.3 à 9.4 : choisissez à nouveau les identifiants et remplissez à nouveau les valeurs de **Config**.

## 11. Arrêter n8n

```
docker compose down
```

Vos workflows, identifiants et tables sont conservés dans un volume Docker. `docker compose up -d` relance tout.
