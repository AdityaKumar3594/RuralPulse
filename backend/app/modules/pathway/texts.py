"""Localised wording for pathway steps. Stage names come from the interview question bank."""

from app.core.localize import FALLBACK_LANG
from app.modules.interview.questions import BY_ID

STEP_TEXT = {
    "tell_us_stage": {
        "en": "Tell us which class or course you are in, so we can plan the next steps",
        "ta": "நீங்கள் எந்த வகுப்பு அல்லது படிப்பில் இருக்கிறீர்கள் என்று சொல்லுங்கள்; அடுத்த படிகளைத் திட்டமிட",
    },
    "complete_stage": {
        "en": "Complete {stage} (this is the usual requirement for the routes below, not an official rule)",
        "ta": "{stage} முடிக்கவும் (கீழ்க்காணும் வழிகளுக்கு இது வழக்கமான தேவை; அதிகாரபூர்வ விதி அல்ல)",
    },
    "skills": {
        "en": "Build these skills (helpful, not required)",
        "ta": "இந்தத் திறன்களை வளர்த்துக்கொள்ளுங்கள் (உதவும், கட்டாயம் அல்ல)",
    },
}


def stage_label(stage: str, lang: str) -> str:
    for opt in BY_ID["q_education_stage"].options:
        if opt.value == stage:
            return opt.label.get(lang) or opt.label[FALLBACK_LANG]
    return stage


def step_title(code: str, lang: str, **fmt: str) -> str:
    text = STEP_TEXT[code].get(lang) or STEP_TEXT[code][FALLBACK_LANG]
    return text.format(**fmt)
