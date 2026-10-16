"""Fixtures canónicos del dominio Metalia CPQ (Catálogo Ternium / Metecno e Inventario en Piso Querétaro)."""

import pytest


@pytest.fixture
def store():
    """Retorna una instancia limpia del almacén y catálogo en memoria de Metalia Querétaro."""
    from app.models.domain import create_default_metalia_store

    return create_default_metalia_store()
