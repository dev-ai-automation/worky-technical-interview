"""Numeros reales del health score sobre el dataset del caso, marca `dataset` (ADR-005, decision D21).

Corre `resolve_identity` + `assemble_master_dataset` + `run_health`
sobre el dataset real, la misma secuencia que usa `cmd_health`, y fija
las cifras que la regla de aceptacion (D18) necesita: 650 empresas, 89
bajas en el denominador del recall, y las metricas al 10, 15 y 20 %,
todas medidas con los pesos originales del ADR-005 (momentum 0.35,
mom 0.20, drawdown 0.15, tenure 0.30).

El conteo de no detectables en k = 2 se mide en 22 de 89, no en las 10
que cita la "ruta rapida" del ADR-005: la propia tabla de tamanos de
pool de `measurements.md` (seccion 1, "Con baja | 89 | 67") ya fija 67
bajas con historia suficiente, es decir 22 sin ella, y es ese numero el
que reproduce este comando. La cifra de "10 de 89" del ADR-005 no
cuadra con su propia tabla de pool y no se fuerza aqui (decision D12
del diseno de A1: el numero medido se publica, la prueba no se ajusta
para igualar una cifra que ni el propio documento sostiene). De esas
22, 4 empresas no tienen ningun mes de uso al corte, 6 tienen un mes y
12 tienen dos: ninguna llega a los tres meses que `MIN_USAGE_MONTHS`
exige para recibir subpuntajes de uso (D19).

Con el conteo de no detectables en 22 de 89 (24.7 %), el techo
estructural del recall general es 67 / 89 = 0.753, sin importar el
peso de cada subpuntaje: una empresa sin historia nunca recibe
`health_score` y nunca puede marcarse, por diseno (D17, D19). Por eso
la regla de aceptacion se restablecio en la Adenda 1 del ADR-005 sobre
la poblacion detectable (AUC >= 0.95 y recall_detectable >= 0.85 al
20 %, contado solo entre las bajas que si recibieron `health_score`),
en vez de sobre el recall general. Con los pesos originales, las 67
bajas detectables ya quedan todas marcadas desde la tasa del 10 %, asi
que `recall_detectable` llega a 1.000 y la regla se cumple; el recall
general sigue reportandose aparte, con su techo de 0.753, como
hallazgo de onboarding para la Parte B: casi una cuarta parte del
churn ocurre antes de que exista suficiente historia de uso para que
el health score pueda verla.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worky_engine.health import metrics as hm
from worky_engine.health.runner import run_health
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.sources import load_raw_tables


@pytest.fixture(scope="module")
def real_health_result(data_dir: Path, tmp_path_factory):
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("health_dataset_numbers") / "worky_health.duckdb"
    con = open_connection(db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_health(con)
    finally:
        con.close()
    return result, assembly_outputs


@pytest.mark.dataset
def test_650_filas_89_bajas_22_no_detectables(real_health_result) -> None:
    result, _ = real_health_result
    scores = result.scores
    assert len(scores) == 650
    assert int(scores["churned"].astype(bool).sum()) == 89
    assert hm.undetectable_count(scores) == 22


@pytest.mark.dataset
def test_marcadas_al_15_por_ciento_sobre_el_libro_activo(real_health_result) -> None:
    """El libro activo con score definido son 518 cuentas (89 - 22 sin historia, misma proporcion en activas).

    El 15 % marca 78 cuentas, no las 81 del ADR-005: ese numero midio
    sobre un libro activo de 541 cuentas con una definicion de
    "historia suficiente" mas laxa (seccion 4 de `measurements.md`,
    donde el mismo dataset reporta 541 y 518 segun la senal). Este
    comando exige los tres subpuntajes de uso a la vez (D13), asi que
    su libro activo son las 518 que tienen los tres definidos.
    """
    scores = real_health_result[0].scores
    capacity = hm.capacity_by_csm(scores)
    assert capacity["flagged_10"]["active_book"] == 518
    assert capacity["flagged_15"]["active_book"] == 518
    assert capacity["flagged_15"]["flagged"] == 78
    assert capacity["flagged_15"]["per_csm"] == pytest.approx(11.1, abs=0.05)


@pytest.mark.dataset
def test_metricas_al_10_15_y_20_por_ciento(real_health_result) -> None:
    """Precision baja con la tasa (marca mas cuentas activas de las mismas 67 detectadas); recall general se queda fijo en 0.753.

    Las 67 bajas detectables ya estan todas marcadas desde el 10 %, asi
    que `recall` y `recall_detectable` no cambian entre tasas: el techo
    de recall general (67 / 89) y `recall_detectable` en 1.000 son los
    mismos al 10, 15 y 20 %.
    """
    scores = real_health_result[0].scores
    table = hm.rate_metrics(scores)

    assert table["flagged_10"]["precision"] == pytest.approx(0.563, abs=0.001)
    assert table["flagged_10"]["recall"] == pytest.approx(0.753, abs=0.001)
    assert table["flagged_10"]["recall_detectable"] == pytest.approx(1.000, abs=0.001)
    assert table["flagged_10"]["recall_mrr"] == pytest.approx(0.608, abs=0.001)

    assert table["flagged_15"]["precision"] == pytest.approx(0.462, abs=0.001)
    assert table["flagged_15"]["recall"] == pytest.approx(0.753, abs=0.001)
    assert table["flagged_15"]["recall_detectable"] == pytest.approx(1.000, abs=0.001)
    assert table["flagged_15"]["recall_mrr"] == pytest.approx(0.608, abs=0.001)

    assert table["flagged_20"]["precision"] == pytest.approx(0.392, abs=0.001)
    assert table["flagged_20"]["recall"] == pytest.approx(0.753, abs=0.001)
    assert table["flagged_20"]["recall_detectable"] == pytest.approx(1.000, abs=0.001)
    assert table["flagged_20"]["recall_mrr"] == pytest.approx(0.608, abs=0.001)


@pytest.mark.dataset
def test_deteccion_temprana_en_k3(real_health_result) -> None:
    result = real_health_result[0]
    early = hm.early_detection_k3(result.scores, result.sensitivities["k3"])
    assert early["eligible"] == 56
    assert early["share"] == pytest.approx(0.929, abs=0.001)


@pytest.mark.dataset
def test_regla_de_aceptacion_se_alcanza_sobre_las_bajas_detectables(real_health_result) -> None:
    """AUC pasa (>= 0.95) y recall_detectable pasa (>= 0.85) al 20 %, con los pesos originales del ADR-005 (Adenda 1, D18).

    El recall general se queda en el mismo techo estructural de 0.753
    (67 / 89): esa cifra se sigue reportando junto con el conteo de 22
    no detectables, pero ya no decide si la regla de aceptacion pasa,
    porque una baja "sin historia" nunca puede marcarse por diseno
    (D17, D19), sin importar el peso de ningun subpuntaje.
    """
    check = hm.acceptance_check(real_health_result[0].scores)
    assert check["auc"] == pytest.approx(0.997, abs=0.001)
    assert check["recall_20"] == pytest.approx(0.753, abs=0.001)
    assert check["recall_detectable_20"] == pytest.approx(1.000, abs=0.001)
    assert check["undetectable"] == 22
    assert check["passed"] is True
