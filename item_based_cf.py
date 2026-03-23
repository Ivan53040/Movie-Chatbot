import argparse
import json
from pathlib import Path

import numpy as np

from build_user_item_matrix import (
    ARTIFACT_DIR,
    MATRIX_PATH,
    MOVIE_INDEX_PATH,
    USER_INDEX_PATH,
    build_user_item_matrix,
)


ITEM_SIMILARITY_PATH = ARTIFACT_DIR / "item_item_similarity.npz"


def _load_json(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_matrix_bundle():
    if not MATRIX_PATH.exists():
        build_user_item_matrix()

    if not MATRIX_PATH.exists():
        raise FileNotFoundError(f"Missing matrix artifact: {MATRIX_PATH}")

    bundle = np.load(MATRIX_PATH, allow_pickle=True)
    matrix = bundle["matrix"].astype(np.float32)
    user_index = _load_json(USER_INDEX_PATH)
    movie_index = _load_json(MOVIE_INDEX_PATH)
    return matrix, user_index, movie_index


def compute_item_similarity(matrix):
    if matrix.size == 0 or matrix.shape[1] == 0:
        return np.zeros((0, 0), dtype=np.float32)

    item_matrix = matrix.T.astype(np.float32)
    norms = np.linalg.norm(item_matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    normalized = item_matrix / norms
    similarity = normalized @ normalized.T
    np.fill_diagonal(similarity, 0.0)
    return similarity.astype(np.float32)


def load_or_build_item_similarity():
    matrix, user_index, movie_index = load_matrix_bundle()
    if ITEM_SIMILARITY_PATH.exists():
        similarity_bundle = np.load(ITEM_SIMILARITY_PATH, allow_pickle=True)
        similarity = similarity_bundle["similarity"].astype(np.float32)
        if similarity.shape[0] == matrix.shape[1]:
            return matrix, user_index, movie_index, similarity

    similarity = compute_item_similarity(matrix)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(ITEM_SIMILARITY_PATH, similarity=similarity)
    return matrix, user_index, movie_index, similarity


def _index_maps(user_index, movie_index):
    user_to_row = {item["user_id"]: int(item["index"]) for item in user_index}
    movie_to_col = {str(item["movie_id"]): int(item["index"]) for item in movie_index}
    col_to_movie = {int(item["index"]): item for item in movie_index}
    return user_to_row, movie_to_col, col_to_movie


def _active_profile(user_vector):
    strong_preferences = np.where(user_vector >= 0.5, user_vector, 0.0)
    if np.count_nonzero(strong_preferences) > 0:
        return strong_preferences
    return np.where(user_vector > 0.0, user_vector, 0.0)


def recommend_for_user(user_id, *, top_k=5):
    matrix, user_index, movie_index, similarity = load_or_build_item_similarity()
    user_to_row, _, col_to_movie = _index_maps(user_index, movie_index)

    if matrix.size == 0 or not user_index or not movie_index:
        return {
            "user_id": user_id,
            "recommendations": [],
            "reason": "No user-item data is available yet.",
        }

    if user_id not in user_to_row:
        return {
            "user_id": user_id,
            "recommendations": [],
            "reason": "Unknown user_id for the current matrix.",
        }

    user_vector = matrix[user_to_row[user_id]]
    active_profile = _active_profile(user_vector)
    if np.count_nonzero(active_profile) == 0:
        return {
            "user_id": user_id,
            "recommendations": [],
            "reason": "This user has no usable interaction history yet.",
        }

    scores = similarity @ active_profile
    seen_mask = user_vector > 0.0
    scores[seen_mask] = -1.0

    ranked_indices = np.argsort(scores)[::-1]
    recommendations = []
    for col_index in ranked_indices:
        score = float(scores[col_index])
        if score <= 0.0:
            continue
        movie = col_to_movie.get(int(col_index))
        if not movie:
            continue
        contributors = top_contributors_for_item(
            target_col=int(col_index),
            active_profile=active_profile,
            similarity=similarity,
            col_to_movie=col_to_movie,
        )
        recommendations.append(
            {
                "movie_id": movie["movie_id"],
                "movie_title": movie["movie_title"],
                "movie_year": movie.get("movie_year"),
                "cf_score": round(score, 4),
                "because_you_interacted_with": contributors,
            }
        )
        if len(recommendations) >= top_k:
            break

    return {
        "user_id": user_id,
        "recommendations": recommendations,
        "reason": "" if recommendations else "No unseen items received a positive CF score.",
    }


def top_contributors_for_item(*, target_col, active_profile, similarity, col_to_movie, top_n=3):
    contributions = similarity[target_col] * active_profile
    contributor_indices = np.argsort(contributions)[::-1]
    reasons = []
    for contributor_col in contributor_indices:
        contribution = float(contributions[contributor_col])
        if contribution <= 0.0:
            continue
        movie = col_to_movie.get(int(contributor_col))
        if not movie:
            continue
        reasons.append(
            {
                "movie_id": movie["movie_id"],
                "movie_title": movie["movie_title"],
                "movie_year": movie.get("movie_year"),
                "contribution": round(contribution, 4),
            }
        )
        if len(reasons) >= top_n:
            break
    return reasons


def known_user_ids(limit=10):
    _, user_index, _ = load_matrix_bundle()
    return [item["user_id"] for item in user_index[:limit]]


def score_movies_for_user(user_id, movies):
    matrix, user_index, movie_index, similarity = load_or_build_item_similarity()
    user_to_row, movie_to_col, col_to_movie = _index_maps(user_index, movie_index)

    if (
        not user_id
        or matrix.size == 0
        or not user_index
        or not movie_index
        or user_id not in user_to_row
    ):
        return {}

    user_vector = matrix[user_to_row[user_id]]
    active_profile = _active_profile(user_vector)
    if np.count_nonzero(active_profile) == 0:
        return {}

    scores = {}
    for movie in movies or []:
        movie_id = movie.get("id", movie.get("movie_id"))
        if movie_id is None:
            continue
        col_index = movie_to_col.get(str(movie_id))
        if col_index is None:
            continue
        cf_score = float(np.dot(similarity[col_index], active_profile))
        if cf_score <= 0.0:
            continue
        scores[str(movie_id)] = {
            "cf_score": round(cf_score, 4),
            "contributors": top_contributors_for_item(
                target_col=int(col_index),
                active_profile=active_profile,
                similarity=similarity,
                col_to_movie=col_to_movie,
            ),
        }
    return scores


def main():
    parser = argparse.ArgumentParser(description="Run item-based collaborative filtering on the user-item matrix.")
    parser.add_argument("--user-id", dest="user_id", default="", help="The anonymous user_id to score.")
    parser.add_argument("--top-k", dest="top_k", type=int, default=5, help="Number of recommendations to return.")
    parser.add_argument(
        "--list-users",
        dest="list_users",
        action="store_true",
        help="List known user_ids from the current matrix.",
    )
    args = parser.parse_args()

    if args.list_users:
        users = known_user_ids(limit=50)
        print(json.dumps({"users": users}, ensure_ascii=False, indent=2))
        return

    if not args.user_id:
        print(
            json.dumps(
                {
                    "error": "Missing --user-id",
                    "example": "python item_based_cf.py --list-users",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = recommend_for_user(args.user_id, top_k=max(1, int(args.top_k or 5)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
