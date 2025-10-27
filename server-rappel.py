import httpx
import uvicorn
from fastmcp import FastMCP
from typing import Optional, Any, Dict, List
from models import Model, ResultEntry

# 1. Initialiser un serveur MCP simple
# (Nous n'utilisons plus from_openapi)
mcp = FastMCP(name="RappelConso")

# 2. Définir l'URL de base de l'API que nous voulons
BASE_API_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/rappelconso-v2-gtin-trie/records"


# 3. Créer un outil spécifique pour ce dataset
@mcp.tool
async def get_rappels_conso(
    limit: int = 20,
    order_by: Optional[str] = None,
    where: Optional[str] = None,
    filters: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Récupère les rappels de produits du dataset 'rappelconso-v2-gtin-trie'.

    Args:
        limit: Le nombre maximum de rappels à retourner. (Défaut: 20)
        order_by: Le champ sur lequel trier les résultats (ex: "date_publication desc").
        where: Une requête de filtre Opendatasoft (ex: "libelle LIKE 'chocolat'").
    """
    print(f"Appel de l'outil get_rappels_conso avec limit={limit}, order_by={order_by}, where={where}, filters={filters}")

    # Préparer les paramètres de la requête
    params: Dict[str, Any] = {
        "limit": limit,
        "order_by": order_by,
    }

    # Build WHERE clause from `where` or `filters` if provided.
    # Validate filter keys against ResultEntry fields to avoid sending invalid field names.
    allowed_fields = set(ResultEntry.__fields__.keys())  # type: ignore

    where_clauses: List[str] = []

    # Accept raw where string as-is (backwards compatible)
    if where:
        where_clauses.append(where)

    # If filters dict is provided, validate and build opendatasoft WHERE fragments
    if filters:
        for key, value in filters.items():
            # Do NOT perform any legacy mapping here: the caller must use real dataset field names (e.g. 'libelle')
            if key not in allowed_fields:
                print(f"Ignorer le filtre inconnu: {key}")
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

            # Lève une erreur si le statut de la réponse est 4xx ou 5xx
            response.raise_for_status()

            # Retourner les données JSON. Try to normalize into our Model when possible.
            data = response.json()
            try:
                # Incoming structure from opendatasoft: { "records": [ { "record": { "fields": { ... } } } ], ... }
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
                                results.append(ResultEntry(**fields))
                            except Exception:
                                # If a single record doesn't match, skip it
                                continue
                    if results:
                        return Model(total_count=len(results), results=results).dict()
            except Exception:
                # If normalization fails, fall back to raw response
                pass

            return data

    except httpx.RequestError as e:
        print(f"Erreur lors de l'appel API: {e}")
        return {"error": f"Erreur lors de l'appel à l'API: {e}"}
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return {"error": f"Erreur inattendue: {e}"}


# 4. Rendre le serveur exécutable (pour les tests)
if __name__ == "__main__":
    print("Serveur RappelConso démarré pour test sur http://127.0.0.1:8000")
    # Cast to Any to satisfy static type checkers (FastMCP is used as an ASGI app at runtime)
    mcp.run()
