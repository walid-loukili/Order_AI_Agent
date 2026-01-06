"""
TECPAP Article Codes Manager
Gestion des codes articles compatibles SAGE X3.

Format des codes articles TECPAP:
- KB = Kraft Blanchi
- KE = Kraft Écru/Naturel
- Format complet: [TYPE][GRAMMAGE]L[LAIZE][FOURNISSEUR]
- Exemple: KB100L28MON = Kraft Blanchi 100g Laize 28 MONDI
"""

# Types de papier TECPAP
PAPER_TYPES = {
    "kraft blanchi": "KB",
    "kraft ecru": "KE",
    "kraft naturel": "KE",
    "kraft": "KE",
    "blanchi": "KB",
    "ecru": "KE",
}

# Fournisseurs de papier
SUPPLIERS = {
    "mondi": "MON",
    "nordic": "NOR",
    "billerud": "BIL",
    "smurfit": "SMU",
    "default": "STD"
}

# Grammages standards (g/m²)
STANDARD_GRAMMAGES = [40, 50, 60, 70, 80, 90, 100, 120, 140]

# Laizes standards (cm)
STANDARD_LAIZES = [15, 18, 20, 22, 25, 28, 30, 32, 35, 40, 45, 50]

# Types de sacs TECPAP
SAC_TYPES = {
    "Sachets fond plat": {"code": "SFP", "description": "Sachets à fond plat pour sandwichs, tacos, viennoiseries"},
    "Sac fond carré sans poignées": {"code": "SFCSP", "description": "Sacs fond carré sans poignées - emballage standard"},
    "Sac fond carré avec poignées plates": {"code": "SFCPP", "description": "Sacs fond carré avec poignées plates - shopping"},
    "Sac fond carré avec poignées torsadées": {"code": "SFCPT", "description": "Sacs fond carré avec poignées torsadées - premium"}
}


def generate_article_code(paper_type=None, grammage=None, laize=None, supplier=None):
    """
    Génère un code article TECPAP au format SAGE X3.
    
    Args:
        paper_type: Type de papier (kraft blanchi, kraft ecru, etc.)
        grammage: Grammage en g/m² (60, 70, 80, 100, etc.)
        laize: Laize en cm (28, 30, etc.)
        supplier: Fournisseur (MONDI, NORDIC, etc.)
    
    Returns:
        Code article formaté (ex: KB100L28MON)
    """
    # Déterminer le code type papier
    type_code = "KE"  # Default: Kraft Écru
    if paper_type:
        paper_type_lower = paper_type.lower()
        for key, code in PAPER_TYPES.items():
            if key in paper_type_lower:
                type_code = code
                break
    
    # Grammage
    gram = str(grammage) if grammage else "80"
    
    # Laize
    laize_str = f"L{laize}" if laize else ""
    
    # Fournisseur
    supplier_code = ""
    if supplier:
        supplier_lower = supplier.lower()
        for key, code in SUPPLIERS.items():
            if key in supplier_lower:
                supplier_code = code
                break
    
    # Construire le code
    article_code = f"{type_code}{gram}{laize_str}{supplier_code}"
    
    return article_code


def parse_article_code(code):
    """
    Parse un code article TECPAP pour extraire ses composants.
    
    Args:
        code: Code article (ex: KB100L28MON)
    
    Returns:
        Dict avec les composants extraits
    """
    if not code:
        return None
    
    result = {
        "paper_type": None,
        "grammage": None,
        "laize": None,
        "supplier": None,
        "raw_code": code
    }
    
    import re
    
    # Type de papier (KB ou KE)
    if code.startswith("KB"):
        result["paper_type"] = "Kraft Blanchi"
        code = code[2:]
    elif code.startswith("KE"):
        result["paper_type"] = "Kraft Écru"
        code = code[2:]
    
    # Grammage (nombre avant L)
    grammage_match = re.match(r"(\d+)", code)
    if grammage_match:
        result["grammage"] = int(grammage_match.group(1))
        code = code[len(grammage_match.group(1)):]
    
    # Laize (après L)
    laize_match = re.match(r"L(\d+)", code)
    if laize_match:
        result["laize"] = int(laize_match.group(1))
        code = code[len(laize_match.group(0)):]
    
    # Fournisseur (le reste)
    if code:
        for name, short_code in SUPPLIERS.items():
            if code == short_code:
                result["supplier"] = name.capitalize()
                break
        if not result["supplier"]:
            result["supplier"] = code
    
    return result


def suggest_article_code_from_description(description):
    """
    Suggère un code article basé sur une description en langage naturel.
    
    Args:
        description: Description du produit (ex: "kraft blanchi 100g laize 28")
    
    Returns:
        Code article suggéré
    """
    if not description:
        return None
    
    description_lower = description.lower()
    
    # Détecter le type de papier
    paper_type = None
    for key in PAPER_TYPES.keys():
        if key in description_lower:
            paper_type = key
            break
    
    # Détecter le grammage
    import re
    grammage = None
    grammage_patterns = [
        r"(\d+)\s*g(?:\/m2|ram|r)?",
        r"(\d+)\s*gr",
        r"grammage\s*[\:\=]?\s*(\d+)",
    ]
    for pattern in grammage_patterns:
        match = re.search(pattern, description_lower)
        if match:
            grammage = int(match.group(1))
            break
    
    # Détecter la laize
    laize = None
    laize_patterns = [
        r"laize?\s*[\:\=]?\s*(\d+)",
        r"l(\d+)",
        r"largeur\s*[\:\=]?\s*(\d+)",
    ]
    for pattern in laize_patterns:
        match = re.search(pattern, description_lower)
        if match:
            laize = int(match.group(1))
            break
    
    # Détecter le fournisseur
    supplier = None
    for key in SUPPLIERS.keys():
        if key in description_lower:
            supplier = key
            break
    
    return generate_article_code(paper_type, grammage, laize, supplier)


def get_all_standard_codes():
    """
    Génère la liste de tous les codes articles standards TECPAP.
    
    Returns:
        Liste de dicts avec code, description
    """
    codes = []
    
    for paper_name, paper_code in PAPER_TYPES.items():
        if paper_code == "KB":
            type_name = "Kraft Blanchi"
        else:
            type_name = "Kraft Écru"
        
        for grammage in STANDARD_GRAMMAGES:
            for laize in STANDARD_LAIZES:
                code = f"{paper_code}{grammage}L{laize}"
                description = f"{type_name} {grammage}g/m² Laize {laize}cm"
                codes.append({
                    "code": code,
                    "description": description,
                    "paper_type": type_name,
                    "grammage": grammage,
                    "laize": laize
                })
    
    return codes


# Tests
if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Test du gestionnaire de codes articles TECPAP")
    print("=" * 50)
    
    # Test génération
    print("\n📝 Test génération de code:")
    code = generate_article_code("kraft blanchi", 100, 28, "mondi")
    print(f"   kraft blanchi 100g laize 28 mondi -> {code}")
    
    # Test parsing
    print("\n🔍 Test parsing de code:")
    parsed = parse_article_code("KB100L28MON")
    print(f"   KB100L28MON -> {parsed}")
    
    # Test suggestion
    print("\n💡 Test suggestion depuis description:")
    desc = "sachets kraft blanchi 80g laize 25"
    suggested = suggest_article_code_from_description(desc)
    print(f"   '{desc}' -> {suggested}")
    
    # Afficher quelques codes standards
    print("\n📦 Exemples de codes standards:")
    standards = get_all_standard_codes()[:5]
    for s in standards:
        print(f"   {s['code']}: {s['description']}")
    
    print(f"\n✅ Total codes standards possibles: {len(get_all_standard_codes())}")
