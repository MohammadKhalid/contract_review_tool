"""
Seed data for German rental law knowledge base.
Contains structured legal content from BGB, BetrKV, and common invalid clause patterns.
"""

from typing import List, Dict, Any
from datetime import datetime

# BGB Mietrecht sections (key excerpts)
BGB_SECTIONS = [
    {
        "citation": "BGB § 535",
        "title": "Inhalt und Hauptpflichten des Mietvertrags",
        "category": "general",
        "text": """(1) Durch den Mietvertrag wird der Vermieter verpflichtet, dem Mieter den Gebrauch der Mietsache während der Mietzeit zu gewähren. Der Mieter ist verpflichtet, dem Vermieter die vereinbarte Miete zu entrichten.

(2) Der Mietvertrag ist formfrei. Bei Grundstücken und Räumen ist jedoch die Schriftform erforderlich, wenn die Parteien eine Vertragsdauer von mehr als einem Jahr vereinbaren.""",
        "summary": "Grundlegende Pflichten: Vermieter gewährt Gebrauch, Mieter zahlt Miete. Schriftform bei >1 Jahr.",
    },
    {
        "citation": "BGB § 536",
        "title": "Mietminderung bei Sach- und Rechtsmängeln",
        "category": "defects",
        "text": """(1) Hat die Mietsache zur Zeit der Überlassung an den Mieter einen Mangel, der ihre Tauglichkeit zum vertragsgemäßen Gebrauch aufhebt oder mindert, oder entsteht im Laufe der Mietzeit ein solcher Mangel, so ist der Mieter für die Zeit, in der die Tauglichkeit aufgehoben ist, von der Entrichtung der Miete befreit.""",
        "summary": "Mieter kann Miete mindern bei Mängeln die den vertragsgemäßen Gebrauch beeinträchtigen.",
    },
    {
        "citation": "BGB § 551",
        "title": "Kaution",
        "category": "deposit",
        "text": """(1) Der Vermieter kann vom Mieter eine Kaution verlangen. Die Kaution darf das Dreifache der auf einen Monat entfallenden Miete nicht übersteigen.

(2) Die Kaution ist in drei gleichen monatlichen Teilen zu leisten. Der erste Teil ist bei Beginn des Mietverhältnisses fällig, die beiden anderen Teile sind mit den beiden nächsten Mietzahlungen fällig.""",
        "summary": "Kaution max. 3 Monatsmieten, in 3 gleichen Teilen zahlbar.",
    },
    {
        "citation": "BGB § 573",
        "title": "Ordentliche Kündigung des Vermieters",
        "category": "termination",
        "text": """(1) Der Vermieter kann nur kündigen, wenn er ein berechtigtes Interesse an der Beendigung des Mietverhältnisses hat. Ein berechtigtes Interesse des Vermieters liegt insbesondere vor, wenn

1. der Mieter seine vertraglichen Pflichten schuldhaft nicht unerheblich verletzt hat,
2. der Vermieter die Räume als Wohnung für sich, seine Familienangehörigen oder Angehörige seines Haushalts benötigt,
3. der Vermieter durch die Fortsetzung des Mietverhältnisses an einer angemessenen wirtschaftlichen Verwertung des Grundstücks gehindert und dadurch erhebliche Nachteile erleiden würde.""",
        "summary": "Vermieter kann nur mit berechtigtem Interesse kündigen (Eigenbedarf, Vertragsverletzung, wirtschaftliche Verwertung).",
    },
    {
        "citation": "BGB § 573c",
        "title": "Fristen der ordentlichen Kündigung",
        "category": "termination",
        "text": """(1) Die Kündigungsfrist beträgt, wenn eine Frist nicht vereinbart worden ist,

1. drei Monate zum Monatsende, wenn der Mieter nach dem 1. Juni 2015 eingezogen ist,
2. drei Monate zum Monatsende, wenn der Vermieter nach dem 1. Juni 2015 die Kündigung ausgesprochen hat.""",
        "summary": "Ordentliche Kündigungsfrist beträgt 3 Monate zum Monatsende.",
    },
    {
        "citation": "BGB § 305",
        "title": "Einbeziehung Allgemeiner Geschäftsbedingungen in den Vertrag",
        "category": "agb",
        "text": """(1) Allgemeine Geschäftsbedingungen sind alle für eine Vielzahl von Verträgen vorformulierten Vertragsbedingungen, die eine Vertragspartei (Verwender) der anderen Vertragspartei bei Abschluss eines Vertrags stellt.""",
        "summary": "Definition von AGB als vorformulierte Vertragsbedingungen für eine Vielzahl von Verträgen.",
    },
    {
        "citation": "BGB § 307",
        "title": "Inhaltskontrolle",
        "category": "agb",
        "text": """(1) Bestimmungen in Allgemeinen Geschäftsbedingungen sind unwirksam, wenn sie den Vertragspartner des Verwenders entgegen den Geboten von Treu und Glauben unangemessen benachteiligen.""",
        "summary": "AGB-Klauseln sind unwirksam wenn sie den Vertragspartner unangemessen benachteiligen.",
    },
    {
        "citation": "BGB § 310",
        "title": "Anwendungsbereich",
        "category": "agb",
        "text": """(1) § 305 Abs. 2 und 3, § 308 Nr. 1, § 308 Nr. 3, § 308 Nr. 4, § 308 Nr. 8 bis 10, § 309 und § 307 Abs. 1 und 3 gelten auch bei Verträgen zwischen einem Unternehmer und einem Verbraucher.""",
        "summary": "Bestimmte AGB-Regeln gelten auch für Verbraucherverträge.",
    },
]

# BetrKV sections
BETRKV_SECTIONS = [
    {
        "citation": "BetrKV § 1",
        "title": "Anwendungsbereich",
        "category": "operating_costs",
        "text": """Diese Verordnung gilt für die Aufstellung der Betriebskostenabrechnung durch den Vermieter gegenüber dem Mieter.""",
        "summary": "Verordnung regelt die Betriebskostenabrechnung.",
    },
    {
        "citation": "BetrKV § 2",
        "title": "Betriebskosten",
        "category": "operating_costs",
        "text": """Betriebskosten sind die Kosten, die dem Eigentümer oder Erbbauberechtigten von Wohnraum laufend für die Instandsetzung und Instandhaltung des Gebäudes, seiner technischen Anlagen und des Grundstücks entstehen.""",
        "summary": "Definition der umlegbaren Betriebskosten.",
    },
]

# Invalid clause patterns
INVALID_CLAUSE_PATTERNS = [
    {
        "topic": "Kaution",
        "clause_pattern": "Kaution übersteigt drei Monatsmieten",
        "why_invalid": "Gemäß BGB § 551 darf die Kaution das Dreifache der monatlichen Miete nicht übersteigen.",
        "legal_basis": "BGB § 551",
        "risk_level": "high",
        "example_text": "Der Mieter leistet eine Kaution in Höhe von vier Monatsmieten.",
        "recommended_response": "Verlangen Sie die Reduzierung der Kaution auf maximal drei Monatsmieten.",
    },
    {
        "topic": "Kaution",
        "clause_pattern": "Kaution muss auf einmal gezahlt werden",
        "why_invalid": "BGB § 551 Abs. 2 verlangt die Zahlung in drei gleichen monatlichen Teilen.",
        "legal_basis": "BGB § 551 Abs. 2",
        "risk_level": "high",
        "example_text": "Die Kaution ist bei Vertragsunterzeichnung in voller Höhe fällig.",
        "recommended_response": "Fordern Sie die Aufteilung in drei monatliche Raten.",
    },
    {
        "topic": "Schönheitsreparaturen",
        "clause_pattern": "Blanket-Klausel für Schönheitsreparaturen ohne Bedingungen",
        "why_invalid": "Schönheitsreparaturklauseln müssen starre Fristen und Abstände vermeiden und den Zustand bei Einzug berücksichtigen.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "high",
        "example_text": "Der Mieter ist verpflichtet, alle 3 Jahre Schönheitsreparaturen durchzuführen.",
        "recommended_response": "Verlangen Sie eine individualvertragliche Regelung oder lassen Sie die Klausel streichen.",
    },
    {
        "topic": "Kündigung",
        "clause_pattern": "Verkürzte Kündigungsfrist für Mieter",
        "why_invalid": "Die Kündigungsfrist für Mieter beträgt mindestens 3 Monate zum Monatsende.",
        "legal_basis": "BGB § 573c",
        "risk_level": "high",
        "example_text": "Der Mieter kann mit einer Frist von 1 Monat kündigen.",
        "recommended_response": "Lassen Sie die Klausel entfernen oder auf 3 Monate zum Monatsende ändern.",
    },
    {
        "topic": "Nebenkosten",
        "clause_pattern": "Pauschale Nebenkostenabrechnung ohne Nachweis",
        "why_invalid": "BetrKV verlangt eine detaillierte Abrechnung der tatsächlich entstandenen Kosten.",
        "legal_basis": "BetrKV § 2",
        "risk_level": "medium",
        "example_text": "Die Nebenkosten betragen pauschal 150€ pro Monat.",
        "recommended_response": "Fordern Sie eine jährliche Abrechnung mit Einzelnachweisen.",
    },
    {
        "topic": "Haustiere",
        "clause_pattern": "Völliges Haustierverbot",
        "why_invalid": "Haustierverbote müssen verhältnismäßig sein und Einzelfallprüfung ermöglichen.",
        "legal_basis": "BGH-Rechtsprechung",
        "risk_level": "medium",
        "example_text": "Haustiere sind in der Wohnung nicht gestattet.",
        "recommended_response": "Verhandeln Sie eine Klausel, die kleine Haustiere erlaubt.",
    },
    {
        "topic": "Untervermietung",
        "clause_pattern": "Völliges Verbot der Untervermietung",
        "why_invalid": "Untervermietung kann nur aus wichtigem Grund untersagt werden.",
        "legal_basis": "BGB § 540",
        "risk_level": "medium",
        "example_text": "Eine Untervermietung ist nicht gestattet.",
        "recommended_response": "Lassen Sie die Klausel streichen oder auf wichtige Gründe beschränken.",
    },
    {
        "topic": "Instandhaltung",
        "clause_pattern": "Mieter haftet für alle Reparaturen unter bestimmter Summe",
        "why_invalid": "Mieter haftet nur für von ihm verursachte Schäden, nicht für normale Abnutzung.",
        "legal_basis": "BGB § 538",
        "risk_level": "high",
        "example_text": "Der Mieter trägt alle Reparaturen bis 100€ selbst.",
        "recommended_response": "Lassen Sie die Klausel entfernen.",
    },
]

# Sources metadata
LEGAL_SOURCES = [
    {
        "source_type": "law",
        "title": "Bürgerliches Gesetzbuch (BGB) - Mietrecht",
        "jurisdiction": "DE",
        "publisher": "gesetze-im-internet.de",
        "source_url": "https://www.gesetze-im-internet.de/bgb/",
        "license_note": "Official German law text, public domain",
    },
    {
        "source_type": "regulation",
        "title": "Betriebskostenverordnung (BetrKV)",
        "jurisdiction": "DE",
        "publisher": "gesetze-im-internet.de",
        "source_url": "https://www.gesetze-im-internet.de/betrkv/",
        "license_note": "Official German regulation, public domain",
    },
    {
        "source_type": "case_law",
        "title": "Bundesgerichtshof (BGH) Mietrecht-Rechtsprechung",
        "jurisdiction": "DE",
        "publisher": "BGH",
        "source_url": "https://www.bundesgerichtshof.de/",
        "license_note": "Court decisions, public domain",
    },
    {
        "source_type": "checklist",
        "title": "Mieterbund Mietvertrag-Checkliste",
        "jurisdiction": "DE",
        "publisher": "Deutscher Mieterbund",
        "source_url": "https://www.mieterbund.de/",
        "license_note": "Educational content, fair use for analysis",
    },
    {
        "source_type": "invalid_clause",
        "title": "Häufig unwirksame Klauseln in Mietverträgen",
        "jurisdiction": "DE",
        "publisher": "Curated legal analysis",
        "license_note": "Educational compilation based on established case law",
    },
]


def get_seed_sources() -> List[Dict[str, Any]]:
    """Get seed legal sources data."""
    return LEGAL_SOURCES


def get_seed_documents() -> List[Dict[str, Any]]:
    """Get seed legal documents data."""
    documents = []

    # Add BGB sections
    for section in BGB_SECTIONS:
        documents.append(
            {"source_title": "Bürgerliches Gesetzbuch (BGB) - Mietrecht", **section}
        )

    # Add BetrKV sections
    for section in BETRKV_SECTIONS:
        documents.append(
            {"source_title": "Betriebskostenverordnung (BetrKV)", **section}
        )

    return documents


def get_seed_invalid_clauses() -> List[Dict[str, Any]]:
    """Get seed invalid clause patterns."""
    return INVALID_CLAUSE_PATTERNS
