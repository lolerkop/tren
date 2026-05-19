EXERCISE_LABELS = {
    "pushups": "Отжимания",
    "pullups": "Подтягивания",
    "dips": "Брусья",
    "squats": "Приседания",
    "dumbbell_rows": "Тяга гантелей 5 кг",
    "dumbbell_curls": "Подъем гантелей 5 кг на бицепс",
    "dumbbell_squats": "Приседания с гантелями 5 кг",
}

EXERCISE_GROUPS = {
    "chest": {
        "label": "Грудь",
        "icon": "🛡",
        "exercises": ["pushups", "dips"],
    },
    "back": {
        "label": "Спина",
        "icon": "🏹",
        "exercises": ["pullups", "dumbbell_rows"],
    },
    "arms": {
        "label": "Руки",
        "icon": "💪",
        "exercises": ["dumbbell_curls"],
    },
    "legs": {
        "label": "Ноги",
        "icon": "🦵",
        "exercises": ["squats", "dumbbell_squats"],
    },
}

DEFAULT_ENABLED_EXERCISES = set(EXERCISE_LABELS)

BASELINE_FIELD_BY_EXERCISE = {
    "pushups": "baseline_pushups",
    "pullups": "baseline_pullups",
    "dips": "baseline_dips",
    "squats": "baseline_squats",
}

STRENGTH_EXERCISES = {
    "pushups",
    "pullups",
    "dips",
    "dumbbell_rows",
    "dumbbell_curls",
}
