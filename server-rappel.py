import httpx
import uvicorn
import re
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from typing import Optional, Any, Dict, List, Literal
from pydantic import Field
from models import Model, ResultEntry
import logging
import sys

# Ensure logs go to stderr (not stdout) so they don't interfere with MCP stdio protocol.
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format='[%(asctime)s] %(levelname)-8s %(message)s')
# 1. Initialiser un serveur MCP simple
# (Nous n'utilisons plus from_openapi)
mcp = FastMCP(name="RappelConso")

# 2. Définir l'URL de base de l'API que nous voulons
# Remarque: le dataset correct observé dans les logs est `rappelconso-v2-gtin-espaces`.
# Le dataset `rappelconso-v2-gtin-trie` renvoyait 404 d'après les logs.
BASE_API_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/rappelconso-v2-gtin-espaces/records"


def validate_where(expr: str) -> bool:
    # Future validation logic to prevent misuse
    return True
# 3. Créer un outil spécifique pour ce dataset
@mcp.tool(exclude_args=["ctx"], description="Récupère les rappels de produits")
async def get_rappels_conso(
    limit: int = Field(20, ge=1, le=100),
    order_by: Optional[Literal["date_publication desc", "date_publication asc", "libelle asc"]] = None,
    where: Optional[str] = Field(
        None,
        description=(
            "Expression de filtre Opendatasoft. "
            "Champs valides: libelle, marque, date_publication, categorie, gtin. "
            "Opérateurs: LIKE, =, >, <."
        )
    ),
    filters: Optional[Dict[str, str]] = None,
    ctx: Context = None
) -> dict:
    """
    Récupère les rappels de produits.

    Champs utilisables dans `where`: libelle, marque, date_publication, categorie, gtin
    Opérateurs supportés: LIKE, =, >, <

    Exemples:
    - where="libelle LIKE 'chocolat'"
    - where="categorie = 'Alimentation'"
    - order_by="date_publication desc"
    """
    if where is not None and not validate_where(where):
        raise ToolError(
            f"Invalid where clause: {where}. Champs autorisés: libelle, marque, date_publication, categorie, gtin. "
            "Exemple: \"libelle LIKE 'chocolat'\""
        )

    # votre logique...
    logging.info(f"Appel de l’outil avec limit={limit}, order_by={order_by}, where={where}, filters={filters}")

    # Préparer les paramètres de la requête
    params: Dict[str, Any] = {
        "limit": limit,
        "order_by": order_by,
        # Demander explicitement toutes les colonnes (comme dans l'exemple fourni)
        "select": "*",
    }

    # Build WHERE clause from `where` or `filters` if provided.
    # Validate filter keys against ResultEntry fields to avoid sending invalid field names.
    # Pydantic v2 deprecates __fields__; prefer model_fields when available.
    try:
        allowed_fields = set(getattr(ResultEntry, "model_fields").keys())
    except Exception:
        # Fallback for Pydantic v1 / older models
        allowed_fields = set(getattr(ResultEntry, "__fields__", {}).keys())  # type: ignore

    where_clauses: List[str] = []


    def _extract_fields_from_where(where_str: str) -> set:
        """Extract candidate field names from an Opendatasoft `where` string.

        Strategy:
        - Remove single-quoted string literals to avoid capturing words inside values.
        - Find tokens that look like identifiers followed by an operator (LIKE, =, !=, <, >, IN, IS...).
        - Return a set of identifier candidates (case-sensitive as dataset fields are).
        """
        if not where_str:
            return set()
        # Remove single-quoted strings (including doubled single quotes)
        without_strings = re.sub(r"'(?:''|[^'])*'", "''", where_str)
        # Regex to capture identifier followed by an operator
        op_pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:LIKE\b|=|!=|<>|>=|<=|>|<|\bIN\b|\bIS\b)", re.I)
        return set(m.group(1) for m in op_pattern.finditer(without_strings))

    # Accept raw where string as-is (backwards compatible), but validate referenced fields
    if where and isinstance(where, str):
        cited = _extract_fields_from_where(where)
        if cited:
            invalid = [f for f in cited if f not in allowed_fields]
            logging.debug(f"Champs autorisés dans 'where': {allowed_fields}")
            if invalid:
                # Return a structured error so callers (and the LLM) are forced to use valid fields
                logging.warning(f"Rejet du paramètre 'where': champs inconnus détectés: {invalid}")
                return {
                    "error": "Invalid field(s) in 'where'",
                    "invalid_fields": invalid,
                    "allowed_fields_sample": sorted(list(allowed_fields))[:50],
                    "message": "Use only fields present in ResultEntry when building 'where' (or use the 'filters' dict with exact field names).",
                }
        else:
            # If we couldn't heuristically extract any field, accept but log a warning
            logging.warning("Aucun champ détecté dans 'where' par l'extracteur heuristique; envoi tel quel à l'API.")
        where_clauses.append(where)

    # If filters dict is provided, validate and build opendatasoft WHERE fragments
    if filters:
        for key, value in filters.items():
            # Do NOT perform any legacy mapping here: the caller must use real dataset field names (e.g. 'libelle')
            if key not in allowed_fields:
                logging.warning(f"Ignorer le filtre inconnu: {key}")
                continue
            # Basic safe quoting for single quotes inside value
            safe_value = str(value).replace("'", "''")
            clause = f"{key} LIKE '{safe_value}'"
            where_clauses.append(clause)

    if where_clauses:
        params["where"] = " AND ".join(where_clauses)

    # Retirer les paramètres qui sont None pour ne pas les envoyer à l'API
    cleaned_params = {k: v for k, v in params.items() if v is not None}

    try:
        # Utiliser httpx pour faire l'appel API asynchrone
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_API_URL, params=cleaned_params)

            # Debug: afficher l'URL finale et le statut
            logging.info(f"Requête GET: {response.url} -> {response.status_code}")

            # Lève une erreur si le statut de la réponse est 4xx ou 5xx
            response.raise_for_status()

            # Retourner les données JSON. Try to normalize into our Model when possible.
            data = response.json()
            try:
                # Incoming structure from opendatasoft: { "records": [ { "record": { "fields": { ... } } }, ... }
                # We'll extract fields into ResultEntry list if present.
                records = data.get("records")
                if isinstance(records, list):
                    results: List[ResultEntry] = []
                    for r in records:
                        # attempt to get fields from known paths
                        fields = None
                        if isinstance(r, dict):
                            fields = r.get("record", {}).get("fields") or r.get("fields")
                        if fields and isinstance(fields, dict):
                            try:
                                results.append(ResultEntry.model_validate(fields))
                            except Exception:
                                # If a single record doesn't match, skip it
                                continue
                    if results:
                        return Model(total_count=len(results), results=results).dict()
            except Exception:
                # If normalization fails, fall back to raw response
                pass

            return data

    except httpx.HTTPStatusError as e:
        # Erreur HTTP (4xx/5xx) renvoyée par raise_for_status()
        resp = e.response
        logging.error(f"Erreur HTTP {resp.status_code} pour {resp.url}: {resp.text}")
        return {"error": "HTTP error", "status_code": resp.status_code, "text": resp.text}
    except httpx.RequestError as e:
        # Erreurs de transport / connexion
        logging.error(f"Erreur lors de l'appel API: {e}")
        return {"error": f"Erreur lors de l'appel à l'API: {e}"}
    except Exception as e:
        logging.error(f"Erreur inattendue: {e}")
        return {"error": f"Erreur inattendue: {e}"}


# Helper function to call the API
async def _call_api(params: Dict[str, Any]) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_API_URL, params=params)
            logging.info(f"Requête GET: {response.url} -> {response.status_code}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        resp = e.response
        logging.error(f"Erreur HTTP {resp.status_code} pour {resp.url}: {resp.text}")
        return {"error": "HTTP error", "status_code": resp.status_code, "text": resp.text}
    except httpx.RequestError as e:
        logging.error(f"Erreur lors de l'appel API: {e}")
        return {"error": f"Erreur lors de l'appel à l'API: {e}"}
    except Exception as e:
        logging.error(f"Erreur inattendue: {e}")
        return {"error": f"Erreur inattendue: {e}"}


async def _get_categories_with_counts() -> dict:
    params = {"facet": "categorie_produit", "limit": 0}
    data = await _call_api(params)
    facets = data.get("facets", [])
    for f in facets:
        if f.get("name") == "categorie_produit":
            categories = [{"name": facet["name"], "count": facet["count"]} for facet in f.get("facets", [])]
            return {"categories": categories}
    return {"error": "No facets found"}


@mcp.tool
async def get_latest_rappels(limit: int = 100) -> dict:
    """
    Récupère les derniers rappels de produits par date de publication (les plus récents en premier).

    Args:
        limit: Le nombre maximum de rappels à retourner. (Défaut: 100)
    """
    params = {"limit": limit, "order_by": "date_publication desc", "select": "*"}
    data = await _call_api(params)

    results: list[ResultEntry] = []
    logging.info(f"data={data}")

    # 1) Opendatasoft-style response: top-level "records" list
    records = data.get("results") if isinstance(data, dict) else None
    if isinstance(records, list):
        for r in records:
            fields = None
            if isinstance(r, dict):
                fields = r.get("record", {}).get("fields") or r.get("fields")
            if fields and isinstance(fields, dict):
                try:
                    results.append(ResultEntry.model_validate(fields))
                except Exception:
                    # skip records that don't match the model
                    continue
        total = data.get("total_count", len(results)) if isinstance(data, dict) else len(results)
        return {"total_count": total, "results": [r.dict() for r in results]}

    # 4) As a last resort, return the raw API response so callers can inspect it
    return data


@mcp.tool
async def get_categories_with_counts() -> dict:
    """
    Récupère les catégories de produits avec le nombre d'occurrences (rappels par catégorie).
    """
    return await _get_categories_with_counts()


@mcp.tool
async def get_most_represented_category() -> dict:
    """
    Récupère la catégorie de produits la plus représentée (avec le plus de rappels).
    """
    counts_data = await _get_categories_with_counts()
    if "categories" in counts_data:
        categories = counts_data["categories"]
        if categories:
            most = max(categories, key=lambda x: x["count"])
            return {"category": most["name"], "count": most["count"]}
    return counts_data


@mcp.tool
async def get_latest_from_category(category: str, limit: int = 10) -> dict:
    """
    Récupère les derniers rappels d'une catégorie spécifique par date de publication.

    Args:
        category: La catégorie de produit (ex: "alimentation").
        limit: Le nombre maximum de rappels à retourner. (Défaut: 10)
    """
    safe_category = category.replace("'", "''")
    where = f"categorie_produit = '{safe_category}'"
    params = {"limit": limit, "order_by": "date_publication desc", "select": "*", "where": where}
    data = await _call_api(params)
    records = data.get("records", [])
    results = []
    for r in records:
        fields = r.get("record", {}).get("fields") or r.get("fields")
        if fields:
            try:
                results.append(ResultEntry.model_validate(fields))
            except:
                continue
    return {"total_count": len(results), "results": [r.dict() for r in results]}


@mcp.prompt
def chercher_rappel_produit(nom_produit: str) -> str:
    """
    Génère un message pour rechercher un rappel de produit par son nom.
    """
    return f"Y a-t-il eu des rappels pour le produit libellé '{nom_produit}'?"


# 4. Rendre le serveur exécutable (pour les tests)
if __name__ == "__main__":
    logging.error("Serveur RappelConso démarré pour test sur http://127.0.0.1:8000")
    # Cast to Any to satisfy static type checkers (FastMCP is used as an ASGI app at runtime)
    mcp.run()

app = mcp.http_app()
