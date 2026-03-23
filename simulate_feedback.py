import hashlib
import json
import sys
from pathlib import Path

from build_user_item_matrix import build_user_item_matrix
from feedback_dataset import (
    log_feedback_label,
    log_feedback_reason,
    log_recommendation_impression,
)
from router import recommend_movies_with_metadata


ROOT_DIR = Path(__file__).parent
ARTIFACT_DIR = ROOT_DIR / "artifacts"
SIMULATION_REPORT_PATH = ARTIFACT_DIR / "synthetic_feedback_report.json"


PERSONAS = [
    {
        "user_id": "synthetic_marvel_fan_01",
        "language": "en",
        "queries": ["latest marvel movie", "exciting marvel movie", "mcu action movie", "fun marvel movie"],
        "franchise": ["marvel", "mcu"],
        "genres": ["action", "science fiction", "adventure"],
        "moods": ["exciting", "funny"],
    },
    {
        "user_id": "synthetic_dc_fan_02",
        "language": "en",
        "queries": ["latest dc movie", "exciting dc movie", "dceu superhero movie", "dark dc movie"],
        "franchise": ["dc", "dceu", "dcu"],
        "genres": ["action", "science fiction"],
        "moods": ["exciting", "dark"],
    },
    {
        "user_id": "synthetic_starwars_fan_03",
        "language": "en",
        "queries": ["star wars movie", "latest star wars movie", "space adventure like star wars", "exciting star wars film"],
        "franchise": ["star wars"],
        "genres": ["science fiction", "adventure", "action"],
        "moods": ["exciting"],
    },
    {
        "user_id": "synthetic_nolan_fan_04",
        "language": "en",
        "queries": ["a great Christopher Nolan movie", "Nolan movie", "mind-bending sci-fi", "movie directed by Christopher Nolan"],
        "director": ["christopher nolan"],
        "genres": ["science fiction", "drama", "action"],
        "moods": ["intense"],
    },
    {
        "user_id": "synthetic_horror_fan_05",
        "language": "en",
        "queries": ["give me a horror movie", "scary movie tonight", "psychological horror", "horror movie with a twist"],
        "genres": ["horror", "thriller"],
        "moods": ["dark", "intense"],
    },
    {
        "user_id": "synthetic_romcom_fan_06",
        "language": "en",
        "queries": ["funny romance movie", "romance after 2015", "cozy romance movie", "feel-good romantic comedy"],
        "genres": ["romance", "comedy"],
        "moods": ["light", "funny", "romantic"],
        "min_year": 2015,
    },
    {
        "user_id": "synthetic_family_parent_07",
        "language": "en",
        "queries": ["family movie tonight", "wholesome animated movie", "movie for kids and parents", "feel-good family movie"],
        "genres": ["family", "animation", "adventure"],
        "moods": ["uplifting", "light"],
    },
    {
        "user_id": "synthetic_korean_thriller_08",
        "language": "en",
        "queries": ["korean thriller", "korean revenge movie", "dark korean movie", "suspenseful korean film"],
        "genres": ["thriller", "crime", "drama"],
        "language_pref": "ko",
        "moods": ["dark", "intense"],
    },
    {
        "user_id": "synthetic_sports_fan_09",
        "language": "en",
        "queries": ["give me a sport movie", "feel-good sports movie", "sports drama", "true story sports movie"],
        "genres": ["drama"],
        "keywords": ["sports"],
        "moods": ["uplifting", "exciting"],
    },
    {
        "user_id": "synthetic_a24_fan_10",
        "language": "en",
        "queries": ["A24-style emotional drama", "quiet emotional drama", "beautifully shot indie drama", "sad movie that is still beautiful"],
        "genres": ["drama"],
        "moods": ["emotional", "quiet"],
        "keywords": ["indie", "a24"],
    },
    {
        "user_id": "synthetic_keanu_fan_11",
        "language": "en",
        "queries": ["movie starring Keanu Reeves", "Keanu Reeves action movie", "John Wick style action", "movie cast by keanu"],
        "cast": ["keanu reeves"],
        "genres": ["action", "thriller", "science fiction"],
    },
    {
        "user_id": "synthetic_tom_cruise_fan_12",
        "language": "en",
        "queries": ["Tom Cruise film", "movie starring Tom Cruise", "mission impossible movie", "fast action movie with Tom Cruise"],
        "cast": ["tom cruise"],
        "franchise": ["mission impossible"],
        "genres": ["action", "thriller"],
    },
    {
        "user_id": "synthetic_animation_fan_13",
        "language": "en",
        "queries": ["animated movie for adults", "beautiful animation movie", "emotional animated film", "animation with heart"],
        "genres": ["animation", "family", "drama"],
        "moods": ["emotional", "uplifting"],
    },
    {
        "user_id": "synthetic_scifi_fan_14",
        "language": "en",
        "queries": ["movie set in space", "underrated sci-fi", "space movie with emotion", "movie with aliens"],
        "genres": ["science fiction", "adventure"],
        "moods": ["intense", "emotional"],
    },
    {
        "user_id": "synthetic_true_story_15",
        "language": "en",
        "queries": ["crime movie based on true events", "biographical drama", "movie based on a true story", "historical thriller"],
        "genres": ["drama", "history", "crime"],
        "keywords": ["true story", "based on true events"],
    },
    {
        "user_id": "synthetic_chinese_family_16",
        "language": "zh",
        "queries": ["我想看一部溫馨的家庭電影", "給我一部動畫電影", "適合全家一起看的電影", "輕鬆感人的電影"],
        "genres": ["family", "animation", "comedy"],
        "moods": ["uplifting", "light", "emotional"],
    },
    {
        "user_id": "synthetic_chinese_horror_17",
        "language": "zh",
        "queries": ["我想看恐怖片", "給我一部驚悚電影", "黑暗一點的電影", "有反轉的恐怖片"],
        "genres": ["horror", "thriller"],
        "moods": ["dark", "intense"],
    },
    {
        "user_id": "synthetic_chinese_romance_18",
        "language": "zh",
        "queries": ["我想看愛情電影", "給我一部浪漫喜劇", "2015 年後的愛情片", "約會夜看的電影"],
        "genres": ["romance", "comedy"],
        "moods": ["romantic", "light"],
        "min_year": 2015,
    },
    {
        "user_id": "synthetic_fincher_fan_19",
        "language": "en",
        "queries": ["Fincher movie", "dark detective story", "psychological thriller", "crime thriller with style"],
        "director": ["david fincher"],
        "genres": ["thriller", "crime", "drama"],
        "moods": ["dark", "intense"],
    },
    {
        "user_id": "synthetic_wholesome_20",
        "language": "en",
        "queries": ["feel-good movie tonight", "light comedy for a lazy night", "warm family movie", "something uplifting"],
        "genres": ["comedy", "family", "animation"],
        "moods": ["uplifting", "light", "funny"],
    },
]


def _stable_noise(*parts):
    seed = "|".join(str(part) for part in parts)
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 1000) / 1000.0


def _movie_text(movie):
    genres = " ".join(str(item).lower() for item in movie.get("genres", []))
    keywords = " ".join(str(item).lower() for item in movie.get("keywords", []))
    cast = " ".join(str(item).lower() for item in movie.get("cast", []))
    director = str(movie.get("director", "")).lower()
    overview = str(movie.get("overview", "")).lower()
    title = str(movie.get("title", "")).lower()
    return " ".join([title, genres, keywords, cast, director, overview])


def _match_count(tokens, haystack):
    return sum(1 for token in tokens if token and token in haystack)


def _score_movie_for_persona(persona, movie):
    haystack = _movie_text(movie)
    score = 0.0

    genres = [item.lower() for item in persona.get("genres", [])]
    moods = [item.lower() for item in persona.get("moods", [])]
    keywords = [item.lower() for item in persona.get("keywords", [])]
    franchises = [item.lower() for item in persona.get("franchise", [])]
    cast = [item.lower() for item in persona.get("cast", [])]
    directors = [item.lower() for item in persona.get("director", [])]

    score += _match_count(genres, haystack) * 1.3
    score += _match_count(moods, haystack) * 0.8
    score += _match_count(keywords, haystack) * 1.6
    score += _match_count(franchises, haystack) * 2.2
    score += _match_count(cast, haystack) * 2.0
    score += _match_count(directors, haystack) * 2.0

    language_pref = str(persona.get("language_pref", "")).strip().lower()
    if language_pref and str(movie.get("language", "")).strip().lower() == language_pref:
        score += 1.1

    min_year = persona.get("min_year")
    try:
        movie_year = int(movie.get("year") or 0)
    except (TypeError, ValueError):
        movie_year = 0
    if min_year and movie_year >= int(min_year):
        score += 0.8

    score += min(float(movie.get("vote_average", 0.0) or 0.0) / 10.0, 1.0) * 0.4
    score += min(float(movie.get("similarity", 0.0) or 0.0), 1.0) * 0.5
    score += _stable_noise(persona["user_id"], movie.get("id", movie.get("title"))) * 0.15
    return round(score, 4)


def _evaluate_results(persona, query, results):
    if not results:
        return False, "No results were returned for this request."

    top_result = results[0]
    top_score = _score_movie_for_persona(persona, top_result)
    average_top3 = sum(_score_movie_for_persona(persona, movie) for movie in results[:3]) / min(len(results), 3)
    threshold = 2.1

    if top_score >= threshold or average_top3 >= threshold:
        return True, f'The top results matched this persona well enough for query "{query}".'

    title = top_result.get("title", "the top result")
    return False, f'"{title}" did not match this persona strongly enough for query "{query}".'


def run_simulation():
    summary = {
        "users": len(PERSONAS),
        "queries_run": 0,
        "helpful": 0,
        "not_helpful": 0,
        "no_results": 0,
        "per_user": [],
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    for persona in PERSONAS:
        user_summary = {
            "user_id": persona["user_id"],
            "language": persona["language"],
            "queries": [],
        }

        for query in persona["queries"]:
            bundle = recommend_movies_with_metadata(
                query,
                top_k=3,
                user_id=persona["user_id"],
                debug=False,
                explain=False,
            )
            results = bundle.get("results", [])
            recommendation_id = log_recommendation_impression(
                user_id=persona["user_id"],
                query=query,
                ui_language=persona["language"],
                route=bundle.get("route"),
                parsed_query=bundle.get("parsed_query", {}),
                results=results,
            )
            helpful, reason = _evaluate_results(persona, query, results)
            log_feedback_label(
                recommendation_id=recommendation_id,
                user_id=persona["user_id"],
                helpful=helpful,
                query=query,
                ui_language=persona["language"],
                route=bundle.get("route"),
                parsed_query=bundle.get("parsed_query", {}),
                results=results,
            )
            if not helpful:
                log_feedback_reason(
                    recommendation_id=recommendation_id,
                    user_id=persona["user_id"],
                    reason=reason,
                    ui_language=persona["language"],
                )

            summary["queries_run"] += 1
            summary["helpful"] += 1 if helpful else 0
            summary["not_helpful"] += 0 if helpful else 1
            summary["no_results"] += 1 if not results else 0
            user_summary["queries"].append(
                {
                    "query": query,
                    "route": bundle.get("route"),
                    "helpful": helpful,
                    "reason": reason,
                    "top_titles": [movie.get("title") for movie in results[:3]],
                }
            )

        summary["per_user"].append(user_summary)

    matrix_summary = build_user_item_matrix()
    summary["matrix"] = matrix_summary
    SIMULATION_REPORT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    try:
        print(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    return summary


if __name__ == "__main__":
    run_simulation()
