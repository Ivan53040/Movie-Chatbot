"""Run the movie search program and run example searches."""
import json
from movie_search import search_movies

# Load movies.json (same as movie_search uses internally)
with open("movies.json", encoding="utf-8") as f:
    movies = json.load(f)

print(f"Loaded {len(movies)} movies from movies.json\n")

# Run the search program with example queries
print("--- search_movies(genre='Drama', year_min=2010) ---")
results = search_movies(genre="Drama", year_min=2010)
for m in results[:5]:
    print(f"  {m['title']} ({m['year']})")
print(f"  ... {len(results)} total\n")

print("--- search_movies(genre='Comedy', mood='witty') ---")
results = search_movies(genre="Comedy", mood="witty")
for m in results[:5]:
    print(f"  {m['title']} ({m['year']}) - {m['mood']}")
print(f"  ... {len(results)} total\n")

print("--- search_movies(year_min=2020) ---")
results = search_movies(year_min=2020)
for m in results[:5]:
    print(f"  {m['title']} ({m['year']}) - {m['mood']}")
print(f"  ... {len(results)} total\n")
