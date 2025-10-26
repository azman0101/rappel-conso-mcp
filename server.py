import httpx
import uvicorn
from fastmcp import FastMCP
import os

# Set this just in case, to use the new parser
os.environ["FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER"] = "true"

# 1. Define the URL for the OpenAPI specification
openapi_spec_url = "https://data.economie.gouv.fr/api/explore/v2.1/swagger.json"

# 2. Fetch the OpenAPI spec
try:
    print(f"Fetching OpenAPI spec from {openapi_spec_url}...")
    response = httpx.get(openapi_spec_url)
    response.raise_for_status()  # Raise an exception for bad status codes
    spec = response.json()
    print("Fetch successful.")
except httpx.RequestError as e:
    print(f"Error fetching OpenAPI spec: {e}")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)


# --- START: FIX ---
# The error log shows the problem is in 'components.schemas.record'.
# It uses 'additionalProperties: {"type": "any"}', which is invalid OpenAPI.
# The correct way to allow any other properties is 'additionalProperties: true'.
# We will manually "patch" the spec in memory.

try:
    record_schema = spec.get("components", {}).get("schemas", {}).get("record", {})

    # Check if the invalid 'additionalProperties' key exists
    if record_schema and isinstance(record_schema.get("additionalProperties"), dict):
        if record_schema["additionalProperties"].get("type") == "any":
            print(
                'Patching invalid \'additionalProperties: {"type": "any"}\' in spec...'
            )
            # Replace the invalid dictionary with a valid boolean
            record_schema["additionalProperties"] = True
            print("Patch applied.")

    # Also patch the 'Reference' part which seems to be missing '$ref'
    # and has the same 'additionalProperties' issue
    record_ref_schema = record_schema.get("Reference", {})
    if record_ref_schema and isinstance(
        record_ref_schema.get("additionalProperties"), dict
    ):
        if record_ref_schema["additionalProperties"].get("type") == "any":
            print("Patching 'Reference' schema...")
            record_ref_schema["additionalProperties"] = True
            print("Patch applied.")

except Exception as e:
    # This is not fatal, but good to know
    print(f"Warning: Could not patch spec, but continuing. Error: {e}")
# --- END: FIX ---


# 3. Create an HTTP client for the API
base_url = spec.get("servers", [{}])[0].get("url", "https://data.economie.gouv.fr")

api_client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

# 4. Create the FastMCP server from the (now patched) OpenAPI spec
print("Creating MCP server from patched OpenAPI spec...")
mcp = FastMCP.from_openapi(
    openapi_spec=spec,  # Pass the patched spec
    client=api_client,
)

# 5. Make the server runnable
if __name__ == "__main__":
    print("Running server for testing...")
    uvicorn.run(mcp, host="127.0.0.1", port=8000)
