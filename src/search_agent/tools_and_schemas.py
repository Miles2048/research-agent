from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import logging

# Configure logging
logger = logging.getLogger(__name__)


class SearchQueryList(BaseModel):
    query: List[str] = Field(
        description="A list of search queries to be used for web research."
    )
    rationale: str = Field(
        description="A brief explanation of why these queries are relevant to the research topic."
    )


class Reflection(BaseModel):
    is_sufficient: bool = Field(
        description="Whether the provided summaries are sufficient to answer the user's question."
    )
    knowledge_gap: str = Field(
        description="A description of what information is missing or needs clarification."
    )
    follow_up_queries: List[str] = Field(
        description="A list of follow-up queries to address the knowledge gap."
    )


# Import existing tools
try:
    from .tools.knowledge_search import knowledge_search
    logger.info("Successfully imported knowledge_search tool")
except ImportError as e:
    logger.error(f"Failed to import knowledge_search tool: {str(e)}")
    # Define a fallback version
    @tool
    def knowledge_search(query: str, top_k: int = 5, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Search internal knowledge base (not available)."""
        logger.error("Knowledge search tool not available due to import error")
        return []


@tool  
def web_search(query: str) -> List[Dict[str, Any]]:
    """Search the web for current information using Exa API.
    
    This tool searches the internet for up-to-date information and recent content.
    Best for: current events, recent updates, general web information, news.
    Use this when you need current information or when the knowledge base doesn't have the answer.
    
    Args:
        query: Search query string - what to search for on the web
        
    Returns:
        List of web search results with title, url, snippet, and full content.
    """
    try:
        from .tools.exa_search import perform_exa_search
        
        logger.info(f"Web search initiated: query='{query}'")
        
        # Perform web search using Exa
        results = perform_exa_search(query, num_results=5)
        
        logger.info(f"Web search completed: {len(results)} results found")
        
        return results
        
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}", exc_info=True)
        return []


