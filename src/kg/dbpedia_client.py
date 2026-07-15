"""
src/kg/dbpedia_client.py
========================
Low-level DBpedia client for the semantic table annotation pipeline.
"""

import time
import requests

from src.config import (
    DBPEDIA_LOOKUP_URL,
    DBPEDIA_SPARQL_URL,
    USER_AGENT,
    KG_REQUEST_DELAY_SECONDS,
    KG_MAX_RETRIES,
    KG_CANDIDATE_LIMIT,
    CTA_TYPES_PER_ENTITY,
)

from src.utils.text_utils import (
    clean_basic_text,
    clean_html_text,
    normalize_for_matching,
)


LOOKUP_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}

SPARQL_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json",
}


# Simple in-memory caches.
# These caches last only during one Python run.
ENTITY_SEARCH_CACHE = {}
ENTITY_TYPES_CACHE = {}


def dbpedia_get(url, params, headers):
    """
    Send a GET request to DBpedia with delay, retry handling, and safe errors.

    Parameters:
        url: DBpedia endpoint URL.
        params: Request parameters.
        headers: Request headers.

    Returns:
        JSON response as a dictionary, or an empty dictionary if the request fails.
    """

    for attempt in range(KG_MAX_RETRIES):
        try:
            time.sleep(KG_REQUEST_DELAY_SECONDS)

            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 429:
                wait_seconds = 2 + attempt * 2
                print(f"DBpedia rate limit hit. Waiting {wait_seconds} seconds...")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            return response.json()

        except Exception as error:
            if attempt == KG_MAX_RETRIES - 1:
                print("DBpedia request error:", error)
                return {}

            wait_seconds = 2 + attempt * 2
            print(f"DBpedia request failed. Retrying in {wait_seconds} seconds...")
            time.sleep(wait_seconds)

    return {}


def search_entities(query, limit=KG_CANDIDATE_LIMIT):
    """
    Search DBpedia entities using a text query.

    Parameters:
        query: Text value to search, for example "Inception".
        limit: Maximum number of candidates to return.

    Returns:
        A list of entity candidate dictionaries.
    """

    query = clean_basic_text(query)

    if query == "":
        return []

    cache_key = (normalize_for_matching(query), limit)

    if cache_key in ENTITY_SEARCH_CACHE:
        return ENTITY_SEARCH_CACHE[cache_key]

    params = {
        "query": query,
        "maxResults": limit,
        "format": "json",
    }

    data = dbpedia_get(
        url=DBPEDIA_LOOKUP_URL,
        params=params,
        headers=LOOKUP_HEADERS,
    )

    candidates = []

    for item in data.get("docs", []):
        resource_list = item.get("resource", [])
        label_list = item.get("label", [])
        comment_list = item.get("comment", [])

        if not resource_list:
            continue

        uri = clean_basic_text(resource_list[0])
        label = clean_html_text(label_list[0]) if label_list else ""
        description = clean_html_text(comment_list[0]) if comment_list else ""

        if uri == "":
            continue

        candidates.append(
            {
                "source": "dbpedia",
                "id": uri,
                "label": label,
                "description": description,
                "url": uri,
                "raw": item,
            }
        )

    ENTITY_SEARCH_CACHE[cache_key] = candidates

    return candidates


def get_entity_types(entity, limit=CTA_TYPES_PER_ENTITY):
    """
    Retrieve DBpedia ontology type candidates for one entity.

    Parameters:
        entity: DBpedia entity dictionary or DBpedia resource URI.
        limit: Maximum number of type candidates to return.

    Returns:
        A list of type candidate dictionaries.
    """

    if entity is None:
        return []

    if isinstance(entity, dict):
        entity_uri = entity.get("id", "")
    else:
        entity_uri = str(entity)

    entity_uri = clean_basic_text(entity_uri)

    if entity_uri == "":
        return []

    cache_key = (entity_uri, limit)

    if cache_key in ENTITY_TYPES_CACHE:
        return ENTITY_TYPES_CACHE[cache_key]

    sparql_query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dbo: <http://dbpedia.org/ontology/>

    SELECT DISTINCT ?type WHERE {{
        <{entity_uri}> rdf:type ?type .
        FILTER(STRSTARTS(STR(?type), STR(dbo:)))
    }}
    LIMIT {int(limit)}
    """

    # Important:
    # DBpedia SPARQL should use format="json" as the URL parameter.
    # The Accept header requests SPARQL JSON results.
    params = {
        "query": sparql_query,
        "format": "json",
    }

    data = dbpedia_get(
        url=DBPEDIA_SPARQL_URL,
        params=params,
        headers=SPARQL_HEADERS,
    )

    type_candidates = []

    bindings = data.get("results", {}).get("bindings", [])

    for item in bindings:
        type_uri = item.get("type", {}).get("value", "")
        type_uri = clean_basic_text(type_uri)

        if type_uri == "":
            continue

        label = type_uri.rsplit("/", 1)[-1]

        type_candidates.append(
            {
                "source": "dbpedia",
                "id": type_uri,
                "label": label,
                "description": "DBpedia ontology class",
                "url": type_uri,
                "relation": "rdf_type",
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

