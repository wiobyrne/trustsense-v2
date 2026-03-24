"""
TrustSense v2 — Prompt Test Script
Run this to iterate on the rubric prompt before building the UI.

Usage:
    python3 prompt_test.py
    python3 prompt_test.py "paste your own text here"
"""

import sys
import json
import ollama

MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are a trust and credibility analyst. Your job is to analyze text for signs of manipulation, deception, phishing, or misinformation.

Analyze the provided text and return ONLY a valid JSON object — no explanation, no markdown, no code fences. Just the raw JSON.

The JSON must have exactly this structure:
{
  "overall_score": <integer 0-100, where 100 = fully trustworthy, 0 = certain scam>,
  "verdict": <must match the score: score 70-100 = "likely trustworthy", score 40-69 = "suspicious", score 0-39 = "likely scam or misinformation">,
  "dimensions": {
    "source_credibility": <0-10, where 10 = clearly identifiable credible source, 0 = anonymous or fake>,
    "urgency_or_pressure": <0-10, where 10 = no urgency or pressure at all, 0 = extreme manufactured urgency>,
    "emotional_manipulation": <0-10, where 10 = neutral tone, 0 = extreme fear/greed/outrage exploitation>,
    "ai_generation_signals": <0-10, where 10 = natural human writing, 0 = clearly AI-generated or templated>,
    "requests_action_or_data": <0-10, where 10 = no requests for action or data, 0 = demands credentials/money/clicks>,
    "factual_consistency": <0-10, where 10 = internally consistent and plausible, 0 = contradictory or implausible>
  },
  "red_flags": [<list of specific phrases or patterns that concern you — empty list if none>],
  "summary": "<2-3 sentence plain English explanation of the score>"
}

CRITICAL RULES:
- overall_score and verdict MUST be consistent. Do not give a score of 8 and a verdict of "likely trustworthy".
- score 70-100 → verdict must be "likely trustworthy"
- score 40-69 → verdict must be "suspicious"
- score 0-39 → verdict must be "likely scam or misinformation"
- All dimension scores use the same direction: higher = safer, lower = more concerning.
"""

# Test samples — swap these out to test different content types
SAMPLES = {
    "phishing_email": """
    URGENT: Your account has been compromised. We detected suspicious login activity from an unknown device.
    You must verify your identity immediately or your account will be permanently suspended within 24 hours.
    Click here to confirm your details: http://secure-account-verify.net/login
    Failure to act will result in permanent loss of access and possible legal action.
    — Security Team, Your Bank
    """,

    "legitimate_email": """
    Hi Ian, just a reminder that our faculty meeting is scheduled for Thursday at 2pm in the main conference room.
    We'll be discussing the spring curriculum updates and the new assessment guidelines.
    Let me know if you have agenda items to add. See you then.
    — Sarah
    """,

    "suspicious_social_post": """
    DOCTORS WON'T TELL YOU THIS!!! Big Pharma is hiding the cure. This one weird trick cures everything.
    Share before they DELETE this post. Our sources are being silenced. Act NOW before it's too late!!!
    Link in bio to get the TRUTH they don't want you to see.
    """,
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

    # Strip markdown code fences if the model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def print_result(text: str, result: dict):
    score = result.get("overall_score", "?")
    verdict = result.get("verdict", "?")
    summary = result.get("summary", "")
    flags = result.get("red_flags", [])
    dims = result.get("dimensions", {})

    # Color coding in terminal
    if score >= 70:
        color = "\033[92m"  # green
    elif score >= 40:
        color = "\033[93m"  # yellow
    else:
        color = "\033[91m"  # red
    reset = "\033[0m"

    print("\n" + "=" * 60)
    print(f"TEXT (first 100 chars): {text.strip()[:100]}...")
    print("=" * 60)
    print(f"TRUST SCORE:  {color}{score}/100{reset}")
    print(f"VERDICT:      {color}{verdict.upper()}{reset}")
    print(f"\nSUMMARY:\n{summary}")
    print("\nDIMENSIONS:")
    for k, v in dims.items():
        bar = "█" * v + "░" * (10 - v)
        print(f"  {k:<30} {bar} {v}/10")
    if flags:
        print("\nRED FLAGS:")
        for f in flags:
            print(f"  ⚠  {f}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Custom text passed as argument
        text = " ".join(sys.argv[1:])
        print(f"\nAnalyzing custom text with {MODEL}...")
        try:
            result = analyze(text)
            print_result(text, result)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print("Raw response may not be valid JSON — try adjusting the prompt.")
    else:
        # Run all built-in samples
        print(f"\nRunning all samples with {MODEL}...\n")
        for name, text in SAMPLES.items():
            print(f"--- Sample: {name} ---")
            try:
                result = analyze(text)
                print_result(text, result)
            except json.JSONDecodeError as e:
                print(f"JSON parse error on '{name}': {e}\n")
