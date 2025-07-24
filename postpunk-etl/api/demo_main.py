"""
PostPunk Search API - Demo Version
Versión simplificada para demostrar el funcionamiento sin depender de MeiliSearch
"""
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import uvicorn
from pydantic import BaseModel
import random

# Mock data para demostración
MOCK_BANDS_DATA = [
    {
        "id": "jd001",
        "source": "musicbrainz",
        "band": "Joy Division",
        "country": "United Kingdom",
        "year_start": 1976,
        "year_end": 1980,
        "album": "Unknown Pleasures",
        "release_date": 1979,
        "member": "Ian Curtis",
        "role": "Vocals",
        "track": "Love Will Tear Us Apart",
        "hit_rank": 1,
        "description": "English rock band formed in Salford in 1976. The group consisted of vocalist Ian Curtis, guitarist/keyboardist Bernard Sumner, bassist Peter Hook and drummer Stephen Morris."
    },
    {
        "id": "cure001",
        "source": "theaudiodb",
        "band": "The Cure",
        "country": "United Kingdom",
        "year_start": 1978,
        "year_end": None,
        "album": "Disintegration",
        "release_date": 1989,
        "member": "Robert Smith",
        "role": "Vocals, Guitar",
        "track": "Close to Me",
        "hit_rank": 2,
        "description": "English rock band formed in 1978. The band members have changed several times, with guitarist, lead vocalist, and songwriter Robert Smith being the only constant member."
    },
    {
        "id": "bauhaus001",
        "source": "discogs",
        "band": "Bauhaus",
        "country": "United Kingdom",
        "year_start": 1978,
        "year_end": 1983,
        "album": "In the Flat Field",
        "release_date": 1980,
        "member": "Peter Murphy",
        "role": "Vocals",
        "track": "Bela Lugosi's Dead",
        "hit_rank": 3,
        "description": "English rock band formed in Northampton in 1978. Known for their dark image and sound, they are often considered one of the first gothic rock groups."
    },
    {
        "id": "siouxsie001",
        "source": "musicbrainz",
        "band": "Siouxsie and the Banshees",
        "country": "United Kingdom",
        "year_start": 1976,
        "year_end": 1996,
        "album": "Juju",
        "release_date": 1981,
        "member": "Siouxsie Sioux",
        "role": "Vocals",
        "track": "Cities in Dust",
        "hit_rank": 4,
        "description": "English rock band formed in London in 1976 by vocalist Siouxsie Sioux and bass guitarist Steven Severin. They were one of the longest-running and most successful acts to emerge from the London punk community."
    },
    {
        "id": "gang001",
        "source": "theaudiodb",
        "band": "Gang of Four",
        "country": "United Kingdom",
        "year_start": 1977,
        "year_end": 1984,
        "album": "Entertainment!",
        "release_date": 1979,
        "member": "Jon King",
        "role": "Vocals",
        "track": "Damaged Goods",
        "hit_rank": 5,
        "description": "English post-punk band formed in Leeds in 1977. The band is characterized by their mix of punk, funk, and political lyrics."
    },
    {
        "id": "wire001",
        "source": "discogs",
        "band": "Wire",
        "country": "United Kingdom",
        "year_start": 1976,
        "year_end": None,
        "album": "Pink Flag",
        "release_date": 1977,
        "member": "Colin Newman",
        "role": "Vocals, Guitar",
        "track": "12XU",
        "hit_rank": 6,
        "description": "English rock band formed in London in 1976. They were originally associated with the punk rock scene, but have evolved beyond punk into post-punk and experimental rock."
    },
    {
        "id": "television001",
        "source": "musicbrainz",
        "band": "Television",
        "country": "United States",
        "year_start": 1973,
        "year_end": 1978,
        "album": "Marquee Moon",
        "release_date": 1977,
        "member": "Tom Verlaine",
        "role": "Vocals, Guitar",
        "track": "Marquee Moon",
        "hit_rank": 7,
        "description": "American rock band from New York City. They are considered influential in the development of punk rock and post-punk."
    },
    {
        "id": "talking001",
        "source": "theaudiodb",
        "band": "Talking Heads",
        "country": "United States",
        "year_start": 1975,
        "year_end": 1991,
        "album": "Remain in Light",
        "release_date": 1980,
        "member": "David Byrne",
        "role": "Vocals, Guitar",
        "track": "Once in a Lifetime",
        "hit_rank": 8,
        "description": "American rock band formed in 1975 in New York City. The band was comprised of David Byrne, Chris Frantz, Tina Weymouth, and Jerry Harrison."
    }
]

# FastAPI app
app = FastAPI(
    title="PostPunk Search API - Demo",
    description="API demo para búsqueda de bandas post-punk (1980-1999)",
    version="1.0.0-demo",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
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
    return HealthResponse(
        status="healthy",
        meilisearch="demo-mode",
        message="PostPunk Search API is running in demo mode"
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
    Búsqueda demo de bandas post-punk
    """
    
    # Simular tiempo de procesamiento
    processing_time = random.randint(10, 50)
    
    # Filtrar datos mock basado en query
    results = []
    query_lower = q.lower()
    
    for band in MOCK_BANDS_DATA:
        # Búsqueda simple en campos principales
        searchable_text = f"{band['band']} {band['album']} {band['track']} {band['member']} {band['description']}".lower()
        
        if query_lower in searchable_text:
            # Aplicar filtros adicionales
            if year and band['year_start'] and band['year_end']:
                if not (band['year_start'] <= year <= band['year_end']):
                    continue
            elif year and band['release_date']:
                if band['release_date'] != year:
                    continue
                    
            if country and band['country']:
                if country.lower() not in band['country'].lower():
                    continue
                    
            if source and band['source'] != source:
                continue
                
            if filter:
                if filter == "band" and query_lower not in band['band'].lower():
                    continue
                elif filter == "album" and query_lower not in band['album'].lower():
                    continue
                elif filter == "track" and query_lower not in band['track'].lower():
                    continue
            
            results.append(SearchResult(**band))
    
    # Aplicar paginación
    total_hits = len(results)
    paginated_results = results[offset:offset + limit]
    
    return SearchResponse(
        hits=paginated_results,
        query=q,
        limit=limit,
        offset=offset,
        estimatedTotalHits=total_hits,
        processingTimeMs=processing_time
    )

@app.get("/api/bands/autocomplete")
async def autocomplete_bands(
    q: str = Query(..., min_length=2, description="Search prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions")
):
    """Get band name suggestions for autocomplete"""
    suggestions = []
    query_lower = q.lower()
    
    for band in MOCK_BANDS_DATA:
        if query_lower in band['band'].lower():
            suggestions.append({
                "band": band['band'],
                "country": band['country'],
                "year_start": band['year_start']
            })
    
    return {"suggestions": suggestions[:limit]}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    return {
        "total_documents": len(MOCK_BANDS_DATA),
        "is_indexing": False,
        "last_update": "2024-07-24T17:00:00Z",
        "index_name": "bands_search_demo"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "PostPunk Search API - Demo Mode",
        "version": "1.0.0-demo",
        "docs": "/api/docs",
        "search": "/api/search?q=joy+division",
        "health": "/api/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "demo_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )