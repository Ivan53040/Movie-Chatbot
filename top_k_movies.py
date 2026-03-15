DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 50
MAX_TOP_K = 20


def normalize_top_k(top_k):
    try:
        value = int(top_k)
    except (TypeError, ValueError):
        return DEFAULT_TOP_K

    if value < 1:
        return DEFAULT_TOP_K
    if value > MAX_TOP_K:
        return MAX_TOP_K
    return value


def candidate_k_for_top_k(top_k):
    normalized_top_k = normalize_top_k(top_k)
    return max(DEFAULT_CANDIDATE_K, normalized_top_k * 10)


def parse_more_command(user_input: str):
    text = str(user_input).strip().lower()
    if not text.startswith("more"):
        return None

    parts = text.split()
    if len(parts) == 1:
        return DEFAULT_TOP_K + 5
    if len(parts) == 2:
        return normalize_top_k(parts[1])
    return None
