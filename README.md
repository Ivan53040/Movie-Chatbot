# ProjectLLM

ProjectLLM is a movie recommendation system that turns free-form user requests into structured search intent, chooses an appropriate retrieval strategy, ranks candidate movies, and returns a small set of recommendations with an LLM-generated explanation for the top result.

In practice, it is a hybrid recommender rather than a single search script. It combines:

- LLM-based query parsing
- rule-based filtering
- embedding-based semantic retrieval
- title-to-title similarity search
- heuristic ranking
- feedback logging
- item-based collaborative filtering for light personalization

## What This Project Is Doing

The project lets a user ask for movies in natural language, for example:

- `Japanese thrillers after 2015`
- `movies like Interstellar`
- `funny Korean movies`
- `robot movies`

The backend then runs a multi-stage pipeline:

```text
User message
  -> LLM parser
  -> deterministic cleanup / normalization
  -> router
  -> retrieval strategy
  -> candidate generation
  -> hard filtering
  -> ranking
  -> optional personalization
  -> explanation generation for the top pick
  -> API/frontend response
```

This means the project is trying to solve two related problems:

1. Understand messy natural language movie requests.
2. Turn that understanding into useful recommendations with interpretable logic.

## Core Techniques Used

This project uses several recommendation and NLP techniques together:

### 1. LLM Parsing

`llama_parser.py` sends the raw user query to an LLM and asks for structured JSON fields such as:

- `genre`
- `mood`
- `year`, `year_min`, `year_max`
- `language`
- `cast`
- `director`
- `keywords`
- `similar_to`
- `semantic_query`

This is the natural-language understanding layer of the system.

### 2. Deterministic Post-Processing

The LLM output is not trusted blindly. The parser applies rule-based cleanup after the model response, including:

- regex-based year correction
- empty / invalid value cleanup
- explicit phrase overrides like `after 2010`
- mood validation
- cast/director alias normalization
- franchise detection

This is a common hybrid NLP technique: use an LLM for broad understanding, then use deterministic rules to improve reliability.

### 3. Rule-Based Filtering

`movie_search.py` applies hard constraints over the dataset. This is the classical filtering part of the recommender.

Supported filters include:

- genre
- mood
- year and year range
- language
- cast
- director
- keywords
- franchise

### 4. Embedding-Based Semantic Search

`semantic_search.py` and `build_embeddings.py` use sentence embeddings to represent movie metadata and user queries in vector space.

The project uses:

- `SentenceTransformer("all-MiniLM-L6-v2")`
- precomputed movie embeddings stored in `movie_embeddings.npz`
- cosine / vector similarity retrieval

This is what allows fuzzy matching such as:

- `robot movies`
- `something emotional but uplifting`
- `space movies like Interstellar`

even when the request does not map cleanly to exact metadata fields.

### 5. Similarity Search

`similar_search.py` supports requests like `movies like Interstellar`.

Technique:

- find the reference movie
- reuse that movie's embedding as the query vector
- retrieve nearby movies in embedding space

So this is item-to-item similarity using content embeddings.

### 6. Hybrid Retrieval Pipeline

`hybrid_search.py` combines:

- semantic or similar-item retrieval
- hard filtering
- ranking

This is a standard recommender pattern:

```text
retrieve many
  -> filter strictly
  -> rank survivors
  -> return top few
```

### 7. Heuristic Ranking

`ranking_layer.py` uses a handcrafted scoring function instead of a trained learning-to-rank model.

Ranking signals include:

- semantic similarity
- vote average
- popularity
- recency bias
- genre match bonus
- language match bonus
- cast/director match bonuses
- mood / keyword bonuses
- franchise bonus
- exact year bonus

This makes the ranking logic transparent and easy to tune.

### 8. Collaborative Filtering Personalization

The project also includes item-based collaborative filtering in `item_based_cf.py`.

Technique:

- build a user-item matrix from logged impressions and feedback
- compute item-item cosine similarity
- use prior user interactions to slightly boost candidate scores

This is a classic recommender-system technique layered on top of the content-based pipeline.

### 9. LLM Explanation Generation

`build_explanation_input.py` prepares a compact structured payload for the top recommendation, and `llm_explanation.py` asks the LLM to generate a short natural-language explanation.

This uses controlled generation rather than letting the LLM inspect the full dataset directly.

## Retrieval / Routing Logic

`router.py` is the orchestration layer. It decides how each query should be handled.

Main routing behavior:

- if `similar_to` exists, use hybrid similar-movie search
- if `semantic_query` exists, use hybrid semantic search
- otherwise, use filter search
- if strict search returns nothing and the query is still broad enough, fall back to semantic search
- if a `user_id` is available, apply collaborative-filtering score boosts

So the project is not "LLM only". The LLM mainly interprets the query and writes the explanation. Retrieval and ranking are mostly classical recommender logic.

## Main Files

- `router.py`: main orchestration and route selection
- `llama_parser.py`: LLM parsing plus rule-based normalization
- `api_parser_client.py`: Groq API client for parser/explanation calls
- `movie_search.py`: strict metadata filtering
- `semantic_search.py`: text-to-movie embedding retrieval
- `similar_search.py`: movie-to-movie similarity retrieval
- `hybrid_search.py`: retrieval + filter + ranking pipeline
- `ranking_layer.py`: handcrafted scoring
- `candidate_movies.py`: candidate pool generation
- `build_explanation_input.py`: explanation payload builder
- `llm_explanation.py`: top-pick explanation generation
- `feedback_dataset.py`: log impressions and feedback
- `build_user_item_matrix.py`: build interaction matrix from logs
- `item_based_cf.py`: item-item collaborative filtering
- `fastapi_server.py`: FastAPI API and React frontend serving
- `frontend_server.py`: older lightweight HTTP server for the static frontend

## Data and Artifacts

- `movies.json`: movie catalog and metadata
- `movie_embeddings.npz`: precomputed movie embeddings
- `logs/`: feedback and recommendation events
- `artifacts/`: user-item matrix, indexes, and item similarity artifacts

## Frontend / API

The project currently exposes a chat-style interface through `fastapi_server.py`.

Main API endpoints:

- `POST /api/chat`: parse the request and return recommendations
- `POST /api/feedback`: log helpful / not-helpful feedback and reasons

The repository contains two frontends:

- `frontend/`: older static HTML/CSS/JS UI
- `frontend-react/`: newer React/Vite frontend used by the FastAPI app

## How To Run

### Start the app

On Windows, the easiest entrypoint is:

```powershell
./start_chatbot.ps1
```

This script:

- builds the React frontend
- finds a free local port
- starts `uvicorn fastapi_server:app`
- opens the browser automatically

### Direct API run

```powershell
python -m uvicorn fastapi_server:app --host 127.0.0.1 --port 8000
```

### Rebuild embeddings

```powershell
python build_embeddings.py
```

### Rebuild user-item matrix

```powershell
python build_user_item_matrix.py
```

### Run collaborative filtering directly

```powershell
python item_based_cf.py --list-users
python item_based_cf.py --user-id <USER_ID> --top-k 5
```

## Current Architecture Summary

The project is best understood as a hybrid movie recommender with an LLM-assisted interface.

It uses:

- LLM parsing for query understanding
- rules for parser correction and strict filtering
- embeddings for semantic retrieval
- content-based item similarity for "movies like X"
- heuristic ranking for final ordering
- feedback logs for learning from user responses
- item-based collaborative filtering for personalization
- LLM generation for short recommendation explanations

## Short Project Summary

If you want one sentence:

ProjectLLM is a hybrid movie recommendation chatbot that uses LLM parsing plus recommender-system techniques to turn natural-language requests into filtered, ranked, explainable movie suggestions.

## Suggested Reading Order

If you want to study the codebase, read these files in order:

1. `router.py`
2. `llama_parser.py`
3. `movie_search.py`
4. `semantic_search.py`
5. `similar_search.py`
6. `hybrid_search.py`
7. `ranking_layer.py`
8. `item_based_cf.py`
9. `build_explanation_input.py`
10. `llm_explanation.py`
11. `fastapi_server.py`

For a longer guided explanation, see `CODE_WALKTHROUGH.md`.
