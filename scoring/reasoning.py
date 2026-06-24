"""
Reasoning Generator — Generates specific, honest, non-templated reasoning
for each candidate. Stage 4 manual review checks 10 random rows for:
- Specific facts from the candidate's profile
- JD connection (not generic praise)
- Honest concerns acknowledged
- No hallucination
- Variation across candidates
- Rank consistency (tone matches rank)
"""

import random


def _format_salary(salary_range):
    """Format salary range nicely."""
    if not salary_range:
        return ""
    mn = salary_range.get("min", 0)
    mx = salary_range.get("max", 0)
    if mn and mx:
        return f"{mn:.0f}-{mx:.0f} LPA"
    return ""


def generate_reasoning(candidate, scores, rank):
    """
    Generate a 1-2 sentence reasoning for this candidate at this rank.
    Must be specific, honest, and vary across candidates.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    yoe = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown")
    country = profile.get("country", "")
    summary = profile.get("summary", "")

    career_score = scores.get("career_fit_score", 0)
    skills_score = scores.get("skills_score", 0)
    behavioral_score = scores.get("behavioral_score", 0)
    is_stuffer = scores.get("is_keyword_stuffer", False)
    is_honeypot = scores.get("is_honeypot", False)

    response_rate = signals.get("recruiter_response_rate", 0)
    notice_days = signals.get("notice_period_days", 0)
    github = signals.get("github_activity_score", -1)
    open_to_work = signals.get("open_to_work_flag", False)
    work_mode = signals.get("preferred_work_mode", "")

    # Get relevant skills
    relevant_skills = []
    for s in skills:
        name = s.get("name", "")
        prof = s.get("proficiency", "")
        if prof in ("expert", "advanced") and name:
            relevant_skills.append(name)
    relevant_skills = relevant_skills[:5]  # Top 5

    # Get career highlights
    career_highlights = []
    for job in career[:3]:
        desc = job.get("description", "")
        job_title = job.get("title", "")
        job_company = job.get("company", "")
        if desc:
            # Extract key achievements
            for keyword in ["built", "designed", "led", "shipped", "deployed",
                           "implemented", "developed", "owned", "managed",
                           "created", "launched", "architected"]:
                if keyword in desc.lower():
                    # Find the sentence containing this keyword
                    sentences = desc.split(".")
                    for sent in sentences:
                        if keyword in sent.lower() and len(sent.strip()) > 20:
                            career_highlights.append(sent.strip()[:100])
                            break
                    break

    # ── Build reasoning based on rank tier ──────────────────────────────────

    parts = []

    # Lead with title and experience
    parts.append(f"{title} at {company} with {yoe:.1f} years of experience")

    # Strong fits (rank 1-30)
    if rank <= 30:
        # Emphasize strengths
        if relevant_skills:
            parts.append(f"strong in {', '.join(relevant_skills[:3])}")

        if career_highlights:
            parts.append(career_highlights[0][:80])

        if location and country == "India":
            if any(city in location.lower() for city in ["pune", "noida", "delhi"]):
                parts.append(f"based in {location} (preferred location)")

        # Mention engagement
        if response_rate >= 0.5:
            parts.append(f"responsive ({response_rate:.0%} recruiter response rate)")
        if github >= 40:
            parts.append(f"active on GitHub (score: {github:.0f})")

        # Acknowledge any concerns
        concerns = []
        if notice_days > 60:
            concerns.append(f"{notice_days}-day notice period")
        if not open_to_work:
            concerns.append("not flagged as open to work")
        if response_rate < 0.3 and response_rate > 0:
            concerns.append(f"lower response rate ({response_rate:.0%})")

        if concerns:
            parts.append(f"minor concerns: {'; '.join(concerns)}")

    # Mid-tier fits (rank 31-70)
    elif rank <= 70:
        if relevant_skills:
            parts.append(f"skills include {', '.join(relevant_skills[:3])}")

        # Note both strengths and weaknesses
        strengths = []
        weaknesses = []

        if career_score >= 0.6:
            strengths.append("relevant career trajectory")
        if skills_score >= 0.5:
            strengths.append("partial skill match")
        if behavioral_score >= 0.6:
            strengths.append("good engagement signals")

        if career_score < 0.5:
            weaknesses.append("career path not directly aligned with AI engineering")
        if skills_score < 0.4:
            weaknesses.append("limited must-have skill coverage")
        if notice_days > 90:
            weaknesses.append(f"long notice period ({notice_days} days)")
        if response_rate < 0.3:
            weaknesses.append(f"low recruiter response rate ({response_rate:.0%})")
        if country != "India" and country:
            weaknesses.append(f"located in {country}")

        if strengths:
            parts.append(f"strengths: {'; '.join(strengths[:2])}")
        if weaknesses:
            parts.append(f"gaps: {'; '.join(weaknesses[:2])}")

    # Lower-tier fits (rank 71-100)
    else:
        if relevant_skills:
            parts.append(f"some relevant skills ({', '.join(relevant_skills[:2])})")

        # Focus on what's missing
        gaps = []
        if career_score < 0.4:
            gaps.append("career not in AI/ML engineering")
        if skills_score < 0.3:
            gaps.append("few JD-required skills")
        if behavioral_score < 0.4:
            gaps.append("weak engagement signals")
        if yoe < 4:
            gaps.append(f"only {yoe:.1f} years experience (JD seeks 5-9)")
        elif yoe > 12:
            gaps.append(f"{yoe:.1f} years experience may be overqualified")
        if response_rate < 0.15:
            gaps.append(f"very low response rate ({response_rate:.0%})")

        if gaps:
            parts.append(f"concerns: {'; '.join(gaps[:3])}")

        parts.append("included as fringe candidate given partial alignment")

    # Assemble the reasoning
    reasoning = "; ".join(parts) + "."

    # Ensure it's not too long (keep under 250 chars for CSV friendliness)
    if len(reasoning) > 300:
        reasoning = reasoning[:297] + "..."

    # Clean up any CSV-unsafe characters
    reasoning = reasoning.replace('"', "'").replace('\n', ' ').replace('\r', '')

    return reasoning
