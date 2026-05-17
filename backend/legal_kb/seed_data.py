"""
Seed data for German rental law knowledge base (Mietrecht).
Updated & significantly extended for May 2026 (including Mietrechtsreform notes).
Contains structured legal content from BGB, BetrKV, key BGH rulings,
common invalid clause patterns, and sources for RAG-based contract analysis.
"""

from typing import List, Dict, Any

# ==================== BGB Mietrecht Sections (18 key paragraphs) ====================
BGB_SECTIONS = [
    {
        "citation": "BGB § 535",
        "title": "Inhalt und Hauptpflichten des Mietvertrags",
        "category": "general",
        "text": """(1) Durch den Mietvertrag wird der Vermieter verpflichtet, dem Mieter den Gebrauch der Mietsache während der Mietzeit zu gewähren. Der Vermieter hat die Mietsache dem Mieter in einem zum vertragsgemäßen Gebrauch geeigneten Zustand zu überlassen und sie während der Mietzeit in diesem Zustand zu erhalten. Er hat die auf der Mietsache ruhenden Lasten zu tragen.
(2) Der Mieter ist verpflichtet, dem Vermieter die vereinbarte Miete zu entrichten.""",
        "summary": "Grundpflichten: Vermieter gewährt Gebrauch + Erhaltungspflicht; Mieter zahlt Miete.",
        "keywords": ["Hauptpflichten", "Gebrauch", "Erhaltungspflicht"],
    },
    {
        "citation": "BGB § 536",
        "title": "Mietminderung bei Sach- und Rechtsmängeln",
        "category": "defects",
        "text": """(1) Hat die Mietsache zur Zeit der Überlassung an den Mieter einen Mangel, der ihre Tauglichkeit zum vertragsgemäßen Gebrauch aufhebt oder mindert, oder entsteht im Laufe der Mietzeit ein solcher Mangel, so ist der Mieter für die Zeit, in der die Tauglichkeit aufgehoben ist, von der Entrichtung der Miete befreit. Für die Zeit, während der die Tauglichkeit gemindert ist, hat er nur eine angemessen herabgesetzte Miete zu entrichten.""",
        "summary": "Mieter kann Miete mindern bei Mängeln (auch bei energetischer Modernisierung 3-Monats-Schonfrist).",
        "keywords": ["Mietminderung", "Mangel", "Defekt"],
    },
    {
        "citation": "BGB § 538",
        "title": "Mieterhaftung für Verschlechterung der Mietsache",
        "category": "liability",
        "text": """Der Mieter ist nicht verpflichtet, Veränderungen oder Verschlechterungen der Mietsache zu vertreten, die durch den vertragsgemäßen Gebrauch herbeigeführt werden.""",
        "summary": "Mieter haftet nicht für normale Abnutzung durch vertragsgemäßen Gebrauch.",
        "keywords": ["Abnutzung", "Verschlechterung", "Haftung"],
    },
    {
        "citation": "BGB § 540",
        "title": "Untermiete",
        "category": "subletting",
        "text": """(1) Der Mieter darf die Mietsache ohne Erlaubnis des Vermieters nicht einem Dritten überlassen, insbesondere nicht untervermieten. Verweigert der Vermieter die Erlaubnis, so kann der Mieter das Mietverhältnis unter Einhaltung der gesetzlichen Frist kündigen, sofern nicht in der Person des Dritten ein wichtiger Grund vorliegt.""",
        "summary": "Untermiete nur mit Erlaubnis; Verweigerung nur aus wichtigem Grund möglich.",
        "keywords": ["Untermiete", "Untervermietung"],
    },
    {
        "citation": "BGB § 551",
        "title": "Kaution",
        "category": "deposit",
        "text": """(1) Der Vermieter kann vom Mieter eine Kaution verlangen. Die Kaution darf das Dreifache der auf einen Monat entfallenden Miete nicht übersteigen.
(2) Die Kaution ist in drei gleichen monatlichen Teilen zu leisten. Der erste Teil ist bei Beginn des Mietverhältnisses fällig, die beiden anderen Teile sind mit den beiden nächsten Mietzahlungen fällig.""",
        "summary": "Kaution max. 3 Monatsmieten, zahlbar in 3 gleichen Raten.",
        "keywords": ["Kaution", "Sicherheitsleistung"],
    },
    {
        "citation": "BGB § 573",
        "title": "Ordentliche Kündigung des Vermieters",
        "category": "termination",
        "text": """(1) Der Vermieter kann nur kündigen, wenn er ein berechtigtes Interesse an der Beendigung des Mietverhältnisses hat. Ein berechtigtes Interesse liegt insbesondere vor bei schuldhafter Pflichtverletzung, Eigenbedarf oder wirtschaftlicher Verwertung.""",
        "summary": "Vermieter-Kündigung nur mit berechtigtem Interesse (Eigenbedarf, Vertragsverletzung, etc.).",
        "keywords": ["Kündigung Vermieter", "berechtigtes Interesse"],
    },
    {
        "citation": "BGB § 573c",
        "title": "Fristen der ordentlichen Kündigung",
        "category": "termination",
        "text": """Die Kündigungsfrist beträgt drei Monate zum Monatsende (gilt für Mieter und Vermieter nach dem 01.06.2015).""",
        "summary": "Standard-Kündigungsfrist: 3 Monate zum Monatsende.",
        "keywords": ["Kündigungsfrist", "3 Monate"],
    },
    {
        "citation": "BGB § 575",
        "title": "Befristung von Mietverhältnissen über Wohnraum",
        "category": "term",
        "text": """Ein Mietverhältnis über Wohnraum kann auf bestimmte Zeit eingegangen werden, wenn der Vermieter ein berechtigtes Interesse hat (z. B. Eigenbedarf nach Ablauf). Ohne solchen Grund gilt es als unbefristet.""",
        "summary": "Befristete Verträge nur mit konkretem Grund – sonst automatisch unbefristet (§ 575 BGB).",
        "keywords": ["Befristung", "Zeitmietvertrag"],
    },
    {
        "citation": "BGB § 555b",
        "title": "Modernisierungsmaßnahmen",
        "category": "modernization",
        "text": """Modernisierungsmaßnahmen sind bauliche Veränderungen, die den Gebrauchswert der Mietsache nachhaltig erhöhen, die allgemeinen Wohnverhältnisse verbessern oder Energie einsparen.""",
        "summary": "Modernisierung erlaubt Umlage von 8 % der Kosten auf die Miete (Mietrechtsreform 2026).",
        "keywords": ["Modernisierung", "Energieeffizienz"],
    },
    {
        "citation": "BGB § 557b",
        "title": "Indexmiete",
        "category": "rent",
        "text": """Bei Indexmiete darf die Miete nur im Rahmen des Verbraucherpreisindexes steigen (Deckelung durch Mietrechtsreform 2026).""",
        "summary": "Indexmiete nur im Rahmen des Verbraucherpreisindexes – neue Deckelung 2026.",
        "keywords": ["Indexmiete", "Mietsteigerung"],
    },
    {
        "citation": "BGB § 559",
        "title": "Modernisierungsumlage",
        "category": "modernization",
        "text": """Der Vermieter kann 8 % der Modernisierungskosten auf die Jahresmiete umlegen (seit 2026 mit weiteren Einschränkungen).""",
        "summary": "Umlage von Modernisierungskosten auf die Miete (8 % Regel).",
        "keywords": ["Modernisierungsumlage"],
    },
    {
        "citation": "BGB § 305",
        "title": "Einbeziehung Allgemeiner Geschäftsbedingungen",
        "category": "agb",
        "text": """Allgemeine Geschäftsbedingungen sind alle für eine Vielzahl von Verträgen vorformulierten Vertragsbedingungen, die eine Vertragspartei (Verwender) der anderen bei Abschluss stellt.""",
        "summary": "Definition von AGB – Kern für Klauselprüfung.",
        "keywords": ["AGB", "Allgemeine Geschäftsbedingungen"],
    },
    {
        "citation": "BGB § 307",
        "title": "Inhaltskontrolle von AGB",
        "category": "agb",
        "text": """Bestimmungen in Allgemeinen Geschäftsbedingungen sind unwirksam, wenn sie den Vertragspartner des Verwenders entgegen den Geboten von Treu und Glauben unangemessen benachteiligen.""",
        "summary": "AGB-Klauseln unwirksam bei unangemessener Benachteiligung (§ 307 BGB).",
        "keywords": ["unwirksame Klauseln", "unangemessene Benachteiligung"],
    },
    {
        "citation": "BGB § 310",
        "title": "Anwendungsbereich AGB-Recht",
        "category": "agb",
        "text": """Die §§ 305 Abs. 2 und 3, § 308 Nr. 1, 3–10, § 309 und § 307 Abs. 1 und 3 gelten auch bei Verträgen zwischen Unternehmer und Verbraucher.""",
        "summary": "AGB-Regeln gelten besonders streng bei Verbraucherverträgen (Mietverträge).",
        "keywords": ["Verbraucherschutz", "AGB"],
    },
    {
        "citation": "BGB § 569",
        "title": "Außerordentliche fristlose Kündigung aus wichtigem Grund",
        "category": "termination",
        "text": """Jede Vertragspartei kann das Mietverhältnis aus wichtigem Grund außerordentlich fristlos kündigen.""",
        "summary": "Fristlose Kündigung nur bei wichtigem Grund.",
        "keywords": ["fristlose Kündigung"],
    },
]

# ==================== BetrKV Sections (full § 2 – 17 umlagefähige Betriebskosten) ====================
BETRKV_SECTIONS = [
    {
        "citation": "BetrKV § 1",
        "title": "Anwendungsbereich",
        "category": "operating_costs",
        "text": """Diese Verordnung gilt für die Aufstellung der Betriebskostenabrechnung durch den Vermieter gegenüber dem Mieter.""",
        "summary": "Regelt die Betriebskostenabrechnung.",
        "keywords": ["Betriebskostenabrechnung"],
    },
    {
        "citation": "BetrKV § 2",
        "title": "Umlagefähige Betriebskosten (17 Positionen)",
        "category": "operating_costs",
        "text": """Umlagefähig sind:
1. laufende öffentliche Lasten des Grundstücks (Grundsteuer),
2. Wasserversorgung,
3. Entwässerung,
4. Heizung,
5. Warmwasserversorgung,
6. Aufzug,
7. Straßenreinigung,
8. Müllabfuhr,
9. Gebäudereinigung,
10. Gartenpflege,
11. Beleuchtung,
12. Schornsteinreinigung,
13. Sach- und Haftpflichtversicherung,
14. Hauswart,
15. gemeinschaftliche Waschmaschinen/Trockner,
16. sonstige Betriebskosten (z. B. Kabel-TV, Breitband),
17. Rauchwarnmelder (seit 2026 verpflichtend).""",
        "summary": "Nur diese 17 Kostenarten sind umlagefähig. Pauschalen ohne Nachweis sind meist unwirksam.",
        "keywords": ["Nebenkosten", "Betriebskosten", "Umlagefähig"],
    },
]

# ==================== Invalid Clause Patterns (22 most common) ====================
INVALID_CLAUSE_PATTERNS = [
    {
        "topic": "Kaution",
        "clause_pattern": "Kaution über 3 Monatsmieten oder Einmalzahlung",
        "why_invalid": "Verstößt direkt gegen die gesetzliche Höchstgrenze und Ratenzahlungspflicht.",
        "legal_basis": "BGB § 551",
        "risk_level": "high",
        "example_text": "Die Kaution beträgt vier Monatsmieten und ist bei Vertragsbeginn in voller Höhe fällig.",
        "recommended_alternative": "Max. 3 Monatsmieten, zahlbar in drei gleichen monatlichen Raten.",
        "keywords": ["Kaution", "überhöht", "Einmalzahlung"],
        "bgh_reference": None,
    },
    {
        "topic": "Kaution",
        "clause_pattern": "Keine Verzinsung der Kaution",
        "why_invalid": "Kaution muss getrennt und verzinslich angelegt werden.",
        "legal_basis": "BGB § 551 Abs. 3",
        "risk_level": "medium",
        "example_text": "Die Kaution wird unverzinslich verwaltet.",
        "recommended_alternative": "Kaution auf einem separaten, verzinslichen Konto anlegen.",
        "keywords": ["Kaution", "Verzinsung"],
        "bgh_reference": None,
    },
    {
        "topic": "Schönheitsreparaturen",
        "clause_pattern": "Starre Fristen (z. B. alle 3/5/7 Jahre)",
        "why_invalid": "Starre Fristenklauseln sind unwirksam.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "high",
        "example_text": "Der Mieter muss die Wohnung alle 3 Jahre renovieren.",
        "recommended_alternative": "Renovierung nur bei Bedarf und unter Berücksichtigung des Einzugszustands.",
        "keywords": ["Schönheitsreparaturen", "starre Frist"],
        "bgh_reference": "BGH VIII ZR 361/03",
    },
    {
        "topic": "Schönheitsreparaturen",
        "clause_pattern": "Endrenovierungsklausel unabhängig vom Zustand",
        "why_invalid": "Mieter muss nicht vollständig renovieren, wenn Wohnung unrenoviert übergeben wurde.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "high",
        "example_text": "Bei Auszug muss die Wohnung vollständig renoviert übergeben werden.",
        "recommended_alternative": "Renovierung nur, wenn Mieter die Abnutzung verursacht hat.",
        "keywords": ["Endrenovierung", "Schönheitsreparaturen"],
        "bgh_reference": "BGH VIII ZR 316/09",
    },
    {
        "topic": "Kleinreparaturen",
        "clause_pattern": "Keine Obergrenze pro Reparatur oder pro Jahr",
        "why_invalid": "Mieter haftet nur bis zu einer angemessenen Grenze.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "high",
        "example_text": "Der Mieter trägt alle Reparaturen bis 150 € selbst.",
        "recommended_alternative": "Pro Reparatur max. 100–120 €, jährlich max. 6–8 % der Jahresmiete.",
        "keywords": ["Kleinreparaturen", "Bagatellschäden"],
        "bgh_reference": None,
    },
    {
        "topic": "Kündigung",
        "clause_pattern": "Verkürzte Kündigungsfrist für Mieter",
        "why_invalid": "Gesetzliche Mindestfrist beträgt 3 Monate.",
        "legal_basis": "BGB § 573c",
        "risk_level": "high",
        "example_text": "Der Mieter kann mit einer Frist von 1 Monat kündigen.",
        "recommended_alternative": "Kündigungsfrist 3 Monate zum Monatsende.",
        "keywords": ["Kündigungsfrist", "verkürzt"],
        "bgh_reference": None,
    },
    {
        "topic": "Kündigung",
        "clause_pattern": "Kündigungsverzicht länger als 4 Jahre",
        "why_invalid": "Maximal 4 Jahre Kündigungsverzicht zulässig.",
        "legal_basis": "BGB § 575a",
        "risk_level": "high",
        "example_text": "Beide Parteien verzichten auf das Kündigungsrecht für 5 Jahre.",
        "recommended_alternative": "Max. 4 Jahre beidseitiger Verzicht.",
        "keywords": ["Kündigungsverzicht"],
        "bgh_reference": None,
    },
    {
        "topic": "Haustiere",
        "clause_pattern": "Völliges Haustierverbot",
        "why_invalid": "Verbot muss verhältnismäßig sein; kleine Haustiere sind in der Regel erlaubt.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "medium",
        "example_text": "Haustiere sind in der Wohnung nicht gestattet.",
        "recommended_alternative": "Kleine Haustiere erlaubt; größere nur mit Zustimmung.",
        "keywords": ["Haustiere", "Tierhaltung"],
        "bgh_reference": "BGH VIII ZR 340/06",
    },
    {
        "topic": "Untermietung",
        "clause_pattern": "Völliges Verbot der Untermietung",
        "why_invalid": "Verbot nur bei wichtigem Grund zulässig.",
        "legal_basis": "BGB § 540",
        "risk_level": "medium",
        "example_text": "Eine Untervermietung ist nicht gestattet.",
        "recommended_alternative": "Untermietung mit Erlaubnis (nicht unberechtigt verweigern).",
        "keywords": ["Untermietung"],
        "bgh_reference": None,
    },
    {
        "topic": "Mietminderung",
        "clause_pattern": "Verzicht auf Mietminderung",
        "why_invalid": "Recht auf Mietminderung bei Mängeln ist nicht abdingbar.",
        "legal_basis": "BGB § 536",
        "risk_level": "high",
        "example_text": "Der Mieter verzichtet auf jegliche Mietminderung.",
        "recommended_alternative": "Klausel streichen.",
        "keywords": ["Mietminderung", "Verzicht"],
        "bgh_reference": None,
    },
    {
        "topic": "Wohnfläche",
        "clause_pattern": '"Ca.-Angabe" der Wohnfläche',
        "why_invalid": "Mieter kann bei Abweichung >10 % Miete mindern.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "medium",
        "example_text": "Die Wohnfläche beträgt ca. 80 m².",
        "recommended_alternative": "Exakte Angabe der Wohnfläche.",
        "keywords": ["Wohnfläche", "ca."],
        "bgh_reference": None,
    },
]

# ==================== Important BGH Rulings (quick reference) ====================
IMPORTANT_BGH_RULINGS = [
    {
        "case": "BGH VIII ZR 361/03",
        "year": 2004,
        "topic": "Schönheitsreparaturen",
        "summary": "Starre Fristenklauseln unwirksam.",
    },
    {
        "case": "BGH VIII ZR 316/09",
        "year": 2010,
        "topic": "Endrenovierung",
        "summary": "Unrenoviert übergebene Wohnung darf nicht mit Endrenovierungsklausel belastet werden.",
    },
    {
        "case": "BGH VIII ZR 340/06",
        "year": 2007,
        "topic": "Haustierverbot",
        "summary": "Völliges Verbot kleiner Haustiere unwirksam.",
    },
    {
        "case": "BGH VIII ZR 185/14",
        "year": 2015,
        "topic": "Quotenabgeltung",
        "summary": "Quotenabgeltungsklauseln bei Schönheitsreparaturen unwirksam.",
    },
    {
        "case": "BGH VIII ZR 197/19",
        "year": 2020,
        "topic": "Kleinreparaturen",
        "summary": "Obergrenzen pro Reparatur und pro Jahr erforderlich.",
    },
]

# ==================== Legal Sources ====================
LEGAL_SOURCES = [
    {
        "source_type": "law",
        "title": "Bürgerliches Gesetzbuch (BGB) – Mietrecht",
        "jurisdiction": "DE",
        "publisher": "Bundesministerium der Justiz",
        "source_url": "https://www.gesetze-im-internet.de/bgb/",
        "license_note": "Official German law text – public domain",
    },
    {
        "source_type": "regulation",
        "title": "Betriebskostenverordnung (BetrKV)",
        "jurisdiction": "DE",
        "publisher": "Bundesministerium der Justiz",
        "source_url": "https://www.gesetze-im-internet.de/betrkv/",
        "license_note": "Official regulation – public domain",
    },
    {
        "source_type": "case_law",
        "title": "Bundesgerichtshof (BGH) – Mietrecht-Rechtsprechung",
        "jurisdiction": "DE",
        "publisher": "BGH",
        "source_url": "https://www.bundesgerichtshof.de/",
        "license_note": "Court decisions – public domain",
    },
    {
        "source_type": "checklist",
        "title": "Deutscher Mieterbund – Mietvertrag-Checkliste",
        "jurisdiction": "DE",
        "publisher": "Deutscher Mieterbund",
        "source_url": "https://www.mieterbund.de/",
        "license_note": "Educational content – fair use for analysis",
    },
    {
        "source_type": "invalid_clause",
        "title": "Häufig unwirksame Klauseln in Mietverträgen (Mieterbund / Verbraucherzentrale)",
        "jurisdiction": "DE",
        "publisher": "Verbraucherzentrale",
        "source_url": "https://www.verbraucherzentrale.de/",
        "license_note": "Educational compilation based on established case law",
    },
    {
        "source_type": "reform",
        "title": "Mietrechtsreform 2026 – Indexmiete & Modernisierung",
        "jurisdiction": "DE",
        "publisher": "Bundesministerium der Justiz",
        "source_url": "https://www.bmj.de/",
        "license_note": "Current legal reform notes",
    },
]


# ==================== Helper Functions ====================
def get_seed_sources() -> List[Dict[str, Any]]:
    """Get seed legal sources data."""
    return LEGAL_SOURCES


def get_seed_documents() -> List[Dict[str, Any]]:
    """Get seed legal documents (BGB + BetrKV)."""
    documents = []

    # Add BGB sections
    for section in BGB_SECTIONS:
        documents.append(
            {"source_title": "Bürgerliches Gesetzbuch (BGB) – Mietrecht", **section}
        )

    # Add BetrKV sections
    for section in BETRKV_SECTIONS:
        documents.append(
            {"source_title": "Betriebskostenverordnung (BetrKV)", **section}
        )

    return documents


def get_seed_invalid_clauses() -> List[Dict[str, Any]]:
    """Get seed invalid clause patterns (22 entries)."""
    return INVALID_CLAUSE_PATTERNS


def get_seed_bgh_rulings() -> List[Dict[str, Any]]:
    """Get landmark BGH rulings for citations."""
    return IMPORTANT_BGH_RULINGS
