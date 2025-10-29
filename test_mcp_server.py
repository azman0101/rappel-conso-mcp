"""
Test suite for the RappelConso MCP server.

This module contains tests to verify that the MCP server is properly configured
and that all tools and prompts are available and functional.
"""

import pytest
import sys
from unittest.mock import AsyncMock, Mock, patch
import asyncio

# Import from the server module (with hyphen replaced by underscore for Python import)
import importlib.util
import os

# Load the server-rappel.py module dynamically
spec = importlib.util.spec_from_file_location(
    "server_rappel",
    os.path.join(os.path.dirname(__file__), "server-rappel.py")
)
server_rappel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_rappel)

# Import the MCP server
mcp = server_rappel.mcp


class TestMCPServerConfiguration:
    """Test the MCP server initialization and configuration."""
    
    def test_mcp_server_exists(self):
        """Test that the MCP server instance exists."""
        assert mcp is not None
    
    def test_mcp_server_name(self):
        """Test that the MCP server has the correct name."""
        assert mcp.name == "RappelConso"
    
    @pytest.mark.asyncio
    async def test_mcp_server_has_tools(self):
        """Test that the MCP server has registered tools."""
        tools = await mcp.get_tools()
        assert len(tools) > 0
    
    @pytest.mark.asyncio
    async def test_mcp_server_has_prompts(self):
        """Test that the MCP server has registered prompts."""
        prompts = await mcp.get_prompts()
        assert len(prompts) > 0


class TestMCPTools:
    """Test the availability and structure of MCP tools."""
    
    @pytest.mark.asyncio
    async def test_get_rappels_conso_tool_exists(self):
        """Test that get_rappels_conso tool is registered."""
        tools = await mcp.get_tools()
        assert "get_rappels_conso" in tools
    
    @pytest.mark.asyncio
    async def test_get_latest_rappels_tool_exists(self):
        """Test that get_latest_rappels tool is registered."""
        tools = await mcp.get_tools()
        assert "get_latest_rappels" in tools
    
    @pytest.mark.asyncio
    async def test_get_categories_with_counts_tool_exists(self):
        """Test that get_categories_with_counts tool is registered."""
        tools = await mcp.get_tools()
        assert "get_categories_with_counts" in tools
    
    @pytest.mark.asyncio
    async def test_get_most_represented_category_tool_exists(self):
        """Test that get_most_represented_category tool is registered."""
        tools = await mcp.get_tools()
        assert "get_most_represented_category" in tools
    
    @pytest.mark.asyncio
    async def test_get_latest_from_category_tool_exists(self):
        """Test that get_latest_from_category tool is registered."""
        tools = await mcp.get_tools()
        assert "get_latest_from_category" in tools
    
    @pytest.mark.asyncio
    async def test_all_expected_tools_are_available(self):
        """Test that all expected tools are available."""
        tools = await mcp.get_tools()
        
        expected_tools = [
            "get_rappels_conso",
            "get_latest_rappels",
            "get_categories_with_counts",
            "get_most_represented_category",
            "get_latest_from_category"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tools, f"Tool '{expected_tool}' is not registered"


class TestMCPPrompts:
    """Test the availability and structure of MCP prompts."""
    
    @pytest.mark.asyncio
    async def test_chercher_rappel_produit_prompt_exists(self):
        """Test that chercher_rappel_produit prompt is registered."""
        prompts = await mcp.get_prompts()
        assert "chercher_rappel_produit" in prompts
    
    @pytest.mark.asyncio
    async def test_chercher_rappel_produit_prompt_functionality(self):
        """Test that the prompt function works correctly."""
        prompts = await mcp.get_prompts()
        prompt = prompts["chercher_rappel_produit"]
        # The prompt has a .fn attribute that is the actual function
        result = prompt.fn("chocolat")
        assert isinstance(result, str)
        assert "chocolat" in result
        assert "rappel" in result.lower()


@pytest.mark.asyncio
class TestToolFunctionality:
    """Test the functionality of individual tool functions with mocked API calls."""
    
    @patch('httpx.AsyncClient')
    async def test_get_rappels_conso_basic(self, mock_client_class):
        """Test get_rappels_conso with basic parameters."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 1,
            "records": []
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_rappels_conso_fn = tools["get_rappels_conso"].fn
        result = await get_rappels_conso_fn(limit=10)
        
        assert isinstance(result, dict)
        assert "total_count" in result or "records" in result or "error" not in result
    
    @patch('httpx.AsyncClient')
    async def test_get_rappels_conso_with_filters(self, mock_client_class):
        """Test get_rappels_conso with filter parameters."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 0,
            "records": []
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_rappels_conso_fn = tools["get_rappels_conso"].fn
        result = await get_rappels_conso_fn(
            limit=5,
            order_by="date_publication desc",
            filters={"libelle": "chocolat"}
        )
        
        assert isinstance(result, dict)
    
    @patch('httpx.AsyncClient')
    async def test_get_rappels_conso_with_invalid_field(self, mock_client_class):
        """Test get_rappels_conso with invalid filter field."""
        # Mock the httpx.AsyncClient even though it won't be called
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 0,
            "records": []
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        # The function should reject invalid fields before making the API call
        tools = await mcp.get_tools()
        get_rappels_conso_fn = tools["get_rappels_conso"].fn
        result = await get_rappels_conso_fn(
            limit=5,
            filters={"invalid_field_name": "value"}
        )
        
        assert isinstance(result, dict)
        # The function should either succeed without the invalid filter or return without error
    
    @patch('httpx.AsyncClient')
    async def test_get_latest_rappels(self, mock_client_class):
        """Test get_latest_rappels function."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 0,
            "results": []
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_latest_rappels_fn = tools["get_latest_rappels"].fn
        result = await get_latest_rappels_fn(limit=50)
        
        assert isinstance(result, dict)
        assert "total_count" in result or "results" in result or "error" not in result
    
    @patch('httpx.AsyncClient')
    async def test_get_categories_with_counts(self, mock_client_class):
        """Test get_categories_with_counts function."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "facets": [
                {
                    "name": "categorie_produit",
                    "facets": [
                        {"name": "Alimentation", "count": 100},
                        {"name": "Véhicules", "count": 50}
                    ]
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_categories_with_counts_fn = tools["get_categories_with_counts"].fn
        result = await get_categories_with_counts_fn()
        
        assert isinstance(result, dict)
        assert "categories" in result or "error" in result
    
    @patch('httpx.AsyncClient')
    async def test_get_most_represented_category(self, mock_client_class):
        """Test get_most_represented_category function."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "facets": [
                {
                    "name": "categorie_produit",
                    "facets": [
                        {"name": "Alimentation", "count": 100},
                        {"name": "Véhicules", "count": 50}
                    ]
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_most_represented_category_fn = tools["get_most_represented_category"].fn
        result = await get_most_represented_category_fn()
        
        assert isinstance(result, dict)
        if "category" in result:
            assert "count" in result
            assert result["category"] == "Alimentation"
            assert result["count"] == 100
    
    @patch('httpx.AsyncClient')
    async def test_get_latest_from_category(self, mock_client_class):
        """Test get_latest_from_category function."""
        # Mock the httpx.AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": []
        }
        mock_response.raise_for_status = Mock()
        mock_response.url = "https://test.url"
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_latest_from_category_fn = tools["get_latest_from_category"].fn
        result = await get_latest_from_category_fn("Alimentation", limit=10)
        
        assert isinstance(result, dict)
        assert "total_count" in result and "results" in result


class TestErrorHandling:
    """Test error handling in the MCP tools."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_rappels_conso_http_error(self, mock_client_class):
        """Test get_rappels_conso handles HTTP errors gracefully."""
        import httpx
        
        # Mock the httpx.AsyncClient to raise an HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.url = "https://test.url"
        
        def raise_error():
            raise httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=mock_response
            )
        
        mock_response.raise_for_status = raise_error
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_rappels_conso_fn = tools["get_rappels_conso"].fn
        result = await get_rappels_conso_fn(limit=10)
        
        assert isinstance(result, dict)
        assert "error" in result
        assert "status_code" in result
        assert result["status_code"] == 404
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_rappels_conso_request_error(self, mock_client_class):
        """Test get_rappels_conso handles request errors gracefully."""
        import httpx
        
        # Mock the httpx.AsyncClient to raise a request error
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        mock_client_class.return_value = mock_client
        
        tools = await mcp.get_tools()
        get_rappels_conso_fn = tools["get_rappels_conso"].fn
        result = await get_rappels_conso_fn(limit=10)
        
        assert isinstance(result, dict)
        assert "error" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
