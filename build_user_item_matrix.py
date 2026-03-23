import json
from pathlib import Path

import numpy as np

from feedback_dataset import USER_MOVIE_RATINGS_PATH


ROOT_DIR = Path(__file__).parent
ARTIFACT_DIR = ROOT_DIR / "artifacts"
MATRIX_PATH = ARTIFACT_DIR / "user_item_matrix.npz"
USER_INDEX_PATH = ARTIFACT_DIR / "user_index.json"
MOVIE_INDEX_PATH = ARTIFACT_DIR / "movie_index.json"
INTERACTION_SUMMARY_PATH = ARTIFACT_DIR / "user_item_interactions.jsonl"


def _load_rating_events(path):
    if not path.exists():
        return []

    events = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _aggregate_events(events):
    aggregated = {}

    for event in events:
        user_id = str(event.get("user_id") or "").strip()
        movie_id = event.get("movie_id")
        movie_title = str(event.get("movie_title") or "").strip()

        if not user_id or movie_id is None or not movie_title:
            continue

        key = (user_id, str(movie_id))
        entry = aggregated.setdefault(
            key,
            {
                "user_id": user_id,
                "movie_id": str(movie_id),
                "movie_title": movie_title,
                "movie_year": event.get("movie_year"),
                "impression_count": 0,
                "helpful_count": 0,
                "not_helpful_count": 0,
                "latest_timestamp": "",
                "latest_feedback_label": None,
                "queries": set(),
            },
        )

        event_type = str(event.get("event_type") or "").strip().lower()
        feedback_label = event.get("feedback_label")
        timestamp = str(event.get("timestamp") or "")
        query = str(event.get("query") or "").strip()

        if query:
            entry["queries"].add(query)

        if event_type == "impression":
            entry["impression_count"] += 1
        elif event_type == "feedback":
            if feedback_label == "helpful":
                entry["helpful_count"] += 1
            elif feedback_label == "not_helpful":
                entry["not_helpful_count"] += 1

        if timestamp >= entry["latest_timestamp"]:
            entry["latest_timestamp"] = timestamp
            if feedback_label in {"helpful", "not_helpful"}:
                entry["latest_feedback_label"] = feedback_label

    return aggregated


def _score_interaction(entry):
    helpful_count = int(entry["helpful_count"])
    not_helpful_count = int(entry["not_helpful_count"])
    impression_count = int(entry["impression_count"])

    if helpful_count or not_helpful_count:
        total_feedback = helpful_count + not_helpful_count
        feedback_ratio = helpful_count / total_feedback if total_feedback else 0.0
        if helpful_count > not_helpful_count:
            return round(max(0.5, feedback_ratio), 4)
        if not_helpful_count > helpful_count:
            return round(min(0.49, feedback_ratio), 4)
        return round(feedback_ratio, 4)

    # Impression-only interactions stay weakly positive instead of zero, so the
    # matrix can still represent exposure for later implicit-feedback methods.
    return round(min(0.25, impression_count * 0.05), 4)


def _build_indexes(aggregated_entries):
    user_ids = sorted({entry["user_id"] for entry in aggregated_entries})
    movies = sorted(
        {
            (entry["movie_id"], entry["movie_title"], entry.get("movie_year"))
            for entry in aggregated_entries
        },
        key=lambda item: (item[1].lower(), item[2] or 0, item[0]),
    )

    user_to_index = {user_id: index for index, user_id in enumerate(user_ids)}
    movie_to_index = {movie_id: index for index, (movie_id, _, _) in enumerate(movies)}

    user_index = [
        {"user_id": user_id, "index": user_to_index[user_id]}
        for user_id in user_ids
    ]
    movie_index = [
        {
            "movie_id": movie_id,
            "movie_title": movie_title,
            "movie_year": movie_year,
            "index": movie_to_index[movie_id],
        }
        for movie_id, movie_title, movie_year in movies
    ]

    return user_to_index, movie_to_index, user_index, movie_index


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_interaction_summary(path, aggregated_entries):
    with path.open("w", encoding="utf-8") as handle:
        for entry in aggregated_entries:
            serializable = dict(entry)
            serializable["queries"] = sorted(entry["queries"])
            handle.write(json.dumps(serializable, ensure_ascii=False) + "\n")


def build_user_item_matrix():
    events = _load_rating_events(USER_MOVIE_RATINGS_PATH)
    aggregated = list(_aggregate_events(events).values())
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    if not aggregated:
        np.savez(
            MATRIX_PATH,
            matrix=np.zeros((0, 0), dtype=np.float32),
            user_ids=np.array([], dtype=str),
            movie_ids=np.array([], dtype=str),
        )
        _write_json(USER_INDEX_PATH, [])
        _write_json(MOVIE_INDEX_PATH, [])
        INTERACTION_SUMMARY_PATH.write_text("", encoding="utf-8")
        return {
            "users": 0,
            "movies": 0,
            "interactions": 0,
            "matrix_path": str(MATRIX_PATH),
        }

    for entry in aggregated:
        entry["preference_score"] = _score_interaction(entry)

    user_to_index, movie_to_index, user_index, movie_index = _build_indexes(aggregated)
    matrix = np.zeros((len(user_index), len(movie_index)), dtype=np.float32)

    for entry in aggregated:
        row_index = user_to_index[entry["user_id"]]
        col_index = movie_to_index[entry["movie_id"]]
        matrix[row_index, col_index] = float(entry["preference_score"])

    np.savez(
        MATRIX_PATH,
        matrix=matrix,
        user_ids=np.array([item["user_id"] for item in user_index], dtype=str),
        movie_ids=np.array([item["movie_id"] for item in movie_index], dtype=str),
    )
    _write_json(USER_INDEX_PATH, user_index)
    _write_json(MOVIE_INDEX_PATH, movie_index)
    _write_interaction_summary(INTERACTION_SUMMARY_PATH, aggregated)

    non_zero = int(np.count_nonzero(matrix))
    print(
        f"Built user-item matrix: users={matrix.shape[0]}, movies={matrix.shape[1]}, non_zero={non_zero}"
    )
    print(f"Saved matrix to {MATRIX_PATH}")
    return {
        "users": matrix.shape[0],
        "movies": matrix.shape[1],
        "interactions": non_zero,
        "matrix_path": str(MATRIX_PATH),
    }


if __name__ == "__main__":
    build_user_item_matrix()
