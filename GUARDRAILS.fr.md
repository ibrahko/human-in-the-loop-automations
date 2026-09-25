# Liste de contrôle des garde-fous pour les automatisations IA

[English](GUARDRAILS.md) · **Français**

Une liste de contrôle d'une page pour décider **quelle part** d'un workflow confier à un modèle d'IA, et pour garder une personne responsable. Les deux projets de ce dépôt la suivent ; la colonne de droite montre où.

## 1. Avant de construire : faut-il vraiment automatiser ?

| Question | Tout automatiser si… | Garder un humain si… | Dans ce dépôt |
|---|---|---|---|
| Combien coûte une erreur ? | peu, facile à corriger | de l'argent, la réputation, un client, une obligation légale | Les réponses aux clients ne partent jamais sans une personne |
| Le résultat peut-il être vérifié par une machine ? | oui (schéma, règles) | seule une personne peut en juger | Les notes des offres sont vérifiées ; le ton d'une réponse est jugé par une personne |
| À quelle fréquence le cas se présente-t-il ? | souvent et de façon semblable | rarement ou très différemment à chaque fois | Remboursements et réclamations : toujours humains |
| Qui répond du résultat ? | personne n'a besoin d'en répondre | une personne ou une équipe nommée | Les colonnes `human_decision` et `decision` |

## 2. Pendant la construction : cinq garde-fous

1. **Écrire ce que l'IA ne doit jamais faire.** Ici : envoyer, postuler, rembourser, promettre de l'argent ou des dates.
2. **Imposer une réponse structurée et la vérifier.** Un schéma JSON, puis du code qui rejette tout ce qui en sort ou qui se contredit. Ne jamais passer du texte libre directement à une action.
3. **Orienter selon le risque, pas seulement selon la confiance de l'IA.** Les catégories sensibles et les mots à risque vont à une personne, quelle que soit la confiance.
4. **En cas d'échec, revenir vers un humain.** Si l'appel à l'IA échoue, l'élément est quand même enregistré et montré à une personne. Rien ne disparaît en silence.
5. **Garder la trace.** Enregistrer côte à côte la réponse de l'IA, la décision humaine et le temps qu'elle a pris.

## 3. Après la mise en service : mesurer par rapport à l'humain

- **Un seul chiffre par workflow** qui compare l'IA à l'humain : le taux d'accord (offres d'emploi), le taux de rejet des brouillons (support). Notez exactement comment il est calculé.
- **Une période récente** (ici, les 28 derniers jours), pour qu'une dérive récente ne soit pas cachée par des mois de bons résultats.
- **L'erreur coûteuse, comptée à part** : une bonne offre que l'IA vous a dit d'ignorer ; un brouillon qu'une personne a dû rejeter.
- **Une règle de décision écrite à l'avance** (la règle d'arrêt) : *sous 70 % d'accord après 20 décisions, mettre en pause et corriger le prompt.* Fixez le seuil avant de voir les chiffres.
- **Faire le point chaque semaine**, pas seulement quand quelque chose casse.

## 4. Adoption : faire en sorte que les gens l'utilisent

- Commencer avec la personne qui fait le travail aujourd'hui ; automatiser l'étape qu'elle trouve la plus pénible, pas la plus impressionnante.
- Afficher les raisons de l'IA à côté de sa réponse, pour que l'on puisse vite ne pas être d'accord.
- Permettre de passer outre l'IA en un clic (le formulaire de relecture), et compter ces corrections comme des données utiles, pas comme des échecs.

---

Auteur : **Ibrahima Koné** · Licence MIT
