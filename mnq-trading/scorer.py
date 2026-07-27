"""Trade scoring — grade every trade against the plan BEFORE entry.

Usage:
    python3 scorer.py            # interactive checklist
or import score_trade() and pass a dict of answers.

The grade maps to permission to take the trade:
    A+  take it at full planned size
    A   take it at full planned size
    B   half size, or skip if you're down on the day
    C   DO NOT TAKE — journal it as a skipped C setup

The single biggest driver of expectancy for discretionary traders is cutting
C trades. Grading before entry is the mechanism.
"""

from __future__ import annotations

CHECKLIST = [
    # (key, question, weight)
    ("htf_trend", "Trading WITH the 15m/1h trend (or a clean sweep-reversal against it)?", 20),
    ("session", "Inside a kill zone (9:45-11:30 or 14:00-15:30 ET), not lunch chop?", 15),
    ("level", "Entry anchored to a real level (PDH/PDL, ONH/ONL, OR high/low, VWAP)?", 15),
    ("liquidity", "Was liquidity taken (sweep) or a clean break-and-retest before entry?", 10),
    ("structure", "CHoCH/BOS confirms the direction on your entry timeframe?", 10),
    ("rr", "At least 2:1 reward-to-risk to a REAL target (next liquidity level)?", 15),
    ("risk_ok", "Risk <= 1% of account, stop at a structural level (not a dollar amount)?", 10),
    ("no_news", "No red-folder news (CPI/FOMC/NFP) within the next 30 minutes?", 5),
]

GRADES = [(90, "A+"), (80, "A"), (65, "B"), (0, "C")]


def score_trade(answers: dict[str, bool]) -> tuple[int, str]:
    """answers maps checklist keys to True/False. Returns (score, grade)."""
    total = sum(w for k, _, w in CHECKLIST if answers.get(k, False))
    for cutoff, grade in GRADES:
        if total >= cutoff:
            return total, grade
    return total, "C"


def interactive() -> None:
    print("Answer y/n for the trade you're ABOUT to take:\n")
    answers = {}
    for key, question, weight in CHECKLIST:
        ans = input(f"  [{weight:>2}] {question} (y/n): ").strip().lower()
        answers[key] = ans.startswith("y")
    score, grade = score_trade(answers)
    print(f"\nScore: {score}/100  ->  Grade: {grade}")
    advice = {
        "A+": "Full size. This is the trade you wait all morning for.",
        "A": "Full size.",
        "B": "Half size at most — and skip it entirely if you're already down on the day.",
        "C": "Do not take this trade. Log it as a skipped C and move on.",
    }
    print(advice[grade])


if __name__ == "__main__":
    interactive()
