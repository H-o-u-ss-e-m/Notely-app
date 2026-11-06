"""
Générateur du Benchmark Notely Étendu (≥ 200 lignes) conforme à §8.9.
Ventilation stricte :
- 120 Français (cours, mathématiques, accents é/è/ê/ë/à/â/ô/û/ç, listes, titres)
- 30 Anglais (cours, définitions, formules)
- 30 Arabe (cours, géométrie, algèbre, vocabulaire RTL)
- 20 Allemand (cours, grammaire, ä/ö/ü/ß)
Total : 200 lignes avec page_group (pg_001 à pg_025) pour valider le split par page.
"""
import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 120 Échantillons Français
FR_SAMPLES = [
    # Analyse mathématique & fonctions
    ("Les fonctions dérivables sur un intervalle ouvert sont continues", "text", True),
    ("Une intégrale indéfinie représente l'ensemble des primitives", "text", True),
    ("Théorème des accroissements finis et corollaires", "title", True),
    ("Soit f une fonction continue et strictement monotone sur [a, b]", "text", True),
    ("Calcul de la dérivée première de la fonction logarithme népérien", "text", True),
    ("La limite de sin(x)/x lorsque x tend vers zéro est égale à un", "text", True),
    ("Le développement limité à l'ordre trois au voisinage de zéro", "text", True),
    ("Toute suite réelle croissante et majorée converge vers sa borne supérieure", "text", True),
    ("Théorème de Bolzano-Weierstrass pour les suites bornées", "title", True),
    ("Étude de la convexité d'une fonction deux fois dérivable", "text", True),
    ("Points d'inflexion et signe de la dérivée seconde", "text", True),
    ("L'intégrale de Riemann d'une fonction continue par morceaux", "text", True),
    ("Intégration par parties et changement de variable", "title", True),
    ("La série harmonique est divergente malgré la décroissance de son terme", "text", True),
    ("Rayon de convergence d'une série entière complexe", "text", True),
    # Algèbre linéaire & géométrie
    ("Le déterminant d'une matrice carrée d'ordre n", "text", True),
    ("Système d'équations linéaires et méthode du pivot de Gauss", "text", True),
    ("Les valeurs propres sont les racines du polynôme caractéristique", "text", True),
    ("Diagonalisation d'une matrice symétrique réelle", "title", True),
    ("Espace vectoriel de dimension finie muni d'une base orthonormée", "text", True),
    ("Le produit scalaire canonique sur l'espace euclidien", "text", True),
    ("Noyau et image d'une application linéaire continue", "text", True),
    ("Théorème du rang pour les morphismes d'espaces vectoriels", "title", True),
    ("Sous-espace supplémentaire et projection orthogonale", "text", True),
    ("Inégalité de Cauchy-Schwarz dans un espace préhilbertien", "text", True),
    # Physique & mécanique
    ("Principe fondamental de la dynamique newtonienne", "title", True),
    ("L'énergie cinétique d'un solide en mouvement de translation", "text", True),
    ("Conservation de l'énergie mécanique en l'absence de frottements", "text", True),
    ("Oscillateur harmonique amorti en régime pseudopériodique", "text", True),
    ("Équations de Maxwell dans le vide et propagation des ondes", "text", True),
    ("Champ électrostatique créé par une distribution sphérique de charges", "text", True),
    ("Loi d'Ohm généralisée et circuits électriques en courant alternatif", "text", True),
    ("Premier principe de la thermodynamique pour un système fermé", "title", True),
    ("Variation d'entropie au cours d'une transformation irréversible", "text", True),
    ("Cycle de Carnot et rendement maximal d'une machine thermique", "text", True),
    # Chimie & biologie
    ("Réaction acido-basique et constante d'acidité en solution aqueuse", "text", True),
    ("Cinétique chimique et ordre global d'une réaction élémentaire", "text", True),
    ("Structure de la molécule d'acide désoxyribonucléique", "title", True),
    ("Synthèse des protéines par les ribosomes dans le cytoplasme", "text", True),
    ("Équilibre d'oxydoréduction et potentiel standard d'électrode", "text", True),
    # Listes et énumérations
    ("1. Définition rigoureuse de la dérivabilité en un point", "list", True),
    ("2. Propriétés algébriques de la dérivée d'une somme", "list", True),
    ("3. Règle de dérivation d'une fonction composée f(g(x))", "list", True),
    ("4. Dérivée de la fonction réciproque f^(-1)", "list", True),
    ("5. Applications à l'optimisation et extrema locaux", "list", True),
    ("a) Hypothèse de départ : f est de classe C1 sur l'intervalle", "list", True),
    ("b) Démonstration par l'absurde de l'unicité de la solution", "list", True),
    ("c) Conclusion générale et interprétation géométrique", "list", True),
    ("I. Rappels fondamentaux sur les espaces préhilbertiens", "list", True),
    ("II. Familles libres, familles génératrices et bases", "list", True),
    # Titres et sous-titres
    ("Chapitre 3 : Équations différentielles linéaires du second ordre", "title", True),
    ("Section 2.4 : Séries de Fourier et phénomènes vibratoires", "title", True),
    ("Annexe B : Formulaire trigonométrique et hyperbolique", "title", True),
    ("Exercice 12 : Résolution approchée par la méthode des trapèzes", "title", True),
    ("Problème de synthèse : Étude d'un pendule simple non linéaire", "title", True),
    # Formules avec texte français
    ("Posons delta = b^2 - 4ac le discriminant de l'équation", "formula", True),
    ("L'intégrale de a à b de f(t) dt vaut F(b) - F(a)", "formula", True),
    ("Pour tout epsilon strictement supérieur à zéro, il existe un rang N", "text", True),
    ("La norme euclidienne vérifie ||x + y|| <= ||x|| + ||y||", "formula", True),
    ("Relation d'Euler : e^(i*pi) + 1 = 0", "formula", True),
    # Phrases variées de cours généraux
    ("L'étudiant a rédigé un mémoire complet sur l'intelligence artificielle", "text", True),
    ("La reconnaissance automatique de l'écriture manuscrite progresse rapidement", "text", True),
    ("Chaque élève doit vérifier ses calculs avant de remettre sa copie", "text", True),
    ("Le professeur a souligné l'importance de la rigueur mathématique", "text", True),
    ("Une bonne méthode de travail permet de réussir les épreuves écrites", "text", True),
    ("L'épreuve comprend trois exercices indépendants et un problème guidé", "text", True),
    ("L'usage de la calculatrice programmable est strictement interdit", "text", True),
    ("Rédigez avec soin en précisant les théorèmes invoqués", "text", True),
    ("La clarté de la rédaction constitue un élément majeur d'évaluation", "text", True),
    ("Tous les résultats numériques seront arrondis au centième près", "text", True),
    # Enrichissement supplémentaire pour atteindre 120
    ("Décomposition en éléments simples d'une fraction rationnelle", "text", True),
    ("Pôles, résidus et intégration le long d'un lacet fermé", "text", True),
    ("Théorème de convergence dominée de Lebesgue", "title", True),
    ("Espace des fonctions intégrables muni de la norme L1", "text", True),
    ("Complétude de l'espace vectoriel normé et suites de Cauchy", "text", True),
    ("Topologie générale : ouverts, fermés, voisinages et compacité", "title", True),
    ("Le théorème de Heine affirme qu'une fonction continue sur un compact est uniformément continue", "text", True),
    ("Différentielle d'une fonction de plusieurs variables réelles", "text", True),
    ("Matrice jacobienne et matrice hessienne d'un champ scalaire", "text", True),
    ("Gradient, divergence et rotationnel en coordonnées cartésiennes", "text", True),
    ("Théorème de Green-Riemann pour une courbe fermée plane", "title", True),
    ("Flux d'un champ de vecteurs à travers une surface orientée", "text", True),
    ("Théorème d'Ostrogradski et divergence volumique", "title", True),
    ("Loi des grands nombres et convergence en probabilité", "text", True),
    ("Théorème central limite et distribution gaussienne centrée réduite", "title", True),
    ("Variable aléatoire discrète suivant une loi binomiale de paramètres n et p", "text", True),
    ("Espérance mathématique et variance d'une variable aléatoire continue", "text", True),
    ("Estimation ponctuelle et intervalle de confiance bilatéral", "text", True),
    ("Test d'hypothèse statistique et risque de première espèce", "title", True),
    ("Régression linéaire simple et méthode des moindres carrés", "text", True),
    ("Coefficient de corrélation linéaire de Pearson", "text", True),
    ("Analyse de la variance à un facteur contrôlé", "text", True),
    ("Arbre de décision binaire et entropie de Shannon", "text", True),
    ("Réseaux de neurones convolutifs appliqués à la vision par ordinateur", "title", True),
    ("Architecture transformeur avec mécanisme d'attention multi-têtes", "text", True),
    ("Rétropropagation du gradient d'erreur stochastique", "text", True),
    ("Normalisation par lots et régularisation par abandon temporaire", "text", True),
    ("Apprentissage semi-supervisé et auto-encodeurs variationnels", "text", True),
    ("Traitement automatique des langues naturelles et plongements lexicaux", "title", True),
    ("Modèles de langage pré-entraînés sur de très grands corpus textuels", "text", True),
    ("Reconnaissance optique de caractères pour documents anciens numérisés", "text", True),
    ("Segmentation sémantique d'images de documents historiques", "text", True),
    ("Binarisation adaptative d'images par la méthode de Sauvola", "text", True),
    ("Extraction de caractéristiques géométriques et fréquentielles", "text", True),
    ("Correction orthographique contextuelle par modèles n-grammes", "text", True),
    ("Dictionnaire utilisateur personnalisé et mémorisation des corrections", "text", True),
    ("Génération de résumés automatiques et extraction d'entités nommées", "text", True),
    ("Modèle de diffusion pour la génération conditionnelle de visages", "text", True),
    ("Système expert à base de règles et chaînage avant", "title", True),
    ("Représentation des connaissances et ontologies formelles", "text", True),
    ("Recherche heuristique dans un graphe d'états par l'algorithme A*", "text", True),
    ("Complexité algorithmique temporelle et spatiale au pire des cas", "text", True),
    ("Tri rapide récursif et analyse probabiliste de la complexité", "text", True),
    ("Structures de données arborescentes : arbres AVL et arbres rouge-noir", "title", True),
    ("Tables de hachage avec résolution des collisions par chaînage", "text", True),
    ("Programmation dynamique pour le problème du sac à dos", "text", True),
    ("Plus court chemin dans un graphe orienté par l'algorithme de Dijkstra", "text", True),
    ("Flot maximal dans un réseau par l'algorithme de Ford-Fulkerson", "title", True),
    ("Classes de complexité P, NP et problèmes NP-complets", "title", True),
    ("Machines de Turing et thèse de Church-Turing", "text", True),
]

# 30 Échantillons Anglais
EN_SAMPLES = [
    ("The quick brown fox jumps over the lazy dog", "text", False),
    ("Linear algebra and abstract vector spaces", "title", False),
    ("Machine learning foundations and deep neural networks", "text", False),
    ("Continuous functions defined on compact metric spaces", "text", False),
    ("Differential calculus and multivariate optimization problems", "text", False),
    ("Principal component analysis for dimensionality reduction", "text", False),
    ("Support vector machines with radial basis function kernels", "text", False),
    ("Stochastic gradient descent with momentum and adaptive learning rates", "text", False),
    ("Convolutional neural networks for computer vision tasks", "title", False),
    ("Recurrent neural networks and long short term memory architectures", "text", False),
    ("Attention mechanisms and transformer based language models", "title", False),
    ("Self-supervised representation learning from unlabelled images", "text", False),
    ("Natural language processing for question answering systems", "text", False),
    ("Markov decision processes and reinforcement learning algorithms", "title", False),
    ("Bellman optimality equation for dynamic programming", "formula", False),
    ("1. Define the objective loss function to minimize", "list", False),
    ("2. Compute the gradient with respect to model parameters", "list", False),
    ("3. Update weights using backpropagation rule", "list", False),
    ("4. Evaluate accuracy on held-out validation dataset", "list", False),
    ("5. Early stopping criterion when validation loss plateaus", "list", False),
    ("Let X be a random variable following a normal distribution", "text", False),
    ("The eigenvalues of a real symmetric matrix are all real", "text", False),
    ("Singular value decomposition of rectangular matrices", "title", False),
    ("Bayesian inference and posterior probability estimation", "text", False),
    ("Maximum likelihood estimation of unknown parameters", "text", False),
    ("Central limit theorem under finite variance conditions", "title", False),
    ("Time series analysis with autoregressive integrated moving average", "text", False),
    ("Graph neural networks for relational structure modeling", "text", False),
    ("Optical character recognition pipeline for document layout analysis", "text", False),
    ("Fast inference engine using dynamic int8 quantization", "text", False),
]

# 30 Échantillons Arabe
AR_SAMPLES = [
    ("الهندسة الإقليدية ونظرية المثلثات في الفضاء", "title", False),
    ("حل المعادلة التفاضلية من الدرجة الأولى", "text", False),
    ("حساب التكامل المحدود للدوال المستمرة", "text", False),
    ("الجبر الخطي والمصفوفات والمحددات", "title", False),
    ("دراسة الدوال العددية والنهايات والاشتقاق", "text", False),
    ("الاحتمالات والإحصاء التطبيقي في العلوم", "text", False),
    ("قوانين نيوتن في الحركة والديناميكا الكلاسيكية", "title", False),
    ("الطاقة الحركية وطاقة الوضع للجسم الساقط", "text", False),
    ("التيار الكهربائي وفرق الجهد والمقاومة", "text", False),
    ("الكيمياء العضوية وبنية الجزيئات الحيوية", "text", False),
    ("١. تعريف الدالة التزايدية بدقة رياضية", "list", False),
    ("٢. حساب نقطة الانقلاب لمنحنى الدالة", "list", False),
    ("٣. استنتاج جدول التغيرات والرسم البياني", "list", False),
    ("٤. تعيين مستقيمات المقاربة الأفقية والعمودية", "list", False),
    ("٥. حساب مساحة الحيز المحصور بين المنحنيين", "list", False),
    ("المتتاليات العددية المتقاربة ونهاياتها", "text", False),
    ("مبرهنة القيم المتوسطة وتطبيقاتها الهندسية", "title", False),
    ("الأعداد المركبة والشكل المثلثي والقطبي", "text", False),
    ("المتجهات في المستوى الإحداثي والجداء السلمي", "text", False),
    ("الدائرة المثلثية وقيم جيب التمام والظل", "text", False),
    ("الخوارزميات وهياكل البيانات المتقدمة في الحاسوب", "title", False),
    ("الذكاء الاصطناعي وتطبيقات التعلم العميق", "text", False),
    ("معالجة اللغات الطبيعية والترجمة الآلية الفورية", "text", False),
    ("التعرف الضوئي على الحروف للنصوص المخطوطة", "text", False),
    ("أمن المعلومات والتشفير باستخدام المفتاح العام", "title", False),
    ("قواعد البيانات العلائقية ولغة الاستعلام الهيكلية", "text", False),
    ("نظرية المجموعات والمنطق الرياضي الاستدلالي", "text", False),
    ("الفضاء الشعاعي والأساس والبعد المنتهي", "text", False),
    ("تكامل الدوال الكسرية باستخدام الكسور الجزئية", "text", False),
    ("مراجعة عامة وشاملة للاختبار النهائي في الرياضيات", "title", False),
]

# 20 Échantillons Allemand
DE_SAMPLES = [
    ("Lineare Algebra und mehrdimensionale Analysis", "title", True),
    ("Die stetigen Funktionen auf kompakten Intervallen", "text", True),
    ("Berechnung der partiellen Ableitungen zweiter Ordnung", "text", True),
    ("Differentialgleichungen und Schwingungssysteme", "text", True),
    ("Der Mittelwertsatz der Differentialrechnung", "title", True),
    ("Integration durch Substitution und partielle Integration", "text", True),
    ("Die Eigenwerte einer symmetrischen Matrix sind reell", "text", True),
    ("Wahrscheinlichkeitstheorie und mathematische Statistik", "title", True),
    ("Konvergenz von Reihen und Potenzreihenentwicklung", "text", True),
    ("Einführung in die theoretische Informatik", "title", True),
    ("1. Definition der Differenzierbarkeit einer Funktion", "list", True),
    ("2. Bestimmung der lokalen Extrema und Wendepunkte", "list", True),
    ("3. Zeichnen des Funktionsgraphen im Koordinatensystem", "list", True),
    ("4. Berechnung der Nullstellen des Polynoms", "list", True),
    ("Das Gaußsche Eliminationsverfahren für lineare Gleichungssysteme", "text", True),
    ("Die Taylorreihe einer unendlich oft differenzierbaren Funktion", "text", True),
    ("Optimierung von Algorithmen zur optischen Zeichenerkennung", "text", True),
    ("Künstliche Intelligenz und maschinelles Lernen in der Praxis", "title", True),
    ("Automatische Texterkennung für handgeschriebene Vorlesungsnotizen", "text", True),
    ("Zusammenfassung der mathematischen Grundlagen für Studierende", "text", True),
]


def generate_extended_benchmark(output_dir: str = "backend/benchmark/dataset"):
    out_dir = Path(output_dir)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_file = out_dir / "labels.json"

    # Polices système sous Windows
    font_fr_en = None
    font_ar = None
    possible_fonts = [
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "C:\\Windows\\Fonts\\times.ttf",
    ]
    for pf in possible_fonts:
        if os.path.exists(pf):
            try:
                font_fr_en = ImageFont.truetype(pf, size=30)
                break
            except Exception:
                continue

    # Police arabe (Arial ou Segoe UI sous Windows contiennent les glyphes arabes)
    ar_fonts = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "C:\\Windows\\Fonts\\trado.ttf",
    ]
    for pf in ar_fonts:
        if os.path.exists(pf):
            try:
                font_ar = ImageFont.truetype(pf, size=28)
                break
            except Exception:
                continue

    if font_fr_en is None:
        font_fr_en = ImageFont.load_default()
    if font_ar is None:
        font_ar = font_fr_en

    all_items = []
    # Assembler avec page_group (ex. 8 items par page -> 25 pages)
    page_counter = 1
    item_in_page = 0

    def add_batch(samples, lang):
        nonlocal page_counter, item_in_page
        for text, cat, has_acc in samples:
            item_in_page += 1
            if item_in_page > 8:
                page_counter += 1
                item_in_page = 1
            page_group = f"pg_{page_counter:03d}"
            all_items.append({
                "text": text,
                "language": lang,
                "category": cat,
                "has_accents": has_acc,
                "page_group": page_group,
            })

    add_batch(FR_SAMPLES, "fr")      # 120 items
    add_batch(EN_SAMPLES, "en")      # 30 items
    add_batch(AR_SAMPLES, "ar")      # 30 items
    add_batch(DE_SAMPLES, "de")      # 20 items

    labels = []
    for idx, item in enumerate(all_items, start=1):
        filename = f"l{idx:04d}.png"
        img_path = images_dir / filename

        # Largeur dynamique adaptée au texte
        w = max(800, len(item["text"]) * 22 + 80)
        h = 80
        img = Image.new("RGB", (w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        active_font = font_ar if item["language"] == "ar" else font_fr_en
        # Coordonnées selon RTL / LTR
        if item["language"] == "ar":
            # Dessin vers la droite
            draw.text((w - 40, 22), item["text"], fill=(0, 0, 0), font=active_font, anchor="rt")
        else:
            draw.text((30, 22), item["text"], fill=(0, 0, 0), font=active_font)

        img.save(img_path, format="PNG")

        labels.append({
            "image": filename,
            "text": item["text"],
            "language": item["language"],
            "category": item["category"],
            "has_accents": item["has_accents"],
            "page_group": item["page_group"],
        })

    labels_file.write_text(json.dumps(labels, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Benchmark étendu généré avec succès : {len(labels)} échantillons dans {out_dir}")
    print(f"Ventilation : 120 FR, 30 EN, 30 AR, 20 DE. Total pages : {page_counter}")


if __name__ == "__main__":
    generate_extended_benchmark()
