# ProjectLLM Movie Recommender

This project is a modular movie recommendation app.

It supports:

- filter search
- semantic search
- "movies like X" search
- hybrid search
- candidate generation
- ranking layer
- API-based parser

The goal of this structure is to make the pipeline easy to learn and easy to modify.

## Pipeline

The app now follows this flow:

```text
User input
  -> Parser
  -> Router
  -> Search strategy
  -> Candidate Movies
  -> Filter
  -> Ranking Layer
  -> Final top results
```

Example:

```text
movies like Interstellar but after 2010
  -> parser extracts:
     similar_to = "Interstellar"
     year_min = 2011
  -> router chooses hybrid similar search
  -> candidate layer builds top 50 similar movies
  -> filter keeps only movies after 2010
  -> ranking layer scores remaining movies
  -> final top 5 returned
```

## File Structure

### [`llama_parser.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/llama_parser.py)

Responsible for:

- calling the LLM parser
- extracting structured query fields
- post-processing the parsed result
- correcting common parser mistakes

Important logic inside:

- convert invalid years like `0` to `None`
- regex-based year override
- remove mood if the user did not explicitly mention it
- distinguish `similar_to` from `semantic_query`

If you want to improve parsing, this is the first file to edit.

### [`api_parser_client.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/api_parser_client.py)

Responsible for:

- calling the remote LLM API
- loading API settings from `.env`
- returning JSON parser output

This file replaces the old local Ollama parser call.
It is currently configured for Groq.

### [`config.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/config.py)

Responsible for:

- loading `.env`
- reading environment variables

This keeps API config separate from parser logic.

### [`router.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/router.py)

Responsible for:

- taking parsed query output
- deciding which search path to use
- printing debug info
- returning final results

Main routes:

- `similar_to` -> hybrid similar search
- `semantic_query` -> hybrid semantic search
- otherwise -> filter search
- final fallback -> plain semantic search

If you want to change the decision flow, edit this file.

### [`movie_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/movie_search.py)

Responsible for filter search.

It handles:

- genre filtering
- mood filtering
- year filtering
- language filtering
- schema normalization

This is the pure rule-based search layer.

If you want stricter or looser filters, edit this file.

### [`semantic_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/semantic_search.py)

Responsible for semantic embedding search.

It handles:

- loading `movies.json`
- loading `movie_embeddings.npz`
- converting query text to embedding
- cosine similarity retrieval
- semantic query normalization for Chinese topic words
- building the text used for embeddings

Main function:

- `cosine_search(query, top_k=...)`

If you want to improve embedding quality, edit this file.

### [`similar_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/similar_search.py)

Responsible for:

- "movies like Interstellar"
- using the selected movie's embedding as the query vector

Main function:

- `recommend_similar_movies(movie_title, top_k=...)`

If you want to improve title-based similarity, edit this file.

### [`candidate_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/candidate_movies.py)

Responsible for candidate generation.

It provides:

- semantic candidate builder
- similar-movie candidate builder
- helper for returning candidate/debug bundles

This layer is where you control candidate pool size like `20`, `50`, or `100`.

### [`top_k_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/top_k_movies.py)

Responsible for:

- default top-k behavior
- max top-k limit
- deciding candidate pool size from top-k
- parsing `more` commands in the CLI

Examples:

- default result count = `5`
- `more` -> show more results for the previous query
- `more 10` -> show top 10 results for the previous query

### [`hybrid_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/hybrid_search.py)

Responsible for the hybrid pipeline:

```text
semantic candidates
  -> filter
  -> ranking
  -> final top results
```

Main functions:

- `hybrid_search(...)`
- `hybrid_recommend_similar_movies(...)`

This file connects candidate generation, filtering, and ranking.

### [`ranking_layer.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/ranking_layer.py)

Responsible for scoring movies after retrieval/filtering.

It currently combines:

- semantic similarity
- vote average
- popularity
- recency bias
- genre bonus
- language bonus
- exact year bonus

Main functions:

- `score_movie(...)`
- `rank_movies(...)`

If you want to change what "best result" means, edit this file.

## Current Ranking Formula

The current ranking layer uses a weighted score:

```text
ranking_score =
  0.60 * similarity
  + 0.18 * vote_average
  + 0.12 * popularity
  + 0.10 * recency
  + optional bonuses
```

Optional bonuses:

- genre match bonus
- language match bonus
- exact year match bonus

This is not a trained recommender model.
It is a handcrafted scoring layer on top of retrieval.

## Candidate Movies

Current default:

- `candidate_k = 50`
- final `top_k = 5`

So the process is:

1. retrieve top 50 candidate movies
2. filter them
3. score them
4. return top 5

The app now supports a Top-K flow:

1. first response returns top 5 movies
2. user can ask for more
3. the router reruns the same query with a larger `top_k`

If you want to experiment:

- increase candidate pool in [`hybrid_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/hybrid_search.py)
- adjust ranking weights in [`ranking_layer.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/ranking_layer.py)
- adjust top-k rules in [`top_k_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/top_k_movies.py)

## Debug Output

Hybrid search prints:

- `semantic candidates`
- `filtered candidates`
- dropped semantic candidates
- final top 5
- similarity score
- ranking score

This is useful for understanding whether the problem is:

- parser
- semantic retrieval
- filtering
- ranking

## How To Run

Run the app from the project folder:

```powershell
C:\Users\ivank\AppData\Local\Python\bin\python.exe router.py
```

Before running, create a `.env` file in the project root.
You can copy from `.env.example`.

Example:

```text
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Install the API client package if needed:

```powershell
C:\Users\ivank\AppData\Local\Python\bin\python.exe -m pip install groq
```

Then:

```text
1. ask for a movie recommendation
2. app returns top 5
3. type "more" to get more results
4. type "more 10" to get top 10 results
```

## How To Rebuild Embeddings

If you update `movies.json`, rebuild embeddings:

```powershell
C:\Users\ivank\AppData\Local\Python\bin\python.exe build_embeddings.py
```

## Good Learning Order

If you want to understand the project step by step, read files in this order:

1. [`llama_parser.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/llama_parser.py)
2. [`api_parser_client.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/api_parser_client.py)
3. [`router.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/router.py)
4. [`movie_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/movie_search.py)
5. [`semantic_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/semantic_search.py)
6. [`candidate_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/candidate_movies.py)
7. [`top_k_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/top_k_movies.py)
8. [`hybrid_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/hybrid_search.py)
9. [`ranking_layer.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/ranking_layer.py)

## Where To Edit Specific Features

If you want to improve parser behavior:

- edit [`llama_parser.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/llama_parser.py)

If you want to improve filter logic:

- edit [`movie_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/movie_search.py)

If you want to improve semantic retrieval:

- edit [`semantic_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/semantic_search.py)

If you want to change candidate pool size:

- edit [`candidate_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/candidate_movies.py)
- or edit [`hybrid_search.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/hybrid_search.py)

If you want to change how many movies are shown first:

- edit [`top_k_movies.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/top_k_movies.py)

If you want to improve final ordering:

- edit [`ranking_layer.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/ranking_layer.py)

If you want to change which route gets used:

- edit [`router.py`](/C:/Users/ivank/OneDrive/Desktop/Sideproject/ProjectLLM/router.py)

## Future Improvements

Good next upgrades:

- multilingual embedding model
- actor and director filters
- keyword filters
- explanation layer for "why this movie was recommended"
- learned ranking weights
- user profile memory
