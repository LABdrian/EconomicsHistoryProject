"""
PostPunk Search API - FastAPI backend
Provides search endpoints using MeiliSearch and serves React frontend
"""
import os
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import uvicorn
from pydantic import BaseModel
import asyncio

# Configuration
MEILISEARCH_HOST = os.getenv('MEILISEARCH_HOST', 'meilisearch')
MEILISEARCH_PORT = int(os.getenv('MEILISEARCH_PORT', '7700'))
MEILISEARCH_INDEX = 'bands_search'
MEILISEARCH_URL = f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}"

# FastAPI app
app = FastAPI(
    title="PostPunk Search API",
    description="API for searching post-punk bands, albums, and tracks (1980-1999)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class SearchResult(BaseModel):
    id: str
    source: str
    band: str
    country: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    album: Optional[str] = None
    release_date: Optional[int] = None
    member: Optional[str] = None
    role: Optional[str] = None
    track: Optional[str] = None
    hit_rank: Optional[int] = None
    description: Optional[str] = None

class SearchResponse(BaseModel):
    hits: List[SearchResult]
    query: str
    limit: int
    offset: int
    estimatedTotalHits: int
    processingTimeMs: int

class HealthResponse(BaseModel):
    status: str
    meilisearch: str
    message: str

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MEILISEARCH_URL}/health")
            meilisearch_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        meilisearch_status = "unreachable"
    
    return HealthResponse(
        status="healthy" if meilisearch_status == "healthy" else "degraded",
        meilisearch=meilisearch_status,
        message="PostPunk Search API is running"
    )

@app.get("/api/search", response_model=SearchResponse)
async def search_bands(
    q: str = Query(..., description="Search query"),
    filter: Optional[str] = Query(None, description="Filter type: band, album, track, or year"),
    year: Optional[int] = Query(None, description="Filter by specific year"),
    country: Optional[str] = Query(None, description="Filter by country"),
    source: Optional[str] = Query(None, description="Filter by data source"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Search for post-punk bands, albums, tracks, and members
    
    - **q**: Search term (required)
    - **filter**: Optional filter type
    - **year**: Filter by specific year
    - **country**: Filter by country
    - **source**: Filter by data source (musicbrainz, theaudiodb, discogs)
    - **limit**: Results per page (1-100)
    - **offset**: Results to skip for pagination
    """
    
    try:
        # Build MeiliSearch query
        search_params = {
            "q": q,
            "limit": limit,
            "offset": offset,
            "attributesToRetrieve": [
                "id", "source", "band", "country", "year_start", "year_end", 
                "album", "release_date", "member", "role", "track", "hit_rank", "description"
            ],
            "attributesToHighlight": ["band", "album", "track", "member", "description"]
        }
        
        # Build filters
        filters = []
        
        if year:
            filters.append(f"year_start <= {year} AND (year_end >= {year} OR year_end IS NULL)")
        
        if country:
            filters.append(f"country = '{country}'")
            
        if source:
            filters.append(f"source = '{source}'")
            
        # Apply filter type
        if filter == "band":
            search_params["attributesToSearchOn"] = ["band"]
        elif filter == "album":
            search_params["attributesToSearchOn"] = ["album"]
        elif filter == "track":
            search_params["attributesToSearchOn"] = ["track"]
        elif filter == "year":
            if year:
                filters.append(f"release_date = {year}")
        
        if filters:
            search_params["filter"] = " AND ".join(filters)
        
        # Query MeiliSearch
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/search",
                json=search_params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"MeiliSearch error: {response.text}"
                )
            
            result = response.json()
            
            # Transform results
            hits = []
            for hit in result.get("hits", []):
                # Clean up null values and format data
                clean_hit = {}
                for key, value in hit.items():
                    if key.startswith("_"):  # Skip MeiliSearch metadata
                        continue
                    clean_hit[key] = value if value is not None else None
                
                hits.append(SearchResult(**clean_hit))
            
            return SearchResponse(
                hits=hits,
                query=q,
                limit=limit,
                offset=offset,
                estimatedTotalHits=result.get("estimatedTotalHits", len(hits)),
                processingTimeMs=result.get("processingTimeMs", 0)
            )
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to search service: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search error: {str(e)}"
        )

@app.get("/api/bands/autocomplete")
async def autocomplete_bands(
    q: str = Query(..., min_length=2, description="Search prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions")
):
    """Get band name suggestions for autocomplete"""
    try:
        search_params = {
            "q": q,
            "limit": limit,
            "attributesToRetrieve": ["band", "country", "year_start"],
            "attributesToSearchOn": ["band"]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/search",
                json=search_params,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract unique band names
                bands = []
                seen = set()
                
                for hit in result.get("hits", []):
                    band_name = hit.get("band", "").strip()
                    if band_name and band_name not in seen:
                        seen.add(band_name)
                        bands.append({
                            "band": band_name,
                            "country": hit.get("country"),
                            "year_start": hit.get("year_start")
                        })
                
                return {"suggestions": bands[:limit]}
            else:
                return {"suggestions": []}
                
    except Exception as e:
        return {"suggestions": []}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        async with httpx.AsyncClient() as client:
            # Get index stats
            response = await client.get(f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/stats")
            
            if response.status_code == 200:
                stats = response.json()
                
                return {
                    "total_documents": stats.get("numberOfDocuments", 0),
                    "is_indexing": stats.get("isIndexing", False),
                    "last_update": stats.get("lastUpdate"),
                    "index_name": MEILISEARCH_INDEX
                }
            else:
                return {
                    "total_documents": 0,
                    "is_indexing": False,
                    "last_update": None,
                    "index_name": MEILISEARCH_INDEX,
                    "error": "Could not retrieve stats"
                }
                
    except Exception as e:
        return {
            "total_documents": 0,
            "is_indexing": False,
            "last_update": None,
            "index_name": MEILISEARCH_INDEX,
            "error": str(e)
        }

# Mount static files for React frontend
app.mount("/static", StaticFiles(directory="web/dist/static"), name="static")

@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    """Serve React frontend for all non-API routes"""
    # Check if file exists in dist directory
    file_path = f"web/dist/{catchall}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Default to index.html for SPA routing
    return FileResponse("web/dist/index.html")

@app.get("/")
async def serve_index():
    """Serve React frontend index"""
    return FileResponse("web/dist/index.html")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )