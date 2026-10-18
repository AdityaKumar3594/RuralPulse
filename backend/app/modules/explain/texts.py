"""Deterministic wording (English / Tamil) used when the AI is unavailable or its output is
rejected. Every concrete value comes from the evidence; nothing here is invented."""

from app.core.localize import FALLBACK_LANG

T: dict[str, dict[str, str]] = {
    # --- recommendation
    "level_strong": {"en": "strong", "ta": "வலுவான"},
    "level_moderate": {"en": "moderate", "ta": "நடுத்தர"},
    "level_weak": {"en": "weak", "ta": "சிறிய"},
    "rec_headline_match": {
        "en": "{title}: a {level} match with what you told us",
        "ta": "{title}: நீங்கள் சொன்னதுடன் {level} பொருத்தம்",
    },
    "rec_headline_explore": {
        "en": "{title}: something different to explore",
        "ta": "{title}: புதிதாக ஆராய்ந்து பார்க்க ஒன்று",
    },
    "rec_why_term": {
        "en": 'You told us "{term}", and this career lists "{matched}".',
        "ta": 'நீங்கள் "{term}" என்று சொன்னீர்கள்; இந்தத் தொழிலில் "{matched}" உள்ளது.',
    },
    "rec_why_explore": {
        "en": "This is from an area you did not mention. We show it to widen your options, not because it matches you.",
        "ta": "இது நீங்கள் குறிப்பிடாத துறை. உங்களுக்குப் பொருந்துகிறது என்பதற்காக அல்ல, உங்கள் தேர்வுகளை விரிவுபடுத்தவே காட்டுகிறோம்.",
    },
    "rec_req_stage": {
        "en": "Usually needs {stage} (a typical route, not an official rule).",
        "ta": "பொதுவாக {stage} தேவை (வழக்கமான வழி; அதிகாரபூர்வ விதி அல்ல).",
    },
    "rec_req_below": {
        "en": "You are in {stage}, so this would come later.",
        "ta": "நீங்கள் {stage} படிக்கிறீர்கள், எனவே இது பின்னர் வரும்.",
    },
    "rec_req_none": {
        "en": "No fixed qualification is usually needed (it varies).",
        "ta": "பொதுவாக குறிப்பிட்ட படிப்பு தேவையில்லை (இடத்துக்கு இடம் மாறும்).",
    },
    "rec_caveat_catalog": {
        "en": "This career entry is a draft that nobody has checked against an official source yet.",
        "ta": "இந்தத் தொழில் விவரம் ஒரு வரைவு; அதிகாரபூர்வ ஆதாரத்துடன் இன்னும் யாரும் சரிபார்க்கவில்லை.",
    },
    "rec_caveat_checked": {
        "en": "This career entry has been checked against an official source.",
        "ta": "இந்தத் தொழில் விவரம் அதிகாரபூர்வ ஆதாரத்துடன் சரிபார்க்கப்பட்டது.",
    },
    "career_cost_unknown": {
        "en": "We do not have cost information.",
        "ta": "செலவு பற்றிய தகவல் எங்களிடம் இல்லை.",
    },
    "career_time_needed_unknown": {
        "en": "We do not know how long it takes.",
        "ta": "எவ்வளவு காலம் ஆகும் என்று தெரியவில்லை.",
    },
    "career_location_not_considered": {
        "en": "We did not consider where you live.",
        "ta": "நீங்கள் வசிக்கும் இடத்தை நாங்கள் கணக்கில் கொள்ளவில்லை.",
    },
    "student_skills_not_told": {
        "en": "Tell us your skills for better suggestions.",
        "ta": "சிறந்த பரிந்துரைகளுக்கு உங்கள் திறன்களைச் சொல்லுங்கள்.",
    },
    "student_interests_not_told": {
        "en": "Tell us what you enjoy for better suggestions.",
        "ta": "சிறந்த பரிந்துரைகளுக்கு உங்கள் விருப்பங்களைச் சொல்லுங்கள்.",
    },
    "next_view_career": {
        "en": "Read about this career and its routes.",
        "ta": "இந்தத் தொழிலையும் அதன் வழிகளையும் படியுங்கள்.",
    },
    "next_plan_prerequisite": {
        "en": "Plan how to reach {stage} first.",
        "ta": "முதலில் {stage} அடைய திட்டமிடுங்கள்.",
    },
    "next_tell_stage": {
        "en": "Tell us which class you are in.",
        "ta": "நீங்கள் எந்த வகுப்பில் இருக்கிறீர்கள் என்று சொல்லுங்கள்.",
    },
    # --- eligibility
    "elig_headline_ELIGIBLE": {
        "en": "Based on what you told us, you meet the rules we could check for {title}.",
        "ta": "நீங்கள் சொன்னதன் அடிப்படையில், {title}-க்கு நாங்கள் சரிபார்க்கக்கூடிய விதிகளை நீங்கள் பூர்த்தி செய்கிறீர்கள்.",
    },
    "elig_headline_INELIGIBLE": {
        "en": "Based on what you told us, you do not meet the rules for {title}.",
        "ta": "நீங்கள் சொன்னதன் அடிப்படையில், {title}-க்கான விதிகளை நீங்கள் பூர்த்தி செய்யவில்லை.",
    },
    "elig_headline_UNKNOWN": {
        "en": "We cannot tell yet whether {title} is open to you.",
        "ta": "{title} உங்களுக்குப் பொருந்துமா என்று இன்னும் சொல்ல முடியவில்லை.",
    },
    "elig_headline_NEEDS_REVIEW": {
        "en": "A person needs to check {title} with you.",
        "ta": "{title}-ஐ உங்களுடன் ஒரு நபர் சரிபார்க்க வேண்டும்.",
    },
    "why_all_met": {
        "en": "Every rule we could check matches what you told us.",
        "ta": "நாங்கள் சரிபார்க்கக்கூடிய ஒவ்வொரு விதியும் நீங்கள் சொன்னதுடன் பொருந்துகிறது.",
    },
    "family_income_above_limit": {
        "en": "The family income limit is {expected} rupees a year; you told us {actual}.",
        "ta": "குடும்ப வருமான வரம்பு ஆண்டுக்கு ரூ. {expected}; நீங்கள் ரூ. {actual} என்று சொன்னீர்கள்.",
    },
    "education_stage_not_met": {
        "en": "This is for a different class or course than the one you told us.",
        "ta": "இது நீங்கள் சொன்ன வகுப்பு அல்லது படிப்பிலிருந்து வேறுபட்டவர்களுக்கானது.",
    },
    "age_below_minimum": {
        "en": "Your age is below the minimum of {limit} years.",
        "ta": "உங்கள் வயது குறைந்தபட்சமான {limit} ஆண்டுகளுக்குக் கீழ் உள்ளது.",
    },
    "age_above_maximum": {
        "en": "Your age is above the maximum of {limit} years.",
        "ta": "உங்கள் வயது அதிகபட்சமான {limit} ஆண்டுகளைவிட அதிகம்.",
    },
    "state_not_covered": {
        "en": "This is only for people in {states}.",
        "ta": "இது {states} பகுதியினருக்கு மட்டும்.",
    },
    "deadline_passed": {
        "en": "The application deadline has passed.",
        "ta": "விண்ணப்பிக்கும் கடைசி தேதி முடிந்துவிட்டது.",
    },
    "expired": {"en": "This opportunity has expired.", "ta": "இந்த வாய்ப்பு காலாவதியாகிவிட்டது."},
    "missing_some": {
        "en": "We are missing some facts, listed below.",
        "ta": "சில தகவல்கள் எங்களிடம் இல்லை; கீழே உள்ளன.",
    },
    "conflicting": {
        "en": "What you told us and what was recorded by others do not match.",
        "ta": "நீங்கள் சொன்னதும் மற்றவர்கள் பதிவு செய்ததும் ஒத்துப்போகவில்லை.",
    },
    "other_criteria_need_review": {
        "en": "The scheme has other conditions we cannot check: {conditions}",
        "ta": "இந்தத் திட்டத்துக்கு நாங்கள் சரிபார்க்க முடியாத வேறு நிபந்தனைகள் உள்ளன: {conditions}",
    },
    "record_stale": {
        "en": "This information is old and may have changed.",
        "ta": "இந்தத் தகவல் பழையது; மாறியிருக்கலாம்.",
    },
    "no_verified_criteria": {
        "en": "We have no checked eligibility rules for this one.",
        "ta": "இதற்குச் சரிபார்க்கப்பட்ட தகுதி விதிகள் எங்களிடம் இல்லை.",
    },
    "req_documents": {
        "en": "Documents usually checked: {docs}.",
        "ta": "பொதுவாகச் சரிபார்க்கப்படும் ஆவணங்கள்: {docs}.",
    },
    "req_benefit": {"en": "Benefit: {text}", "ta": "பயன்: {text}"},
    "req_deadline": {"en": "Deadline: {date}.", "ta": "கடைசி தேதி: {date}."},
    "fresh_fresh": {
        "en": "Last checked on {date} against the official page; it can still change.",
        "ta": "{date} அன்று அதிகாரபூர்வ பக்கத்துடன் சரிபார்க்கப்பட்டது; இன்னும் மாறலாம்.",
    },
    "fresh_stale": {
        "en": "This was last checked on {date}, which was a while ago. Check the official page.",
        "ta": "இது கடைசியாக {date} அன்று சரிபார்க்கப்பட்டது; அது சற்று பழையது. அதிகாரபூர்வ பக்கத்தைப் பாருங்கள்.",
    },
    "fresh_unverified": {
        "en": "This information has not been checked against an official page.",
        "ta": "இந்தத் தகவல் அதிகாரபூர்வ பக்கத்துடன் சரிபார்க்கப்படவில்லை.",
    },
    "fresh_expired": {"en": "This record has expired.", "ta": "இந்தப் பதிவு காலாவதியாகிவிட்டது."},
    "not_human_reviewed": {
        "en": " Nobody has re-checked it by hand yet.",
        "ta": " இதை இன்னும் யாரும் கையால் மீண்டும் சரிபார்க்கவில்லை.",
    },
    "fact_education_stage": {
        "en": "Which class or course you are in",
        "ta": "நீங்கள் எந்த வகுப்பு அல்லது படிப்பில் இருக்கிறீர்கள்",
    },
    "fact_annual_family_income_inr": {
        "en": "Your family's income in a year",
        "ta": "உங்கள் குடும்பத்தின் ஒரு வருட வருமானம்",
    },
    "fact_state": {"en": "Which state you live in", "ta": "நீங்கள் வசிக்கும் மாநிலம்"},
    "fact_date_of_birth": {"en": "Your date of birth", "ta": "உங்கள் பிறந்த தேதி"},
    "next_ELIGIBLE": {
        "en": "Open the official page and check how to apply: {url}",
        "ta": "அதிகாரபூர்வ பக்கத்தைத் திறந்து விண்ணப்பிக்கும் முறையைப் பாருங்கள்: {url}",
    },
    "next_INELIGIBLE": {
        "en": "Look for other options in your pathway.",
        "ta": "உங்கள் பாதையில் உள்ள மற்ற வாய்ப்புகளைப் பாருங்கள்.",
    },
    "next_UNKNOWN_missing": {
        "en": "Answer the questions listed above so we can check again.",
        "ta": "மேலே உள்ள கேள்விகளுக்குப் பதில் சொல்லுங்கள்; நாங்கள் மீண்டும் சரிபார்க்கிறோம்.",
    },
    "next_UNKNOWN": {
        "en": "Check the official page: {url}",
        "ta": "அதிகாரபூர்வ பக்கத்தைப் பாருங்கள்: {url}",
    },
    "next_NEEDS_REVIEW": {
        "en": "Ask a teacher or facilitator to check the other conditions with you, then look at the official page: {url}",
        "ta": "ஆசிரியர் அல்லது உதவியாளரிடம் மற்ற நிபந்தனைகளைச் சரிபார்க்கச் சொல்லுங்கள்; பிறகு அதிகாரபூர்வ பக்கத்தைப் பாருங்கள்: {url}",
    },
    # --- pathway
    "path_headline": {"en": "Your steps towards {title}", "ta": "{title} நோக்கிய உங்கள் படிகள்"},
    "path_why": {
        "en": "These steps come from the usual routes listed for this career. They are not official rules.",
        "ta": "இந்தப் படிகள் இந்தத் தொழிலுக்குப் பட்டியலிடப்பட்ட வழக்கமான வழிகளிலிருந்து வந்தவை; அதிகாரபூர்வ விதிகள் அல்ல.",
    },
    "path_alternatives": {
        "en": "The routes are alternatives: you need only one of them.",
        "ta": "இந்த வழிகள் மாற்று வழிகள்; அவற்றில் ஒன்று மட்டும் போதும்.",
    },
    "path_unknown_effort": {
        "en": "We do not know how long each step takes or what it costs.",
        "ta": "ஒவ்வொரு படிக்கும் எவ்வளவு காலம், எவ்வளவு செலவு ஆகும் என்று தெரியவில்லை.",
    },
    "path_next": {"en": "Next step: {step}", "ta": "அடுத்த படி: {step}"},
    "path_all_done": {
        "en": "You have finished every step listed.",
        "ta": "பட்டியலிடப்பட்ட எல்லாப் படிகளையும் முடித்துவிட்டீர்கள்.",
    },
}


def tr(key: str, lang: str, **fmt: object) -> str:
    entry = T[key]
    return (entry.get(lang) or entry[FALLBACK_LANG]).format(**fmt)
