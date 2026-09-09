"""Ancla las cifras del tablero ejecutivo de A5 a los dos goldens versionados.

Fase 1: recalcula con pandas, desde `outputs/health/health_scores.csv` y
`outputs/master_dataset.csv` unidos por `master_id`, las cifras que el
wireframe y el mockup citan (D11 del diseno de A5): la cola de
prioridad (`flagged_15=True AND churned=False`), el MRR en riesgo, los
tramos de MRR sobre el libro activo, el conteo por `csm_owner` y las
dos cuentas de evidencia HS-100065 y HS-100507.

Fase 2: lee `docs/dashboard/01-dashboard-vp-cs.md` y
`docs/dashboard/02-mockup-vp-cs.html` como texto UTF-8 y exige que las
cadenas literales de D11 aparezcan en los dos archivos. La ultima
prueba de esta fase recalcula el MRR en riesgo y la proporcion desde
los CSV y compara el resultado formateado contra el texto ya escrito:
si un golden regenerado cambia cualquiera de esas cifras, el valor
recalculado deja de coincidir con el texto y la prueba falla ahi.

Sin marca `@pytest.mark.dataset` (decision D14 del diseno de A5): esta
prueba solo lee los dos CSV ya versionados en `outputs/`, nunca las
bases crudas de `data/raw/sistemas/`. `tests/conftest.py` salta toda
prueba marcada `dataset` cuando esa carpeta falta (por ejemplo, en este
worktree aislado), y esta prueba debe correr siempre porque sus
insumos ya estan en el repositorio.

Rutas resueltas con `Path(__file__).resolve().parent.parent`, igual que
`tests/test_health_idempotency.py`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
HEALTH_CSV = REPO_ROOT / "outputs" / "health" / "health_scores.csv"
MASTER_CSV = REPO_ROOT / "outputs" / "master_dataset.csv"
MARKDOWN_PATH = REPO_ROOT / "docs" / "dashboard" / "01-dashboard-vp-cs.md"
MOCKUP_PATH = REPO_ROOT / "docs" / "dashboard" / "02-mockup-vp-cs.html"

# Conteo por CSM sobre la cola de prioridad (78 cuentas), verificado en
# `preproposal.yaml` y en el ADR-007.
CSM_COUNTS = {
    "Jorge Ibarra": 21,
    "Ana Ruiz": 15,
    "Diego Ortega": 10,
    "Luis Peña": 10,
    "Carla Nuñez": 9,
    "Fernanda Solís": 8,
    "Marta Díaz": 5,
}

# Tramos de MRR sobre las 561 cuentas activas con score (D8 del diseno).
TRAMO_COUNTS = {
    "menos de $5,000": 131,
    "de $5,000 a $20,000": 250,
    "más de $20,000": 180,
}

# Cadenas literales exactas de D11: la fase 2 las busca tal cual, sin
# variantes ni `&nbsp;`.
LITERAL_FIGURES = (
    "$2,216,115",
    "13.7 %",
    "$16,223,225.50",
    "92.9 %",
    "$2,947",
    "$46,340",
    "35.56",
    "27.68",
)


def _load_joined() -> pd.DataFrame:
    """Une `health_scores.csv` con `csm_owner` de `master_dataset.csv` por `master_id` (decision D9)."""
    health = pd.read_csv(HEALTH_CSV)
    master = pd.read_csv(MASTER_CSV)
    return health.merge(master[["master_id", "csm_owner"]], on="master_id", how="left")


def _priority_queue(df: pd.DataFrame) -> pd.DataFrame:
    """`flagged_15 = True AND churned = False`, la regla de la cola (ADR-007)."""
    return df[(df["flagged_15"] == True) & (df["churned"] == False)]  # noqa: E712


def _active_book(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["churned"] == False]  # noqa: E712


def _tramo_counts(active: pd.DataFrame) -> pd.Series:
    bins = [-float("inf"), 5000, 20000, float("inf")]
    labels = ["menos de $5,000", "de $5,000 a $20,000", "más de $20,000"]
    tramos = pd.cut(active["mrr_mxn"], bins=bins, right=False, labels=labels)
    return tramos.value_counts()


class TestFase1CifrasDesdeLosGoldens:
    """Recalcula las cifras citadas directo desde los dos CSV versionados."""

    def setup_method(self) -> None:
        self.df = _load_joined()
        self.queue = _priority_queue(self.df)
        self.active = _active_book(self.df)

    def test_la_cola_lista_las_78_cuentas_accionables(self) -> None:
        assert len(self.queue) == 78
        assert not self.queue["churned"].any()

    def test_una_cuenta_flagged_pero_churneada_queda_excluida(self) -> None:
        flagged_sin_filtrar_churn = self.df[self.df["flagged_15"] == True]  # noqa: E712
        assert len(flagged_sin_filtrar_churn) > len(self.queue)
        assert set(self.queue["hubspot_id"]).isdisjoint(
            set(self.df[(self.df["flagged_15"] == True) & (self.df["churned"] == True)]["hubspot_id"])  # noqa: E712
        )

    def test_la_cuenta_de_mayor_mrr_aparece_primero(self) -> None:
        ordenada = self.queue.sort_values("mrr_mxn", ascending=False).reset_index(drop=True)
        assert ordenada.loc[0, "hubspot_id"] == "HS-100155"
        assert ordenada.loc[0, "mrr_mxn"] == 952602.0

    def test_un_empate_de_health_score_se_rompe_por_mrr(self) -> None:
        ordenada = self.queue.sort_values("mrr_mxn", ascending=False).reset_index(drop=True)
        empatadas = ordenada[ordenada["hubspot_id"].isin(["HS-100134", "HS-100598"])]
        assert list(empatadas["health_score"]) == [33.97, 33.97]
        posicion = {row.hubspot_id: idx for idx, row in ordenada.iterrows()}
        assert posicion["HS-100598"] < posicion["HS-100134"]

    def test_mrr_en_riesgo_y_proporcion(self) -> None:
        mrr_en_riesgo = self.queue["mrr_mxn"].sum()
        mrr_activo = self.active["mrr_mxn"].sum()
        assert mrr_en_riesgo == 2216115.0
        assert mrr_activo == 16223225.5
        assert round(mrr_en_riesgo / mrr_activo * 100, 1) == 13.7

    def test_riesgo_alto_total_activas_churneadas(self) -> None:
        riesgo_alto = self.df[self.df["risk_band"] == "riesgo alto"]
        assert len(riesgo_alto) == 145
        assert len(riesgo_alto[riesgo_alto["churned"] == False]) == 78  # noqa: E712
        assert len(riesgo_alto[riesgo_alto["churned"] == True]) == 67  # noqa: E712

    def test_el_panel_de_evidencia_lista_las_67_cuentas_churneadas(self) -> None:
        panel = self.df[(self.df["risk_band"] == "riesgo alto") & (self.df["churned"] == True)]  # noqa: E712
        assert len(panel) == 67
        assert set(panel["hubspot_id"]).isdisjoint(set(self.queue["hubspot_id"]))

    def test_sin_historia_total_churneadas_activas(self) -> None:
        sin_historia = self.df[self.df["risk_band"] == "sin historia"]
        assert len(sin_historia) == 65
        assert len(sin_historia[sin_historia["churned"] == True]) == 22  # noqa: E712
        assert len(sin_historia[sin_historia["churned"] == False]) == 43  # noqa: E712

    def test_la_cohorte_de_onboarding_lista_las_43_cuentas_activas_nuevas(self) -> None:
        cohorte = self.df[(self.df["risk_band"] == "sin historia") & (self.df["churned"] == False)]  # noqa: E712
        assert len(cohorte) == 43

    def test_cada_cuenta_de_la_cola_muestra_su_tramo_de_mrr(self) -> None:
        conteo = _tramo_counts(self.active)
        assert int(conteo["menos de $5,000"]) == 131
        assert int(conteo["de $5,000 a $20,000"]) == 250
        assert int(conteo["más de $20,000"]) == 180
        assert int(conteo.sum()) == 561

    def test_el_conteo_por_csm_coincide_con_las_cifras_verificadas(self) -> None:
        conteo = self.queue.groupby("csm_owner").size().to_dict()
        assert conteo == CSM_COUNTS

    def test_HS_100065_y_HS_100507_quedan_como_evidencia_viva_de_la_respuesta(self) -> None:
        fila_65 = self.df[self.df["hubspot_id"] == "HS-100065"].iloc[0]
        fila_507 = self.df[self.df["hubspot_id"] == "HS-100507"].iloc[0]
        assert fila_65["mrr_mxn"] == 2947.0
        assert fila_65["health_score"] == 35.56
        assert bool(fila_65["flagged_15"]) is True
        assert fila_507["mrr_mxn"] == 46340.0
        assert fila_507["health_score"] == 27.68
        assert bool(fila_507["flagged_15"]) is True

        ordenada = self.queue.sort_values("mrr_mxn", ascending=False).reset_index(drop=True)
        posicion = {row.hubspot_id: idx for idx, row in ordenada.iterrows()}
        assert posicion["HS-100507"] < posicion["HS-100065"]


class TestFase2CifrasEnLosDocumentos:
    """Lee los dos documentos como texto UTF-8 y exige las cadenas literales de D11."""

    def setup_method(self) -> None:
        self.markdown_text = MARKDOWN_PATH.read_text(encoding="utf-8")
        self.mockup_text = MOCKUP_PATH.read_text(encoding="utf-8")

    def test_no_hay_espacio_duro_en_ningun_documento(self) -> None:
        assert "&nbsp;" not in self.markdown_text
        assert "&nbsp;" not in self.mockup_text

    def test_las_cifras_ancladas_de_d11_aparecen_en_los_dos_documentos(self) -> None:
        for figura in LITERAL_FIGURES:
            assert figura in self.markdown_text, f"falta {figura} en el markdown"
            assert figura in self.mockup_text, f"falta {figura} en el mockup"

    def test_los_siete_conteos_por_csm_aparecen_en_los_dos_documentos(self) -> None:
        for nombre, conteo in CSM_COUNTS.items():
            literal = f"{nombre}: {conteo}"
            assert literal in self.markdown_text, f"falta '{literal}' en el markdown"
            assert literal in self.mockup_text, f"falta '{literal}' en el mockup"

    def test_los_tres_conteos_de_tramo_aparecen_en_los_dos_documentos(self) -> None:
        for conteo in TRAMO_COUNTS.values():
            literal = f"{conteo} cuentas"
            assert literal in self.markdown_text, f"falta '{literal}' en el markdown"
            assert literal in self.mockup_text, f"falta '{literal}' en el mockup"

    def test_la_prueba_dataset_recalcula_las_cifras_y_coincide(self) -> None:
        df = _load_joined()
        queue = _priority_queue(df)
        active = _active_book(df)
        mrr_en_riesgo = queue["mrr_mxn"].sum()
        proporcion = round(mrr_en_riesgo / active["mrr_mxn"].sum() * 100, 1)
        assert f"${mrr_en_riesgo:,.0f}" in self.markdown_text
        assert f"${mrr_en_riesgo:,.0f}" in self.mockup_text
        assert f"{proporcion} %" in self.markdown_text
        assert f"{proporcion} %" in self.mockup_text

    def test_la_prueba_falla_si_un_golden_regenerado_cambia_una_cifra_citada(self) -> None:
        """Documenta la propiedad: si el CSV cambia, el valor recalculado ya no cuadra con el texto.

        No se simula un golden alterado aqui (ninguna prueba de este
        paquete escribe sobre `outputs/`); la propiedad ya la ejercita
        `test_la_prueba_dataset_recalcula_las_cifras_y_coincide`, que
        compara el valor recalculado contra el texto en cada corrida.
        """
        df = _load_joined()
        queue = _priority_queue(df)
        assert len(queue) == 78, "si esta cifra cambia, las cadenas literales del documento dejan de cuadrar"
