"""
Behavioral Signals Scoring — Layer 4
Scores candidate availability, engagement, and platform activity.
The JD emphasizes: "A perfect-on-paper candidate who hasn't logged in for
6 months and has a 5% recruiter response rate is not actually available."
"""

from datetime import datetime, date


def _days_since(date_str, reference_date=None):
    """Calculate days between a date string and reference date."""
    if not date_str:
        return 999
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        ref = reference_date or date(2026, 5, 24)  # Approx hackathon date
        return (ref - d).days
    except (ValueError, TypeError):
        return 999


def score_behavioral(candidate):
    """
    Score behavioral signals (0.0 to 1.0).

    This acts as an availability & engagement multiplier.
    A technically perfect candidate with poor engagement signals is
    effectively unavailable for hire.

    Components:
    - Engagement & Responsiveness (30%)
    - Availability & Notice Period (25%)
    - Platform Activity & Validation (20%)
    - Professional Credibility (15%)
    - Salary Fit (10%)
    """
    signals = candidate.get("redrob_signals", {})

    # ── 1. Engagement & Responsiveness (30%) ────────────────────────────────
    response_rate = signals.get("recruiter_response_rate", 0.0)
    response_time = signals.get("avg_response_time_hours", 999)
    last_active = signals.get("last_active_date", "")
    days_inactive = _days_since(last_active)

    # Response rate scoring
    if response_rate >= 0.7:
        response_score = 1.0
    elif response_rate >= 0.5:
        response_score = 0.8
    elif response_rate >= 0.3:
        response_score = 0.6
    elif response_rate >= 0.15:
        response_score = 0.4
    elif response_rate >= 0.05:
        response_score = 0.2
    else:
        response_score = 0.05  # Near-zero response = effectively unavailable

    # Response time scoring (faster = better)
    if response_time <= 12:
        time_score = 1.0
    elif response_time <= 24:
        time_score = 0.9
    elif response_time <= 48:
        time_score = 0.75
    elif response_time <= 96:
        time_score = 0.55
    elif response_time <= 168:  # 1 week
        time_score = 0.35
    else:
        time_score = 0.15

    # Activity recency scoring
    if days_inactive <= 7:
        activity_score = 1.0
    elif days_inactive <= 14:
        activity_score = 0.95
    elif days_inactive <= 30:
        activity_score = 0.85
    elif days_inactive <= 60:
        activity_score = 0.65
    elif days_inactive <= 90:
        activity_score = 0.45
    elif days_inactive <= 180:
        activity_score = 0.25
    else:
        activity_score = 0.10  # 6+ months inactive

    engagement_score = 0.45 * response_score + 0.25 * time_score + 0.30 * activity_score

    # ── 2. Availability & Notice Period (25%) ───────────────────────────────
    open_to_work = signals.get("open_to_work_flag", False)
    notice_days = signals.get("notice_period_days", 90)
    work_mode = signals.get("preferred_work_mode", "")
    willing_to_relocate = signals.get("willing_to_relocate", False)

    # Open to work is a strong signal
    availability_score = 0.5
    if open_to_work:
        availability_score = 0.8

    # Notice period: JD says "sub-30 preferred, can buy out up to 30"
    if notice_days <= 15:
        notice_score = 1.0
    elif notice_days <= 30:
        notice_score = 0.95  # JD can buy out
    elif notice_days <= 45:
        notice_score = 0.80
    elif notice_days <= 60:
        notice_score = 0.65
    elif notice_days <= 90:
        notice_score = 0.45
    else:
        notice_score = 0.25  # 90+ days is a hard sell

    availability_total = 0.50 * availability_score + 0.50 * notice_score

    # ── 3. Platform Activity & Validation (20%) ────────────────────────────
    profile_completeness = signals.get("profile_completeness_score", 0)
    views_30d = signals.get("profile_views_received_30d", 0)
    apps_30d = signals.get("applications_submitted_30d", 0)
    search_30d = signals.get("search_appearance_30d", 0)
    saved_30d = signals.get("saved_by_recruiters_30d", 0)
    connections = signals.get("connection_count", 0)
    endorsements = signals.get("endorsements_received", 0)

    # Profile completeness
    completeness_score = min(1.0, profile_completeness / 90.0)

    # Market demand (saved by recruiters is strongest signal)
    demand_score = 0.0
    if saved_30d >= 10:
        demand_score = 1.0
    elif saved_30d >= 5:
        demand_score = 0.8
    elif saved_30d >= 2:
        demand_score = 0.6
    elif saved_30d >= 1:
        demand_score = 0.4
    else:
        demand_score = 0.2

    # Profile views
    views_score = min(1.0, views_30d / 30.0)

    # Search appearances
    search_score = min(1.0, search_30d / 200.0)

    platform_score = (
        0.25 * completeness_score +
        0.35 * demand_score +
        0.20 * views_score +
        0.20 * search_score
    )

    # Verification bonuses
    verified_email = signals.get("verified_email", False)
    verified_phone = signals.get("verified_phone", False)
    linkedin = signals.get("linkedin_connected", False)

    verification_bonus = 0.0
    if verified_email:
        verification_bonus += 0.02
    if verified_phone:
        verification_bonus += 0.02
    if linkedin:
        verification_bonus += 0.03

    platform_score = min(1.0, platform_score + verification_bonus)

    # ── 4. Professional Credibility (15%) ───────────────────────────────────
    github_score_raw = signals.get("github_activity_score", -1)
    interview_rate = signals.get("interview_completion_rate", 0)
    offer_rate = signals.get("offer_acceptance_rate", -1)

    # GitHub activity (very important for an engineering role)
    if github_score_raw < 0:
        github_score = 0.3  # No GitHub → neutral-low
    elif github_score_raw >= 60:
        github_score = 1.0
    elif github_score_raw >= 40:
        github_score = 0.8
    elif github_score_raw >= 20:
        github_score = 0.6
    else:
        github_score = 0.4

    # Interview completion (shows professionalism)
    if interview_rate >= 0.85:
        interview_score = 1.0
    elif interview_rate >= 0.7:
        interview_score = 0.8
    elif interview_rate >= 0.5:
        interview_score = 0.6
    else:
        interview_score = 0.35

    # Offer acceptance (shows commitment vs serial interviewer)
    if offer_rate < 0:
        offer_score = 0.5  # No history
    elif offer_rate >= 0.7:
        offer_score = 1.0
    elif offer_rate >= 0.5:
        offer_score = 0.8
    elif offer_rate >= 0.3:
        offer_score = 0.6
    else:
        offer_score = 0.4

    credibility_score = 0.40 * github_score + 0.35 * interview_score + 0.25 * offer_score

    # ── 5. Salary Fit (10%) ─────────────────────────────────────────────────
    salary_range = signals.get("expected_salary_range_inr_lpa", {})
    salary_min = salary_range.get("min", 0)
    salary_max = salary_range.get("max", 0)

    # Series A Senior AI Engineer in India: roughly 25-55 LPA reasonable range
    # Too low might indicate junior, too high might be unaffordable
    if salary_max == 0:
        salary_score = 0.5  # Unknown
    elif salary_min <= 55 and salary_max >= 20:
        # Overlaps with reasonable range
        if 25 <= salary_min <= 45:
            salary_score = 1.0  # Sweet spot
        elif salary_min < 25:
            salary_score = 0.75  # Might be too junior
        else:
            salary_score = 0.65  # On the higher end
    elif salary_min > 60:
        salary_score = 0.3  # Probably too expensive for Series A
    elif salary_max < 15:
        salary_score = 0.4  # Very low expectations → might not be senior enough
    else:
        salary_score = 0.5

    # ── Composite Score ─────────────────────────────────────────────────────
    composite = (
        0.30 * engagement_score +
        0.25 * availability_total +
        0.20 * platform_score +
        0.15 * credibility_score +
        0.10 * salary_score
    )

    return {
        "behavioral_score": round(composite, 4),
        "engagement_score": round(engagement_score, 4),
        "availability_score": round(availability_total, 4),
        "platform_score": round(platform_score, 4),
        "credibility_score": round(credibility_score, 4),
        "salary_score": round(salary_score, 4),
        "response_rate": response_rate,
        "days_inactive": days_inactive,
        "notice_period": notice_days,
        "open_to_work": open_to_work,
        "github_activity": github_score_raw,
    }
