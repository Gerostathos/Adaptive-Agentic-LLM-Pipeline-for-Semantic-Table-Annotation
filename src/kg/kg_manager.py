"""
src/kg/kg_manager.py
====================
Knowledge graph manager for the STA pipeline.

This file provides a simple common interface for different knowledge graphs.
"""

from src.config import (
    DEFAULT_KG_SOURCE,
    KG_CANDIDATE_LIMIT,
    CTA_TYPES_PER_ENTITY,
)

from src.utils.text_utils import clean_basic_text
from src.kg import wikidata_client
from src.kg import dbpedia_client


def normalize_text(value):
    """
    Normalize a text query before sending it to a knowledge graph.

    This is not semantic cleaning. It only performs final safe text cleanup.
    """

    return clean_basic_text(value)


def get_entity_candidates(
    query,
    source=DEFAULT_KG_SOURCE,
    limit=KG_CANDIDATE_LIMIT,
):
    """
    Retrieve entity candidates from a knowledge graph.

    Parameters:
        query: Text value to search.
        source: Knowledge graph source, for example "wikidata".
        limit: Maximum number of candidates.

    Returns:
        List of candidate dictionaries.
    """

    query = normalize_text(query)

    if query == "":
        return []

    source = str(source).strip().lower()

    if source == "wikidata":
        return wikidata_client.search_entities(
            query=query,
            limit=limit,
        )

    if source == "dbpedia":
        return dbpedia_client.search_entities(
        query=query,
        limit=limit,
        )

    raise ValueError(f"Unknown knowledge graph source: {source}")


def get_entity_types(
    entity,
    source=DEFAULT_KG_SOURCE,
    limit=CTA_TYPES_PER_ENTITY,
):
    """
    Retrieve type/class candidates for one selected entity.

    Parameters:
        entity: Entity dictionary or entity ID string.
        source: Knowledge graph source.
        limit: Maximum number of type candidates.

    Returns:
        List of type candidate dictionaries.
    """

    if entity is None:
        return []

    source = str(source).strip().lower()

    if isinstance(entity, dict):
        entity_id = entity.get("id", "")
    else:
        entity_id = str(entity)

    entity_id = normalize_text(entity_id)

    if entity_id == "":
        return []

    if source == "wikidata":
        return wikidata_client.get_entity_types(
            entity_id=entity_id,
            limit=limit,
        )

    if source == "dbpedia":
        return dbpedia_client.get_entity_types(
            entity=entity,
            limit=limit,
        )

    raise ValueError(f"Unknown knowledge graph source: {source}")


def print_kg_candidates(candidates):
    """
    Print KG candidates for debugging.
    """

    if not candidates:
        print("No KG candidates found.")
        return

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index}. "
            f"{candidate.get('label', '')} "
            f"({candidate.get('id', '')}) - "
            f"{candidate.get('description', '')}"
        )
