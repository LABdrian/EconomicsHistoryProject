"""
PostPunk Search API - FastAPI backend híbrido
Funciona con MeiliSearch + MongoDB en Docker o con datos mock en local
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
import logging

# Configuración
ENVIRONMENT = os.getenv('ENVIRONMENT', 'local')  # 'docker' o 'local'
MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', 'http://meilisearch:7700')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', 'postpunk-search-key-2024')
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://mongo:27017/postpunk')
MEILISEARCH_INDEX = 'bands_search'

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="PostPunk Search API",
    description="API para buscar bandas post-punk, álbumes y tracks (1980-1999)",
    version="1.0.0",
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
    mode: str  # 'production' o 'demo'

class HealthResponse(BaseModel):
    status: str
    mode: str
    services: Dict[str, str]
    message: str

# Datos mock para demo local
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
        "description": "English rock band formed in Salford in 1976. Influential post-punk pioneers."
    },
    {
        "id": "no001",
        "source": "musicbrainz", 
        "band": "New Order",
        "country": "United Kingdom",
        "year_start": 1980,
        "year_end": None,
        "album": "Power, Corruption & Lies",
        "release_date": 1983,
        "member": "Bernard Sumner",
        "role": "Guitar",
        "track": "Blue Monday",
        "hit_rank": 1,
        "description": "Electronic rock band formed from the ashes of Joy Division."
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
        "role": "Vocals",
        "track": "Just Like Heaven",
        "hit_rank": 2,
        "description": "Gothic rock and post-punk legends from Crawley, England."
    },
    {
        "id": "talking001",
        "source": "discogs",
        "band": "Talking Heads",
        "country": "United States",
        "year_start": 1975,
        "year_end": 1991,
        "album": "Remain in Light",
        "release_date": 1980,
        "member": "David Byrne",
        "role": "Vocals",
        "track": "Once in a Lifetime",
        "hit_rank": 1,
        "description": "American art rock band known for their innovative post-punk sound."
    },
    {
        "id": "wire001",
        "source": "musicbrainz",
        "band": "Wire",
        "country": "United Kingdom",
        "year_start": 1976,
        "year_end": None,
        "album": "Pink Flag",
        "release_date": 1977,
        "member": "Colin Newman",
        "role": "Vocals",
        "track": "12XU",
        "hit_rank": 3,
        "description": "British post-punk band known for their minimalist and experimental approach."
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
        "track": "Love Like Anthrax",
        "hit_rank": 2,
        "description": "British post-punk band known for their political lyrics and funk-influenced rhythms."
    }
]

async def check_services():
    """Verificar disponibilidad de servicios externos"""
    services = {
        "meilisearch": "unreachable",
        "mongodb": "unreachable"
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test MeiliSearch con API key
            try:
                headers = {"Authorization": f"Bearer {MEILISEARCH_KEY}"}
                response = await client.get(f"{MEILISEARCH_URL}/health", headers=headers)
                services["meilisearch"] = "healthy" if response.status_code == 200 else "unhealthy"
            except Exception as e:
                logger.warning(f"MeiliSearch check failed: {e}")
                services["meilisearch"] = "unreachable"
            
            # Test MongoDB con conexión real
            try:
                from pymongo import MongoClient
                mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
                # Intentar una operación simple para verificar conectividad
                mongo_client.admin.command('ping')
                services["mongodb"] = "healthy"
                mongo_client.close()
            except Exception as e:
                logger.warning(f"MongoDB check failed: {e}")
                services["mongodb"] = "unreachable"
                
    except Exception as e:
        logger.warning(f"Error checking services: {e}")
    
    return services

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint con detección automática de modo"""
    services = await check_services()
    
    # Determinar modo basado en servicios disponibles
    if services["meilisearch"] == "healthy":
        mode = "production"
        status = "healthy"
        message = "PostPunk Search API running in production mode"
    else:
        mode = "demo"
        status = "demo"
        message = "PostPunk Search API running in demo mode with mock data"
    
    return HealthResponse(
        status=status,
        mode=mode,
        services=services,
        message=message
    )

async def search_meilisearch(q: str, limit: int, offset: int, filters: List[str]) -> Dict[str, Any]:
    """Búsqueda usando MeiliSearch real"""
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
    
    if filters:
        search_params["filter"] = " AND ".join(filters)
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {MEILISEARCH_KEY}"}
        response = await client.post(
            f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/search",
            json=search_params,
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"MeiliSearch error: {response.text}"
            )
        
        return response.json()

def search_mock_data(q: str, limit: int, offset: int, country: Optional[str], 
                    year: Optional[int], source: Optional[str]) -> Dict[str, Any]:
    """Búsqueda usando datos mock locales"""
    # Filtrar datos mock
    filtered_data = MOCK_BANDS_DATA.copy()
    
    # Aplicar filtros
    if country:
        filtered_data = [item for item in filtered_data if item.get("country", "").lower() == country.lower()]
    
    if year:
        filtered_data = [
            item for item in filtered_data 
            if (item.get("year_start", 0) <= year and 
                (item.get("year_end") is None or item.get("year_end", 9999) >= year))
        ]
    
    if source:
        filtered_data = [item for item in filtered_data if item.get("source", "").lower() == source.lower()]
    
    # Búsqueda por texto
    if q.strip():
        q_lower = q.lower()
        filtered_data = [
            item for item in filtered_data
            if (q_lower in item.get("band", "").lower() or
                q_lower in item.get("album", "").lower() or
                q_lower in item.get("track", "").lower() or
                q_lower in item.get("member", "").lower() or
                q_lower in item.get("description", "").lower())
        ]
    
    # Aplicar paginación
    total = len(filtered_data)
    paginated_data = filtered_data[offset:offset + limit]
    
    return {
        "hits": paginated_data,
        "estimatedTotalHits": total,
        "processingTimeMs": 5  # Mock processing time
    }

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
    Búsqueda de bandas post-punk con detección automática de modo
    """
    
    # Verificar servicios disponibles
    services = await check_services()
    use_production = services["meilisearch"] == "healthy"
    
    try:
        if use_production:
            # Modo producción con MeiliSearch
            logger.info("Using production mode with MeiliSearch")
            
            # Construir filtros
            filters = []
            if year:
                filters.append(f"year_start <= {year} AND (year_end >= {year} OR year_end IS NULL)")
            if country:
                filters.append(f"country = '{country}'")
            if source:
                filters.append(f"source = '{source}'")
            
            result = await search_meilisearch(q, limit, offset, filters)
            
            # Transform results
            hits = []
            for hit in result.get("hits", []):
                clean_hit = {k: v for k, v in hit.items() if not k.startswith("_")}
                hits.append(SearchResult(**clean_hit))
            
            return SearchResponse(
                hits=hits,
                query=q,
                limit=limit,
                offset=offset,
                estimatedTotalHits=result.get("estimatedTotalHits", len(hits)),
                processingTimeMs=result.get("processingTimeMs", 0),
                mode="production"
            )
            
        else:
            # Modo demo con datos mock
            logger.info("Using demo mode with mock data")
            
            result = search_mock_data(q, limit, offset, country, year, source)
            
            hits = [SearchResult(**hit) for hit in result["hits"]]
            
            return SearchResponse(
                hits=hits,
                query=q,
                limit=limit,
                offset=offset,
                estimatedTotalHits=result["estimatedTotalHits"],
                processingTimeMs=result["processingTimeMs"],
                mode="demo"
            )
            
    except httpx.RequestError as e:
        # Fallback a datos mock si hay error de conexión
        logger.warning(f"Connection error, falling back to demo mode: {e}")
        result = search_mock_data(q, limit, offset, country, year, source)
        hits = [SearchResult(**hit) for hit in result["hits"]]
        
        return SearchResponse(
            hits=hits,
            query=q,
            limit=limit,
            offset=offset,
            estimatedTotalHits=result["estimatedTotalHits"],
            processingTimeMs=result["processingTimeMs"],
            mode="demo_fallback"
        )

@app.get("/api/bands/autocomplete")
async def autocomplete_bands(
    q: str = Query(..., min_length=2, description="Search prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions")
):
    """Autocompletado de nombres de bandas"""
    services = await check_services()
    
    if services["meilisearch"] == "healthy":
        # Modo producción
        try:
            search_params = {
                "q": q,
                "limit": limit,
                "attributesToRetrieve": ["band", "country", "year_start"],
                "attributesToSearchOn": ["band"]
            }
            
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {MEILISEARCH_KEY}"}
                response = await client.post(
                    f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/search",
                    json=search_params,
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
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
        except Exception as e:
            logger.warning(f"Autocomplete error, using fallback: {e}")
    
    # Modo demo/fallback
    q_lower = q.lower()
    suggestions = []
    seen = set()
    
    for item in MOCK_BANDS_DATA:
        band_name = item.get("band", "")
        if (band_name.lower().startswith(q_lower) and 
            band_name not in seen):
            seen.add(band_name)
            suggestions.append({
                "band": band_name,
                "country": item.get("country"),
                "year_start": item.get("year_start")
            })
            
            if len(suggestions) >= limit:
                break
    
    return {"suggestions": suggestions}

@app.get("/api/stats")
async def get_stats():
    """Estadísticas de la base de datos"""
    services = await check_services()
    
    if services["meilisearch"] == "healthy":
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {MEILISEARCH_KEY}"}
                response = await client.get(f"{MEILISEARCH_URL}/indexes/{MEILISEARCH_INDEX}/stats", headers=headers)
                
                if response.status_code == 200:
                    stats = response.json()
                    return {
                        "total_documents": stats.get("numberOfDocuments", 0),
                        "is_indexing": stats.get("isIndexing", False),
                        "last_update": stats.get("lastUpdate"),
                        "index_name": MEILISEARCH_INDEX,
                        "mode": "production"
                    }
        except Exception as e:
            logger.warning(f"Stats error: {e}")
    
    # Modo demo
    return {
        "total_documents": len(MOCK_BANDS_DATA),
        "is_indexing": False,
        "last_update": "2024-01-15T00:00:00Z",
        "index_name": "demo_data",
        "mode": "demo"
    }

# Servir frontend React (si existe)
if os.path.exists("web/dist"):
    app.mount("/static", StaticFiles(directory="web/dist/static"), name="static")
    
    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        """Servir React frontend"""
        file_path = f"web/dist/{catchall}"
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("web/dist/index.html")
    
    @app.get("/")
    async def serve_index():
        """Servir página principal React"""
        return FileResponse("web/dist/index.html")
else:
    @app.get("/")
    async def root():
        """API raíz cuando no hay frontend"""
        return {
            "message": "PostPunk Search API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/health"
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )