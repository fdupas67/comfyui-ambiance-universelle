# Ambiance universelle : nœud ComfyUI

Choisissez **l'heure**, **la saison** et **la météo** dans des listes déroulantes : le nœud compose le prompt complet pour changer l'ambiance d'une image IA, sans réécrire le texte à chaque fois.

Le prompt ne nomme aucun élément de l'image : un bloc universel demande à l'IA d'analyser l'image de départ et d'adapter elle-même les horloges, l'éclairage, les reflets, les feuillages, les fruits et les sols. Le même texte fonctionne donc sur n'importe quelle image (ville, campagne, montagne, port).

## Ce que contient le nœud

- **3 listes déroulantes** : moment de la journée (7 choix), saison (4 choix), météo (7 choix).
- **Deux modes** : éditer une image existante, ou générer une image à partir d'un texte (zone `texte_scene`).
- **Une heure qui s'adapte à la saison** : le lever et le coucher du soleil ne tombent pas à la même heure en été et en hiver, et les horloges de l'image suivent.
- **Des cases de rappel** (horloge, éclairage, reflets, composition) à activer seulement si un défaut apparaît.
- **Une sortie `nom_fichier`** pour nommer automatiquement les images enregistrées.

Aucune bibliothèque supplémentaire n'est nécessaire (Python standard uniquement).

## Installation

Le dossier du nœud doit se trouver directement dans `ComfyUI/custom_nodes`, avec le fichier `__init__.py` à l'intérieur.

**Méthode 1 : git clone (recommandée).** Ouvrez un terminal dans le dossier `custom_nodes`, puis :

```
git clone <adresse copiée avec le bouton vert « Code »>
```

**Méthode 2 : zip.** Bouton vert « Code », puis « Download ZIP ». Décompressez-le dans `custom_nodes`. Vérifiez que le fichier se trouve bien à l'emplacement `custom_nodes/<nom du dossier>/__init__.py`. Sous Windows, avec « Extraire tout », effacez la fin du chemin de destination proposé, sinon un dossier de trop est créé et ComfyUI ne charge pas le nœud.

**Méthode 3 : gestionnaire de nœuds.** Selon votre version, un gestionnaire de nœuds peut installer un nœud à partir de l'adresse Git du dépôt.

Quittez complètement ComfyUI, relancez-le, puis double-cliquez sur le canevas et tapez « Ambiance universelle ».

## Utilisation

- La sortie `prompt` se relie au champ prompt de votre nœud de génération d'image. L'image de départ se branche sur l'entrée image de ce nœud, pas sur le nœud Ambiance universelle.
- La sortie `nom_fichier` se relie au préfixe du nœud d'enregistrement.

| Cas | Image de départ | `texte_scene` | `mode` |
| --- | --- | --- | --- |
| À partir d'une image | branchée | vide | Éditer une image |
| À partir d'un texte | aucune | description de la scène (sans heure, saison ni météo) | Générer depuis un texte |
| Image avec consigne | branchée | consigne supplémentaire | Éditer une image |

Commencez avec toutes les cases de rappel à `false`, et n'en activez qu'une à la fois si un défaut apparaît.

## Documentation

- [Guide d'utilisation (PDF)](docs/guide_ambiance_universelle.pdf)
- [Tous les prompts (PDF)](docs/prompts_ambiance_universelle.pdf)

## Limites

La précision des horloges, des reflets et de l'éclairage dépend du modèle de génération utilisé : testez le nœud sur plusieurs images très différentes. Partez toujours de l'image d'origine, jamais d'une variante déjà modifiée.

## Licence

MIT
