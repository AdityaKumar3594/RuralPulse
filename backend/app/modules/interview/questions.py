"""Versioned question bank. Question ids are stable: never reuse or repurpose one.

Each question writes to exactly one profile field. To add a language, add its key to every
`prompt`/`why`/option label; missing translations fall back to English at read time.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

QUESTION_BANK_VERSION = "2026-10-1"
FALLBACK_LANG = "en"

Text = Mapping[str, str]
Kind = Literal["single_choice", "list_text", "number", "short_text"]

_IN_EDUCATION = {
    "class_9",
    "class_10",
    "class_11",
    "class_12",
    "iti_or_diploma",
    "undergraduate",
    "graduate",
}


@dataclass(frozen=True)
class Option:
    value: str
    label: Text


@dataclass(frozen=True)
class Question:
    id: str
    field_key: str
    kind: Kind
    priority: int  # higher is asked earlier: how much the answer changes what we can recommend
    prompt: Text
    why: Text  # shown to the student: why we ask (data minimisation, transparency)
    options: tuple[Option, ...] = ()
    applies_when: Callable[[Mapping[str, Any]], bool] | None = None
    # Number questions: bounds shown to the UI (the profile field validator is authoritative).
    min_value: int | None = None
    max_value: int | None = None
    # Asked only when needed (e.g. by an eligibility check), never in the general interview.
    on_demand: bool = False
    # False for answers that decide eligibility: the LLM must not convert or guess them.
    allow_ai: bool = True
    llm_hint: str | None = None  # extraction instruction for the LLM, number questions


def localize(text: Text, lang: str) -> str:
    return text.get(lang) or text[FALLBACK_LANG]


def _stage_known(values: Mapping[str, Any]) -> bool:
    return values.get("education_stage") in _IN_EDUCATION


QUESTIONS: tuple[Question, ...] = (
    Question(
        id="q_education_stage",
        field_key="education_stage",
        kind="single_choice",
        priority=100,
        prompt={
            "en": "Which class or course are you in now?",
            "ta": "நீங்கள் இப்போது எந்த வகுப்பு அல்லது படிப்பில் இருக்கிறீர்கள்?",
        },
        why={
            "en": "So we only suggest courses and schemes that fit your level.",
            "ta": "உங்கள் நிலைக்குப் பொருத்தமான படிப்புகளையும் திட்டங்களையும் மட்டும் பரிந்துரைக்க.",
        },
        options=(
            Option("class_9", {"en": "Class 9", "ta": "9ஆம் வகுப்பு"}),
            Option("class_10", {"en": "Class 10", "ta": "10ஆம் வகுப்பு"}),
            Option("class_11", {"en": "Class 11", "ta": "11ஆம் வகுப்பு"}),
            Option("class_12", {"en": "Class 12", "ta": "12ஆம் வகுப்பு"}),
            Option("iti_or_diploma", {"en": "ITI or Diploma", "ta": "ஐ.டி.ஐ / டிப்ளமோ"}),
            Option("undergraduate", {"en": "Studying for a degree", "ta": "பட்டப் படிப்பு படிக்கிறேன்"}),
            Option("graduate", {"en": "Finished a degree", "ta": "பட்டம் முடித்துவிட்டேன்"}),
            Option(
                "not_in_school",
                {"en": "Not studying right now", "ta": "இப்போது படிக்கவில்லை"},
            ),
        ),
    ),
    Question(
        id="q_interests",
        field_key="interests",
        kind="list_text",
        priority=90,
        prompt={
            "en": "What do you enjoy doing, at school or in your free time? Tell us in your own words.",
            "ta": "பள்ளியிலோ ஓய்வு நேரத்திலோ நீங்கள் எதைச் செய்ய விரும்புகிறீர்கள்? உங்கள் சொந்த வார்த்தைகளில் சொல்லுங்கள்.",
        },
        why={
            "en": "Your interests help us show many kinds of work you may like.",
            "ta": "உங்கள் விருப்பங்கள் உங்களுக்குப் பிடிக்கக்கூடிய பல வகை வேலைகளைக் காட்ட உதவும்.",
        },
    ),
    Question(
        id="q_subject_preferences",
        field_key="subject_preferences",
        kind="list_text",
        priority=80,
        prompt={
            "en": "Which subjects or kinds of work do you like the most?",
            "ta": "எந்தப் பாடங்கள் அல்லது வேலைகள் உங்களுக்கு மிகவும் பிடிக்கும்?",
        },
        why={
            "en": "To match learning paths to what you enjoy.",
            "ta": "நீங்கள் விரும்புவதற்கு ஏற்ற கற்றல் பாதைகளைப் பொருத்த.",
        },
        applies_when=lambda v: v.get("education_stage") != "not_in_school",
    ),
    Question(
        id="q_goals",
        field_key="goals",
        kind="list_text",
        priority=70,
        prompt={
            "en": "Is there any work or study you would like to do in future? It is fine if you do not know yet.",
            "ta": "எதிர்காலத்தில் நீங்கள் செய்ய விரும்பும் வேலை அல்லது படிப்பு ஏதாவது உண்டா? இன்னும் தெரியவில்லை என்றாலும் பரவாயில்லை.",
        },
        why={
            "en": "You do not need to know job names. Say it in any way you like.",
            "ta": "வேலைகளின் பெயர்கள் தெரிய வேண்டியதில்லை. உங்களுக்குத் தெரிந்த விதத்தில் சொல்லுங்கள்.",
        },
    ),
    Question(
        id="q_skills",
        field_key="skills",
        kind="list_text",
        priority=60,
        prompt={
            "en": "What can you already do well? For example farming, stitching, fixing things, cooking, using a phone, helping others.",
            "ta": "நீங்கள் ஏற்கனவே எதை நன்றாகச் செய்வீர்கள்? எடுத்துக்காட்டு: விவசாயம், தையல், பழுது பார்த்தல், சமையல், கைபேசி பயன்படுத்துதல், பிறருக்கு உதவுதல்.",
        },
        why={
            "en": "Skills you already have are a good starting point for a learning path.",
            "ta": "உங்களிடம் உள்ள திறன்கள் கற்றல் பாதைக்கு நல்ல தொடக்கம்.",
        },
    ),
    Question(
        id="q_weekly_learning_hours",
        field_key="weekly_learning_hours",
        kind="number",
        priority=50,
        min_value=0,
        max_value=70,
        llm_hint=(
            "Extract the number of hours per WEEK. Convert if needed (e.g. 2 hours a day is 14). "
            "Set found=false if no amount of time is stated."
        ),
        prompt={
            "en": "About how many hours in a week can you spend on learning?",
            "ta": "ஒரு வாரத்தில் கற்றுக்கொள்ள உங்களுக்கு எத்தனை மணி நேரம் கிடைக்கும்?",
        },
        why={
            "en": "So the plan fits the time you really have.",
            "ta": "உங்களுக்கு உண்மையில் இருக்கும் நேரத்துக்கு ஏற்ற திட்டத்தை அமைக்க.",
        },
    ),
    Question(
        id="q_state",
        field_key="state",
        kind="short_text",
        priority=45,
        prompt={"en": "Which state do you live in?", "ta": "நீங்கள் எந்த மாநிலத்தில் வசிக்கிறீர்கள்?"},
        why={
            "en": "Many schemes and scholarships are only for some states.",
            "ta": "பல திட்டங்களும் உதவித்தொகைகளும் சில மாநிலங்களுக்கு மட்டுமே.",
        },
    ),
    Question(
        id="q_district",
        field_key="district",
        kind="short_text",
        priority=40,
        prompt={"en": "Which district do you live in?", "ta": "நீங்கள் எந்த மாவட்டத்தில் வசிக்கிறீர்கள்?"},
        why={
            "en": "To find training and opportunities near you.",
            "ta": "உங்களுக்கு அருகிலுள்ள பயிற்சிகளையும் வாய்ப்புகளையும் கண்டறிய.",
        },
    ),
    Question(
        id="q_connectivity",
        field_key="connectivity",
        kind="single_choice",
        priority=30,
        prompt={
            "en": "How is the internet where you study?",
            "ta": "நீங்கள் படிக்கும் இடத்தில் இணைய இணைப்பு எப்படி உள்ளது?",
        },
        why={
            "en": "So we suggest lessons that work on your connection.",
            "ta": "உங்கள் இணைப்பில் வேலை செய்யும் பாடங்களைப் பரிந்துரைக்க.",
        },
        options=(
            Option("good", {"en": "Good", "ta": "நன்றாக உள்ளது"}),
            Option("patchy", {"en": "Comes and goes", "ta": "சில நேரம் மட்டும் கிடைக்கும்"}),
            Option("poor", {"en": "Very poor", "ta": "மிகவும் மோசம்"}),
        ),
    ),
    Question(
        id="q_device_type",
        field_key="device_type",
        kind="single_choice",
        priority=30,
        prompt={
            "en": "Which phone or device do you use?",
            "ta": "எந்தக் கைபேசி அல்லது சாதனத்தைப் பயன்படுத்துகிறீர்கள்?",
        },
        why={
            "en": "So lessons work on your device.",
            "ta": "உங்கள் சாதனத்தில் பாடங்கள் வேலை செய்ய.",
        },
        options=(
            Option("basic_phone", {"en": "Button phone", "ta": "பொத்தான் கைபேசி"}),
            Option("smartphone", {"en": "Smartphone", "ta": "ஸ்மார்ட்போன்"}),
            Option(
                "shared_device",
                {"en": "A device shared at home", "ta": "வீட்டில் பகிர்ந்து பயன்படுத்தும் சாதனம்"},
            ),
            Option("computer", {"en": "Computer", "ta": "கணினி"}),
        ),
    ),
    Question(
        id="q_subjects_studied",
        field_key="subjects_studied",
        kind="list_text",
        priority=20,
        prompt={
            "en": "Which subjects do you study?",
            "ta": "நீங்கள் எந்தப் பாடங்களைப் படிக்கிறீர்கள்?",
        },
        why={
            "en": "Some courses need certain subjects.",
            "ta": "சில படிப்புகளுக்குக் குறிப்பிட்ட பாடங்கள் தேவை.",
        },
        applies_when=_stage_known,
    ),
)

QUESTIONS = QUESTIONS + (
    Question(
        id="q_annual_family_income",
        field_key="annual_family_income_inr",
        kind="number",
        priority=0,
        on_demand=True,
        allow_ai=False,
        min_value=0,
        max_value=100_000_000,
        prompt={
            "en": "What is your family's total income in one year, in rupees? Add up what your parents or guardians earn.",
            "ta": "உங்கள் குடும்பத்தின் ஒரு வருட மொத்த வருமானம் எவ்வளவு (ரூபாயில்)? பெற்றோர் அல்லது பாதுகாவலர்கள் சம்பாதிப்பதைக் கூட்டிச் சொல்லுங்கள்.",
        },
        why={
            "en": "Some scholarships have an income limit. We ask this only when you check one, and you can say you do not know.",
            "ta": "சில உதவித்தொகைகளுக்கு வருமான வரம்பு உண்டு. நீங்கள் ஒன்றைப் பார்க்கும்போது மட்டுமே இதைக் கேட்கிறோம்; தெரியவில்லை என்றும் சொல்லலாம்.",
        },
    ),
)

BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}

MESSAGES: dict[str, Text] = {
    "clarify_choice": {
        "en": "I could not tell which option you mean. Please choose one.",
        "ta": "நீங்கள் எந்த விருப்பத்தைக் குறிப்பிடுகிறீர்கள் என்று புரியவில்லை. ஒன்றைத் தேர்ந்தெடுக்கவும்.",
    },
    "clarify_text": {
        "en": "I did not understand that. Could you say it in a different way?",
        "ta": "இது எனக்குப் புரியவில்லை. வேறு விதமாகச் சொல்ல முடியுமா?",
    },
    "moving_on": {
        "en": "That is okay. We can come back to this later.",
        "ta": "பரவாயில்லை. இதைப் பிறகு பார்க்கலாம்.",
    },
}
