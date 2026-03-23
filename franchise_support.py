FRANCHISE_RULES = {
    "dc": {
        "aliases": ["dc", "dceu", "dcu", "dc universe", "dc extended universe"],
        "keyword": "dc extended universe",
        "semantic": "dc universe superhero movie",
        "title_terms": ["batman", "superman", "wonder woman", "justice league", "aquaman"],
        "keyword_terms": ["dc universe", "dc extended universe", "dc elseworlds", "based on comic"],
    },
    "marvel": {
        "aliases": ["marvel", "mcu", "marvel cinematic universe"],
        "keyword": "marvel cinematic universe",
        "semantic": "marvel cinematic universe superhero movie",
        "title_terms": ["avengers", "iron man", "captain america", "deadpool", "spider-man", "fantastic 4"],
        "keyword_terms": ["marvel cinematic universe", "mcu", "based on comic"],
    },
    "star wars": {
        "aliases": ["star wars", "starwars"],
        "keyword": "star wars",
        "semantic": "star wars space opera movie",
        "title_terms": ["star wars"],
        "keyword_terms": ["star wars", "jedi", "space opera", "rebellion"],
    },
    "harry potter": {
        "aliases": ["harry potter"],
        "keyword": None,
        "semantic": "harry potter wizard fantasy movie",
        "title_terms": ["harry potter"],
        "keyword_terms": [],
    },
    "lord of the rings": {
        "aliases": ["lord of the rings", "the lord of the rings", "lotr"],
        "keyword": None,
        "semantic": "lord of the rings epic fantasy adventure movie",
        "title_terms": ["lord of the rings"],
        "keyword_terms": [],
    },
    "the hobbit": {
        "aliases": ["the hobbit", "hobbit"],
        "keyword": None,
        "semantic": "the hobbit fantasy adventure movie",
        "title_terms": ["the hobbit"],
        "keyword_terms": [],
    },
    "pirates of the caribbean": {
        "aliases": ["pirates of the caribbean"],
        "keyword": None,
        "semantic": "pirates of the caribbean swashbuckling fantasy adventure movie",
        "title_terms": ["pirates of the caribbean"],
        "keyword_terms": [],
    },
    "jurassic world": {
        "aliases": ["jurassic world", "jurassic"],
        "keyword": None,
        "semantic": "jurassic world dinosaur adventure movie",
        "title_terms": ["jurassic world"],
        "keyword_terms": [],
    },
    "back to the future": {
        "aliases": ["back to the future"],
        "keyword": None,
        "semantic": "back to the future time travel adventure movie",
        "title_terms": ["back to the future"],
        "keyword_terms": [],
    },
    "spider-man": {
        "aliases": ["spider-man", "spiderman", "spider verse", "spider-verse"],
        "keyword": None,
        "semantic": "spider-man superhero movie",
        "title_terms": ["spider-man", "spider verse", "spider-verse", "amazing spider-man"],
        "keyword_terms": [],
    },
    "avengers": {
        "aliases": ["avengers"],
        "keyword": None,
        "semantic": "avengers superhero team movie",
        "title_terms": ["avengers"],
        "keyword_terms": [],
    },
    "iron man": {
        "aliases": ["iron man"],
        "keyword": None,
        "semantic": "iron man marvel superhero movie",
        "title_terms": ["iron man"],
        "keyword_terms": [],
    },
    "deadpool": {
        "aliases": ["deadpool"],
        "keyword": None,
        "semantic": "deadpool anti hero superhero movie",
        "title_terms": ["deadpool"],
        "keyword_terms": [],
    },
    "captain america": {
        "aliases": ["captain america"],
        "keyword": None,
        "semantic": "captain america marvel superhero movie",
        "title_terms": ["captain america"],
        "keyword_terms": [],
    },
    "avatar": {
        "aliases": ["avatar"],
        "keyword": None,
        "semantic": "avatar science fiction epic adventure movie",
        "title_terms": ["avatar"],
        "keyword_terms": [],
    },
    "toy story": {
        "aliases": ["toy story"],
        "keyword": None,
        "semantic": "toy story animated family movie",
        "title_terms": ["toy story"],
        "keyword_terms": [],
    },
    "shrek": {
        "aliases": ["shrek"],
        "keyword": None,
        "semantic": "shrek animated fantasy comedy movie",
        "title_terms": ["shrek"],
        "keyword_terms": [],
    },
    "children of the corn": {
        "aliases": ["children of the corn"],
        "keyword": None,
        "semantic": "children of the corn horror movie",
        "title_terms": ["children of the corn"],
        "keyword_terms": [],
    },
    "scream": {
        "aliases": ["scream"],
        "keyword": None,
        "semantic": "scream slasher horror movie",
        "title_terms": ["scream"],
        "keyword_terms": [],
    },
    "kill bill": {
        "aliases": ["kill bill"],
        "keyword": None,
        "semantic": "kill bill revenge action movie",
        "title_terms": ["kill bill"],
        "keyword_terms": [],
    },
    "the chronicles of narnia": {
        "aliases": ["chronicles of narnia", "the chronicles of narnia", "narnia"],
        "keyword": None,
        "semantic": "chronicles of narnia fantasy adventure movie",
        "title_terms": ["chronicles of narnia", "narnia"],
        "keyword_terms": [],
    },
    "the conjuring": {
        "aliases": ["the conjuring", "conjuring"],
        "keyword": None,
        "semantic": "the conjuring supernatural horror movie",
        "title_terms": ["the conjuring"],
        "keyword_terms": [],
    },
    "mission: impossible": {
        "aliases": ["mission impossible", "mission: impossible"],
        "keyword": None,
        "semantic": "mission impossible spy action movie",
        "title_terms": ["mission: impossible", "mission impossible"],
        "keyword_terms": [],
    },
    "james bond": {
        "aliases": ["james bond", "bond 007", "007"],
        "keyword": None,
        "semantic": "james bond spy action movie",
        "title_terms": [],
        "keyword_terms": ["james bond"],
    },
    "fast & furious": {
        "aliases": ["fast & furious", "fast and furious", "fast furious"],
        "keyword": None,
        "semantic": "fast and furious street racing action movie",
        "title_terms": ["fast x", "fast furious"],
        "keyword_terms": [],
    },
}


def iter_franchise_aliases():
    for franchise, rule in FRANCHISE_RULES.items():
        for alias in rule.get("aliases", []):
            yield alias, franchise


def detect_franchise_from_text(text):
    lowered = str(text or "").lower()
    best_match = None
    for alias, franchise in iter_franchise_aliases():
        if alias in lowered:
            if best_match is None or len(alias) > len(best_match[0]):
                best_match = (alias, franchise)
    return best_match[1] if best_match else None


def get_franchise_rule(franchise):
    return FRANCHISE_RULES.get(str(franchise or "").strip().lower())


def franchise_keyword(franchise):
    rule = get_franchise_rule(franchise)
    return rule.get("keyword") if rule else None


def franchise_semantic_query(franchise):
    rule = get_franchise_rule(franchise)
    return rule.get("semantic") if rule else None


def normalize_franchise_from_value(value):
    lowered = str(value or "").strip().lower()
    if not lowered:
        return None
    for alias, franchise in iter_franchise_aliases():
        if lowered == alias:
            return franchise
    return None


def movie_matches_franchise(movie, franchise):
    rule = get_franchise_rule(franchise)
    if not rule:
        return False

    title_text = str(movie.get("title", "")).strip().lower()
    keyword_text = " ".join(str(item).strip().lower() for item in movie.get("keywords", []) if str(item).strip())
    combined = f"{title_text} {keyword_text}"

    for term in rule.get("title_terms", []):
        if term in title_text:
            return True
    for term in rule.get("keyword_terms", []):
        if term in combined:
            return True
    return False
