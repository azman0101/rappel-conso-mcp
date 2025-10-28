import httpx
import uvicorn
from fastmcp import FastMCP
from typing import Optional

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
    where: Optional[str] = None
) -> dict:
    """
    Récupère les rappels de produits du dataset 'rappelconso-v2-gtin-trie'.

    Args:
        limit: Le nombre maximum de rappels à retourner. (Défaut: 20)
        order_by: Le champ sur lequel trier les résultats (ex: "date_publication desc").
        where: Une requête de filtre Opendatasoft (ex: "nom_produit LIKE 'chocolat'").
    """
    print(f"Appel de l'outil get_rappels_conso avec limit={limit}, order_by={order_by}, where={where}")

    # Préparer les paramètres de la requête
    params = {
        "limit": limit,
        "order_by": order_by,
        "where": where,
    }

    # Retirer les paramètres qui sont None pour ne pas les envoyer à l'API
    cleaned_params = {k: v for k, v in params.items() if v is not None}

    try:
        # Utiliser httpx pour faire l'appel API asynchrone
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_API_URL, params=cleaned_params)
            
            # Lève une erreur si le statut de la réponse est 4xx ou 5xx
            response.raise_for_status()
            
            # Retourner les données JSON
            return response.json()
            
    except httpx.RequestError as e:
        print(f"Erreur lors de l'appel API: {e}")
        return {"error": f"Erreur lors de l'appel à l'API: {e}"}
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return {"error": f"Erreur inattendue: {e}"}


@mcp.prompt
def chercher_rappel_produit(nom_produit: str) -> str:
    """
    Génère un message pour rechercher un rappel de produit par son nom.
    """
    return f"Y a-t-il eu des rappels pour le produit libellé '{nom_produit}'?"


# 4. Rendre le serveur exécutable (pour les tests)
if __name__ == "__main__":
    print("Serveur RappelConso démarré pour test sur http://127.0.0.1:8000")
    uvicorn.run(mcp, host="127.0.0.1", port=8000)

