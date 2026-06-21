import json
import os
import math
import argparse
import csv
from datetime import datetime

# IT consulting & services companies to penalize
consulting_companies = {
    'TCS', 'Infosys', 'Wipro', 'Accenture', 'Cognizant', 'Capgemini',
    'Tech Mahindra', 'Mphasis', 'HCL', 'Mindtree', 'Genpact AI',
    'Deloitte', 'PwC', 'EY', 'KPMG'
}

# disqualified roles for founding team fit
disqualified_titles = {
    'marketing manager', 'operations manager', 'accountant', 'sales executive',
    'hr manager', 'customer support', 'civil engineer', 'mechanical engineer',
    'project manager', 'qa engineer'
}

# startup founding dates (used to filter out chronological contradictions)
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

# target keywords parsed from job description
jd_keywords = {
    'rag', 'retrieval-augmented generation', 'vector', 'database', 'embeddings',
    'sentence-transformers', 'transformers', 'pinecone', 'weaviate', 'qdrant',
    'milvus', 'faiss', 'elasticsearch', 'opensearch', 'search', 'retrieval',
    'semantic', 'matching', 'ranking', 'recommendation', 'nlp', 'language',
    'ndcg', 'map', 'mrr', 'evaluation', 'xgboost', 'lora', 'qlora', 'peft',
    'fine-tuning', 'python', 'backend', 'system design'
}

similarity_cache = {}

def calculate_token_similarity(term, targets):
    # compute similarity between candidate terms and JD keywords using token Jaccard and n-grams
    term_lower = term.lower().strip()
    if term_lower in similarity_cache:
        return similarity_cache[term_lower]
        
    best_sim = 0.0
    for target in targets:
        # 1. Exact or substring check
        if term_lower == target or target in term_lower or term_lower in target:
            sim = 1.0
        else:
            # 2. Token overlap Jaccard similarity
            term_tokens = set(term_lower.split())
            target_tokens = set(target.split())
            if term_tokens and target_tokens:
                intersect = term_tokens.intersection(target_tokens)
                union = term_tokens.union(target_tokens)
                sim = len(intersect) / len(union)
            else:
                sim = 0.0
        
        # 3. Simple character n-gram fallback (length 3)
        if sim < 0.4 and len(term_lower) >= 3 and len(target) >= 3:
            t_grams = set(term_lower[i:i+3] for i in range(len(term_lower)-2))
            trg_grams = set(target[i:i+3] for i in range(len(target)-2))
            char_sim = len(t_grams.intersection(trg_grams)) / len(t_grams.union(trg_grams))
            sim = max(sim, char_sim)
            
        best_sim = max(best_sim, sim)
        
    similarity_cache[term_lower] = best_sim
    return best_sim

def is_honeypot_candidate(c):
    # check for logical contradictions in profile (mismatched duration, startup dates, etc.)
    prof = c.get('profile', {})
    hist = c.get('career_history', [])
    edu = c.get('education', [])
    skills = c.get('skills', [])
    
    # 1. work_before_edu: started working > 15 years before starting college (impossible age conflict)
    edu_starts = [e.get('start_year') for e in edu if e.get('start_year')]
    if edu_starts:
        min_edu_start = min(edu_starts)
        for h in hist:
            sd = h.get('start_date')
            if sd:
                try:
                    start_yr = int(sd.split('-')[0])
                    if min_edu_start - start_yr > 15:
                        return True
                except:
                    pass
                    
    # 2. job_duration_mismatch: duration exceeds date calendar range by factor of 2 + 12 months (impossible inflated duration)
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
                if dur > 2 * diff_months + 12:
                    return True
            except:
                pass
                
    # 3. education end_year precedes start_year
    for e in edu:
        sy = e.get('start_year')
        ey = e.get('end_year')
        if sy and ey and sy > ey:
            return True
            
    # 4. zero_dur_skills: expert/advanced skills with 0 months duration (threshold: >= 5 skills)
    z_skills = sum(1 for s in skills if s.get('proficiency') in ['expert', 'advanced'] and s.get('duration_months', 0) == 0)
    if z_skills >= 5:
        return True
        
    # 5. founding_year_violations: working at a company before its founding year
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

def calculate_consulting_ratio(hist):
    # calculate fraction of candidate's total duration spent in consulting
    if not hist:
        return 0.0
    consulting_months = 0
    total_months = 0
    for h in hist:
        dur = h.get('duration_months', 0)
        comp = h.get('company')
        total_months += dur
        if comp in consulting_companies:
            consulting_months += dur
    if total_months == 0:
        return 0.0
    return consulting_months / total_months

def get_yoe_score(yoe):
    # experience fit score (peaks at 5-9 years experience, max 25 pts)
    if 5.0 <= yoe <= 9.0:
        return 25.0
    elif yoe < 5.0:
        return max(0.0, 25.0 - (5.0 - yoe) * 5.0)
    else:
        return max(0.0, 25.0 - (yoe - 9.0) * 1.5)

def get_skills_score(skills):
    # skill scoring based on JD token similarity and duration (max 40 pts)
    if not skills:
        return 0.0
    total_match = 0.0
    for s in skills:
        name = s.get('name', '')
        prof = s.get('proficiency', 'beginner')
        dur = s.get('duration_months', 0)
        
        sim = calculate_token_similarity(name, jd_keywords)
        if sim > 0.4:
            # Proficiency multiplier
            prof_mult = 1.2 if prof == 'expert' else (1.0 if prof == 'advanced' else (0.8 if prof == 'intermediate' else 0.5))
            # Duration multiplier (capped logarithmic scaling)
            dur_mult = min(1.2, math.log(dur + 1) / math.log(60)) if dur > 0 else 1.0
            total_match += sim * prof_mult * dur_mult
            
    return min(40.0, total_match * 8.0)

def get_title_score(prof, hist):
    # title relevance score (checks current title, headline, and historical descriptions; max 25 pts)
    title = prof.get('current_title', '')
    headline = prof.get('headline', '')
    
    # filter out disqualified titles immediately
    for dt in disqualified_titles:
        if dt in title.lower():
            return -50.0
            
    cur_sim = max(calculate_token_similarity(title, jd_keywords), calculate_token_similarity(headline, jd_keywords))
    
    desc_matches = 0
    seen = set()
    for h in hist:
        desc = h.get('description', '')
        for t in jd_keywords:
            if t in desc.lower() and t not in seen:
                desc_matches += 1
                seen.add(t)
                
    hist_score = min(10.0, desc_matches * 2.5)
    return min(25.0, cur_sim * 15.0 + hist_score)

def get_location_score(prof):
    # location fit score (prioritizes pune/noida/tier-1 relocation, max 10 pts)
    country = prof.get('country', '').lower().strip()
    loc = prof.get('location', '').lower()
    willing = prof.get('willing_to_relocate', False) or (prof.get('willing_to_relocate') == 'true')
    
    is_india = 'india' in country or loc in ['pune', 'noida', 'delhi ncr', 'mumbai', 'hyderabad', 'gurgaon', 'bangalore', 'chennai']
    tier1_cities = ['pune', 'noida', 'delhi', 'ncr', 'mumbai', 'hyderabad', 'gurgaon', 'bangalore', 'chennai', 'kolkata']
    is_tier1 = any(city in loc for city in tier1_cities)
    
    if is_india:
        return 10.0 if is_tier1 else (8.0 if willing else 2.0)
    return 4.0 if willing else 0.0

def get_behavioral_multiplier(sigs):
    # behavioral modifier using average of platform engagement metrics
    scores = []
    
    # 1. Recruiter Response Rate (weight 3)
    rrr = sigs.get('recruiter_response_rate', 0.0)
    scores.append((rrr, 3))
    
    # 2. Last active days (weight 2)
    last_act_str = sigs.get('last_active_date', '')
    act_score = 1.0
    if last_act_str:
        try:
            last_act = datetime.strptime(last_act_str, "%Y-%m-%d")
            curr_date = datetime(2026, 6, 20)
            days_inactive = (curr_date - last_act).days
            # map inactivity to score decays
            if days_inactive > 360:
                act_score = 0.5
            elif days_inactive > 180:
                act_score = 0.7
        except:
            pass
    scores.append((act_score, 2))
    
    # 3. Notice period (weight 2)
    notice = sigs.get('notice_period_days', 90)
    notice_score = 1.1 if notice <= 30 else (1.0 if notice <= 60 else (0.8 if notice <= 90 else 0.5))
    scores.append((notice_score, 2))
    
    # 4. Open to Work Flag (weight 1)
    otw = 1.1 if sigs.get('open_to_work_flag', False) else 0.95
    scores.append((otw, 1))
    
    # Weighted average
    total_score = sum(val * wt for val, wt in scores)
    total_wt = sum(wt for val, wt in scores)
    avg_score = total_score / total_wt
    
    return max(0.5, min(1.2, avg_score))

def score_candidate(c):
    # master scoring wrapper (returns -999.0 for honeypots)
    if is_honeypot_candidate(c):
        return -999.0
        
    prof = c.get('profile', {})
    hist = c.get('career_history', [])
    sigs = c.get('redrob_signals', {})
    
    yoe = prof.get('years_of_experience', 0.0)
    
    yoe_score = get_yoe_score(yoe)
    skills_score = get_skills_score(c.get('skills', []))
    title_score = get_title_score(prof, hist)
    loc_score = get_location_score(prof)
    
    # Base Relevance Score (0 - 100 scale)
    raw_score = yoe_score + skills_score + title_score + loc_score
    
    # apply continuous consulting penalty
    c_ratio = calculate_consulting_ratio(hist)
    consulting_mult = 1.0 - 0.5 * c_ratio
    
    # get behavioral signal multiplier
    behavior_mult = get_behavioral_multiplier(sigs)
    
    return raw_score * consulting_mult * behavior_mult

def generate_reasoning(c):
    # generate fact-based justification sentence using top skills and signals
    prof = c.get('profile', {})
    skills = c.get('skills', [])
    sigs = c.get('redrob_signals', {})
    
    yoe = prof.get('years_of_experience', 0.0)
    title = prof.get('current_title', 'Engineer')
    loc = prof.get('location', 'India')
    rrr = sigs.get('recruiter_response_rate', 0.0)
    notice = sigs.get('notice_period_days', 90)
    
    # Find top matching skills
    cand_skills = [s.get('name') for s in skills if s.get('name')]
    matched = []
    for cs in cand_skills:
        if calculate_token_similarity(cs, jd_keywords) > 0.5:
            matched.append(cs)
            
    top_skills = matched[:2]
    skills_phrase = f"with experience in {', '.join(top_skills)}" if top_skills else "with strong backend capabilities"
    act_phrase = f"highly active on the platform ({int(rrr * 100)}% response rate)"
    
    # Handle location / notice gaps
    if notice > 60:
        gap_phrase = f"though notice period is {notice} days"
    elif 'india' not in prof.get('country', '').lower() and sigs.get('willing_to_relocate'):
        gap_phrase = "willing to relocate to India"
    else:
        gap_phrase = f"based in {loc}"
        
    variant = int(c['candidate_id'].split('_')[-1]) % 3
    if variant == 0:
        return f"{title} offering {yoe} years of experience, specializing in {skills_phrase}. The candidate is {act_phrase} and {gap_phrase}."
    elif variant == 1:
        return f"Product-oriented {title} ({yoe} years YoE) {skills_phrase}. Displays {act_phrase}; currently {gap_phrase}."
    else:
        return f"Applied AI professional ({yoe} years experience) currently working as a {title}, {skills_phrase}. {act_phrase} and {gap_phrase}."

def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranking System")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl file")
    parser.add_argument("--out", required=True, help="Path to write the submission.csv file")
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
