"""
Honeypot Detection — Layer 5
Detects ~80 honeypot candidates with subtly impossible profiles.
Per the spec: "8 years of experience at a company founded 3 years ago;
'expert' proficiency in 10 skills with 0 years used."
Submissions with honeypot rate > 10% in top 100 are DISQUALIFIED.
"""

from datetime import datetime, date


def _parse_date(date_str):
    """Parse a date string, return None on failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def detect_honeypot(candidate):
    """
    Check if a candidate is a honeypot.
    Returns (is_honeypot: bool, confidence: float, reasons: list[str])

    Honeypot indicators:
    1. Career dates that are impossible (duration > actual time span)
    2. Overlapping career positions that can't be concurrent
    3. Expert in many skills with 0 duration/endorsements
    4. Total career experience vastly exceeds years_of_experience
    5. Education dates that are impossible
    6. Signup before platform existence / future dates
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    reasons = []
    suspicion_score = 0.0

    # ── 1. Career Date Impossibilities ──────────────────────────────────────
    for job in career:
        start_str = job.get("start_date", "")
        end_str = job.get("end_date", "")
        claimed_months = job.get("duration_months", 0)
        is_current = job.get("is_current", False)

        start_date = _parse_date(start_str)
        end_date = _parse_date(end_str) if end_str else date(2026, 5, 24)

        if start_date and end_date:
            actual_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

            # Claimed duration >> actual possible time
            if claimed_months > actual_months + 6:  # 6 month tolerance
                reasons.append(
                    f"Claims {claimed_months} months at {job.get('company', '?')} "
                    f"but dates span only {actual_months} months"
                )
                suspicion_score += 0.35

            # Start date after end date
            if not is_current and end_date < start_date:
                reasons.append(
                    f"End date before start date at {job.get('company', '?')}"
                )
                suspicion_score += 0.40

            # Future start date
            if start_date > date(2026, 6, 1):
                reasons.append(f"Future start date at {job.get('company', '?')}")
                suspicion_score += 0.30

    # ── 2. Total Experience vs Career History ───────────────────────────────
    claimed_yoe = profile.get("years_of_experience", 0)
    total_career_months = sum(job.get("duration_months", 0) for job in career)

    # If they have 3 jobs totaling 150 months but claim 6 years → suspicious
    # (unless jobs overlapped, which we'll check)
    if total_career_months > 0 and claimed_yoe > 0:
        career_years = total_career_months / 12.0
        if career_years > claimed_yoe * 1.8:  # Too much overlap or fake
            # Check for actual overlaps
            overlap_ok = _check_reasonable_overlaps(career)
            if not overlap_ok:
                reasons.append(
                    f"Career history totals {career_years:.1f} years "
                    f"but claims {claimed_yoe} years with no obvious overlap"
                )
                suspicion_score += 0.25

    # ── 3. Expert Skills with Zero Evidence ─────────────────────────────────
    expert_zero_count = 0
    for skill in skills:
        prof = skill.get("proficiency", "beginner")
        endorsements = skill.get("endorsements", 0)
        duration = skill.get("duration_months", 0)

        if prof in ("expert", "advanced") and endorsements == 0 and duration == 0:
            expert_zero_count += 1

    if expert_zero_count >= 5:
        reasons.append(
            f"Claims {expert_zero_count} expert/advanced skills with "
            f"zero endorsements AND zero duration"
        )
        suspicion_score += 0.45

    elif expert_zero_count >= 3:
        reasons.append(
            f"Claims {expert_zero_count} expert/advanced skills with "
            f"zero endorsements AND zero duration"
        )
        suspicion_score += 0.25

    # ── 4. Education Date Impossibilities ───────────────────────────────────
    for edu in education:
        start_year = edu.get("start_year", 0)
        end_year = edu.get("end_year", 0)

        if start_year and end_year:
            # Degree completed in < 1 year or > 8 years
            duration = end_year - start_year
            if duration < 0:
                reasons.append(
                    f"Education end year before start year at {edu.get('institution', '?')}"
                )
                suspicion_score += 0.35
            elif duration > 8:
                reasons.append(
                    f"Education spanning {duration} years at {edu.get('institution', '?')}"
                )
                suspicion_score += 0.15

        # Future end year
        if end_year and end_year > 2027:
            reasons.append(f"Future graduation year {end_year}")
            suspicion_score += 0.20

    # ── 5. Behavioral Signal Impossibilities ────────────────────────────────
    signup_date = _parse_date(signals.get("signup_date", ""))
    last_active = _parse_date(signals.get("last_active_date", ""))

    if signup_date and last_active:
        if last_active < signup_date:
            reasons.append("Last active before signup date")
            suspicion_score += 0.30

    # Profile views without being active
    views = signals.get("profile_views_received_30d", 0)
    apps = signals.get("applications_submitted_30d", 0)
    if last_active:
        days_since_active = (date(2026, 5, 24) - last_active).days
        if days_since_active > 180 and apps > 10:
            reasons.append("Claims recent applications but inactive for 6+ months")
            suspicion_score += 0.25

    # ── 6. Skill Count Impossibilities ──────────────────────────────────────
    # Expert in 10+ completely different domains → impossible for one person
    expert_skills = [s for s in skills if s.get("proficiency") == "expert"]
    if len(expert_skills) >= 10:
        # Check diversity of domains
        skill_names = [s.get("name", "").lower() for s in expert_skills]
        diverse_domains = set()
        domain_map = {
            "ai": ["ai", "ml", "deep learning", "neural", "nlp", "computer vision"],
            "web": ["react", "angular", "vue", "html", "css", "javascript"],
            "data": ["sql", "spark", "hadoop", "kafka", "airflow"],
            "devops": ["docker", "kubernetes", "terraform", "aws", "gcp"],
            "design": ["photoshop", "figma", "illustrator"],
        }
        for domain, keywords in domain_map.items():
            for sn in skill_names:
                if any(kw in sn for kw in keywords):
                    diverse_domains.add(domain)
                    break

        if len(diverse_domains) >= 4:
            reasons.append(f"Expert in {len(expert_skills)} skills across {len(diverse_domains)} unrelated domains")
            suspicion_score += 0.30

    # ── 7. Cross-field title/experience mismatch ────────────────────────────
    # E.g., "8 years experience" but only career history shows 2 jobs of 6 months each
    if claimed_yoe >= 5 and len(career) >= 1:
        max_single_job = max(job.get("duration_months", 0) for job in career)
        if max_single_job < 6 and claimed_yoe > 5:
            reasons.append(
                f"Claims {claimed_yoe} years but longest job is only "
                f"{max_single_job} months"
            )
            suspicion_score += 0.20

    # ── Final Decision ──────────────────────────────────────────────────────
    is_honeypot = suspicion_score >= 0.50
    confidence = min(1.0, suspicion_score)

    return {
        "is_honeypot": is_honeypot,
        "honeypot_confidence": round(confidence, 4),
        "honeypot_reasons": reasons,
    }


def _check_reasonable_overlaps(career):
    """Check if career positions have reasonable overlaps."""
    if len(career) < 2:
        return True

    # Sort by start date
    sorted_jobs = sorted(career, key=lambda j: j.get("start_date", "0000"))

    overlap_months = 0
    for i in range(len(sorted_jobs) - 1):
        end_str = sorted_jobs[i].get("end_date", "")
        next_start_str = sorted_jobs[i + 1].get("start_date", "")

        if not end_str or not next_start_str:
            continue

        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            next_start = datetime.strptime(next_start_str, "%Y-%m-%d").date()

            if end_date > next_start:
                overlap_days = (end_date - next_start).days
                overlap_months += overlap_days / 30.0
        except (ValueError, TypeError):
            continue

    # Some overlap is normal (notice period, transition)
    return overlap_months < 12  # More than 12 months overlap is suspicious
