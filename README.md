# MAL Anime Recommender 🎌

An intelligent anime recommendation system that uses MyAnimeList data via the Jikan API to recommend anime based on genre and year, with a sophisticated weighted scoring algorithm.

## Features ✨

- **Smart Recommendations**: Uses Bayesian Average algorithm to balance rating quality and popularity
- **Flexible Filtering**: Search by genre, year, or both
- **Comprehensive Genre Support**: 17+ genres including Action, Romance, Comedy, Sci-Fi, etc.
- **Interactive Mode**: Easy-to-use command-line interface
- **Rate-Limited API Calls**: Respects Jikan API guidelines

## How It Works 🔍

### Weighted Scoring Algorithm

The recommender doesn't just use raw MAL scores. It implements a **Bayesian Average** that considers:

1. **Rating Score** (quality indicator)
2. **Number of Voters** (confidence/popularity indicator)

**Formula:**
```
Weighted Score = (v/(v+m)) × R + (m/(v+m)) × C

Where:
- v = votes for this anime
- m = average votes in dataset (benchmark)
- R = this anime's rating
- C = global average rating
```

**Why?** This prevents a 10/10 anime with only 5 votes from outranking a 9.5/10 anime with 500,000 votes.

## Installation 🚀

### Prerequisites
- Python 3.7+
- pip

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/poseidon816/mal-anime-recommender.git
cd mal-anime-recommender
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the program**
```bash
python mal_recommender.py
```

## Usage 📖

### Basic Example

```python
from mal_recommender import MALRecommender

recommender = MALRecommender()

# Get top 10 Action anime from 2020
recommendations = recommender.recommend(genre="Action", year=2020, top_n=10)

for anime in recommendations:
    print(anime)
```

### Available Genres

Action, Adventure, Comedy, Drama, Fantasy, Horror, Mystery, Romance, Sci-Fi, Slice of Life, Sports, Supernatural, Thriller, Psychological, Seinen, Shounen, Shoujo

### Command Line Usage

Run the program and follow the interactive prompts:

```bash
python mal_recommender.py
```

**Example interaction:**
```
Enter genre (or press Enter to skip): Romance
Enter year (or press Enter to skip): 2023

🏆 Top 10 Recommendations:
1. Your Lie in April (2014) - Score: 8.64 | Users: 1,234,567 | Weighted: 8.62
...
```

## API Information ℹ️

This project uses the [Jikan API](https://jikan.moe/), an unofficial MyAnimeList REST API.

- **Rate Limit**: 1 request per second (automatically handled)
- **No Authentication Required**
- **Free to use**

## Project Structure 📁

```
mal-anime-recommender/
├── mal_recommender.py      # Main program
├── requirements.txt         # Python dependencies
├── README.md               # Documentation
└── .gitignore              # Git ignore file
```

## Future Enhancements 🚧

- [ ] Multiple genre filtering
- [ ] Filter by anime type (TV, Movie, OVA)
- [ ] Export recommendations to CSV/JSON
- [ ] GUI interface
- [ ] Caching for faster repeated searches
- [ ] User preference learning

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments 🙏

- [MyAnimeList](https://myanimelist.net/) for anime data
- [Jikan API](https://jikan.moe/) for providing free API access
- Inspired by recommendation algorithms used by Netflix and Amazon

## Contact 📧

Harish Mogaveer - harishmogaveer816@gmail.com

Project Link: [https://github.com/poseidon816/mal-anime-recommender.git]

---

⭐ If you found this project helpful, please give it a star on GitHub!