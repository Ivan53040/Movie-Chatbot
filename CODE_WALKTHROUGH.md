# Code Walkthrough

This document is meant to help you read the project like a developer, not just use it.

If you only want one mental model for the whole repo, use this:

```text
User request
  -> parse the request into structured fields
  -> choose a retrieval strategy
  -> gather candidate movies
  -> apply hard filters
  -> rank the survivors
  -> generate one explanation for the top pick
  -> return results to CLI or frontend
```

## 1. What problem this project solves

This project is a movie recommender with two styles of search:

- strict search: "show me Japanese thrillers after 2015"
- fuzzy search: "something like Interstellar" or "robot movies"

The code mixes classic filtering with embedding-based semantic search. That is the main idea of the whole architecture.

## 2. The easiest way to understand the repo

Read the backend in this order:

1. `router.py`
2. `movie_query_parser.py`
3. `movie_search.py`
4. `semantic_search.py`
5. `similar_search.py`
6. `hybrid_search.py`
7. `ranking_layer.py`
8. `build_explanation_input.py`
9. `llm_explanation.py`
10. `frontend_server.py`

Why start with `router.py`?

Because it is the control tower. It does not do every job itself, but it shows which module is responsible for which step.

## 3. Top-level folders and files

### Core backend

- `router.py`: main orchestration layer for CLI and recommendation flow
- `movie_query_parser.py`: turns free text into structured query fields
- `movie_search.py`: rule-based filtering over `movies.json`
- `semantic_search.py`: embedding retrieval using `movie_embeddings.npz`
- `similar_search.py`: "movies like X" retrieval using the reference movie embedding
- `hybrid_search.py`: retrieval + filtering + ranking pipeline
- `ranking_layer.py`: converts candidate movies into ordered results
- `build_explanation_input.py`: prepares structured reasoning data for the LLM
- `llm_explanation.py`: asks the LLM for a short explanation of the top pick
- `frontend_server.py`: small HTTP server that serves the browser UI and exposes `/api/chat`

### Data and generated assets

- `movies.json`: main movie dataset
- `movie_embeddings.npz`: precomputed embedding vectors for the movies
- `build_embeddings.py`: regenerates embeddings after the dataset changes

### Frontends

- `frontend/`: the static HTML/CSS/JS app actually served by `frontend_server.py`
- `frontend-react/`: separate React/Vite frontend, likely an alternative or in-progress UI

## 4. The data model you should keep in your head

The most important object in the codebase is the parsed query dictionary.

It usually looks like this:

```python
{
    "genre": None,
    "mood": None,
    "year_min": None,
    "year_max": None,
    "year": None,
    "language": None,
    "cast": None,
    "director": None,
    "keywords": None,
    "similar_to": None,
    "semantic_query": None,
}
```

This object is the contract between the parser and the rest of the system.

Once you understand what each field means, the rest of the project becomes much easier to follow.

## 5. End-to-end request flow

Use this example:

```text
movies like Interstellar but after 2010
```

### Step 1: parse the user message

File: `movie_query_parser.py`

The parser tries to convert natural language into the structured query object.

Expected result for that example:

```python
{
    "similar_to": "Interstellar",
    "year_min": 2011,
    ...
}
```

Important detail:

The parser is not trusted blindly. After the LLM responds, `_normalize_parsed_query()` fixes and overrides common mistakes with regex and hand-written rules.

That means this file has two parser layers:

- LLM extraction
- deterministic cleanup

This is a very practical design choice because LLM output is often close, but not fully reliable.

### Step 2: choose the route

File: `router.py`

The router decides which strategy to use:

- if `similar_to` exists: use similar-movie hybrid search
- if `semantic_query` exists: use semantic hybrid search
- otherwise: use pure filter search
- if pure filter search returns nothing and there are no hard filters: fall back to semantic search

This file is the best place to answer questions like:

- "Why did this query use embeddings?"
- "When does the code choose filter-only search?"
- "Why do some queries get explanations and others do not?"

### Step 3: generate candidates

Files: `candidate_movies.py`, `semantic_search.py`, `similar_search.py`

The project separates candidate generation from final ranking.

That means it first gets a wider pool, such as top 50 likely matches, and only later decides the final top 5.

This is a common recommender-system pattern:

```text
retrieve many
  -> filter
  -> score
  -> show a few
```

`semantic_search.py` handles text-to-movie retrieval:

- load `movies.json`
- load `movie_embeddings.npz`
- embed the query text
- compute dot product similarity
- return the top matches with a `similarity` score

`similar_search.py` handles title-to-title retrieval:

- find the target movie in the dataset
- use its stored embedding as the query vector
- score all other movies against it
- exclude the movie itself

If the title is not found exactly, it falls back to semantic search using text like `movies like Interstellar`.

### Step 4: apply hard filters

File: `movie_search.py`

The filtering layer decides whether a movie is allowed to stay in the candidate set.

This is strict AND logic:

- if you ask for genre and year and language, all of them must match
- if one required condition fails, the movie is removed

Important distinction:

- retrieval finds plausible movies
- filtering enforces exact constraints

Examples of filters:

- genre
- mood
- year / year range
- language
- cast
- director
- keywords

This same module is also used for plain rule-based search when there is no semantic route.

### Step 5: rank the survivors

File: `ranking_layer.py`

After filtering, the code gives each remaining movie a handcrafted score.

Current score ingredients:

- semantic similarity
- vote average
- popularity
- recency
- genre bonus
- language bonus
- cast bonus
- director bonus
- mood bonus
- keyword bonus
- exact year bonus

This is not a trained ML ranking model. It is a manually designed scoring function.

That is useful for learning because you can see exactly why the order changes.

### Step 6: explain the top pick

Files: `build_explanation_input.py`, `llm_explanation.py`

Only the first result gets a generated explanation.

The explanation flow is:

1. convert the top result into structured facts and reason tags
2. send that compact payload to the LLM
3. ask for a short paragraph in the user's language
4. attach the text back to the first movie as `top_pick_text`

This design is good because the LLM does not need raw access to the full dataset. It only receives a small, controlled payload.

## 6. The real role of each important file

### `router.py`

Think of this as the project's application service layer.

Key responsibilities:

- build ranking context from parsed query
- choose hybrid search vs filter search
- retry with relaxed filters in some cases
- exclude already seen movie IDs for "more" style flows
- attach explanation text
- provide CLI entry point

Important functions:

- `recommend_movies()`: normal entry point from text input
- `recommend_from_query()`: lower-level route executor after parsing
- `recommend_movies_with_metadata()`: returns route and parsed query for the frontend

### `movie_query_parser.py`

Think of this as a guarded parser, not just an LLM call.

Key idea:

The LLM proposes structure, then the code cleans it up.

Things this file corrects:

- bad years like `0`
- phrases like `after 2010`
- accidental mood inference when the mood was not explicit
- cast/director alias normalization
- broad topics that should become `semantic_query` or `keywords`
- title-like phrases that should become `similar_to`

There is also a fallback parser when the API is unavailable.

That fallback is important because it makes the app still usable even when the remote model fails.

### `movie_search.py`

Think of this as the exact-match engine.

Important functions:

- `search_movies()`: load all movies and apply filters
- `filter_movies()`: apply filtering to any movie list
- `find_person_candidates()`: used by the frontend to ask clarifying questions for actor/director names

One useful reading trick:

Start with `_matches_filters()`. That function tells you exactly what "matching the query" means in this project.

### `semantic_search.py`

Think of this as the semantic retrieval engine.

Important functions:

- `cosine_search()`: main embedding search
- `normalize_semantic_query()`: expands certain topic words before embedding
- `make_movie_text()`: defines the text representation used when building embeddings

A subtle but important detail:

The query is expanded for terms like `robot`, `superhero`, and some Chinese keywords before embedding. That is a hand-written retrieval boost.

### `similar_search.py`

Think of this as semantic search where the query is another movie.

The central idea:

If a user names a movie title, the system can skip query text embedding and use the stored vector for that movie directly.

### `hybrid_search.py`

Think of this as glue code.

It is intentionally small because it combines three existing building blocks:

```text
candidate builder
  -> filter_movies()
  -> rank_movies()
```

The code is simple here because the complexity is pushed into well-separated modules.

### `ranking_layer.py`

Think of this as the project's opinionated definition of "best".

Important thing to notice:

The code copies each movie before scoring it. That avoids mutating the original candidate objects too early.

### `build_explanation_input.py`

Think of this as the safety layer before the explanation model.

It decides:

- which movie gets explained
- which fields are sent
- what reason tags the LLM is allowed to use

This is one of the cleanest modules in the repo for learning good LLM integration design.

### `llm_explanation.py`

Think of this as a narrow wrapper around one prompt.

It is intentionally small:

- build explanation input
- send prompt
- parse JSON output
- return `top_pick_text`

That narrow scope is a good design habit.

### `frontend_server.py`

Think of this as a minimal API server, not a full framework app.

It serves:

- `GET /` for the static frontend
- `POST /api/chat` for recommendations

It also adds a useful clarification feature:

If the parser thinks a name fragment might be either a cast member or a director, the frontend can ask the user which one they meant.

## 7. Important design ideas hidden in the code

### LLMs are used in narrow places

The project does not let the LLM control everything.

The LLM is used for:

- parsing the user request
- writing one explanation paragraph

The deterministic code still owns:

- filtering
- routing
- ranking
- retrieval pipeline structure

This is a strong design choice because it keeps behavior easier to debug.

### Candidate generation is separated from ranking

This is one of the most important architectural choices in the repo.

Why it matters:

- retrieval can stay broad
- ranking can be tuned without changing retrieval
- filtering can stay strict
- you can inspect failure points more easily

### The router contains fallback logic

The router is not just a switch statement.

It also:

- relaxes some filters when retrieval is too narrow
- falls back from title similarity to semantic search
- falls back from LLM parser to rule-based parser

That is why the app feels more forgiving than the individual modules might suggest.

## 8. How CLI and frontend differ

### CLI path

Entry point: `router.py`

The CLI loop:

1. read user input
2. parse `more` commands
3. call `recommend_movies()`
4. print the top pick and extra recommendations

### Browser path

Entry point: `frontend_server.py`

The browser flow:

1. frontend JS sends `POST /api/chat`
2. server parses and routes the request
3. server returns JSON with `parsed_query`, `route`, and `results`
4. frontend renders the top pick and metadata chips

The static frontend in `frontend/` is the one wired into the Python server today.

## 9. How the "more" feature works

File: `top_k_movies.py`

The first response defaults to `5` movies.

If the user types:

- `more` -> ask for 10 total
- `more 10` -> ask for 10 total

The router expands both:

- `top_k`
- candidate pool size

This matters because showing more results should usually search a wider pool, not just reveal lower-ranked items from a tiny pool.

## 10. How to debug wrong recommendations

When the output looks wrong, inspect the pipeline in this order:

1. parser: did the query fields make sense?
2. route: did the router choose the right strategy?
3. candidates: did semantic retrieval bring the right movies?
4. filters: did strict filters remove the good options?
5. ranking: did the scoring formula overvalue popularity or recency?
6. explanation: is the explanation wrong, or is the recommendation itself wrong?

Practical rule:

If the top candidates are already wrong, the problem is usually parsing or retrieval.
If the candidate list looks good but order is bad, the problem is usually ranking.

## 11. Best files to study for learning

If your goal is to improve your programming, these files teach different lessons:

- `router.py`: orchestration and fallback design
- `movie_query_parser.py`: defensive LLM integration
- `movie_search.py`: clean filter logic over JSON data
- `semantic_search.py`: basic embedding retrieval
- `ranking_layer.py`: handcrafted recommender scoring
- `build_explanation_input.py`: controlled prompt payload design

## 12. Good beginner exercises in this repo

If you want to learn by editing, these are good first tasks:

1. Add a new filter, such as runtime range.
2. Add more cast/director aliases in `movie_query_parser.py`.
3. Change ranking weights in `ranking_layer.py` and compare results.
4. Add new semantic query expansions in `semantic_search.py`.
5. Extend the frontend to show ranking score or similarity.

## 13. Where to make specific changes

- parser behavior: `movie_query_parser.py`
- exact filter logic: `movie_search.py`
- semantic retrieval behavior: `semantic_search.py`
- "movies like X" logic: `similar_search.py`
- candidate pool size: `top_k_movies.py` or `hybrid_search.py`
- ranking formula: `ranking_layer.py`
- explanation prompt: `llm_explanation.py`
- frontend API behavior: `frontend_server.py`
- static UI: `frontend/`

## 14. Short summary of the architecture

If you forget everything else, remember this:

- `movie_query_parser.py` turns free text into structure
- `router.py` decides the search path
- retrieval modules find candidate movies
- `movie_search.py` applies exact constraints
- `ranking_layer.py` orders the survivors
- explanation modules justify the first result
- `frontend_server.py` exposes the system to the browser

That is the entire project in one chain of responsibility.
