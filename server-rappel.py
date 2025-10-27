import httpx
import uvicorn
from fastmcp import FastMCP
from typing import Optional, Any, cast
import re
import urllib.parse

# 1. Initialiser un serveur MCP simple
# (Nous n'utilisons plus from_openapi)
mcp = FastMCP(name="Serveur RappelConso")

# 2. Définir l'URL de base de l'API que nous voulons
BASE_API_URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/rappelconso-v2-gtin-trie/records"


# 3. Créer un outil spécifique pour ce dataset
@mcp.tool
async def get_rappels_conso(
    limit: int = 20,
    order_by: Optional[str] = None,
    where: Optional[str] = None,
    q: Optional[str] = None,
    refine_field: Optional[str] = None,
    refine_value: Optional[str] = None,
) -> dict:
    """
    Récupère les rappels de produits du dataset 'rappelconso-v2-gtin-trie'.

    Args:
        limit: Le nombre maximum de rappels à retourner. (Défaut: 20)
        order_by: Le champ sur lequel trier les résultats (ex: "date_publication desc").
        where: Une requête de filtre Opendatasoft (ex: "nom_produit LIKE 'chocolat'").
    """
    print(f"Appel de l'outil get_rappels_conso avec limit={limit}, order_by={order_by}, where={where}")
    if q:
        print(f"Recherche full-text fournie via q={q}")
    if refine_field and refine_value:
        print(f"Refine fournie: {refine_field}={refine_value}")

    # Préparer les paramètres de la requête
    # Build params and try to translate/sanitize `where` into safer alternatives
    params: dict[str, Any] = {"limit": limit}
    if order_by:
        params["order_by"] = order_by

    # If explicit q provided, prefer it (full-text search)
    if q:
        params["q"] = q

    # If refine provided, add as refine.<field>=value (exact match)
    if refine_field and refine_value:
        params[f"refine.{refine_field}"] = refine_value

    # Try to interpret the `where` parameter if given and q/refine not provided
    if where and not q and not (refine_field and refine_value):
        # Try to match simple patterns: field LIKE 'value' or field = 'value'
        like_match = re.match(r"^\s*([a-zA-Z0-9_\.]+)\s+LIKE\s+'(.+)'\s*$", where, re.I)
        eq_match = re.match(r"^\s*([a-zA-Z0-9_\.]+)\s*=\s*'(.+)'\s*$", where)

        if like_match:
            field, value = like_match.group(1), like_match.group(2)
            # Strip % wildcards and use q for a safer full-text search
            value_unquoted = value.replace('%', '')
            params["q"] = value_unquoted
            print(f"Translating WHERE LIKE to q full-text search: q={value_unquoted}")
        elif eq_match:
            field, value = eq_match.group(1), eq_match.group(2)
            # Use refine for exact matches which the API supports
            params[f"refine.{field}"] = value
            print(f"Translating WHERE equality to refine: refine.{field}={value}")
        else:
            # Last resort: send the where clause as-is but URL-encode it to reduce malformed requests
            # The httpx client will encode params, but we make sure there's no control characters
            safe_where = where.strip()
            params["where"] = safe_where
            print(f"Sending raw WHERE to API (no safe translation found): where={safe_where}")

    # Remove any None values
    cleaned_params = {k: v for k, v in params.items() if v is not None}

    try:
        # Utiliser httpx pour faire l'appel API asynchrone
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_API_URL, params=cleaned_params)
            try:
                # Lève une erreur si le statut de la réponse est 4xx ou 5xx
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                text = exc.response.text
                hint = None
                # Provide clearer hints for common client errors
                if status == 400:
                    hint = (
                        "Le paramètre `where` semble mal formé (400 Bad Request). "
                        "Essayez `q='terme'` pour une recherche full-text ou `refine.<champ>=<valeur>` "
                        "pour des correspondances exactes. Exemple: q=boudin ou refine.nom_produit=boudin."
                    )
                elif status == 401 or status == 403:
                    hint = "Problème d'authentification/permission avec l'API publique."
                else:
                    hint = "Vérifiez les paramètres envoyés (limit, order_by, where, q, refine.*)."

                print(f"HTTP error from API: {status} - hint: {hint}")
                return {
                    "error": f"Client error {status} when calling external API",
                    "status": status,
                    "detail": text,
                    "hint": hint,
                    "params_sent": cleaned_params,
                }

            # Retourner les données JSON
            return response.json()

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
