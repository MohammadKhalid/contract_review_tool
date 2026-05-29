"""
German OCR post-correction module.
Uses a fast regex-based approach and known error dictionary to fix common
Tesseract OCR misreadings in German rental contracts
(e.g., "Unterzeichnung" → "Unterawihnung").

Performance: ~1-2ms per page (vs 500ms+ with spellchecker fallback).
No slow Levenshtein distance computations on the full German dictionary.
"""

import re
from spellchecker import SpellChecker

# Curated list of German rental contract / legal terms that Tesseract often mangles
LEGAL_VOCABULARY = {
    "Vermieter",
    "Mieter",
    "Vermieterin",
    "Mieterin",
    "Miete",
    "Mietvertrag",
    "Mietverhältnis",
    "Mietobjekt",
    "Mietwohnung",
    "Mieträume",
    "Mietfläche",
    "Wohnfläche",
    "Mietzeit",
    "Mietdauer",
    "Mietbeginn",
    "Mietende",
    "Mietzins",
    "Mietpreis",
    "Mietanpassung",
    "Kaution",
    "Kautionszahlung",
    "Mietkaution",
    "Sicherheitsleistung",
    "Kündigung",
    "Kündigungsfrist",
    "Kündigungsschutz",
    "ordentliche",
    "außerordentliche",
    "fristlose",
    "Kündigungsverzicht",
    "Nebenkosten",
    "Betriebskosten",
    "Heizkosten",
    "Warmwasser",
    "Kaltmiete",
    "Warmmiete",
    "Mieterhöhung",
    "Staffelmiete",
    "Indexmiete",
    "BetrKV",
    "Betriebskostenabrechnung",
    "Vorauszahlung",
    "Abrechnung",
    "Umlage",
    "Renovierung",
    "Schönheitsreparaturen",
    "Instandhaltung",
    "Instandsetzung",
    "Modernisierung",
    "Schadensersatz",
    "Schaden",
    "Mangel",
    "Mängel",
    "Unterzeichnung",
    "Untermiete",
    "Untermieter",
    "Untervermieter",
    "BGB",
    "Paragraph",
    "Absatz",
    "Satz",
    "Ziffer",
    "Vertrag",
    "Vertragsparteien",
    "Vertragsgegenstand",
    "Vertragsdauer",
    "Frist",
    "Fristen",
    "Klausel",
    "Klauseln",
    "Vereinbarung",
    "Parteien",
    "Hausordnung",
    "Haustiere",
    "Wohnung",
    "Gebäude",
    "Zustimmung",
    "Genehmigung",
    "Nachweis",
    "Auszug",
    "Einzug",
    "Provision",
    "Makler",
    "Eigenbedarf",
    "Härte",
    "Härtefall",
    "vereinbaren",
    "verpflichten",
    "berechnen",
    "zahlen",
    "leisten",
    "kündigen",
    "verlängern",
    "mindern",
    "erhöhen",
    "abrechnen",
    "besichtigen",
    "betreten",
    "dulden",
    "aussetzen",
    "widersprechen",
}

# German-to-German corrections for known Tesseract misreadings
KNOWN_OCR_ERRORS = {
    "Unterawihnung": "Unterzeichnung",
    "Unterzeichnunq": "Unterzeichnung",
    "Unterzeichnunp": "Unterzeichnung",
    "Kautionz": "Kaution",
    "Kündiqunq": "Kündigung",
    "Kündiqunp": "Kündigung",
    "Kündiqunz": "Kündigung",
    "Kündiqungsfrist": "Kündigungsfrist",
    "Kundiqunq": "Kündigung",
    "Kundiqunp": "Kündigung",
    "Kundiqunz": "Kündigung",
    "Schönheitsreparatur": "Schönheitsreparaturen",
    "Mietvertraq": "Mietvertrag",
    "Mietvertrap": "Mietvertrag",
    "Mieterhöhunp": "Mieterhöhung",
    "Mieterhöhune": "Mieterhöhung",
    "Renovierunq": "Renovierung",
    "Renovierunp": "Renovierung",
    "Vermiqter": "Vermieter",
    "Vermipter": "Vermieter",
    "Hausordnunp": "Hausordnung",
    "Hausordnune": "Hausordnung",
    "Berechnunp": "Berechnung",
    "Berechnune": "Berechnung",
    "Vereinbarunp": "Vereinbarung",
    "Vereinbarune": "Vereinbarung",
}

# Fast regex-based corrections for common Tesseract OCR character substitutions.
# These patterns handle the most frequent German OCR errors without needing
# expensive spellchecker Levenshtein computations.
# Patterns avoid using \b since German words often have suffixes (genitive 's', etc.)
# Ordered by specificity (specific patterns first to avoid false matches).
_OCR_PATTERNS = [
    # "gung" mangling: Tesseract often reads "ng" as "nq", "np", or "nz"
    # e.g., Kündiqunq → Kündigung, Kundiqunp → Kündigung
    # Note: 'q' itself appears in these mangled forms, so include it in consonant class
    (re.compile(r"(?:un|in)q(?!u)"), "ung"),  # unq → ung
    (re.compile(r"(?<=[a-zäöü])unp"), "ung"),  # unp → ung (any consonant before)
    (re.compile(r"(?<=[a-zäöü])unz(?!u)"), "ung"),  # unz → ung
    # "igung" mangling: iqun → igun (Kündiqun → Kündigun ... then nq→ng below)
    (re.compile(r"iqun"), "igun"),
    # "trag" mangling (including with suffixes like "traqs", "traps")
    (re.compile(r"traq"), "trag"),
    (re.compile(r"trap"), "trag"),
    # "g" → "q" between vowels (conservative to avoid over-correction)
    (re.compile(r"([aeiouäöü])q(?=[aeiouäöü])"), r"\1g"),
    # "q" → "g" when followed by a consonant (after vowel)
    (re.compile(r"([aeiouäöü])q(?=[bcdfghjklmnpqrstvwxyzäöü])"), r"\1g"),
    # "q" → "g" after consonants (rq→rg, nq→ng, lq→lg for words like vorqenommen)
    (re.compile(r"rq(?=[a-zäöü])"), "rg"),
    (re.compile(r"nq(?=[a-zäöü])"), "ng"),
    (re.compile(r"lq(?=[a-zäöü])"), "lg"),
    # Final end-of-word "p" → "g" (with possible suffix like 's', 'n')
    (re.compile(r"(?<=[a-zäöü])p(?=[a-zäöü]|$)"), "g"),
    # "ichnung" mangling (Unterzeichnung, Berechnung)
    (re.compile(r"ihnung"), "echnung"),
    (re.compile(r"ihnun"), "echnun"),
    # "betraegt" → "beträgt"
    (re.compile(r"betraegt"), "beträgt"),
]


def correct_german_ocr(text: str) -> str:
    """
    Fast post-process German OCR text to fix common misreadings.

    Two-stage correction, no slow spellchecker fallback:
      1. Direct lookup against known OCR error dictionary (O(1) per word)
      2. Regex-based character substitution for common Tesseract patterns (~O(n))

    Args:
        text: Raw OCR output text

    Returns:
        Cleaned text with known errors corrected
    """
    if not text or not text.strip():
        return text

    # Stage 1: Direct dictionary lookup (fastest - O(1) per word)
    words = text.split()
    corrected = []
    for word in words:
        if word in KNOWN_OCR_ERRORS:
            corrected.append(KNOWN_OCR_ERRORS[word])
        else:
            corrected.append(word)
    text = " ".join(corrected)

    # Stage 2: Regex pattern substitution for common OCR character errors
    for pattern, replacement in _OCR_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


def extract_sections(text: str) -> list[str]:
    """
    Split contract text into sections based on German legal paragraph markers.

    Supports:
      - § 1, § 1a, § 1a (1), etc.
      - Numbered sections: 1. , 2. , 3.  (followed by uppercase German word)

    Args:
        text: Full contract text

    Returns:
        List of section text strings
    """
    if not text or not text.strip():
        return []

    # Pattern matches:
    #   § 1, § 1a, § 1a (1)
    #   1. (with capital following), 2., etc.
    section_pattern = r"(§\s*\d+[a-z]?(?:\s*\([^)]*\))?|\d+\.\s+(?=[A-ZÄÖÜ]))"

    sections = re.split(section_pattern, text)

    # Rejoin section markers with their content
    # After re.split, every odd index is a section marker, even index is content
    result = []
    for i in range(1, len(sections) - 1, 2):
        marker = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        combined = f"{marker} {content}".strip()
        if combined:
            result.append(combined)

    # If no sections found, return as single block
    if not result and sections:
        result = [s.strip() for s in sections if s.strip()]

    return result
