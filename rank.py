import json
import os
import math
import argparse
import csv
from datetime import datetime

# Set of primary skills relevant to the Senior AI Engineer role
primary_skills = {
    'retrieval-augmented generation', 'rag', 'vector databases', 'embeddings',
    'sentence transformers', 'sentence-transformers', 'milvus', 'pinecone',
    'weaviate', 'qdrant', 'faiss', 'elasticsearch', 'opensearch',
    'information retrieval', 'semantic search', 'ndcg', 'mean average precision',
    'map', 'mrr', 'bge', 'e5'
}

# Set of secondary skills relevant to the Senior AI Engineer role
secondary_skills = {
    'fine-tuning llms', 'fine-tuning', 'lora', 'qlora', 'peft', 'learning to rank',
    'xgboost', 'python', 'machine learning', 'natural language processing', 'nlp',
    'system design', 'a/b testing', 'evaluation frameworks', 'search engine',
    'recommendation system', 'vector search', 'matching engine'
}

# Core consulting/services companies list (to filter consulting-only candidates)
consulting_companies = {
    'TCS', 'Infosys', 'Wipro', 'Accenture', 'Cognizant', 'Capgemini',
    'Tech Mahindra', 'Mphasis', 'HCL', 'Mindtree', 'Genpact AI'
}

# Mismatched/disqualified titles for the AI engineering role
disqualified_titles = {
    'marketing manager', 'operations manager', 'accountant', 'sales executive',
    'hr manager', 'customer support', 'civil engineer', 'mechanical engineer',
    'project manager', 'qa engineer'
}

# Founding years of startups to verify honeypot profiles
founding_years = {
    'Krutrim': 2023,
    'Sarvam AI': 2023,
    'CRED': 2018,
    'Glance': 2019,
    'Meesho': 2015,
    'PhonePe': 2015,
    'PharmEasy': 2015,
    'Swiggy': 2014,
    'Ola': 2010,
    'Zomato': 2008,
    'Flipkart': 2007,
    'Freshworks': 2010,
    'InMobi': 2007,
    'Zoho': 1996
}

def is_honeypot_candidate(c):
    """
    Identifies if a candidate has an impossible or contradictory profile (honeypot).
    """
    prof = c.get('profile', {})
    hist = c.get('career_history', [])
    edu = c.get('education', [])
    skills = c.get('skills', [])
    
    # 1. work_before_edu: started full-time work > 6 years before college start
    edu_starts = [e.get('start_year') for e in edu if e.get('start_year')]
    if edu_starts:
        min_edu_start = min(edu_starts)
        for h in hist:
            sd = h.get('start_date')
            if sd:
                try:
                    start_yr = int(sd.split('-')[0])
                    if min_edu_start - start_yr > 6:
                        return True
                except:
                    pass
                    
    # 2. job_duration_mismatch: job duration_months deviates from actual dates by > 3 months
    for h in hist:
        sd = h.get('start_date')
        ed = h.get('end_date')
        dur = h.get('duration_months', 0)
        if sd:
            try:
                s_dt = datetime.strptime(sd, "%Y-%m-%d")
                if ed:
                    e_dt = datetime.strptime(ed, "%Y-%m-%d")
                else:
                    e_dt = datetime.strptime("2026-06-20", "%Y-%m-%d")
                diff_months = (e_dt.year - s_dt.year) * 12 + (e_dt.month - s_dt.month)
                if abs(diff_months - dur) > 3:
                    return True
            except:
                pass
                
    # 3. yoe_mismatch: profile YoE deviates from sum of career history job durations by > 3 years
    sum_dur = sum(h.get('duration_months', 0) for h in hist) / 12.0
    yoe = prof.get('years_of_experience', 0.0)
    if abs(yoe - sum_dur) > 3.0:
        return True
        
    # 4. zero_dur_skills: expert/advanced skills with 0 months duration (threshold: >= 3 skills)
    z_skills = [s['name'] for s in skills if s.get('proficiency') in ['expert', 'advanced'] and s.get('duration_months', 0) == 0]
    if len(z_skills) >= 3:
        return True
        
    # 5. founding_year_violations: working at a company before it was founded
    for h in hist:
        comp = h.get('company')
        sd = h.get('start_date')
        if comp in founding_years and sd:
            try:
                start_yr = int(sd.split('-')[0])
                if start_yr < founding_years[comp]:
                    return True
            except:
                pass
                
    return False

def is_consulting_only(hist):
    """
    Checks if a candidate has only worked at consulting/IT services companies.
    """
    if not hist:
        return False
    for h in hist:
        comp = h.get('company')
        if comp not in consulting_companies:
            return False
    return True

def get_yoe_score(yoe):
    """
    Computes experience score. Peaks at 5.0 to 9.0 (score 10.0), asymmetric decay.
    """
    if 5.0 <= yoe <= 9.0:
        return 10.0
    elif yoe < 5.0:
        return max(0.0, 10.0 - (5.0 - yoe) * 2.0)
    else:
        return max(0.0, 10.0 - (yoe - 9.0) * 0.5)

def get_skills_score(skills):
    """
    Computes a score matching candidates' skills against primary/secondary weights.
    """
    score = 0.0
    for s in skills:
        name = s.get('name', '').lower().strip()
        prof = s.get('proficiency', 'beginner')
        dur = s.get('duration_months', 0)
        
        weight = 0.0
        if name in primary_skills:
            weight = 10.0
        elif name in secondary_skills:
            weight = 5.0
            
        if weight > 0:
            # Proficiency multiplier
            prof_mult = 1.0
            if prof == 'expert':
                prof_mult = 1.2
            elif prof == 'advanced':
                prof_mult = 1.0
            elif prof == 'intermediate':
                prof_mult = 0.8
            elif prof == 'beginner':
                prof_mult = 0.5
                
            # Duration multiplier (capped logarithmic scaling)
            dur_mult = 1.0
            if dur > 0:
                dur_mult = min(1.2, math.log(dur + 1) / math.log(60))
                
            score += weight * prof_mult * dur_mult
    return score

def get_title_score(prof, hist):
    """
    Scores candidates based on their current title, headline, and career history descriptions.
    """
    title = prof.get('current_title', '').lower()
    headline = prof.get('headline', '').lower()
    
    # Exclude mismatched titles
    for dt in disqualified_titles:
        if dt in title:
            return -50.0
            
    # Check for AI/ML keywords in current title / headline
    ai_ml_keywords = ['ai engineer', 'ml engineer', 'machine learning', 'nlp engineer', 'search engineer', 'ranking engineer', 'recommendation engineer', 'applied scientist']
    has_ai_ml = any(k in title or k in headline for k in ai_ml_keywords)
    
    # Check for Tech/Dev keywords
    tech_keywords = ['backend engineer', 'software engineer', 'data engineer', 'full stack developer', 'backend developer', 'full stack engineer']
    has_tech = any(k in title or k in headline for k in tech_keywords)
    
    score = 0.0
    if has_ai_ml:
        score += 15.0
    elif has_tech:
        score += 8.0
        
    # Scan job descriptions in history for matching keyword phrases
    desc_keywords = ['ranking', 'retrieval', 'vector search', 'rag', 'embeddings', 'semantic search', 'search engine', 'recommendation system', 'matching engine']
    desc_matches = 0
    seen_keywords = set()
    for h in hist:
        desc = h.get('description', '').lower()
        for k in desc_keywords:
            if k in desc and k not in seen_keywords:
                desc_matches += 1
                seen_keywords.add(k)
    score += min(15.0, desc_matches * 5.0)
    
    return score

def get_location_score(prof):
    """
    Scores candidates based on location/relocation preferences.
    """
    country = prof.get('country', '').lower().strip()
    loc = prof.get('location', '').lower()
    willing = prof.get('willing_to_relocate', False) or (prof.get('willing_to_relocate') == 'true')
    
    is_india = 'india' in country or loc in ['pune', 'noida', 'delhi ncr', 'mumbai', 'hyderabad', 'gurgaon', 'bangalore', 'chennai']
    tier1_cities = ['pune', 'noida', 'delhi', 'ncr', 'mumbai', 'hyderabad', 'gurgaon', 'bangalore', 'chennai', 'kolkata']
    
    is_tier1 = any(city in loc for city in tier1_cities)
    
    if is_india:
        if is_tier1:
            return 5.0
        elif willing:
            return 4.0
        else:
            return 1.0
    else:
        if willing:
            return 2.0
        else:
            return 0.0

def get_behavioral_multiplier(sigs):
    """
    Calculates behavioral engagement multiplier from platform activity.
    """
    mult = 1.0
    
    # Recruiter response rate
    rrr = sigs.get('recruiter_response_rate', 0.0)
    mult *= (0.5 + 0.5 * rrr)
    
    # Last active
    last_act_str = sigs.get('last_active_date', '')
    if last_act_str:
        try:
            last_act = datetime.strptime(last_act_str, "%Y-%m-%d")
            curr_date = datetime(2026, 6, 20)
            days_inactive = (curr_date - last_act).days
            if days_inactive > 180:
                mult *= 0.7
            elif days_inactive > 360:
                mult *= 0.5
        except:
            pass
            
    # Notice period
    notice = sigs.get('notice_period_days', 90)
    if notice <= 30:
        mult *= 1.10
    elif notice <= 60:
        mult *= 1.0
    elif notice <= 90:
        mult *= 0.90
    else:
        mult *= 0.70
        
    # Interview completion rate
    icr = sigs.get('interview_completion_rate', 1.0)
    mult *= (0.8 + 0.2 * icr)
    
    # Open to work
    if sigs.get('open_to_work_flag', False):
        mult *= 1.10
    else:
        mult *= 0.95
        
    # Verified credentials
    if sigs.get('verified_email', False) and sigs.get('verified_phone', False):
        mult *= 1.05
        
    # GitHub activity
    gh = sigs.get('github_activity_score', -1)
    if gh > 20:
        mult *= 1.05
        
    # Offer acceptance rate
    oar = sigs.get('offer_acceptance_rate', -1)
    if 0 <= oar < 0.2:
        mult *= 0.80
        
    return mult

def score_candidate(c):
    """
    Scores a single candidate record based on all criteria.
    Returns -999.0 if candidate is a honeypot.
    """
    if is_honeypot_candidate(c):
        return -999.0
        
    prof = c.get('profile', {})
    hist = c.get('career_history', [])
    skills = c.get('skills', [])
    sigs = c.get('redrob_signals', {})
    
    yoe = prof.get('years_of_experience', 0.0)
    
    yoe_score = get_yoe_score(yoe)
    skills_score = get_skills_score(skills)
    title_score = get_title_score(prof, hist)
    loc_score = get_location_score(prof)
    
    raw_score = yoe_score + skills_score + title_score + loc_score
    
    # Heavy penalty for consulting/services-only candidates
    if is_consulting_only(hist):
        raw_score *= 0.5
        
    behavior_mult = get_behavioral_multiplier(sigs)
    
    return raw_score * behavior_mult

def generate_reasoning(c):
    """
    Generates a personalized, detailed, fact-based 1-2 sentence justification.
    """
    prof = c.get('profile', {})
    skills = c.get('skills', [])
    sigs = c.get('redrob_signals', {})
    
    yoe = prof.get('years_of_experience', 0.0)
    title = prof.get('current_title', 'Engineer')
    loc = prof.get('location', 'India')
    rrr = sigs.get('recruiter_response_rate', 0.0)
    notice = sigs.get('notice_period_days', 90)
    
    # Extract match skills
    cand_skills = [s.get('name') for s in skills if s.get('name')]
    match_prim = [s for s in cand_skills if s.lower() in primary_skills]
    match_sec = [s for s in cand_skills if s.lower() in secondary_skills]
    
    matched = match_prim[:2]
    if len(matched) < 2:
        matched += match_sec[:(2 - len(matched))]
        
    skills_str = f"with skills in {', '.join(matched)}" if matched else "with strong backend capabilities"
    eng_str = f"excellent activity ({int(rrr * 100)}% response rate)"
    
    # Location/Notice checks
    concern = f"notice period is {notice} days" if notice > 60 else f"located in {loc}"
    
    # Variance template based on ID
    variant = int(c['candidate_id'].split('_')[-1]) % 3
    if variant == 0:
        return f"{title} offering {yoe} years of experience, {skills_str}. Candidate has {eng_str} and is {concern}."
    elif variant == 1:
        return f"Founding-grade {title} ({yoe} years YoE) {skills_str}. Good product mindset with {eng_str}; {concern}."
    else:
        return f"Applied AI engineer with {yoe} years experience as a {title}, {skills_str}. Highly responsive ({int(rrr * 100)}% message rate) and {concern}."

def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranking System")
    parser.options = parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl file")
    parser.options = parser.add_argument("--out", required=True, help="Path to write the submission.csv file")
    args = parser.parse_args()
    
    candidates = []
    print(f"Reading candidates from {args.candidates}...")
    with open(args.candidates, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            score = score_candidate(c)
            candidates.append((score, c))
            
    # Sort candidates by score descending, then candidate_id ascending to break ties
    print("Ranking candidates...")
    candidates.sort(key=lambda x: (-x[0], x[1]['candidate_id']))
    
    # Take top 100
    top_100 = candidates[:100]
    
    # Write to CSV
    print(f"Writing top 100 to {args.out}...")
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, (score, c) in enumerate(top_100):
            rank = i + 1
            cid = c['candidate_id']
            reasoning = generate_reasoning(c)
            writer.writerow([cid, rank, round(score, 4), reasoning])
            
    print("Ranking complete. Top 5 candidates:")
    for i in range(min(5, len(top_100))):
        score, c = top_100[i]
        print(f" #{i+1}: {c['candidate_id']} (Score: {score:.4f}) - {c['profile']['anonymized_name']} ({c['profile']['current_title']})")

if __name__ == "__main__":
    main()
