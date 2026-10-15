"""
Nœud ComfyUI : Ambiance universelle (heure / saison / météo)

Installation :
  1. Copier ce fichier dans  ComfyUI/custom_nodes/
  2. Redémarrer ComfyUI
  3. Ajouter le nœud : clic droit > Add Node > Ambiance > Ambiance universelle

Le nœud sort le prompt complet (bloc universel + module Heure + module Saison
+ module Météo) à brancher sur le champ prompt du nœud GPT Image.
Deux modes : édition d'une image (par défaut) ou génération depuis un texte
(zone texte_scene, placée au-dessus du bloc). Aucun module ne nomme un élément d'image : le prompt fonctionne sur n'importe
quelle image de départ, branchée sur l'entrée image du nœud GPT Image.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Bloc universel (toujours le même)
# ---------------------------------------------------------------------------

BLOC_UNIVERSEL = (
    "Modifie uniquement le moment de la journée, la saison et la météo de cette image, "
    "tels qu'indiqués plus bas. Analyse d'abord l'image et conserve-la strictement : "
    "même composition, même cadrage, même angle de caméra, mêmes éléments à leur place "
    "exacte, mêmes proportions, même style visuel, mêmes textes visibles. N'ajoute, "
    "ne retire et ne déplace aucun élément ni aucun personnage.\n\n"
    "Adapte automatiquement tout ce que le nouveau contexte implique sur cette image, "
    "sans que cela soit précisé :\n"
    "- Lumière naturelle : position et hauteur du soleil ou de la lune, couleur de la "
    "lumière, direction et longueur des ombres, cohérentes avec l'heure et l'orientation "
    "de la scène.\n"
    "- Sources lumineuses artificielles présentes (lampadaires, lanternes, enseignes, "
    "vitrines, fenêtres, phares, feux, cheminées, etc.) : allumées dès que la lumière "
    "naturelle est faible (nuit, crépuscule, orage, brouillard dense, tempête), éteintes "
    "en plein jour, avec des halos cohérents.\n"
    "- Horloges, cadrans, pendules ou montres visibles : les aiguilles indiquent "
    "exactement l'heure précisée dans le module Heure ; elles sont éclairées la nuit.\n"
    "- Surfaces réfléchissantes (eau, sol mouillé, vitres, métal, neige, glace) : reflets "
    "cohérents avec le ciel, la lumière et les sources lumineuses du moment.\n"
    "- Ciel, nuages, végétation, sols et matériaux : adaptés à la saison et à la météo.\n\n"
    "Règles de cohérence : la météo prime sur l'heure pour l'aspect du ciel et la dureté "
    "des ombres. Si une saison est précisée, l'heure du lever et du coucher du soleil s'y "
    "adapte, et les horloges suivent. Une seule lumière dominante, cohérente, par image."
)

# Variante pour la génération depuis un texte (pas d'image de départ) :
# même règles d'adaptation, mais sans "conserve cette image".
_SUITE_ADAPTATION = BLOC_UNIVERSEL.split("\n\n", 1)[1].replace(
    "le nouveau contexte implique sur cette image", "ce contexte implique sur la scène"
).replace(
    "artificielles présentes (", "artificielles présentes dans la scène ("
)

BLOC_GENERATION = (
    "Génère une image de la scène décrite ci-dessus, au moment de la journée, à la "
    "saison et par la météo indiqués plus bas. Respecte strictement la scène décrite : "
    "lieu, éléments, composition et style visuel. N'ajoute rien qui la contredise.\n\n"
    + _SUITE_ADAPTATION
)

MODE_EDITION = "Éditer une image"
MODE_TEXTE = "Générer depuis un texte"

# ---------------------------------------------------------------------------
# Modules d'heure
# Pour chaque moment : (heure par défaut, heure été, heure hiver, corps du texte)
# Le nœud choisit lui-même l'heure selon la saison sélectionnée.
# ---------------------------------------------------------------------------

ECLAIRAGE_LEVER = {
    None: (
        "Éclairage artificiel selon la saison : encore allumé en hiver, quelques sources "
        "seulement au printemps et à l'automne, éteint en été car il fait déjà jour, "
        "avec au plus une ou deux fenêtres éclairées."
    ),
    "Hiver": "Éclairage artificiel encore allumé.",
    "Été": "Éclairage artificiel éteint car il fait déjà jour, avec au plus une ou deux fenêtres éclairées.",
    "Printemps": "Quelques sources lumineuses artificielles seulement encore allumées.",
    "Automne": "Quelques sources lumineuses artificielles seulement encore allumées.",
}

MOMENTS = {
    "Lever du soleil": (
        "7h", "6h", "8h",
        "lever du soleil",
        "Soleil très bas à l'horizon, lumière dorée-rosée rasante, ombres très longues et "
        "douces. Ciel dégradé bleu pâle, rose et orangé avec quelques nuages rosés. Légère "
        "brume matinale au ras du sol, rosée sur les surfaces. {eclairage_lever} "
        "Atmosphère calme et fraîche.",
    ),
    "Milieu de matinée": (
        "10h", "10h", "10h",
        "milieu de matinée",
        "Soleil haut d'un côté de la scène, lumière claire et dorée, ombres nettes de "
        "longueur moyenne. Ciel limpide avec quelques petits nuages blancs. Éclairage "
        "artificiel éteint. Atmosphère vive et lumineuse.",
    ),
    "Midi": (
        "12h", "12h", "12h",
        "plein midi",
        "Soleil au zénith, lumière blanche-dorée intense, ombres très courtes et très "
        "contrastées. Ciel d'un bleu profond, presque sans nuages. Éclairage artificiel "
        "éteint. Atmosphère de plein jour.",
    ),
    "Milieu d'après-midi": (
        "16h", "16h", "16h",
        "milieu d'après-midi",
        "Soleil descendant du côté opposé à celui du matin, lumière chaude ambrée, ombres "
        "allongées qui tombent à l'opposé de celles du matin. Ciel bleu doux avec de fins "
        "nuages dorés, teintes miel sur les matériaux clairs. Éclairage artificiel éteint. "
        "Atmosphère paisible et dorée.",
    ),
    "Coucher du soleil": (
        "20h30", "21h30", "17h",
        "coucher du soleil",
        "Soleil rasant à l'horizon, contre-jour orangé-rouge, longues ombres violacées, "
        "halos lumineux dans les feuillages, la brume ou les vitres. Ciel spectaculaire "
        "orange, rose et violet avec des nuages enflammés. Éclairage artificiel qui "
        "commence à s'allumer. Atmosphère romantique et nostalgique.",
    ),
    "Début de nuit (heure bleue)": (
        "22h", "22h", "19h",
        "début de nuit, heure bleue",
        "Ciel bleu nuit profond avec une dernière lueur violette à l'horizon et les "
        "premières étoiles. Éclairage artificiel entièrement allumé, en lumière chaude "
        "orangée qui dessine des halos sur les surfaces et contraste avec l'ambiance "
        "froide bleutée. Fenêtres et vitrines éclairées. Atmosphère douce et féerique.",
    ),
    "Pleine nuit": (
        "2h du matin", "2h du matin", "2h du matin",
        "pleine nuit",
        "Pleine lune haute dans un ciel noir-bleu étoilé, lumière lunaire argentée et "
        "froide, ombres bleutées marquées. Éclairage public et lanternes allumés, mais "
        "commerces fermés et sombres, une seule fenêtre faiblement éclairée. Surfaces "
        "légèrement luisantes. Atmosphère silencieuse et mystérieuse.",
    ),
}

# ---------------------------------------------------------------------------
# Modules de saison (incluant la règle sur les fruits, valable en Europe)
# ---------------------------------------------------------------------------

SAISONS = {
    "Printemps": (
        "Saison : printemps. Feuillages en jeunes pousses vert tendre lumineux, arbres en "
        "fleurs, fleurs colorées partout où il y a des plantes (massifs, jardinières, "
        "balcons, prairies, bords de chemin). Pétales épars au sol, herbe fraîche, cultures "
        "vertes. Arbres fruitiers en fleurs, sans aucun fruit mûr : retire tout fruit "
        "visible sur les arbres. Neige qui fond en altitude, eaux vives. Ciel clair avec "
        "nuages blancs duveteux, lumière douce et fraîche."
    ),
    "Été": (
        "Saison : plein été. Feuillages denses vert foncé projetant des ombres épaisses, "
        "fleurs rouges et orangées, herbes et cultures hautes et dorées. Fruits encore "
        "petits et verts, non mûrs, sauf les fruits d'été (cerises, abricots, prunes). "
        "Sols secs et chauds, neige limitée aux plus hauts sommets, eaux turquoise ou "
        "scintillantes. Ciel d'un bleu intense, lumière chaude et dorée, léger flou de "
        "chaleur."
    ),
    "Automne": (
        "Saison : automne. Feuillages orange, jaune doré et roux, quelques feuilles qui "
        "tombent, tapis de feuilles mortes au sol et sur les surfaces horizontales. Plantes "
        "de saison dans les massifs et jardinières, champs récoltés (chaume, labours), "
        "herbes sèches. Fruits mûrs et colorés sur les arbres fruitiers, quelques fruits "
        "tombés au sol, certains arbres déjà dégarnis. Ciel bleu pâle avec nuages "
        "gris-blanc, lumière basse, dorée et chaude."
    ),
    "Hiver": (
        "Saison : hiver. Arbres aux branches nues couvertes de givre, végétation en "
        "sommeil, aucun fruit sur les arbres ni au sol{exception_sud}. Fine couche de "
        "neige sur les toits, le mobilier, les rebords et toutes les surfaces horizontales, "
        "sols humides ou gelés avec des plaques de neige, plans d'eau gris et en partie "
        "gelés. Ciel blanc-gris lumineux, lumière froide et douce. Éclairage artificiel "
        "plus chaleureux, petites vapeurs près des cheminées et des bouches d'aération."
    ),
}

EXCEPTION_SUD = ", sauf les agrumes et les oliviers, qui gardent leurs fruits"

# ---------------------------------------------------------------------------
# Modules de météo
# ---------------------------------------------------------------------------

METEOS = {
    "Pluie douce": (
        "Météo : pluie légère. Ciel gris clair uniforme, fines gouttes visibles, toutes les "
        "surfaces exposées mouillées et brillantes avec leurs reflets, petites flaques. "
        "Végétation foncée et gorgée d'eau, gouttes qui perlent sur les feuilles et les "
        "objets. Lumière douce, sans ombres marquées."
    ),
    "Orage": (
        "Météo : orage. Ciel noir-violet chargé de nuages lourds, un éclair lumineux au "
        "loin, lumière dramatique et contrastée. Pluie forte et oblique, grandes flaques, "
        "tout ce qui peut bouger est agité par le vent (feuillages, drapeaux, toiles, "
        "vagues). Éclairage artificiel allumé même de jour, reflets intenses sur les "
        "surfaces mouillées."
    ),
    "Arc-en-ciel après la pluie": (
        "Météo : juste après la pluie. Ciel mi-nuageux mi-ensoleillé, grand arc-en-ciel "
        "visible, rayons de soleil qui traversent les feuillages ou les nuages. Surfaces "
        "mouillées brillantes avec flaques qui reflètent le ciel, gouttes qui tombent "
        "encore des feuilles et des rebords, légère vapeur au sol. Lumière dorée et "
        "fraîche."
    ),
    "Neige abondante": (
        "Météo : forte chute de neige. Gros flocons dans l'air, épaisse couche de neige sur "
        "toutes les surfaces horizontales (sols, toits, mobilier, balcons, branches, "
        "bateaux). Ciel blanc-gris laiteux, lumière froide et feutrée. Halos chauds des "
        "sources lumineuses artificielles dans les flocons, reflets dorés sur la neige."
    ),
    "Brouillard": (
        "Météo : brouillard épais. Brume blanche dense qui estompe l'arrière-plan : les "
        "éléments proches restent lisibles mais adoucis, les éléments lointains "
        "disparaissent. Lumière diffuse laiteuse, sans ombres dures. Halos lumineux autour "
        "de chaque source lumineuse, surfaces humides, rosée sur les objets."
    ),
    "Grand vent": (
        "Météo : jour de grand vent. Tout ce qui peut bouger bouge : branches, feuillages, "
        "herbes, drapeaux, toiles, vêtements, fumées, vagues. Feuilles et poussières "
        "emportées dans l'air. Ciel contrasté entre éclaircies et gros nuages en "
        "mouvement, lumière dorée par intermittence."
    ),
    "Canicule": (
        "Météo : canicule. Ciel blanc-bleu écrasé de chaleur, soleil aveuglant, ombres très "
        "dures et courtes, halo de chaleur ondulant au-dessus des sols. Surfaces claires "
        "presque blanches, végétation un peu desséchée, volets et ouvertures mi-clos. "
        "Lumière saturée et jaune, atmosphère de sieste."
    ),
}

# ---------------------------------------------------------------------------
# Lignes de rappel facultatives (à activer si un point ne suit pas)
# ---------------------------------------------------------------------------

RAPPEL_HORLOGE = "Les aiguilles des horloges visibles indiquent exactement l'heure précisée."
RAPPEL_ECLAIRAGE = "Toute source lumineuse artificielle de l'image est allumée."
RAPPEL_REFLETS = "Toutes les surfaces réfléchissantes montrent les reflets du ciel et des lumières."
RAPPEL_COMPOSITION = (
    "Ne change aucun élément, aucune position, aucun texte : ne modifie que la lumière, "
    "la saison et la météo."
)

RAPPEL_COMPOSITION_TEXTE = (
    "Respecte exactement la scène décrite : n'ajoute et ne retire aucun élément."
)

AUCUNE = "Aucune"


def _slug(texte):
    """Transforme un libellé en fragment de nom de fichier."""
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^a-zA-Z0-9]+", "-", texte).strip("-").lower()
    return texte


def _module_heure(moment, saison):
    defaut, ete, hiver, libelle, corps = MOMENTS[moment]
    if saison == "Été":
        heure = ete
    elif saison == "Hiver":
        heure = hiver
    else:
        heure = defaut
    cle_saison = saison if saison in ("Hiver", "Été", "Printemps", "Automne") else None
    eclairage = ECLAIRAGE_LEVER.get(cle_saison, ECLAIRAGE_LEVER[None])
    corps = corps.replace("{eclairage_lever}", eclairage)
    return f"Moment : {libelle}. Heure indiquée : {heure}. {corps}"


class AmbianceUniverselle:
    """Assemble le bloc universel et les modules heure / saison / météo."""

    CATEGORY = "Ambiance"
    FUNCTION = "assembler"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "nom_fichier")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "moment": (list(MOMENTS.keys()),),
                "saison": ([AUCUNE] + list(SAISONS.keys()),),
                "meteo": ([AUCUNE] + list(METEOS.keys()),),
            },
            "optional": {
                "inclure_bloc_universel": ("BOOLEAN", {"default": True}),
                "scene_sud_europe": ("BOOLEAN", {"default": False}),
                "rappel_horloge": ("BOOLEAN", {"default": False}),
                "rappel_eclairage": ("BOOLEAN", {"default": False}),
                "rappel_reflets": ("BOOLEAN", {"default": False}),
                "rappel_composition": ("BOOLEAN", {"default": False}),
                "mode": ([MODE_EDITION, MODE_TEXTE],),
                "texte_scene": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    def assembler(
        self,
        moment,
        saison,
        meteo,
        inclure_bloc_universel=True,
        scene_sud_europe=False,
        rappel_horloge=False,
        rappel_eclairage=False,
        rappel_reflets=False,
        rappel_composition=False,
        mode=MODE_EDITION,
        texte_scene="",
    ):
        texte_scene = (texte_scene or "").strip()
        if mode == MODE_TEXTE and not texte_scene:
            raise ValueError(
                "Mode 'Générer depuis un texte' : renseigne texte_scene "
                "(ou branche un texte sur cette entrée)."
            )

        parties = []

        # Le texte de la scène vient en premier, au-dessus du bloc.
        if texte_scene:
            parties.append(texte_scene)

        if inclure_bloc_universel:
            parties.append(BLOC_GENERATION if mode == MODE_TEXTE else BLOC_UNIVERSEL)

        modules = [_module_heure(moment, saison)]

        if saison != AUCUNE:
            texte_saison = SAISONS[saison]
            if saison == "Hiver":
                texte_saison = texte_saison.replace(
                    "{exception_sud}", EXCEPTION_SUD if scene_sud_europe else ""
                )
            modules.append(texte_saison)

        if meteo != AUCUNE:
            modules.append(METEOS[meteo])

        parties.append("\n".join(modules))

        rappels = []
        if rappel_horloge:
            rappels.append(RAPPEL_HORLOGE)
        if rappel_eclairage:
            rappels.append(RAPPEL_ECLAIRAGE)
        if rappel_reflets:
            rappels.append(RAPPEL_REFLETS)
        if rappel_composition:
            rappels.append(
                RAPPEL_COMPOSITION_TEXTE if mode == MODE_TEXTE else RAPPEL_COMPOSITION
            )
        if rappels:
            parties.append(" ".join(rappels))

        prompt = "\n\n".join(parties)

        elements = [_slug(moment)]
        if saison != AUCUNE:
            elements.append(_slug(saison))
        if meteo != AUCUNE:
            elements.append(_slug(meteo))
        nom_fichier = "_".join(elements)

        return (prompt, nom_fichier)


NODE_CLASS_MAPPINGS = {"AmbianceUniverselle": AmbianceUniverselle}
NODE_DISPLAY_NAME_MAPPINGS = {
    "AmbianceUniverselle": "Ambiance universelle (heure / saison / météo)"
}
