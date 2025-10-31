import requests
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
import statistics

@dataclass
class Anime:
    """Data class to store anime information"""
    mal_id: int
    title: str
    score: float
    scored_by: int
    year: Optional[int]
    genres: List[str]
    weighted_score: float = 0.0
    
    def __repr__(self):
        return f"{self.title} ({self.year}) - Score: {self.score:.2f} | Users: {self.scored_by:,} | Weighted: {self.weighted_score:.2f}"


class MALRecommender:
    """Anime recommender using Jikan API (unofficial MAL API)"""
    
    BASE_URL = "https://api.jikan.moe/v4"
    
    # Genre ID mapping (Jikan API requires genre IDs, not names)
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
        """Initialize recommender with rate limiting"""
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Jikan requires 1 second between requests
        
    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling and rate limiting"""
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            print(f"🌐 API Request: {url}")
            print(f"📋 Parameters: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            print(f"✓ Response received: {len(data.get('data', []))} items\n")
            
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            return None
    
    def calculate_weighted_score(self, score: float, scored_by: int, 
                                 global_avg_score: float, min_votes: int) -> float:
        """
        Calculate Bayesian Average (weighted rating)
        
        Formula: (v / (v + m)) * R + (m / (v + m)) * C
        Where:
        - v = number of votes for this anime (scored_by)
        - m = minimum votes required (we use average votes as benchmark)
        - R = average rating for this anime (score)
        - C = global average score across all anime
        
        This approach:
        1. Gives more weight to popular anime (high scored_by)
        2. Pulls low-vote anime towards the global average
        3. Prevents 10/10 anime with only 5 votes from ranking #1
        """
        v = scored_by
        m = min_votes
        R = score
        C = global_avg_score
        
        weighted = (v / (v + m)) * R + (m / (v + m)) * C
        return weighted
    
    def get_genre_id(self, genre_name: str) -> Optional[int]:
        """Convert genre name to genre ID"""
        if not genre_name:
            return None
        return self.GENRE_MAP.get(genre_name.lower())
    
    def search_anime_by_genre_year(self, genre: str = None, year: int = None, 
                                    limit: int = 50) -> List[Anime]:
        """
        Search anime by genre and/or year
        
        Args:
            genre: Genre name (e.g., 'Action', 'Romance', 'Comedy')
            year: Year of release
            limit: Maximum number of results (default 50, max 25 per page)
        
        Returns:
            List of Anime objects
        """
        print(f"\n🔍 Searching for anime...")
        if genre:
            print(f"   Genre: {genre}")
        if year:
            print(f"   Year: {year}")
        
        anime_list = []
        page = 1
        total_fetched = 0
        
        # Jikan API returns max 25 items per page
        while total_fetched < limit:
            params = {
                'page': page,
                'limit': min(25, limit - total_fetched),
                'order_by': 'score',
                'sort': 'desc',
                'min_score': 1  # Only get rated anime
            }
            
            # Add genre filter if provided
            if genre:
                genre_id = self.get_genre_id(genre)
                if genre_id:
                    params['genres'] = genre_id
                    print(f"   Using Genre ID: {genre_id}")
                else:
                    print(f"⚠️  Genre '{genre}' not found. Available genres:")
                    print(f"   {', '.join(self.GENRE_MAP.keys())}")
                    return []
            
            # Add year filter if provided (using filter parameter)
            if year:
                params['start_date'] = f"{year}-01-01"
                params['end_date'] = f"{year}-12-31"
            
            data = self._make_request("anime", params)
            
            if not data or 'data' not in data:
                print("❌ No data returned from API")
                break
            
            items = data['data']
            if not items:
                print(f"ℹ️  No more items found (page {page})")
                break
            
            for item in items:
                # Filter only anime with valid scores
                if item.get('score') and item.get('scored_by'):
                    anime = Anime(
                        mal_id=item['mal_id'],
                        title=item['title'],
                        score=item['score'],
                        scored_by=item['scored_by'],
                        year=item.get('year'),
                        genres=[g['name'] for g in item.get('genres', [])]
                    )
                    anime_list.append(anime)
            
            total_fetched += len(items)
            print(f"   Fetched {total_fetched} anime so far...")
            
            # Check if there are more pages
            if not data.get('pagination', {}).get('has_next_page'):
                break
            
            page += 1
        
        print(f"✓ Found {len(anime_list)} anime with valid ratings\n")
        return anime_list
    
    def recommend(self, genre: str = None, year: int = None, 
                  top_n: int = 10) -> List[Anime]:
        """
        Get top N anime recommendations based on weighted scoring
        
        Algorithm:
        1. Fetch anime matching criteria
        2. Calculate global average score and votes
        3. Apply Bayesian average to each anime
        4. Return top N by weighted score
        """
        # Fetch anime data
        anime_list = self.search_anime_by_genre_year(genre, year, limit=100)
        
        if not anime_list:
            print("❌ No anime found matching criteria")
            return []
        
        # Calculate statistics for weighting
        all_scores = [a.score for a in anime_list]
        all_votes = [a.scored_by for a in anime_list]
        
        global_avg_score = statistics.mean(all_scores)
        avg_votes = statistics.mean(all_votes)
        
        print(f"📊 Dataset Statistics:")
        print(f"   Global average score: {global_avg_score:.2f}")
        print(f"   Average votes per anime: {avg_votes:,.0f}")
        print(f"   Using Bayesian Average for weighted scoring\n")
        
        # Calculate weighted scores
        for anime in anime_list:
            anime.weighted_score = self.calculate_weighted_score(
                anime.score,
                anime.scored_by,
                global_avg_score,
                int(avg_votes)
            )
        
        # Sort by weighted score
        anime_list.sort(key=lambda x: x.weighted_score, reverse=True)
        
        return anime_list[:top_n]


def main():
    """Main function to demonstrate the recommender"""
    print("=" * 70)
    print("🎌 MAL Anime Recommendation System")
    print("=" * 70)
    
    recommender = MALRecommender()
    
    # Show available genres
    # print("\n📚 Available Genres:")
    # print("-" * 70)
    # genres = list(recommender.GENRE_MAP.keys())
    # for i in range(0, len(genres), 4):
    #     print("   " + ", ".join(f"{g.title()}" for g in genres[i:i+4]))
    
    # # Example 1: Recommend Action anime from 2020
    # print("\n" + "=" * 70)
    # print("📺 Example 1: Top Action Anime from 2020")
    # print("-" * 70)
    # recommendations = recommender.recommend(genre="Action", year=2020, top_n=5)
    
    # if recommendations:
    #     for i, anime in enumerate(recommendations, 1):
    #         print(f"{i}. {anime}")
    #         print(f"   Genres: {', '.join(anime.genres)}\n")
    
    # Example 2: Recommend Romance anime (any year)
    # print("\n" + "=" * 70)
    # print("📺 Example 2: Top Romance Anime (All Time)")
    # print("-" * 70)
    # recommendations = recommender.recommend(genre="Romance", top_n=5)
    
    # if recommendations:
    #     for i, anime in enumerate(recommendations, 1):
    #         print(f"{i}. {anime}")
    #         print(f"   Genres: {', '.join(anime.genres)}\n")
    
    # Interactive mode
    print("\n" + "=" * 70)
    print("🎮 Interactive Mode")
    print("-" * 70)
    
    genre_input = input("Enter genre (or press Enter to skip): ").strip()
    year_input = input("Enter year (or press Enter to skip): ").strip()
    
    genre = genre_input if genre_input else None
    year = int(year_input) if year_input.isdigit() else None
    
    print("\n" + "-" * 70)
    recommendations = recommender.recommend(genre=genre, year=year, top_n=10)
    
    if recommendations:
        print(f"\n🏆 Top 10 Recommendations:")
        print("-" * 70)
        for i, anime in enumerate(recommendations, 1):
            print(f"{i}. {anime}")
            print(f"   Genres: {', '.join(anime.genres)}\n")
    
    print("=" * 70)
    print("✨ Thank you for using MAL Recommender!")
    print("=" * 70)


if __name__ == "__main__":
    main()