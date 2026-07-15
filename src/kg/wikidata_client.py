"""
src/kg/wikidata_client.py
=========================
Low-level Wikidata client for the semantic table annotation pipeline.

This file only communicates with Wikidata and returns clean Python dictionaries.
It does not know anything about tables, columns, CEA, or CTA.
"""

import time
import requests
from src.utils.text_utils import clean_basic_text, normalize_for_matching

from src.config import (
    WIKIDATA_API_URL,
    USER_AGENT,
    KG_REQUEST_DELAY_SECONDS,
    KG_MAX_RETRIES,
    KG_CANDIDATE_LIMIT,
)


HEADERS = {
    "User-Agent": USER_AGENT
}


# Simple in-memory caches.
# These caches last only during one Python run.
ENTITY_SEARCH_CACHE = {}
ENTITY_DATA_CACHE = {}
LABEL_CACHE = {}
ENTITY_TYPES_CACHE = {}


def wikidata_get(params):
    """
    Send a GET request to Wikidata with delay, retry handling, and safe errors.

    Parameters:
        params: Dictionary of Wikidata API parameters.

    Returns:
        JSON response as a dictionary, or an empty dictionary if the request fails.
    """

    for attempt in range(KG_MAX_RETRIES):
        try:
            time.sleep(KG_REQUEST_DELAY_SECONDS)

            response = requests.get(
                WIKIDATA_API_URL,
                params=params,
                headers=HEADERS,
                timeout=20,
            )

            if response.status_code == 429:
                wait_seconds = 2 + attempt * 2
                print(f"Wikidata rate limit hit. Waiting {wait_seconds} seconds...")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            return response.json()

        except Exception as error:
            if attempt == KG_MAX_RETRIES - 1:
                print("Wikidata request error:", error)
                return {}

            wait_seconds = 2 + attempt * 2
            print(f"Wikidata request failed. Retrying in {wait_seconds} seconds...")
            time.sleep(wait_seconds)

    return {}


def search_entities(query, limit=KG_CANDIDATE_LIMIT, language="en"):
    """
    Search Wikidata entities using a text query.

    Parameters:
        query: Text value to search, for example "Inception".
        limit: Maximum number of candidates to return.
        language: Search language.

    Returns:
        A list of entity candidate dictionaries.
    """

    query = clean_basic_text(query)

    if query == "":
        return []

    cache_key = (normalize_for_matching(query), limit, language)

    if cache_key in ENTITY_SEARCH_CACHE:
        return ENTITY_SEARCH_CACHE[cache_key]

    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": language,
        "uselang": language,
        "format": "json",
        "type": "item",
        "limit": limit,
    }

    data = wikidata_get(params)

    if not data:
        ENTITY_SEARCH_CACHE[cache_key] = []
        return []

    candidates = []

    for item in data.get("search", []):
        entity_id = item.get("id", "")
        label = item.get("label", "")
        description = item.get("description", "")

        if entity_id == "":
            continue

        candidates.append(
            {
                "source": "wikidata",
                "id": entity_id,
                "label": label,
                "description": description,
                "url": f"https://www.wikidata.org/wiki/{entity_id}",
                "raw": item,
            }
        )

    ENTITY_SEARCH_CACHE[cache_key] = candidates

    return candidates


def get_entity_data(entity_id):
    """
    Retrieve Wikidata claims, labels, and descriptions for one entity.

    Parameters:
        entity_id: Wikidata entity ID, for example "Q25188".

    Returns:
        Raw Wikidata entity data dictionary.
    """

    entity_id = clean_basic_text(entity_id)

    if entity_id == "":
        return {}

    if entity_id in ENTITY_DATA_CACHE:
        return ENTITY_DATA_CACHE[entity_id]

    params = {
        "action": "wbgetentities",
        "ids": entity_id,
        "format": "json",
        "props": "claims|labels|descriptions",
        "languages": "en",
    }

    data = wikidata_get(params)

    if not data:
        ENTITY_DATA_CACHE[entity_id] = {}
        return {}

    entity_data = data.get("entities", {}).get(entity_id, {})

    ENTITY_DATA_CACHE[entity_id] = entity_data

    return entity_data


def get_labels(entity_ids):
    """
    Retrieve English labels and descriptions for multiple Wikidata IDs.

    Parameters:
        entity_ids: List of Wikidata IDs, for example ["Q11424", "Q5"].

    Returns:
        Dictionary mapping entity ID to label/description data.
    """

    if not entity_ids:
        return {}

    results = {}
    missing_ids = []

    for entity_id in entity_ids:
        entity_id = clean_basic_text(entity_id)

        if entity_id == "":
            continue

        if entity_id in LABEL_CACHE:
            results[entity_id] = LABEL_CACHE[entity_id]
        else:
            missing_ids.append(entity_id)

    if not missing_ids:
        return results

    params = {
        "action": "wbgetentities",
        "ids": "|".join(missing_ids),
        "format": "json",
        "props": "labels|descriptions",
        "languages": "en",
    }

    data = wikidata_get(params)

    if not data:
        return results

    for entity_id, entity_data in data.get("entities", {}).items():
        label = entity_data.get("labels", {}).get("en", {}).get("value", "")
        description = entity_data.get("descriptions", {}).get("en", {}).get("value", "")

        label_info = {
            "label": label,
            "description": description,
        }

        LABEL_CACHE[entity_id] = label_info
        results[entity_id] = label_info

    return results


def get_entity_types(entity_id, limit=10):
    """
    Retrieve Wikidata type candidates for one entity.

    Uses property P31, which means 'instance of'.

    Parameters:
        entity_id: Wikidata entity ID, for example "Q25188".
        limit: Maximum number of type candidates to return.

    Returns:
        A list of type candidate dictionaries.
    """

    entity_id = clean_basic_text(entity_id)

    if entity_id == "":
        return []

    cache_key = (entity_id, limit)

    if cache_key in ENTITY_TYPES_CACHE:
        return ENTITY_TYPES_CACHE[cache_key]

    entity_data = get_entity_data(entity_id)

    if not entity_data:
        ENTITY_TYPES_CACHE[cache_key] = []
        return []

    claims = entity_data.get("claims", {})
    p31_claims = claims.get("P31", [])

    type_ids = []

    for claim in p31_claims:
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            type_id = value.get("id", "")

            if type_id and type_id not in type_ids:
                type_ids.append(type_id)

        except Exception:
            continue

        if len(type_ids) >= limit:
            break

    label_map = get_labels(type_ids)

    type_candidates = []

    for type_id in type_ids:
        label = label_map.get(type_id, {}).get("label", "")
        description = label_map.get(type_id, {}).get("description", "")

        type_candidates.append(
            {
                "source": "wikidata",
                "id": type_id,
                "label": label,
                "description": description,
                "url": f"https://www.wikidata.org/wiki/{type_id}",
                "relation": "P31_instance_of",
            }
        )

    ENTITY_TYPES_CACHE[cache_key] = type_candidates

    return type_candidates


def print_candidates(candidates):
    """
    Print entity or type candidates for debugging.
    """

    if not candidates:
        print("No candidates found.")
        return

    for index, candidate in enumerate(candidates, start=1):
        print(
            f"{index}. "
            f"{candidate.get('label', '')} "
            f"({candidate.get('id', '')}) - "
            f"{candidate.get('description', '')}"
        )
