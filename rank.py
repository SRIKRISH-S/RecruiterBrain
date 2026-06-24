#!/usr/bin/env python3
"""
RecruiterBrain — Intelligent Candidate Discovery & Ranking Engine
================================================================
Ranks 100K candidates against the "Senior AI Engineer — Founding Team"
job description using a 5-layer scoring pipeline:

  Layer 1+2: Career Fit (title, experience, industry, production ML evidence)
  Layer 3:   Skills Intelligence (with anti-keyword-stuffing detection)
  Layer 4:   Behavioral Signals (engagement, availability, credibility)
  Layer 5:   Honeypot Detection (catch impossible profiles)

Produces a CSV with top-100 ranked candidates and specific reasoning.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Constraints: < 5 min, 16GB RAM, CPU only, no network.
"""

import argparse
import csv
import io
import json
import sys
import time
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent dir to path for scoring module imports
sys.path.insert(0, str(Path(__file__).parent))

from scoring.career_fit import score_career_fit
from scoring.skills_intelligence import score_skills
from scoring.behavioral_signals import score_behavioral
from scoring.honeypot_detector import detect_honeypot
from scoring.reasoning import generate_reasoning


# ─── Scoring Weights ──────────────────────────────────────────────────────────
# These weights determine how much each layer contributes to the final score.
# Career fit is dominant because the JD is very specific about who they want.

WEIGHTS = {
    "career_fit":  0.40,   # Title, experience, industry, production ML evidence
    "skills":      0.30,   # Skill matching with anti-stuffing
    "behavioral":  0.20,   # Engagement, availability, credibility
    "education":   0.10,   # Education quality (bonus layer)
}


def score_education(candidate):
    """
    Score education quality (0.0 to 1.0).
    JD cares about this less than career trajectory, but
    tier-1 institutions and CS degrees are bonuses.
    """
    education = candidate.get("education", [])
    if not education:
        return {"education_score": 0.3}  # No education data → neutral-low

    best_score = 0.0

    for edu in education:
        tier = edu.get("tier", "unknown")
        degree = edu.get("degree", "").lower()
        field = edu.get("field_of_study", "").lower()

        # Tier scoring
        tier_scores = {
            "tier_1": 1.0,
            "tier_2": 0.75,
            "tier_3": 0.50,
            "tier_4": 0.35,
            "unknown": 0.40,
        }
        tier_score = tier_scores.get(tier, 0.40)

        # Degree level
        degree_scores = {
            "ph.d.": 0.85, "phd": 0.85, "ph.d": 0.85,
            "m.tech": 0.90, "m.tech.": 0.90, "mtech": 0.90,
            "m.s.": 0.85, "ms": 0.85, "m.sc.": 0.80,
            "m.e.": 0.85, "me": 0.85,
            "mba": 0.60,
            "b.tech": 0.70, "b.tech.": 0.70, "btech": 0.70,
            "b.e.": 0.70, "be": 0.65, "b.e": 0.70,
            "b.sc.": 0.55, "bsc": 0.55, "b.sc": 0.55,
            "b.s.": 0.60, "bs": 0.60,
            "bca": 0.50, "mca": 0.65,
            "diploma": 0.35,
        }
        degree_score = 0.50
        for deg_key, deg_val in degree_scores.items():
            if deg_key in degree:
                degree_score = deg_val
                break

        # Field relevance
        cs_fields = ["computer science", "computer engineering", "software",
                     "information technology", "artificial intelligence",
                     "machine learning", "data science", "electrical engineering",
                     "electronics", "ece", "cse", "it", "mathematics",
                     "statistics", "computational"]
        field_score = 0.40
        for f in cs_fields:
            if f in field:
                field_score = 0.90
                break

        edu_score = 0.40 * tier_score + 0.30 * degree_score + 0.30 * field_score
        best_score = max(best_score, edu_score)

    return {"education_score": round(best_score, 4)}


def compute_final_score(career_scores, skills_scores, behavioral_scores,
                        education_scores, honeypot_result):
    """
    Compute the final composite score combining all layers.
    Honeypot detection acts as a hard filter (score → 0 if honeypot).
    """
    career = career_scores.get("career_fit_score", 0)
    skills_val = skills_scores.get("skills_score", 0)
    behavioral = behavioral_scores.get("behavioral_score", 0)
    education = education_scores.get("education_score", 0)

    # Base composite
    composite = (
        WEIGHTS["career_fit"] * career +
        WEIGHTS["skills"] * skills_val +
        WEIGHTS["behavioral"] * behavioral +
        WEIGHTS["education"] * education
    )

    # Honeypot penalty: if detected as honeypot, crush the score
    if honeypot_result.get("is_honeypot", False):
        composite *= 0.01  # Effectively zero

    # Keyword stuffer penalty (additional to what skills_intelligence already applies)
    if skills_scores.get("is_keyword_stuffer", False):
        stuffer_conf = skills_scores.get("stuffer_confidence", 0)
        composite *= max(0.1, 1.0 - stuffer_conf * 0.5)

    return round(composite, 6)


def process_candidate(candidate):
    """Process a single candidate through all scoring layers."""
    # Layer 1+2: Career Fit
    career_scores = score_career_fit(candidate)

    # Layer 3: Skills Intelligence
    skills_scores = score_skills(candidate)

    # Layer 4: Behavioral Signals
    behavioral_scores = score_behavioral(candidate)

    # Layer 5: Honeypot Detection
    honeypot_result = detect_honeypot(candidate)

    # Bonus: Education
    education_scores = score_education(candidate)

    # Final composite score
    final_score = compute_final_score(
        career_scores, skills_scores, behavioral_scores,
        education_scores, honeypot_result
    )

    # Merge all scores
    all_scores = {}
    all_scores.update(career_scores)
    all_scores.update(skills_scores)
    all_scores.update(behavioral_scores)
    all_scores.update(education_scores)
    all_scores.update(honeypot_result)
    all_scores["final_score"] = final_score

    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "candidate": candidate,
        "scores": all_scores,
        "final_score": final_score,
    }


def main():
    parser = argparse.ArgumentParser(
        description="RecruiterBrain — Intelligent Candidate Ranking Engine"
    )
    parser.add_argument(
        "--candidates", required=True,
        help="Path to candidates.jsonl file"
    )
    parser.add_argument(
        "--out", required=True,
        help="Path to output submission CSV"
    )
    parser.add_argument(
        "--top-n", type=int, default=100,
        help="Number of top candidates to output (default: 100)"
    )
    parser.add_argument(
        "--dashboard-data", type=str, default=None,
        help="Optional: path to save dashboard JSON data"
    )
    args = parser.parse_args()

    start_time = time.time()

    print("=" * 70)
    print("  RecruiterBrain — Intelligent Candidate Discovery & Ranking")
    print("  Senior AI Engineer — Founding Team @ Redrob AI")
    print("=" * 70)

    # ── Load candidates ─────────────────────────────────────────────────────
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        print(f"ERROR: File not found: {candidates_path}")
        sys.exit(1)

    print(f"\n📂 Loading candidates from: {candidates_path}")

    # Stream processing for memory efficiency
    results = []
    total = 0
    honeypot_count = 0
    stuffer_count = 0

    with open(candidates_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                print(f"  ⚠ Skipping malformed JSON on line {line_num}")
                continue

            total += 1
            result = process_candidate(candidate)
            results.append(result)

            if result["scores"].get("is_honeypot", False):
                honeypot_count += 1
            if result["scores"].get("is_keyword_stuffer", False):
                stuffer_count += 1

            if total % 10000 == 0:
                elapsed = time.time() - start_time
                print(f"  ⏱ Processed {total:,} candidates ({elapsed:.1f}s)")

    elapsed = time.time() - start_time
    print(f"\n✅ Processed {total:,} candidates in {elapsed:.1f}s")
    print(f"  🍯 Honeypots detected: {honeypot_count}")
    print(f"  🎭 Keyword stuffers detected: {stuffer_count}")

    # ── Sort and select top N ───────────────────────────────────────────────
    results.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
    top_n = results[:args.top_n]

    # Verify honeypot rate in top 100
    top_honeypots = sum(1 for r in top_n if r["scores"].get("is_honeypot", False))
    honeypot_rate = top_honeypots / len(top_n) if top_n else 0
    print(f"\n  🎯 Honeypot rate in top {args.top_n}: {honeypot_rate:.1%} "
          f"({'✅ PASS' if honeypot_rate <= 0.10 else '❌ FAIL (>10%%)'})")

    # ── Generate reasoning and write CSV ────────────────────────────────────
    print(f"\n📝 Generating reasoning and writing CSV...")

    output_path = Path(args.out)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, result in enumerate(top_n, 1):
            candidate = result["candidate"]
            scores = result["scores"]
            final_score = result["final_score"]

            # Normalize score to 0-1 range relative to top score
            max_score = top_n[0]["final_score"] if top_n else 1
            normalized_score = round(final_score / max_score if max_score > 0 else 0, 4)

            reasoning = generate_reasoning(candidate, scores, rank)

            writer.writerow([
                result["candidate_id"],
                rank,
                normalized_score,
                reasoning,
            ])

    # ── Save dashboard data ─────────────────────────────────────────────────
    dashboard_path = args.dashboard_data
    if not dashboard_path:
        dashboard_path = str(output_path.parent / "dashboard" / "data.json")

    Path(dashboard_path).parent.mkdir(parents=True, exist_ok=True)

    dashboard_data = {
        "metadata": {
            "total_candidates": total,
            "honeypots_detected": honeypot_count,
            "stuffers_detected": stuffer_count,
            "top_n": args.top_n,
            "honeypot_rate_top100": round(honeypot_rate, 4),
            "processing_time_seconds": round(time.time() - start_time, 2),
        },
        "top_candidates": [],
        "score_distribution": {
            "career_fit": [],
            "skills": [],
            "behavioral": [],
        },
    }

    for rank, result in enumerate(top_n, 1):
        candidate = result["candidate"]
        scores = result["scores"]
        profile = candidate.get("profile", {})
        signals = candidate.get("redrob_signals", {})

        max_score = top_n[0]["final_score"] if top_n else 1
        normalized_score = round(result["final_score"] / max_score if max_score > 0 else 0, 4)

        # Extract top skills for display
        top_skills = []
        for s in candidate.get("skills", []):
            if s.get("proficiency") in ("expert", "advanced"):
                top_skills.append(s.get("name", ""))
        top_skills = top_skills[:8]

        dashboard_data["top_candidates"].append({
            "rank": rank,
            "candidate_id": result["candidate_id"],
            "name": profile.get("anonymized_name", ""),
            "title": profile.get("current_title", ""),
            "company": profile.get("current_company", ""),
            "yoe": profile.get("years_of_experience", 0),
            "location": profile.get("location", ""),
            "country": profile.get("country", ""),
            "score": normalized_score,
            "career_fit": scores.get("career_fit_score", 0),
            "skills_match": scores.get("skills_score", 0),
            "behavioral": scores.get("behavioral_score", 0),
            "education": scores.get("education_score", 0),
            "is_honeypot": scores.get("is_honeypot", False),
            "is_stuffer": scores.get("is_keyword_stuffer", False),
            "top_skills": top_skills,
            "response_rate": signals.get("recruiter_response_rate", 0),
            "github_score": signals.get("github_activity_score", -1),
            "notice_period": signals.get("notice_period_days", 0),
            "open_to_work": signals.get("open_to_work_flag", False),
            "work_mode": signals.get("preferred_work_mode", ""),
            "title_score": scores.get("title_score", 0),
            "exp_score": scores.get("exp_score", 0),
            "industry_score": scores.get("industry_score", 0),
            "prod_ml_score": scores.get("prod_ml_score", 0),
            "location_score": scores.get("location_score", 0),
            "must_have_score": scores.get("must_have_score", 0),
            "nice_to_have_score": scores.get("nice_to_have_score", 0),
            "engagement_score": scores.get("engagement_score", 0),
            "availability_score": scores.get("availability_score", 0),
            "credibility_score": scores.get("credibility_score", 0),
        })

        dashboard_data["score_distribution"]["career_fit"].append(scores.get("career_fit_score", 0))
        dashboard_data["score_distribution"]["skills"].append(scores.get("skills_score", 0))
        dashboard_data["score_distribution"]["behavioral"].append(scores.get("behavioral_score", 0))

    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2)

    elapsed_total = time.time() - start_time
    print(f"\n✅ Submission written to: {output_path}")
    print(f"📊 Dashboard data saved to: {dashboard_path}")
    print(f"⏱ Total time: {elapsed_total:.1f}s")

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  TOP 10 CANDIDATES")
    print(f"{'='*70}")
    for r in dashboard_data["top_candidates"][:10]:
        print(f"  #{r['rank']:>3} | {r['candidate_id']} | {r['title']:<30} | "
              f"{r['company']:<15} | {r['yoe']:.1f}yr | "
              f"Score: {r['score']:.4f}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
