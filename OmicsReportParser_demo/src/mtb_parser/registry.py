"""Table registry: the single source of truth for schemas (D3/D4/D5).

Expected headers are the German header cells exactly as printed (normalized
whitespace); they double as the output column names.  Only derived columns
(``block``, ``hotspot``) use English snake_case.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SubTableSpec:
    """Expected structure of one (possibly side-by-side or stacked) sub-table."""

    headers: list[str]
    block: Optional[str] = None  # value for the derived 'block' column
    # optional remapping of detected header -> union column (t01)
    column_map: Optional[dict[str, str]] = None


@dataclass(frozen=True)
class TableSpec:
    table_id: str
    number: Optional[int]          # printed 'Tabelle N' (None for appendices)
    slug: str                      # output file name (without extension)
    expected_headers: list[str]    # German, as printed; also the column names
    anchor: int                    # column index whose word starts a new row
    hotspot: bool = False          # emit derived 'hotspot' column
    forward_fill: tuple[str, ...] = ()  # columns merged across block rows (t02)
    sub_tables: Optional[list[SubTableSpec]] = None  # t01/t07/t08 structure
    # union of all sub-table columns + 'block' (t01/t07/t08); else expected_headers
    output_columns: Optional[list[str]] = None
    title_fallback: str = ""


def _mutation9() -> list[str]:
    return ["Gen", "Transkript", "AA-Austausch", "Funktion / VarSome",
            "VAF [%] (Coverage)", "MAF", "ACMG", "REVEL", "Cancergene"]


def _mutation10(germline_label: str) -> list[str]:
    return ["Gen", "Transkript", "AA-Austausch", "Funktion / VarSome",
            "VAF [%] (Coverage) Tumor", f"VAF [%] (Coverage) {germline_label}",
            "MAF", "ACMG", "REVEL", "Cancergene"]


def _pathway(germline_suffix: list[str] | None = None) -> list[str]:
    """t09/t15 (and t12 with Topart): pathway label + 9 mutation columns."""
    base = ["Signalweg"] + _mutation9()[:3] + ["Funktion"] + _mutation9()[4:7] + ["REVEL"]
    return base + (germline_suffix or [])


_HALLMARKS = ["Term", "Count", "Size", "p-value", "adj.P.Val"]
_T01_UNION = ["block", "Eigenschaften", "Komplexe Biomarker", "Studie",
              "Anzahl", "Wert", "Studiencheck", "Einordnung"]
_T07_UNION = ["block", "OG", "CN", "CN-Typ", "Status"]
_T08_UNION = ["block", "TSG", "CN", "CN-Typ", "Status"]

TABLE_SPECS: list[TableSpec] = [
    TableSpec(
        "t01", 1, "01_key_results",
        expected_headers=[],  # per sub-table
        anchor=0,
        sub_tables=[
            SubTableSpec(["Eigenschaften", "Anzahl", "Einordnung"], block="Eigenschaften",
                         column_map={"Eigenschaften": "Eigenschaften", "Anzahl": "Anzahl",
                                     "Einordnung": "Einordnung"}),
            SubTableSpec(["Komplexe Biomarker", "Wert", "Einordnung"], block="Komplexe Biomarker",
                         column_map={"Komplexe Biomarker": "Komplexe Biomarker", "Wert": "Wert",
                                     "Einordnung": "Einordnung"}),
            SubTableSpec(["Studie", "Studiencheck"], block="Studie",
                         column_map={"Studie": "Studie", "Studiencheck": "Studiencheck"}),
        ],
        output_columns=_T01_UNION,
        title_fallback="Schlüsselergebnisse der Analyse",
    ),
    TableSpec(
        "t02", 2, "02_acmg_classified_mutations",
        expected_headers=["Kategorie", "REVEL", "Gen", "Transkript", "AA-Austausch",
                          "VAF [%]", "Cancergene", "VarSome"],
        anchor=2, hotspot=True, forward_fill=("Kategorie",),
        title_fallback="Mutationen mit ACMG Klassifizierungen",
    ),
    TableSpec("t03", 3, "03_sample_quality_issues",
              ["Probe", "Auffälligkeiten"], 0,
              title_fallback="Auffälligkeiten in Qualitätsmerkmalen der Proben"),
    TableSpec("t04", 4, "04_mutation_summary",
              ["Mutationstyp", "Anzahl", "Zygosität", "Tumorsuppressoren", "Onkogene",
               "Hotspots"], 0,
              title_fallback="Zusammenfassung der identifizierten Mutationen"),
    TableSpec("t05", 5, "05_somatic_cancer_gene_mutations", _mutation9(), 0, hotspot=True,
              title_fallback="Alle identifizierten somatischen Mutationen in Cancergenes"),
    TableSpec("t06", 6, "06_loh_cancer_gene_mutations",
              _mutation10("Keimbahn"), 0, hotspot=True,
              title_fallback="Loss of Heterozygosity in Cancergenes"),
    TableSpec(
        "t07", 7, "07_cnv_oncogenes",
        expected_headers=[],
        anchor=0,
        sub_tables=[
            SubTableSpec(["OG", "CN", "CN-Typ", "Status"], block="gain"),
            SubTableSpec(["OG", "CN", "CN-Typ", "Status"], block="loss"),
            SubTableSpec(["OG", "CN", "CN-Typ"], block="mixed"),
        ],
        output_columns=_T07_UNION,
        title_fallback="Identifizierte CNVs in Onkogenen",
    ),
    TableSpec(
        "t08", 8, "08_cnv_tumor_suppressors",
        expected_headers=[],
        anchor=0,
        sub_tables=[
            SubTableSpec(["TSG", "CN", "CN-Typ", "Status"], block="gain"),
            SubTableSpec(["TSG", "CN", "CN-Typ", "Status"], block="loss"),
            SubTableSpec(["TSG", "CN", "CN-Typ"], block="mixed"),
        ],
        output_columns=_T08_UNION,
        title_fallback="Identifizierte CNVs in Tumorsuppressoren",
    ),
    TableSpec("t09", 9, "09_somatic_pathway_mutations",
              _pathway(),
              1, hotspot=True,
              title_fallback="Identifizierte somatische Mutationen in wichtigen Signalwegen"),
    TableSpec("t10", 10, "10_cnv_pathways",
              ["Signalweg", "Status", "Kopien", "Gene"], 0,
              title_fallback="CNVs in wichtigen Signalwegen"),
    TableSpec("t11", 11, "11_mutation_signatures",
              ["Signatur", "Beschreibung", "Anteil in %", "Konfidenzintervall in %"], 0,
              title_fallback="Ergebnisse Mutationssignatur Analyse"),
    TableSpec("t12", 12, "12_topart_g1_somatic_mutations",
              _pathway(),
              1, hotspot=True,
              title_fallback="Somatische Mutationen in TOPART-G1-Genen"),
    TableSpec("t13", 13, "13_topart_germline_mutations", _mutation10("Normal"), 0, hotspot=True,
              title_fallback="Keimbahnmutationen relevant für den Topart-Score"),
    TableSpec("t14", 14, "14_germline_cancer_gene_mutations", _mutation10("Normal"), 0,
              hotspot=True,
              title_fallback="Identifizierte Keimbahn Mutationen in Cancergenes"),
    TableSpec("t15", 15, "15_germline_pathway_mutations",
              _pathway(),
              1, hotspot=True,
              title_fallback="Identifizierte Keimbahnmutationen in wichtigen Signalwegen"),
    TableSpec("t16", 16, "16_hallmarks_snv", _HALLMARKS, 0,
              title_fallback="Ergebnisse Hallmarks of Cancer Analyse, top 20"),
    TableSpec("t17", 17, "17_hallmarks_cnv_gain", _HALLMARKS, 0,
              title_fallback="Ergebnisse Hallmarks of Cancer Analyse - GAIN, top 20"),
    TableSpec("t18", 18, "18_hallmarks_cnv_loss", _HALLMARKS, 0,
              title_fallback="Ergebnisse Hallmarks of Cancer Analyse - LOSS, top 20"),
    TableSpec("t19", 19, "19_quality_criteria",
              ["Parameter", "Tumor", "Tumor Soll", "Normal", "Normal Soll"], 0,
              title_fallback="Qualitätskriterien"),
    TableSpec("t20", 20, "20_all_somatic_mutations_vaf_gt10", _mutation9(), 0, hotspot=True,
              title_fallback="Alle identifizierten somatischen Mutationen mit VAF > 10%"),
    TableSpec("t21", 21, "21_all_somatic_mutations_vaf_5_to_10", _mutation9(), 0, hotspot=True,
              title_fallback="Alle identifizierten somatischen Mutationen mit VAF 5% - 10%"),
    TableSpec("t22", 22, "22_all_loh_mutations", _mutation10("Normal"), 0, hotspot=True,
              title_fallback="Identifizierte Loss of Heterozygosity"),
    TableSpec("t23", 23, "23_filtered_mutations_oncokb", _mutation9() + ["Filter"], 0,
              hotspot=True,
              title_fallback="Alle identifizierten Mutationen in OncoKBs Genen"),
    TableSpec("t24", 24, "24_all_germline_mutations_vaf_gt10", _mutation10("Normal"), 0,
              hotspot=True,
              title_fallback="Alle identifizierten Keimbahnmutationen mit VAF > 10%"),
    TableSpec("t25", 25, "25_all_germline_mutations_vaf_5_to_10", _mutation10("Keimbahn"), 0,
              hotspot=True,
              title_fallback="Alle identifizierten Keimbahnmutationen mit VAF 5% - 10%"),
    TableSpec("t26", 26, "26_cnv_regions_cancer_genes",
              ["Chr", "CN", "Status", "Tumorsuppressoren", "Onkogene"], 0,
              title_fallback="Identifizierte CNVs mit Beteiligung von Cancergenes"),
    TableSpec("t27", 27, "27_soratram_genes", ["Gen", "AA-Austausch"], 0,
              title_fallback="Soratram - Gene"),
    TableSpec("t28", 28, "28_mk6482_phase2_genes", ["Gen"], 0,
              title_fallback="MK-6482-015 Phase2 - Gene"),
    TableSpec("app_c", None, "appendix_c_abbreviations",
              ["Abkürzung", "Bedeutung"], 0,
              title_fallback="Abkürzungsverzeichnis"),
    TableSpec("app_d", None, "appendix_d_software",
              ["Software", "Version"], 0,
              title_fallback="Programmversionen"),
]

SPEC_BY_ID = {s.table_id: s for s in TABLE_SPECS}
SPEC_BY_NUMBER = {s.number: s for s in TABLE_SPECS if s.number is not None}
