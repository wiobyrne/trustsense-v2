"""
TrustSense v2 — Streamlit App
Run with: streamlit run app.py
"""

import json
import streamlit as st
import ollama

MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are helping everyday people — not tech experts — figure out if a message, email, or post is trying to trick or deceive them.

Write everything as if you're explaining to a family member who isn't good with technology. Use simple, clear words. No jargon.

Analyze the provided text and return ONLY a valid JSON object — no explanation, no markdown, no code fences. Just the raw JSON.

The JSON must have exactly this structure:
{
  "overall_score": <integer 0-100, where 100 = completely safe, 0 = definite scam>,
  "verdict": <must match the score: score 70-100 = "looks safe", score 40-69 = "something feels off", score 0-39 = "this looks like a scam">,
  "dimensions": {
    "source_credibility": <0-10, where 10 = clearly from a real, known person or organization, 0 = anonymous or fake>,
    "urgency_or_pressure": <0-10, where 10 = no pressure at all, 0 = extreme pressure to act immediately>,
    "emotional_manipulation": <0-10, where 10 = calm and neutral, 0 = uses fear, panic, or greed to force a reaction>,
    "ai_generation_signals": <0-10, where 10 = sounds like a real person wrote it, 0 = sounds robotic or copy-pasted>,
    "requests_action_or_data": <0-10, where 10 = asks for nothing personal, 0 = demands passwords, money, or personal info>,
    "factual_consistency": <0-10, where 10 = everything makes sense and adds up, 0 = full of contradictions or impossible claims>
  },
  "red_flags": [<plain English description of each warning sign — write it like you're pointing it out to a friend. Empty list if none.>],
  "what_to_do": "<One or two plain sentences telling the reader exactly what they should do. E.g. 'Do not click any links. Delete this email.' or 'This looks fine — no action needed.'>",
  "summary": "<2-3 sentences explaining why this got the score it did. Write like you're talking to someone who isn't tech-savvy. No jargon.>"
}

CRITICAL RULES:
- overall_score and verdict MUST be consistent.
- score 70-100 → verdict must be "looks safe"
- score 40-69 → verdict must be "something feels off"
- score 0-39 → verdict must be "this looks like a scam"
- All dimension scores use the same direction: higher = safer, lower = more concerning.
- Never use technical terms like 'phishing', 'AI-generated', or 'malicious' in summaries or red flags. Say 'scam email', 'sounds robotic', 'trying to trick you' instead.
"""

DIMENSION_LABELS = {
    "source_credibility": "Do we know who sent this?",
    "urgency_or_pressure": "Is it pressuring you to act fast?",
    "emotional_manipulation": "Is it trying to scare or excite you?",
    "ai_generation_signals": "Does it sound like a real person?",
    "requests_action_or_data": "Is it asking for personal info or money?",
    "factual_consistency": "Does the story add up?",
}

EXAMPLES = {
    "Phishing email": "URGENT: Your account has been compromised. We detected suspicious login activity from an unknown device. You must verify your identity immediately or your account will be permanently suspended within 24 hours. Click here to confirm your details: http://secure-account-verify.net/login. Failure to act will result in permanent loss of access and possible legal action. — Security Team, Your Bank",
    "Legitimate email": "Hi Ian, just a reminder that our faculty meeting is scheduled for Thursday at 2pm in the main conference room. We'll be discussing the spring curriculum updates and the new assessment guidelines. Let me know if you have agenda items to add. See you then. — Sarah",
    "Suspicious social post": "DOCTORS WON'T TELL YOU THIS!!! Big Pharma is hiding the cure. This one weird trick cures everything. Share before they DELETE this post. Our sources are being silenced. Act NOW before it's too late!!! Link in bio to get the TRUTH they don't want you to see.",
}

VERDICT_STYLE = {
    "looks safe": ("green", "✅"),
    "something feels off": ("orange", "⚠️"),
    "this looks like a scam": ("red", "🚨"),
}


def analyze(text: str) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this text:\n\n{text}"},
        ],
    )
    raw = response["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def score_emoji(score: int) -> str:
    if score >= 70:
        return "🟢"
    elif score >= 40:
        return "🟡"
    return "🔴"


# --- Page config ---
st.set_page_config(page_title="TrustSense", page_icon="🔍", layout="centered")

st.title("🔍 TrustSense")
st.markdown("**Not sure if a message is trying to trick you?** Paste it below and get a straight answer.")
st.caption("⚠️ This tool detects deception and manipulation — not spam. An unwanted but honest email may still score high.")

# --- Example loader ---
with st.expander("Try an example"):
    for label, text in EXAMPLES.items():
        if st.button(label):
            st.session_state["input_text"] = text

# --- Input ---
input_text = st.text_area(
    "Paste the message here",
    value=st.session_state.get("input_text", ""),
    height=200,
    placeholder="Paste an email, text message, social media post, or news article...",
)

analyze_btn = st.button("Check this message", type="primary", disabled=not input_text.strip())

# --- Analysis ---
if analyze_btn and input_text.strip():
    with st.spinner("Reading the message..."):
        try:
            result = analyze(input_text)

            score = result.get("overall_score", 0)
            verdict = result.get("verdict", "something feels off").lower()
            summary = result.get("summary", "")
            what_to_do = result.get("what_to_do", "")
            flags = result.get("red_flags", [])
            dims = result.get("dimensions", {})

            color, icon = VERDICT_STYLE.get(verdict, ("orange", "⚠️"))

            st.divider()

            # Verdict banner
            if verdict == "looks safe":
                st.success(f"{icon} **{verdict.upper()}** — Trust Score: {score}/100")
            elif verdict == "something feels off":
                st.warning(f"{icon} **{verdict.upper()}** — Trust Score: {score}/100")
            else:
                st.error(f"{icon} **{verdict.upper()}** — Trust Score: {score}/100")

            # What to do — most important, shown first
            if what_to_do:
                st.markdown(f"### What should you do?\n{what_to_do}")

            # Summary
            st.markdown(f"**Why this score?** {summary}")

            st.divider()

            # Dimensions — plain language
            st.markdown("### How we looked at it")
            for key, label in DIMENSION_LABELS.items():
                val = dims.get(key, 0)
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"**{label}**")
                    st.progress(val / 10)
                with col_b:
                    st.markdown(f"<br><span style='font-size:1.1em'>{val}/10</span>", unsafe_allow_html=True)

            # Red flags
            if flags:
                st.divider()
                st.markdown("### Warning signs we spotted")
                for flag in flags:
                    st.warning(f"⚠️ {flag}")
            else:
                st.divider()
                st.success("✅ No warning signs found.")

        except json.JSONDecodeError:
            st.error("Something went wrong reading the response. Try again.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Footer ---
st.divider()
st.caption("Your text never leaves your computer — this runs entirely on your device.")
