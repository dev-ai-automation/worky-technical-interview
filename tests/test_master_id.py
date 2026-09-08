"""Pruebas de `worky_engine.identity_resolution.keys`: determinismo del master_id.

Confirma el hash determinista de la seccion 3.6 del diseno, el separador
que evita colisiones de concatenacion, la reutilizacion desde un
crosswalk existente y el aborto ante una colision real.
"""

from __future__ import annotations

import pytest

from worky_engine.identity_resolution.keys import (
    assert_unique_master_ids,
    compute_master_id,
    resolve_master_id,
)


def test_compute_master_id_es_determinista() -> None:
    first = compute_master_id("gaitan115", "sanches")
    second = compute_master_id("gaitan115", "sanches")
    assert first == second
    assert len(first) == 12
    assert all(char in "0123456789abcdef" for char in first)


def test_compute_master_id_evita_colision_de_concatenacion() -> None:
    # ("ab", "c") y ("a", "bc") no deben producir el mismo id sin el separador.
    assert compute_master_id("ab", "c") != compute_master_id("a", "bc")


def test_resolve_master_id_reutiliza_el_existente() -> None:
    # El id existente no coincide con el hash fresco a proposito, para
    # demostrar que la reutilizacion gana incluso cuando difiere.
    existing = {"HS-100028": "custom000001"}

    result = resolve_master_id("HS-100028", "sanches231", "sanches", existing)

    assert result == "custom000001"
    assert result != compute_master_id("sanches231", "sanches")


def test_resolve_master_id_genera_uno_nuevo_cuando_no_existe() -> None:
    result = resolve_master_id("HS-200099", "nueva99", "nueva empresa", {})

    assert result == compute_master_id("nueva99", "nueva empresa")


def test_assert_unique_master_ids_no_falla_sin_colision() -> None:
    companies = [
        {"hubspot_id": "HS-100001", "master_id": "aaaaaaaaaaaa"},
        {"hubspot_id": "HS-100002", "master_id": "bbbbbbbbbbbb"},
    ]

    assert_unique_master_ids(companies)  # no debe lanzar


def test_assert_unique_master_ids_aborta_ante_colision_real() -> None:
    companies = [
        {"hubspot_id": "HS-100001", "master_id": "aaaaaaaaaaaa"},
        {"hubspot_id": "HS-100002", "master_id": "aaaaaaaaaaaa"},
    ]

    with pytest.raises(ValueError, match="colision de master_id"):
        assert_unique_master_ids(companies)
