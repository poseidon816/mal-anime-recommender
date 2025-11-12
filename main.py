from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import requests
import time
import statistics
from datetime import datetime

# ============================================================================
# DATA MODELS (Request/Response schemas)
# ============================================================================

class AnimeResponse(BaseModel):
    """Response model for anime data"""
    mal_id: int
    title: str
    score: float
    scored_by: int
    year: Optional[int]
    genres: List[str]
    weighted_score: float
    image_url: Optional[str] = None
    synopsis: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "mal_id": 5114,
                "title": "Fullmetal Alchemist: Brotherhood",
                "score": 9.1,
                "scored_by": 1500000,
                "year": 2009,
                "genres": ["Action", "Adventure", "Drama"],
                "weighted_score": 9.08,
                "image_url": "https://cdn.myanimelist.net/images/anime/1223/96541.jpg",
                "synopsis": "Two brothers search for the Philosopher's Stone..."
            }
        }

class RecommendationRequest(BaseModel):
    """Request model for getting recommendations"""
    genre: Optional[str] = Field(None, description="Genre name (e.g., 'Action', 'Romance')")
    year: Optional[int] = Field(None, description="Year of release", ge=1960, le=2025)
    limit: int = Field(10, description="Number of recommendations", ge=1, le=50)

class GenreInfo(BaseModel):
    """Genre information model"""
    name: str
    id: int

class StatsResponse(BaseModel):
    """Statistics response model"""
    total_anime: int
    global_avg_score: float
    avg_votes: float
    algorithm: str = "Bayesian Average"

# ============================================================================
# MAL RECOMMENDER SERVICE
# ============================================================================

class MALRecommenderService:
    """Anime recommender service using Jikan API"""
    
    BASE_URL = "https://api.jikan.moe/v4"
    
    GENRE_MAP = {
        'action': 1,
        'adventure': 2,
        'comedy': 4,
        'drama': 8,
        'fantasy': 10,
        'horror': 14,
        'mystery': 7,
        'romance': 22,
        'sci-fi': 24,
        'slice of life': 36,
        'sports': 30,
        'supernatural': 37,
        'thriller': 41,
        'psychological': 40,
        'seinen': 42,
        'shounen': 27,
        'shoujo': 25
    }
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 1.0
        
    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request with error handling and rate limiting"""
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            raise HTTPException(status_code=503, detail=f"External API error: {str(e)}")
    
    def calculate_weighted_score(self, score: float, scored_by: int, 
                                 global_avg_score: float, min_votes: int) -> float:
        """Calculate Bayesian Average (weighted rating)"""
        v = scored_by
        m = min_votes
        R = score
        C = global_avg_score
        
        weighted = (v / (v + m)) * R + (m / (v + m)) * C
        return round(weighted, 2)
    
    def get_genre_id(self, genre_name: str) -> Optional[int]:
        """Convert genre name to genre ID"""
        if not genre_name:
            return None
        return self.GENRE_MAP.get(genre_name.lower())
    
    def search_anime(self, genre: str = None, year: int = None, 
                    limit: int = 50) -> tuple[List[dict], dict]:
        """
        Search anime by genre and/or year
        Returns: (anime_list, stats)
        """
        anime_list = []
        page = 1
        total_fetched = 0
        max_pages = 4  # Limit to 4 pages (100 anime) to avoid long waits
        
        while total_fetched < limit and page <= max_pages:
            params = {
                'page': page,
                'limit': min(25, limit - total_fetched),
                'order_by': 'score',
                'sort': 'desc',
                'min_score': 1
            }
            
            if genre:
                genre_id = self.get_genre_id(genre)
                if not genre_id:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid genre. Available: {', '.join(self.GENRE_MAP.keys())}"
                    )
                params['genres'] = genre_id
            
            if year:
                params['start_date'] = f"{year}-01-01"
                params['end_date'] = f"{year}-12-31"
            
            data = self._make_request("anime", params)
            
            if not data or 'data' not in data:
                break
            
            items = data['data']
            if not items:
                break
            
            for item in items:
                if item.get('score') and item.get('scored_by'):
                    anime_data = {
                        'mal_id': item['mal_id'],
                        'title': item['title'],
                        'score': item['score'],
                        'scored_by': item['scored_by'],
                        'year': item.get('year'),
                        'genres': [g['name'] for g in item.get('genres', [])],
                        'image_url': item.get('images', {}).get('jpg', {}).get('image_url'),
                        'synopsis': item.get('synopsis', '')[:200] + '...' if item.get('synopsis') else None
                    }
                    anime_list.append(anime_data)
            
            total_fetched += len(items)
            
            if not data.get('pagination', {}).get('has_next_page'):
                break
            
            page += 1
        
        # Calculate statistics
        if anime_list:
            all_scores = [a['score'] for a in anime_list]
            all_votes = [a['scored_by'] for a in anime_list]
            
            stats = {
                'total_anime': len(anime_list),
                'global_avg_score': round(statistics.mean(all_scores), 2),
                'avg_votes': round(statistics.mean(all_votes), 0)
            }
        else:
            stats = {'total_anime': 0, 'global_avg_score': 0, 'avg_votes': 0}
        
        return anime_list, stats
    
    def get_recommendations(self, genre: str = None, year: int = None, 
                           top_n: int = 10) -> tuple[List[AnimeResponse], StatsResponse]:
        """Get top N anime recommendations with weighted scoring"""
        anime_list, stats = self.search_anime(genre, year, limit=100)
        
        if not anime_list:
            raise HTTPException(status_code=404, detail="No anime found matching criteria")
        
        # Calculate weighted scores
        for anime in anime_list:
            anime['weighted_score'] = self.calculate_weighted_score(
                anime['score'],
                anime['scored_by'],
                stats['global_avg_score'],
                int(stats['avg_votes'])
            )
        
        # Sort by weighted score
        anime_list.sort(key=lambda x: x['weighted_score'], reverse=True)
        
        # Convert to response models
        recommendations = [AnimeResponse(**anime) for anime in anime_list[:top_n]]
        stats_response = StatsResponse(**stats)
        
        return recommendations, stats_response

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="MAL Anime Recommender API",
    description="Intelligent anime recommendation system using MyAnimeList data with weighted scoring algorithm",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration (allow frontend to access API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
recommender = MALRecommenderService()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "MAL Anime Recommender API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "recommendations": "/api/recommendations",
            "genres": "/api/genres",
            "health": "/api/health"
        }
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MAL Anime Recommender"
    }

@app.get("/api/genres", response_model=List[GenreInfo], tags=["Genres"])
async def get_genres():
    """Get list of available genres"""
    genres = [
        GenreInfo(name=name.title(), id=genre_id)
        for name, genre_id in recommender.GENRE_MAP.items()
    ]
    return sorted(genres, key=lambda x: x.name)

@app.get("/api/recommendations", response_model=dict, tags=["Recommendations"])
async def get_recommendations(
    genre: Optional[str] = Query(None, description="Genre name (e.g., 'Action', 'Romance')"),
    year: Optional[int] = Query(None, description="Year of release", ge=1960, le=2025),
    limit: int = Query(10, description="Number of recommendations", ge=1, le=50)
):
    """
    Get anime recommendations based on genre and/or year
    
    Uses Bayesian Average algorithm to balance rating quality and popularity:
    - Weighted Score = (v/(v+m)) × R + (m/(v+m)) × C
    - v = votes for this anime
    - m = average votes (benchmark)
    - R = this anime's rating
    - C = global average rating
    """
    try:
        recommendations, stats = recommender.get_recommendations(genre, year, limit)
        
        return {
            "success": True,
            "filters": {
                "genre": genre,
                "year": year,
                "limit": limit
            },
            "statistics": stats,
            "recommendations": recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/recommendations", response_model=dict, tags=["Recommendations"])
async def post_recommendations(request: RecommendationRequest):
    """
    Get anime recommendations (POST method)
    Alternative endpoint using request body instead of query parameters
    """
    try:
        recommendations, stats = recommender.get_recommendations(
            request.genre, 
            request.year, 
            request.limit
        )
        
        return {
            "success": True,
            "filters": {
                "genre": request.genre,
                "year": request.year,
                "limit": request.limit
            },
            "statistics": stats,
            "recommendations": recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================================================
# RUN SERVER (for local development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)