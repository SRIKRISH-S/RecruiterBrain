import streamlit as st
import json
import pandas as pd
import sys
import time
import io
import csv
from pathlib import Path

# Add the parent directory of scoring to python path
sys.path.insert(0, str(Path(__file__).parent))

from scoring.career_fit import score_career_fit
from scoring.skills_intelligence import score_skills
from scoring.behavioral_signals import score_behavioral
from scoring.honeypot_detector import detect_honeypot
from scoring.reasoning import generate_reasoning

# Page config
st.set_page_config(
    page_title="RecruiterBrain — Sandbox & Demo",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS
st.markdown("""
<style>
    /* Dark mode premium look */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a22 100%);
        color: #e2e8f0;
    }
    
    /* Sleek card styling */
    .card {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .card-title {
        color: #3b82f6;
        font-weight: 700;
        font-size: 1.25rem;
        margin-bottom: 10px;
    }
    
    .metric-value {
        font-size: 2.25rem;
        font-weight: 800;
        background: linear-gradient(to right, #60a5fa, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Table styling */
    .dataframe {
        background-color: #1f2937 !important;
        color: #e2e8f0 !important;
        border-radius: 8px;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 75%;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 0.375rem;
        margin-right: 5px;
    }
    .badge-success { background-color: #059669; color: white; }
    .badge-warning { background-color: #d97706; color: white; }
    .badge-danger { background-color: #dc2626; color: white; }
    .badge-info { background-color: #2563eb; color: white; }
</style>
""", unsafe_allow_input_html=True)

# Application Header
st.title("🧠 RecruiterBrain Sandbox")
st.markdown("##### Intelligent Candidate Discovery & Ranking Engine — Redrob Hackathon Submission")
st.markdown("---")

# Sidebar - Settings & Customization
st.sidebar.header("Scoring Engine Controls")

st.sidebar.markdown("### Layer Weights")
st.sidebar.caption("Adjust the weights of the 5 scoring layers. Must sum to 100%.")

w_career = st.sidebar.slider("Career Fit (L1+L2)", 0, 100, 40, 5)
w_skills = st.sidebar.slider("Skills Intelligence (L3)", 0, 100, 30, 5)
w_behavioral = st.sidebar.slider("Behavioral Signals (L4)", 0, 100, 20, 5)
w_education = st.sidebar.slider("Education (Bonus)", 0, 100, 10, 5)

total_weight = w_career + w_skills + w_behavioral + w_education
if total_weight != 100:
    st.sidebar.error(f"Total weight is {total_weight}%. It must sum to exactly 100%!")
else:
    st.sidebar.success("Weights sum to 100%!")

st.sidebar.markdown("### Honeypot Controls")
hard_filter_honeypots = st.sidebar.checkbox("Hard Filter Honeypots (Crush score to ~0)", value=True)

# Preloaded data path
DEFAULT_CANDIDATES_PATH = Path(__file__).parent / "sample_candidates.json"

st.sidebar.markdown("### Input Dataset Source")
dataset_source = st.sidebar.radio(
    "Choose data source:",
    ("Use Preloaded Sample (50 Candidates)", "Upload custom JSON/JSONL file")
)

uploaded_file = None
if dataset_source == "Upload custom JSON/JSONL file":
    uploaded_file = st.sidebar.file_uploader("Upload candidates file", type=["json", "jsonl"])

# Load candidates
candidates = []
source_name = ""

if dataset_source == "Use Preloaded Sample (50 Candidates)":
    if DEFAULT_CANDIDATES_PATH.exists():
        try:
            with open(DEFAULT_CANDIDATES_PATH, "r", encoding="utf-8") as f:
                candidates_data = json.load(f)
                if isinstance(candidates_data, list):
                    candidates = candidates_data
                else:
                    candidates = [candidates_data]
            source_name = "Preloaded Sample"
        except Exception as e:
            st.error(f"Error loading preloaded candidates: {e}")
    else:
        st.error(f"Preloaded sample candidates not found at {DEFAULT_CANDIDATES_PATH}. Please upload a file.")
else:
    if uploaded_file is not None:
        try:
            file_contents = uploaded_file.read().decode("utf-8")
            # Try loading as JSON list
            try:
                candidates = json.loads(file_contents)
                if not isinstance(candidates, list):
                    candidates = [candidates]
            except json.JSONDecodeError:
                # Try loading as JSONL
                candidates = []
                for line in file_contents.splitlines():
                    if line.strip():
                        candidates.append(json.loads(line))
            source_name = uploaded_file.name
        except Exception as e:
            st.error(f"Error parsing uploaded file: {e}")

# Helper functions for calculations
def score_edu_local(candidate):
    education = candidate.get("education", [])
    if not education:
        return {"education_score": 0.3}

    best_score = 0.0
    for edu in education:
        tier = edu.get("tier", "unknown")
        degree = edu.get("degree", "").lower()
        field = edu.get("field_of_study", "").lower()

        tier_scores = {
            "tier_1": 1.0, "tier_2": 0.75, "tier_3": 0.50, "tier_4": 0.35, "unknown": 0.40
        }
        tier_score = tier_scores.get(tier, 0.40)

        degree_scores = {
            "ph.d.": 0.85, "phd": 0.85, "ph.d": 0.85,
            "m.tech": 0.90, "m.tech.": 0.90, "mtech": 0.90,
            "m.s.": 0.85, "ms": 0.85, "m.sc.": 0.80, "m.e.": 0.85, "me": 0.85,
            "mba": 0.60,
            "b.tech": 0.70, "b.tech.": 0.70, "btech": 0.70,
            "b.e.": 0.70, "be": 0.65, "b.e": 0.70,
            "b.sc.": 0.55, "bsc": 0.55, "b.sc": 0.55,
            "b.s.": 0.60, "bs": 0.60, "bca": 0.50, "mca": 0.65, "diploma": 0.35,
        }
        degree_score = 0.50
        for deg_key, deg_val in degree_scores.items():
            if deg_key in degree:
                degree_score = deg_val
                break

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

def compute_final_score_local(career_scores, skills_scores, behavioral_scores, education_scores, honeypot_result, w_c, w_s, w_b, w_e):
    career = career_scores.get("career_fit_score", 0)
    skills_val = skills_scores.get("skills_score", 0)
    behavioral = behavioral_scores.get("behavioral_score", 0)
    education = education_scores.get("education_score", 0)

    composite = (
        (w_c / 100.0) * career +
        (w_s / 100.0) * skills_val +
        (w_b / 100.0) * behavioral +
        (w_e / 100.0) * education
    )

    if hard_filter_honeypots and honeypot_result.get("is_honeypot", False):
        composite *= 0.01

    if skills_scores.get("is_keyword_stuffer", False):
        stuffer_conf = skills_scores.get("stuffer_confidence", 0)
        composite *= max(0.1, 1.0 - stuffer_conf * 0.5)

    return round(composite, 6)

def run_ranking(candidates_list, w_c, w_s, w_b, w_e):
    results = []
    honeypots = 0
    stuffers = 0
    
    for candidate in candidates_list:
        career_scores = score_career_fit(candidate)
        skills_scores = score_skills(candidate)
        behavioral_scores = score_behavioral(candidate)
        honeypot_result = detect_honeypot(candidate)
        education_scores = score_edu_local(candidate)
        
        final_score = compute_final_score_local(
            career_scores, skills_scores, behavioral_scores, education_scores, honeypot_result,
            w_c, w_s, w_b, w_e
        )
        
        all_scores = {}
        all_scores.update(career_scores)
        all_scores.update(skills_scores)
        all_scores.update(behavioral_scores)
        all_scores.update(education_scores)
        all_scores.update(honeypot_result)
        all_scores["final_score"] = final_score
        
        if honeypot_result.get("is_honeypot", False):
            honeypots += 1
        if skills_scores.get("is_keyword_stuffer", False):
            stuffers += 1
            
        results.append({
            "candidate_id": candidate.get("candidate_id", ""),
            "candidate": candidate,
            "scores": all_scores,
            "final_score": final_score,
        })
        
    # Sort results
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results, honeypots, stuffers

# Main Area UI
if not candidates:
    st.info("👋 Welcome to the Sandbox! Please upload a candidates dataset or choose the preloaded sample from the sidebar to begin.")
else:
    if total_weight != 100:
        st.warning("⚠️ Please adjust the sidebar sliders so that they sum to exactly 100% to run the ranking engine.")
    else:
        st.success(f"Loaded {len(candidates)} candidates from {source_name}. Running RecruiterBrain ranking engine...")
        
        start_t = time.time()
        results, honeypots_caught, stuffers_caught = run_ranking(candidates, w_career, w_skills, w_behavioral, w_education)
        elapsed_t = time.time() - start_t
        
        # Display Overview Stats Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">Processed</div>
                <div class="metric-value">{len(candidates)}</div>
                <div style="font-size: 0.8rem; color: #9ca3af;">Total Candidates</div>
            </div>
            """, unsafe_allow_input_html=True)
        with col2:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">Speed</div>
                <div class="metric-value">{elapsed_t:.4f}s</div>
                <div style="font-size: 0.8rem; color: #9ca3af;">Processing Time</div>
            </div>
            """, unsafe_allow_input_html=True)
        with col3:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">Honeypots Caught</div>
                <div class="metric-value">{honeypots_caught}</div>
                <div style="font-size: 0.8rem; color: #9ca3af;">Impossible Profiles Filtered</div>
            </div>
            """, unsafe_allow_input_html=True)
        with col4:
            st.markdown(f"""
            <div class="card">
                <div class="card-title">Keyword Stuffers</div>
                <div class="metric-value">{stuffers_caught}</div>
                <div style="font-size: 0.8rem; color: #9ca3af;">Penalized Keyword Stuffers</div>
            </div>
            """, unsafe_allow_input_html=True)
            
        # Display Leaderboard
        st.markdown("### 🏆 Candidate Leaderboard")
        st.caption("Top matching candidates based on your weight configuration.")
        
        # Prepare tabular data for display
        table_rows = []
        for rank, r in enumerate(results, 1):
            cand = r["candidate"]
            scores = r["scores"]
            
            # Extract current job details if available
            jobs = cand.get("experience", [])
            current_job = "Unemployed / Not Specified"
            if jobs:
                current_job = f"{jobs[0].get('title', 'Engineer')} @ {jobs[0].get('company', 'Unknown')}"
                
            badges = []
            if scores.get("is_honeypot", False):
                badges.append("🚨 Honeypot")
            if scores.get("is_keyword_stuffer", False):
                badges.append("⚠️ Stuffer")
                
            table_rows.append({
                "Rank": rank,
                "Candidate ID": r["candidate_id"],
                "Score": round(r["final_score"], 4),
                "Career Fit": round(scores.get("career_fit_score", 0), 2),
                "Skills Score": round(scores.get("skills_score", 0), 2),
                "Behavioral Score": round(scores.get("behavioral_score", 0), 2),
                "Education Score": round(scores.get("education_score", 0), 2),
                "Current Job": current_job,
                "Status": ", ".join(badges) if badges else "Verified ✅"
            })
            
        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # CSV Download Button
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["candidate_id", "score", "reasoning"])
        for r in results:
            cand = r["candidate"]
            scores = r["scores"]
            reasoning = generate_reasoning(cand, scores)
            writer.writerow([r["candidate_id"], round(r["final_score"], 6), reasoning])
            
        st.download_button(
            label="📥 Download Ranked Submission CSV",
            data=csv_data.getvalue(),
            file_name="submission.csv",
            mime="text/csv"
        )
        
        # Candidate Detail Inspector
        st.markdown("---")
        st.markdown("### 🔍 Candidate Profile Inspector")
        st.caption("Select a candidate to view their complete profile, scoring breakdowns, and AI recruiter reasoning.")
        
        cand_options = {f"Rank {row['Rank']}: {row['Candidate ID']} ({row['Current Job']})": row['Rank'] - 1 for row in table_rows}
        selected_option = st.selectbox("Select Candidate to Inspect:", list(cand_options.keys()))
        
        if selected_option:
            idx = cand_options[selected_option]
            selected_cand = results[idx]
            cand = selected_cand["candidate"]
            scores = selected_cand["scores"]
            
            col_l, col_r = st.columns([2, 3])
            
            with col_l:
                st.markdown("#### 📊 Score Analysis")
                st.metric("Final Score", f"{selected_cand['final_score']:.4f}")
                
                # Simple progress bars for layers
                st.write(f"**Career Fit Layer:** {scores.get('career_fit_score', 0.0):.2f}")
                st.progress(min(max(float(scores.get('career_fit_score', 0.0)), 0.0), 1.0))
                
                st.write(f"**Skills Intelligence Layer:** {scores.get('skills_score', 0.0):.2f}")
                st.progress(min(max(float(scores.get('skills_score', 0.0)), 0.0), 1.0))
                
                st.write(f"**Behavioral Signals Layer:** {scores.get('behavioral_score', 0.0):.2f}")
                st.progress(min(max(float(scores.get('behavioral_score', 0.0)), 0.0), 1.0))
                
                st.write(f"**Education Bonus Layer:** {scores.get('education_score', 0.0):.2f}")
                st.progress(min(max(float(scores.get('education_score', 0.0)), 0.0), 1.0))
                
                # Check status
                if scores.get("is_honeypot", False):
                    st.error("🚨 **Honeypot Profile Detected!** This profile exhibits impossible career dates or contradictory signals. Score has been heavily penalized.")
                elif scores.get("is_keyword_stuffer", False):
                    st.warning(f"⚠️ **Keyword Stuffing Detected (Confidence: {scores.get('stuffer_confidence', 0.0):.2f})!** Candidate has claimed multiple expert skills with insufficient backing in career descriptions or tenure. Score was down-weighted.")
                else:
                    st.success("✅ **Profile Verified.** Authentic skill and career trajectory profile.")
                    
                # Explain reasoning
                st.markdown("#### 🤖 AI Recruiter Reasoning")
                reasoning = generate_reasoning(cand, scores)
                st.info(reasoning)
                
            with col_r:
                st.markdown("#### 💼 Resume Details")
                
                # Basic info
                col_i1, col_i2 = st.columns(2)
                with col_i1:
                    st.write(f"**Primary Location:** {cand.get('location', 'Not Specified')}")
                    st.write(f"**Notice Period:** {cand.get('notice_period', 'Not Specified')} days")
                with col_i2:
                    st.write(f"**Expected Salary:** ₹{cand.get('expected_salary', 'Not Specified')}/year")
                    st.write(f"**Recruiter Response Rate:** {cand.get('recruiter_response_rate', 'Not Specified')}%")
                
                # Skills section
                st.write("**Skills:**")
                skills = cand.get("skills", [])
                skills_html = ""
                for s in skills:
                    name = s.get("name", "")
                    lvl = s.get("level", "intermediate")
                    dur = s.get("duration_months", 0)
                    ends = s.get("endorsements", 0)
                    
                    bg_color = "#3b82f6" if lvl == "expert" else "#10b981" if lvl == "intermediate" else "#6b7280"
                    skills_html += f'<span class="badge" style="background-color: {bg_color}; color: white; margin-bottom: 5px;">{name} ({lvl}, {dur}m, {ends}⭐)</span>'
                st.markdown(skills_html, unsafe_allow_input_html=True)
                
                # Experience section
                st.write("**Work Experience:**")
                for exp in cand.get("experience", []):
                    with st.expander(f"**{exp.get('title')}** @ {exp.get('company')} ({exp.get('duration_months', 0)} months)"):
                        st.write(f"*Location:* {exp.get('location', 'Not Specified')} | *Employment Type:* {exp.get('employment_type', 'Full-time')}")
                        st.write(exp.get("description", "No description provided."))
                        
                # Education section
                st.write("**Education:**")
                for edu in cand.get("education", []):
                    st.markdown(f"- **{edu.get('degree')} in {edu.get('field_of_study')}** — *{edu.get('institution')}* ({edu.get('tier', 'unknown').upper()})")
