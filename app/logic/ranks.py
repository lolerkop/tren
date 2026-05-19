RANKS = [
    (1, "Novice"),
    (5, "Warrior"),
    (10, "Veteran"),
    (18, "Champion"),
]


def rank_for_level(level: int) -> str:
    rank = "Novice"
    for min_level, name in RANKS:
        if level >= min_level:
            rank = name
    return rank


def add_xp(level: int, xp: int, gained: int) -> tuple[int, int]:
    xp += gained
    while xp >= xp_to_next_level(level):
        xp -= xp_to_next_level(level)
        level += 1
    return level, xp


def xp_to_next_level(level: int) -> int:
    return 100 + level * 35
