"""Nombre normalizado de empresa, segun la seccion 3.1 del diseno y el ADR-001.

Quita acentos, puntuacion y razon social del nombre crudo, para que
`identity_resolution` compare la parte que en verdad identifica a la
empresa. La razon social solo se elimina cuando el token calza completo
al final del nombre, nunca como una subcadena dentro de otra palabra.
"""

from __future__ import annotations

import unicodedata

# Orden irrelevante: se revisan todas en cada pasada hasta que ninguna
# calce, asi que un nombre con mas de una razon social encadenada (por
# ejemplo "... y Asociados SA de CV") se limpia por completo.
_LEGAL_SUFFIXES = (
    "s a de c v",
    "sa de cv",
    "y asociados",
    "e hijos",
    "sa",
    "sc",
    "ac",
)


def normalize_company_name(raw: str | None) -> str | None:
    """Reduce un nombre de empresa a su forma comparable entre sistemas.

    Aplica descomposicion NFKD para quitar acentos, pasa a minusculas,
    sustituye la puntuacion por espacio, colapsa espacios repetidos y
    elimina la razon social como token final. `Gaitan y Asociados, S.A.
    de C.V.` produce `gaitan`.
    """
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None

    value = _strip_accents(value).lower()
    value = "".join(char if _is_word_char(char) else " " for char in value)
    value = " ".join(value.split())
    value = _strip_legal_suffixes(value)
    return value if value else None


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == " "


def _strip_legal_suffixes(value: str) -> str:
    changed = True
    while changed:
        changed = False
        for suffix in _LEGAL_SUFFIXES:
            if value == suffix:
                value = ""
                changed = True
                break
            if value.endswith(" " + suffix):
                value = value[: -(len(suffix) + 1)]
                changed = True
                break
    return value
