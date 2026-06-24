"""
Career Fit Scoring — Layer 1+2
Analyzes title relevance, industry fit, experience band, career trajectory,
and production ML evidence to score how well a candidate matches the
"Senior AI Engineer — Founding Team" role at Redrob AI.
"""

import re
from datetime import datetime, date

# ─── Title Relevance Mapping ───────────────────────────────────────────────────
# The JD is for "Senior AI Engineer" at an AI-native talent platform.
# Titles directly in AI/ML/Data Science → high relevance
# Backend/Data Engineering with ML exposure → medium relevance
# Completely unrelated (HR, Marketing, Accountant, etc.) → near-zero

TITLE_TIER = {
    # Tier 1: Direct AI/ML titles (score 1.0)
    "ai engineer": 1.0,
    "senior ai engineer": 1.0,
    "machine learning engineer": 1.0,
    "senior machine learning engineer": 1.0,
    "ml engineer": 1.0,
    "senior ml engineer": 1.0,
    "junior ml engineer": 0.7,
    "lead ai engineer": 1.0,
    "principal ai engineer": 1.0,
    "staff ai engineer": 1.0,
    "applied ml engineer": 1.0,
    "nlp engineer": 0.95,
    "deep learning engineer": 0.95,
    "research engineer": 0.75,  # Good but JD warns about pure research

    # Tier 2: Data Science (score 0.85-0.9)
    "data scientist": 0.90,
    "senior data scientist": 0.90,
    "lead data scientist": 0.90,
    "principal data scientist": 0.90,
    "applied scientist": 0.85,

    # Tier 3: Adjacent engineering roles (score 0.5-0.75)
    "backend engineer": 0.60,
    "senior backend engineer": 0.65,
    "software engineer": 0.55,
    "senior software engineer": 0.60,
    "full stack engineer": 0.45,
    "data engineer": 0.65,
    "senior data engineer": 0.70,
    "platform engineer": 0.50,
    "devops engineer": 0.30,
    "analytics engineer": 0.55,

    # Tier 4: Non-technical / irrelevant (these are TRAPS per the JD)
    "marketing manager": 0.0,
    "hr manager": 0.0,
    "accountant": 0.0,
    "sales executive": 0.0,
    "content writer": 0.0,
    "graphic designer": 0.0,
    "customer support": 0.0,
    "operations manager": 0.05,
    "business analyst": 0.20,
    "project manager": 0.15,
    "product manager": 0.35,
    "civil engineer": 0.0,
    "mechanical engineer": 0.0,
    "electrical engineer": 0.10,
}

# Consulting companies the JD explicitly flags as poor fit
CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "l&t infotech", "lti", "ltimindtree",
    "mphasis", "mindtree", "hexaware", "cyient", "persistent",
    "zensar", "niit", "birlasoft", "sonata software",
    "tata consultancy services", "infosys limited", "wipro limited",
}

# Product companies → bonus (JD wants "product companies, not pure services")
KNOWN_PRODUCT_COMPANIES = {
    "google", "meta", "facebook", "amazon", "microsoft", "apple",
    "netflix", "uber", "airbnb", "stripe", "flipkart", "swiggy",
    "zomato", "razorpay", "cred", "meesho", "phonepe", "paytm",
    "ola", "byju's", "unacademy", "upstox", "groww", "zerodha",
    "sharechat", "dream11", "myntra", "freshworks", "zoho",
    "postman", "browserstack", "druva", "hasura", "frappe",
    "slack", "spotify", "twitter", "linkedin", "salesforce",
    "atlassian", "datadog", "snowflake", "databricks", "openai",
    "anthropic", "cohere", "huggingface", "weights & biases",
}

# Keywords in career descriptions that indicate actual production ML work
PRODUCTION_ML_KEYWORDS = [
    "embeddings", "embedding", "vector search", "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "elasticsearch",
    "opensearch", "retrieval", "ranking", "recommendation",
    "deployed", "production", "a/b test", "ab test",
    "ndcg", "mrr", "precision", "recall", "evaluation",
    "fine-tun", "lora", "qlora", "peft",
    "transformer", "bert", "gpt", "llm",
    "sentence-transformer", "bge", "e5",
    "pytorch", "tensorflow", "keras",
    "mlops", "ml pipeline", "model serving",
    "inference", "latency", "throughput",
    "nlp", "natural language", "information retrieval",
    "search system", "search engine", "search infrastructure",
    "candidate matching", "talent", "recruiting",
    "hybrid search", "bm25", "tfidf", "tf-idf",
    "feature engineering", "feature store",
    "real-time", "real time", "batch processing",
    "spark", "airflow", "kafka",
    "data pipeline", "etl",
    "xgboost", "lightgbm", "learning to rank", "learn-to-rank",
    "model training", "model evaluation", "model deployment",
]

# Keywords indicating "shipper" vs "researcher" (JD prefers shippers)
SHIPPER_KEYWORDS = [
    "shipped", "launched", "deployed", "production", "live",
    "users", "customers", "scale", "scaled",
    "startup", "series a", "series b", "early stage",
    "product", "feature", "release", "sprint",
    "agile", "scrum", "kanban",
    "metrics", "kpi", "revenue", "growth",
    "api", "microservice", "backend", "frontend",
]

RESEARCHER_KEYWORDS = [
    "paper", "publication", "journal", "conference",
    "thesis", "dissertation", "phd",
    "academic", "university lab", "research lab",
    "theoretical", "proof",
]

# Location preferences
PREFERRED_LOCATIONS = [
    "pune", "noida", "delhi", "delhi ncr", "gurgaon", "gurugram",
    "new delhi", "greater noida", "faridabad", "ghaziabad",
]

TIER1_INDIAN_CITIES = [
    "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "ahmedabad", "jaipur",
]


def _normalize(text):
    """Lowercase and strip for matching."""
    return text.strip().lower() if text else ""


def _company_is_consulting(company_name):
    """Check if company is a pure consulting/services firm."""
    name = _normalize(company_name)
    return any(c in name for c in CONSULTING_COMPANIES)


def _company_is_product(company_name):
    """Check if company is a known product company."""
    name = _normalize(company_name)
    return any(c in name for c in KNOWN_PRODUCT_COMPANIES)


def _count_keywords(text, keywords):
    """Count how many distinct keywords appear in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def _get_title_score(title):
    """Get title relevance score, with fuzzy matching for variations."""
    t = _normalize(title)

    # Direct lookup
    if t in TITLE_TIER:
        return TITLE_TIER[t]

    # Fuzzy matching for title variations
    best = 0.0
    for known_title, score in TITLE_TIER.items():
        if known_title in t or t in known_title:
            best = max(best, score)

    # Check for AI/ML keywords in title
    ai_keywords = ["ai", "machine learning", "ml", "deep learning",
                    "nlp", "data scien", "artificial intelligence"]
    for kw in ai_keywords:
        if kw in t:
            best = max(best, 0.75)

    return best


def score_career_fit(candidate):
    """
    Score a candidate's career fit (0.0 to 1.0).

    Components:
    - Title relevance (40% weight)
    - Experience band fit (15% weight)
    - Industry/company quality (15% weight)
    - Production ML evidence in career descriptions (20% weight)
    - Location fit (10% weight)
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    signals = candidate.get("redrob_signals", {})

    # ── 1. Title Relevance (40%) ────────────────────────────────────────────
    current_title = profile.get("current_title", "")
    title_score = _get_title_score(current_title)

    # Also check career history for past ML/AI roles
    past_ml_title_bonus = 0.0
    for job in career:
        job_title_score = _get_title_score(job.get("title", ""))
        if job_title_score > 0.7:
            past_ml_title_bonus = max(past_ml_title_bonus, job_title_score * 0.3)

    title_score = min(1.0, title_score + past_ml_title_bonus)

    # ── 2. Experience Band (15%) ────────────────────────────────────────────
    yoe = profile.get("years_of_experience", 0)
    # JD says 5-9 years, but seriously considers outside if strong signals
    if 5 <= yoe <= 9:
        exp_score = 1.0
    elif 4 <= yoe < 5:
        exp_score = 0.85
    elif 9 < yoe <= 12:
        exp_score = 0.80
    elif 3 <= yoe < 4:
        exp_score = 0.60
    elif 12 < yoe <= 15:
        exp_score = 0.65
    elif yoe > 15:
        exp_score = 0.40  # Too senior / likely architecture-only
    elif yoe < 3:
        exp_score = 0.25  # Too junior
    else:
        exp_score = 0.5

    # ── 3. Industry / Company Quality (15%) ─────────────────────────────────
    industry_score = 0.5  # Neutral baseline

    # Check current company
    current_company = profile.get("current_company", "")
    if _company_is_consulting(current_company):
        # JD explicitly warns about only-consulting careers
        # Check if they have ANY product company experience
        has_product_exp = any(
            _company_is_product(job.get("company", "")) or
            not _company_is_consulting(job.get("company", ""))
            for job in career if not job.get("is_current", False)
        )
        if has_product_exp:
            industry_score = 0.50  # Consulting now but has product exp → OK
        else:
            industry_score = 0.15  # Only consulting → poor fit

    elif _company_is_product(current_company):
        industry_score = 0.90

    # Check career for startup/product company experience
    startup_exp = False
    product_exp_count = 0
    for job in career:
        company = job.get("company", "")
        desc = job.get("description", "")
        if _company_is_product(company):
            product_exp_count += 1
        if any(kw in desc.lower() for kw in ["startup", "series a", "series b", "early stage", "seed"]):
            startup_exp = True

    if product_exp_count >= 2:
        industry_score = min(1.0, industry_score + 0.15)
    if startup_exp:
        industry_score = min(1.0, industry_score + 0.10)

    # Check for title-chasing pattern (JD explicitly flags this)
    if len(career) >= 3:
        durations = [job.get("duration_months", 24) for job in career]
        avg_tenure = sum(durations) / len(durations)
        if avg_tenure < 18:  # Average < 1.5 years = title chaser
            industry_score *= 0.7

    # Current industry check
    current_industry = _normalize(profile.get("current_industry", ""))
    tech_industries = ["technology", "software", "it services", "internet",
                       "saas", "cloud", "ai", "machine learning", "data",
                       "fintech", "e-commerce", "analytics"]
    if any(ind in current_industry for ind in tech_industries):
        industry_score = min(1.0, industry_score + 0.05)

    # ── 4. Production ML Evidence (20%) ─────────────────────────────────────
    # This is THE key differentiator — look at what they actually DID
    all_descriptions = " ".join(job.get("description", "") for job in career)
    summary = profile.get("summary", "")
    combined_text = all_descriptions + " " + summary

    prod_ml_count = _count_keywords(combined_text, PRODUCTION_ML_KEYWORDS)
    shipper_count = _count_keywords(combined_text, SHIPPER_KEYWORDS)
    researcher_count = _count_keywords(combined_text, RESEARCHER_KEYWORDS)

    # Normalize production ML evidence (0-1)
    prod_ml_score = min(1.0, prod_ml_count / 12.0)  # 12+ keywords = max

    # Shipper vs researcher bonus/penalty
    if shipper_count > researcher_count:
        prod_ml_score = min(1.0, prod_ml_score + 0.10)
    elif researcher_count > shipper_count + 3:
        prod_ml_score *= 0.80  # Pure researcher penalty

    # Special checks from JD:
    # "AI experience primarily from recent LangChain/OpenAI projects" → penalize
    if "langchain" in combined_text.lower() and prod_ml_count < 5:
        prod_ml_score *= 0.70

    # Check for specific systems the JD values
    high_value_systems = ["ranking system", "recommendation system", "search system",
                          "retrieval system", "matching system", "recommendation engine",
                          "search engine", "ranker", "recommender"]
    for sys_kw in high_value_systems:
        if sys_kw in combined_text.lower():
            prod_ml_score = min(1.0, prod_ml_score + 0.15)
            break

    # ── 5. Location Fit (10%) ───────────────────────────────────────────────
    location = _normalize(profile.get("location", ""))
    country = _normalize(profile.get("country", ""))
    willing_to_relocate = signals.get("willing_to_relocate", False)
    preferred_work_mode = signals.get("preferred_work_mode", "")

    if country != "india" and country != "":
        # Outside India — JD says case-by-case, no visa sponsorship
        location_score = 0.20
        if willing_to_relocate:
            location_score = 0.35
    elif any(city in location for city in PREFERRED_LOCATIONS):
        location_score = 1.0  # Pune/Noida/Delhi NCR
    elif any(city in location for city in TIER1_INDIAN_CITIES):
        location_score = 0.75  # Other Tier-1 Indian cities
        if willing_to_relocate:
            location_score = 0.90
    elif country == "india":
        location_score = 0.55
        if willing_to_relocate:
            location_score = 0.70
    else:
        location_score = 0.40

    # Work mode: JD says hybrid (flexible cadence)
    if preferred_work_mode in ("hybrid", "flexible"):
        location_score = min(1.0, location_score + 0.05)
    elif preferred_work_mode == "remote" and not willing_to_relocate:
        location_score *= 0.90  # Slight penalty

    # ── Composite Score ─────────────────────────────────────────────────────
    composite = (
        0.40 * title_score +
        0.15 * exp_score +
        0.15 * industry_score +
        0.20 * prod_ml_score +
        0.10 * location_score
    )

    return {
        "career_fit_score": round(composite, 4),
        "title_score": round(title_score, 4),
        "exp_score": round(exp_score, 4),
        "industry_score": round(industry_score, 4),
        "prod_ml_score": round(prod_ml_score, 4),
        "location_score": round(location_score, 4),
    }
