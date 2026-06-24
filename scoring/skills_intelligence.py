"""
Skills Intelligence Scoring — Layer 3
Matches candidate skills against JD requirements with anti-keyword-stuffing
detection. Cross-references skill claims with endorsements, duration, and
career history descriptions to catch fake profiles.
"""


# ─── JD Skill Requirements ────────────────────────────────────────────────────
# Organized by JD priority

MUST_HAVE_SKILLS = {
    # Embeddings-based retrieval systems
    "sentence-transformers": 1.0, "sentence transformers": 1.0,
    "openai embeddings": 0.9, "bge": 0.95, "e5": 0.95,
    "embeddings": 0.85, "embedding": 0.85,
    "text embeddings": 0.9, "semantic search": 0.9,
    "dense retrieval": 0.9, "vector embeddings": 0.9,

    # Vector databases / hybrid search
    "pinecone": 0.95, "weaviate": 0.95, "qdrant": 0.95,
    "milvus": 0.95, "opensearch": 0.9, "elasticsearch": 0.9,
    "faiss": 0.95, "vector database": 0.95, "vector db": 0.9,
    "hybrid search": 0.9, "vector search": 0.9,
    "annoy": 0.85, "scann": 0.85, "hnsw": 0.85,

    # Python
    "python": 0.8, "fastapi": 0.7, "flask": 0.6, "django": 0.5,

    # Ranking evaluation
    "ndcg": 0.95, "mrr": 0.9, "map": 0.7, "precision": 0.6,
    "recall": 0.6, "a/b testing": 0.85, "ab testing": 0.85,
    "evaluation": 0.6, "ranking": 0.8, "information retrieval": 0.9,
    "ir": 0.7, "search ranking": 0.9,
}

NICE_TO_HAVE_SKILLS = {
    # LLM fine-tuning
    "lora": 0.8, "qlora": 0.8, "peft": 0.8,
    "fine-tuning": 0.75, "fine-tuning llms": 0.85, "fine tuning": 0.75,

    # Learning-to-rank
    "xgboost": 0.7, "lightgbm": 0.7, "learning to rank": 0.85,
    "learn-to-rank": 0.85, "lambdamart": 0.85,

    # HR-tech / recruiting
    "hr-tech": 0.7, "recruiting": 0.65, "talent": 0.5,
    "candidate matching": 0.8, "applicant tracking": 0.6,

    # Distributed systems / ML infra
    "distributed systems": 0.6, "kubernetes": 0.5, "docker": 0.5,
    "mlops": 0.6, "ml pipeline": 0.65, "kubeflow": 0.6,
    "mlflow": 0.6, "weights & biases": 0.55, "wandb": 0.55,

    # Core ML
    "pytorch": 0.75, "tensorflow": 0.7, "keras": 0.6,
    "transformers": 0.8, "huggingface": 0.75, "hugging face": 0.75,
    "bert": 0.7, "gpt": 0.6, "llm": 0.7,
    "nlp": 0.75, "natural language processing": 0.75,
    "deep learning": 0.7, "machine learning": 0.65,
    "neural network": 0.6, "neural networks": 0.6,

    # Data engineering (adjacent)
    "spark": 0.5, "airflow": 0.5, "kafka": 0.45,
    "sql": 0.4, "postgresql": 0.4, "mongodb": 0.35,
    "redis": 0.35, "aws": 0.4, "gcp": 0.4, "azure": 0.35,

    # Open source
    "open source": 0.5, "github": 0.4, "open-source": 0.5,
}

# Skills that are IRRELEVANT to this role (traps for keyword stuffers)
IRRELEVANT_SKILLS = {
    "photoshop", "illustrator", "figma", "canva", "indesign",
    "autocad", "solidworks", "creo", "ansys", "catia",
    "tally", "sap", "oracle erp", "quickbooks",
    "salesforce crm", "hubspot", "mailchimp",
    "wordpress", "wix", "squarespace",
    "video editing", "premiere pro", "after effects",
    "civil engineering", "structural analysis",
    "mechanical design", "hvac", "piping",
    "accounting", "bookkeeping", "tax",
    "recruitment", "payroll", "employee engagement",
    "cold calling", "door-to-door", "telemarketing",
    "tailwind",  # CSS framework, not AI
    "bootstrap", "css", "html",
}

# All relevant skill names (for matching against assessment scores too)
ALL_RELEVANT_SKILLS = set()
ALL_RELEVANT_SKILLS.update(k.lower() for k in MUST_HAVE_SKILLS)
ALL_RELEVANT_SKILLS.update(k.lower() for k in NICE_TO_HAVE_SKILLS)


def _normalize(text):
    return text.strip().lower() if text else ""


def _is_keyword_stuffer(candidate):
    """
    Detect keyword-stuffing pattern:
    - Non-technical title BUT claims many AI skills
    - Claims expert in many skills but low endorsements / duration
    - Skills don't match career descriptions at all
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    title = _normalize(profile.get("current_title", ""))

    # Non-technical titles that shouldn't have 8+ AI skills
    non_tech_titles = ["marketing manager", "hr manager", "accountant",
                       "sales executive", "content writer", "graphic designer",
                       "customer support", "operations manager",
                       "civil engineer", "mechanical engineer"]

    is_non_tech = any(nt in title for nt in non_tech_titles)

    # Count AI-relevant skills
    ai_skill_count = 0
    suspicious_claims = 0
    for skill in skills:
        name = _normalize(skill.get("name", ""))
        prof = skill.get("proficiency", "beginner")
        endorsements = skill.get("endorsements", 0)
        duration = skill.get("duration_months", 0)

        if name in ALL_RELEVANT_SKILLS or any(r in name for r in ALL_RELEVANT_SKILLS):
            ai_skill_count += 1
            # Expert with 0 endorsements and short duration → suspicious
            if prof in ("expert", "advanced") and endorsements < 3 and duration < 6:
                suspicious_claims += 1

    # Pattern: non-tech title + many AI skills → keyword stuffer
    if is_non_tech and ai_skill_count >= 6:
        return True, 0.9  # High confidence stuffer

    # Pattern: many suspicious expert claims
    if suspicious_claims >= 4:
        return True, 0.7

    # Check if skills appear in career descriptions
    if ai_skill_count >= 5:
        all_desc = " ".join(j.get("description", "").lower() for j in career)
        desc_match_count = 0
        for skill in skills:
            name = _normalize(skill.get("name", ""))
            if name in all_desc or any(part in all_desc for part in name.split()):
                desc_match_count += 1

        # If they claim 8+ AI skills but descriptions mention < 2 → suspicious
        if ai_skill_count >= 8 and desc_match_count < 2:
            return True, 0.6

    return False, 0.0


def score_skills(candidate):
    """
    Score candidate's skills match (0.0 to 1.0).

    Components:
    - Must-have skill coverage (45% weight)
    - Nice-to-have skill coverage (20% weight)
    - Skill quality (endorsements, duration, proficiency) (20% weight)
    - Anti-stuffing penalty (15% weight — acts as a multiplier)
    """
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    assessments = signals.get("skill_assessment_scores", {})

    # ── 1. Must-Have Skill Coverage (45%) ───────────────────────────────────
    must_have_matched = set()
    must_have_total_value = 0.0

    for skill in skills:
        name = _normalize(skill.get("name", ""))
        prof = skill.get("proficiency", "beginner")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)

        for mh_skill, mh_value in MUST_HAVE_SKILLS.items():
            if mh_skill in name or name in mh_skill:
                if mh_skill not in must_have_matched:
                    must_have_matched.add(mh_skill)
                    # Weight by proficiency and duration
                    prof_mult = {"expert": 1.0, "advanced": 0.85,
                                 "intermediate": 0.65, "beginner": 0.35}.get(prof, 0.5)
                    duration_mult = min(1.0, duration / 24.0)  # 2+ years = full
                    endorse_mult = min(1.0, 0.5 + endorsements / 20.0)

                    effective_value = mh_value * prof_mult * max(duration_mult, 0.3) * max(endorse_mult, 0.3)
                    must_have_total_value += effective_value

    # Normalize: hitting 6+ distinct must-have categories = 1.0
    must_have_score = min(1.0, must_have_total_value / 4.0)

    # ── 2. Nice-to-Have Skill Coverage (20%) ────────────────────────────────
    nice_matched = set()
    nice_total_value = 0.0

    for skill in skills:
        name = _normalize(skill.get("name", ""))
        prof = skill.get("proficiency", "beginner")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)

        for nh_skill, nh_value in NICE_TO_HAVE_SKILLS.items():
            if nh_skill in name or name in nh_skill:
                if nh_skill not in nice_matched:
                    nice_matched.add(nh_skill)
                    prof_mult = {"expert": 1.0, "advanced": 0.85,
                                 "intermediate": 0.65, "beginner": 0.40}.get(prof, 0.5)
                    duration_mult = min(1.0, duration / 18.0)
                    effective_value = nh_value * prof_mult * max(duration_mult, 0.3)
                    nice_total_value += effective_value

    nice_score = min(1.0, nice_total_value / 5.0)

    # ── 3. Skill Quality / Assessment Validation (20%) ──────────────────────
    quality_score = 0.5  # Baseline

    # Use platform assessment scores as validation
    if assessments:
        relevant_assessments = []
        for skill_name, score_val in assessments.items():
            name_lower = skill_name.lower()
            if name_lower in ALL_RELEVANT_SKILLS or any(r in name_lower for r in ["ml", "ai", "nlp", "python", "data"]):
                relevant_assessments.append(score_val)

        if relevant_assessments:
            avg_score = sum(relevant_assessments) / len(relevant_assessments)
            quality_score = min(1.0, avg_score / 80.0)  # 80+ = full score

    # Check for irrelevant skills ratio
    irrelevant_count = 0
    for skill in skills:
        name = _normalize(skill.get("name", ""))
        if name in IRRELEVANT_SKILLS or any(ir in name for ir in IRRELEVANT_SKILLS):
            irrelevant_count += 1

    total_skills = len(skills)
    if total_skills > 0:
        irrelevant_ratio = irrelevant_count / total_skills
        if irrelevant_ratio > 0.6:  # Mostly irrelevant skills
            quality_score *= 0.4

    # ── 4. Anti-Stuffing (15% — penalty multiplier) ─────────────────────────
    is_stuffer, stuffer_confidence = _is_keyword_stuffer(candidate)
    anti_stuff_score = 1.0
    if is_stuffer:
        anti_stuff_score = max(0.05, 1.0 - stuffer_confidence)

    # ── Composite Score ─────────────────────────────────────────────────────
    raw_score = (
        0.45 * must_have_score +
        0.20 * nice_score +
        0.20 * quality_score +
        0.15 * 1.0  # Baseline for non-stuffers
    )

    # Apply anti-stuffing as a multiplier
    final_score = raw_score * anti_stuff_score

    return {
        "skills_score": round(final_score, 4),
        "must_have_score": round(must_have_score, 4),
        "nice_to_have_score": round(nice_score, 4),
        "quality_score": round(quality_score, 4),
        "is_keyword_stuffer": is_stuffer,
        "stuffer_confidence": round(stuffer_confidence, 4),
        "must_have_matched_count": len(must_have_matched),
        "nice_matched_count": len(nice_matched),
    }
