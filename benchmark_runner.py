import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from llama_parser import parse_user_query
from movie_search import filter_movies
from router import recommend_from_query


MOVIES_PATH = Path(__file__).parent / "movies.json"
REPORT_PATH = Path(__file__).parent / "benchmark_report.json"
PARSER_CACHE_PATH = Path(__file__).parent / "parser_benchmark_cache.json"
PARSER_FAILURE_LOG_PATH = Path(__file__).parent / "parser_failure_log.json"
SEARCH_SAMPLE_SIZE = 1000
PARSER_SAMPLE_SIZE = 300
SEED = 42
PARSER_FOCUS_CATEGORIES = {"similar", "keyword", "keyword_year"}


def load_movies():
    with open(MOVIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def unique_values(movies, field):
    values = []
    seen = set()
    for movie in movies:
        raw_value = movie.get(field)
        if isinstance(raw_value, list):
            iterable = raw_value
        else:
            iterable = [raw_value]
        for item in iterable:
            if not item:
                continue
            key = str(item).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            values.append(key)
    return values


def build_query_cases(movies):
    random.seed(SEED)

    year_values = sorted(
        {
            int(movie["year"])
            for movie in movies
            if str(movie.get("year", "")).isdigit()
        }
    )

    movies_with_cast = [movie for movie in movies if movie.get("cast")]
    movies_with_director = [movie for movie in movies if movie.get("director")]
    movies_with_genres = [movie for movie in movies if movie.get("genres")]
    movies_with_keywords = [movie for movie in movies if movie.get("keywords")]
    movies_with_language = [
        movie
        for movie in movies
        if movie.get("language") and movie.get("genres")
    ]
    similar_titles = [movie["title"] for movie in movies if movie.get("title")]

    def _movie_year(movie):
        try:
            return int(movie.get("year"))
        except (TypeError, ValueError):
            return None

    def cast_case():
        movie = random.choice(movies_with_cast)
        cast_name = random.choice(movie["cast"])
        return {
            "category": "cast",
            "query": f"I want a movie starring {cast_name}",
            "expected": {"cast": cast_name},
        }

    def director_case():
        movie = random.choice(movies_with_director)
        director_name = movie["director"]
        return {
            "category": "director",
            "query": f"I want a movie directed by {director_name}",
            "expected": {"director": director_name},
        }

    def genre_case():
        movie = random.choice(movies_with_genres)
        genre_name = random.choice(movie["genres"])
        return {
            "category": "genre",
            "query": f"I want to watch a {genre_name} movie",
            "expected": {"genre": genre_name},
        }

    def keyword_case():
        movie = random.choice(movies_with_keywords)
        keyword_name = random.choice(movie["keywords"])
        return {
            "category": "keyword",
            "query": f"I want a movie about {keyword_name}",
            "expected": {"keywords": keyword_name},
        }

    def genre_year_case():
        movie = random.choice(
            [
                m
                for m in movies_with_genres
                if _movie_year(m) and _movie_year(m) > min(year_values)
            ]
        )
        genre_name = random.choice(movie["genres"])
        movie_year = _movie_year(movie)
        year_value = random.randint(min(year_values), movie_year - 1)
        return {
            "category": "genre_year",
            "query": f"I want a {genre_name} movie after {year_value}",
            "expected": {"genre": genre_name, "year_min": year_value + 1},
        }

    def language_genre_case():
        movie = random.choice(movies_with_language)
        language_name = movie["language"]
        genre_name = random.choice(movie["genres"])
        return {
            "category": "language_genre",
            "query": f"I want a {language_name} {genre_name} movie",
            "expected": {"language": language_name, "genre": genre_name},
        }

    def cast_genre_case():
        movie = random.choice([m for m in movies_with_cast if m.get("genres")])
        cast_name = random.choice(movie["cast"])
        genre_name = random.choice(movie["genres"])
        return {
            "category": "cast_genre",
            "query": f"I want a {genre_name} movie starring {cast_name}",
            "expected": {"cast": cast_name, "genre": genre_name},
        }

    def director_genre_case():
        movie = random.choice([m for m in movies_with_director if m.get("genres")])
        director_name = movie["director"]
        genre_name = random.choice(movie["genres"])
        return {
            "category": "director_genre",
            "query": f"I want a {genre_name} movie directed by {director_name}",
            "expected": {"director": director_name, "genre": genre_name},
        }

    def keyword_year_case():
        movie = random.choice(
            [
                m
                for m in movies_with_keywords
                if _movie_year(m) and _movie_year(m) > min(year_values)
            ]
        )
        keyword_name = random.choice(movie["keywords"])
        movie_year = _movie_year(movie)
        year_value = random.randint(min(year_values), movie_year - 1)
        return {
            "category": "keyword_year",
            "query": f"I want a movie about {keyword_name} after {year_value}",
            "expected": {"keywords": keyword_name, "year_min": year_value + 1},
        }

    def similar_case():
        title_value = random.choice(similar_titles)
        return {
            "category": "similar",
            "query": f"I want movies like {title_value}",
            "expected": {"similar_to": title_value},
        }

    templates = [
        cast_case,
        director_case,
        genre_case,
        keyword_case,
        genre_year_case,
        language_genre_case,
        cast_genre_case,
        director_genre_case,
        keyword_year_case,
        similar_case,
    ]

    cases = []
    for _ in range(SEARCH_SAMPLE_SIZE):
        builder = random.choice(templates)
        case = builder()
        cases.append(case)
    return cases


def derive_expected_from_parsed(parsed_query):
    return {
        "genre": parsed_query.get("genre"),
        "mood": parsed_query.get("mood"),
        "year_min": parsed_query.get("year_min"),
        "year_max": parsed_query.get("year_max"),
        "year": parsed_query.get("year"),
        "language": parsed_query.get("language"),
        "cast": parsed_query.get("cast"),
        "director": parsed_query.get("director"),
        "keywords": parsed_query.get("keywords"),
    }


def filter_expectation_subset(expected):
    return {
        key: value
        for key, value in expected.items()
        if key in {
            "genre",
            "mood",
            "year_min",
            "year_max",
            "year",
            "language",
            "cast",
            "director",
            "keywords",
        }
    }


def expected_parse_match(parsed, expected):
    if not expected:
        return any(value is not None for value in parsed.values())
    for key, expected_value in expected.items():
        if parsed.get(key) != expected_value:
            return False
    return True


def evaluate_search_case(case):
    expected_query = case["expected"] or {}
    expected_filters = filter_expectation_subset(expected_query)
    results = recommend_from_query(
        expected_query,
        user_input=case["query"],
        top_k=5,
        debug=False,
        explain=False,
    )

    parse_success = True

    if results:
        valid_results = filter_movies(results, **expected_filters)
        result_match_ratio = len(valid_results) / len(results)
        top_result_match = len(valid_results) > 0 and valid_results[0]["title"] == results[0]["title"]
    else:
        result_match_ratio = 0.0
        top_result_match = False

    return {
        "category": case["category"],
        "query": case["query"],
        "parsed": expected_query,
        "results_count": len(results),
        "top_titles": [movie["title"] for movie in results[:5]],
        "parse_success": parse_success,
        "top_result_match": top_result_match,
        "result_match_ratio": result_match_ratio,
    }


def evaluate_parser_case(case):
    parsed = parse_user_query(case["query"])
    return {
        "category": case["category"],
        "query": case["query"],
        "expected": case["expected"],
        "parsed": parsed,
        "parse_success": expected_parse_match(parsed, case["expected"]),
    }


def build_parser_cases(cases):
    focus_cases = [case for case in cases if case["category"] in PARSER_FOCUS_CATEGORIES]
    other_cases = [case for case in cases if case["category"] not in PARSER_FOCUS_CATEGORIES]

    parser_cases = []
    target_size = min(PARSER_SAMPLE_SIZE, len(cases))
    focus_target = min(len(focus_cases), int(target_size * 0.65))

    if focus_target:
        parser_cases.extend(random.sample(focus_cases, k=focus_target))

    remaining = target_size - len(parser_cases)
    if remaining > 0 and other_cases:
        parser_cases.extend(random.sample(other_cases, k=min(remaining, len(other_cases))))

    if len(parser_cases) < target_size:
        leftovers = [case for case in cases if case not in parser_cases]
        parser_cases.extend(
            random.sample(
                leftovers,
                k=min(target_size - len(parser_cases), len(leftovers)),
            )
        )

    random.shuffle(parser_cases)
    return parser_cases


def load_parser_cache():
    if not PARSER_CACHE_PATH.exists():
        return {}
    return json.loads(PARSER_CACHE_PATH.read_text(encoding="utf-8"))


def save_parser_cache(cache):
    PARSER_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate_parser_case_cached(case, cache):
    cached = cache.get(case["query"])
    if cached is not None:
        return cached

    result = evaluate_parser_case(case)
    cache[case["query"]] = result
    return result


def build_parser_failure_log(parser_results):
    failures = [result for result in parser_results if not result["parse_success"]]
    failures.sort(key=lambda item: (item["category"], item["query"]))

    grouped_counts = Counter(result["category"] for result in failures)
    return {
        "total_failures": len(failures),
        "failures_by_category": dict(grouped_counts),
        "failures": failures,
    }


def save_parser_failure_log(parser_results):
    failure_log = build_parser_failure_log(parser_results)
    PARSER_FAILURE_LOG_PATH.write_text(
        json.dumps(failure_log, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return failure_log


def summarize_search(results):
    by_category = defaultdict(list)
    for item in results:
        by_category[item["category"]].append(item)

    summary = {}
    for category, items in by_category.items():
        parse_success_rate = sum(1 for item in items if item["parse_success"]) / len(items)
        top_result_match_rate = sum(1 for item in items if item["top_result_match"]) / len(items)
        avg_result_match_ratio = sum(item["result_match_ratio"] for item in items) / len(items)
        no_result_rate = sum(1 for item in items if item["results_count"] == 0) / len(items)
        summary[category] = {
            "count": len(items),
            "parse_success_rate": round(parse_success_rate, 3),
            "top_result_match_rate": round(top_result_match_rate, 3),
            "avg_result_match_ratio": round(avg_result_match_ratio, 3),
            "no_result_rate": round(no_result_rate, 3),
        }

    failure_counter = Counter()
    for item in results:
        if not item["parse_success"]:
            failure_counter["parse_failed"] += 1
        if item["results_count"] == 0:
            failure_counter["no_results"] += 1
        elif not item["top_result_match"]:
            failure_counter["top_result_mismatch"] += 1

    return {
        "total_cases": len(results),
        "summary_by_category": summary,
        "failure_counts": dict(failure_counter),
    }


def summarize_parser(results):
    by_category = defaultdict(list)
    for item in results:
        by_category[item["category"]].append(item)

    summary = {}
    for category, items in by_category.items():
        parse_success_rate = sum(1 for item in items if item["parse_success"]) / len(items)
        summary[category] = {
            "count": len(items),
            "parse_success_rate": round(parse_success_rate, 3),
        }

    failure_count = sum(1 for item in results if not item["parse_success"])
    return {
        "total_cases": len(results),
        "summary_by_category": summary,
        "failure_count": failure_count,
    }


def main():
    movies = load_movies()
    cases = build_query_cases(movies)
    search_results = []

    for index, case in enumerate(cases, start=1):
        result = evaluate_search_case(case)
        search_results.append(result)
        if index % 50 == 0:
            print(f"Processed search benchmark {index}/{len(cases)}")

    parser_cases = build_parser_cases(cases)
    parser_cache = load_parser_cache()
    parser_results = []
    for index, case in enumerate(parser_cases, start=1):
        parser_results.append(evaluate_parser_case_cached(case, parser_cache))
        if index % 10 == 0:
            save_parser_cache(parser_cache)
        if index % 25 == 0:
            print(f"Processed parser benchmark {index}/{len(parser_cases)}")

    save_parser_cache(parser_cache)

    parser_failure_log = save_parser_failure_log(parser_results)
    parser_failures = parser_failure_log["failures"]

    report = {
        "config": {
            "search_sample_size": SEARCH_SAMPLE_SIZE,
            "parser_sample_size": PARSER_SAMPLE_SIZE,
            "seed": SEED,
            "parser_focus_categories": sorted(PARSER_FOCUS_CATEGORIES),
        },
        "search_aggregate": summarize_search(search_results),
        "parser_aggregate": summarize_parser(parser_results),
        "search_examples": search_results[:50],
        "parser_examples": parser_results[:50],
        "parser_failures": parser_failures[:100],
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report["search_aggregate"], ensure_ascii=False, indent=2))
    print(json.dumps(report["parser_aggregate"], ensure_ascii=False, indent=2))
    print(json.dumps(parser_failure_log["failures_by_category"], ensure_ascii=False, indent=2))
    print(f"\nSaved full report to {REPORT_PATH}")
    print(f"Saved parser failure log to {PARSER_FAILURE_LOG_PATH}")


if __name__ == "__main__":
    main()
