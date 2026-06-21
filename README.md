# India Runs: Intelligent Candidate Discovery & Ranking (Redrob AI)

This repository contains the code and implementation for **Track 01: The Data & AI Challenge** of the **India Runs** hackathon, organized by **Redrob AI** in partnership with **Hack2skill**.

## Project Overview

The objective of this challenge is to build an intelligent candidate discovery and ranking system that goes beyond simple keyword matching. The system ranks a 100,000-candidate synthetic pool to identify the top 100 best-fit candidates for a **Senior AI Engineer — Founding Team** role.

### Key Objectives:
1. **Semantic Matching:** Understand candidates' experience and roles contextually rather than matching surface keywords.
2. **Consulting-firm Detection:** Downweight candidates who have spent their entire careers in consulting/IT services companies (per the Job Description's explicit constraints).
3. **Honeypot Mitigation:** Detect and filter out ~80 impossible/contradictory profiles (honeypots) present in the dataset.
4. **Behavioral Integration:** Utilize the 23 behavioral platform signals (notice period, recruiter response rate, activity) to adjust ranking relevance.
5. **Reproducibility:** Run end-to-end on CPU with less than 16GB RAM in under 5 minutes without external network calls.

---

## Technical Design & Strategy

### 1. Anomaly & Honeypot Detection
Our ranking system includes a robust validator that screens candidates for synthetic logical contradictions, assigning a score of `-999.0` to filter them out entirely:
* **Skill experience mismatch:** Checks if candidates claim `expert` or `advanced` proficiency in 3+ skills with `duration_months == 0`.
* **Job duration contradictions:** Verifies that the reported job `duration_months` in the career history aligns closely (within 3 months) with the time difference between its `start_date` and `end_date`.
* **Education timing mismatch:** Flags candidates who started full-time work more than 6 years before beginning their college degree.
* **Startup founding dates:** Flags candidates who claim to have worked at startups like `Krutrim` before 2023, `Sarvam AI` before 2023, or `CRED` before 2018.

### 2. Candidate Fit Scoring
Candidates are scored based on the following:
* **Experience Curve:** Asymmetric scoring peaking around 5-9 years, with high penalties for junior profiles (< 3 years) and mild decay for senior profiles (> 9 years).
* **Skill Relevance:** Weighted score based on primary skills (RAG, Vector Databases, Embeddings, Semantic Search, evaluation metrics) and secondary skills (LLM fine-tuning, LoRA, Python, NLP).
* **Title & Career Relevance:** Boosts applied ML, NLP, search, and backend engineering titles, while penalizing completely mismatched titles (e.g. Accountant, Marketing Manager).
* **Location/Relocation score:** Prioritizes Noida/Pune-based or Tier-1 India relocation candidates.

### 3. Behavioral Multiplier
A multiplicative modifier scales the fit score based on real platform activity:
* Notice period (bonus for sub-30 days, penalty for >90 days).
* Recruiter response rate and interview completion rate.
* Platform activity decay (based on days since `last_active_date`).
* GitHub activity bonus.

### 4. Dynamically Tailored Reasonings
For the top 100 candidates, the system generates a tailored, fact-based reasoning statement highlighting exact years of experience, current role, primary skills, location fit, and active engagement metrics to pass manual review.

## Repository Structure

```
India-Runs/
├── data/                             # Raw candidate datasets and schemas
│   ├── candidates.jsonl              # Full dataset (100k candidates)
│   ├── sample_candidates.json        # Small sample candidates dataset
│   └── candidate_schema.json         # Candidate JSON schema
├── src/                              # Core candidate discovery and ranking code
│   └── rank.py                       # Main evaluation & ranking script
├── submission/                       # Challenge submissions and metadata
│   ├── submission.csv                # Output containing top 100 candidates
│   ├── sample_submission.csv         # Target submission layout reference
│   ├── submission_metadata.yaml      # Submission metadata with required stats
│   └── submission_metadata_template.yaml # Schema metadata template
├── report/                           # Reference files, analysis and validation notebooks
│   ├── validation.ipynb              # Jupyter notebook for scoring analysis & honeypots list
│   └── *.docx, *.txt                 # Hackathon instructions and Redrob signals documentation
└── testing/                          # Test scripts and format verification
    └── validate_submission.py        # Submission format compliance validator
```

## Getting Started

### Prerequisites
* Python 3.8+
* Standard libraries (`json`, `csv`, `math`, `datetime`, `argparse`)

### Installation & Run

1. Clone this repository:
   ```bash
   git clone https://github.com/adarsh3908/India-Runs.git
   cd India-Runs
   ```

2. Place the `candidates.jsonl` file in the `data/` directory.

3. Run the ranker:
   ```bash
   python src/rank.py --candidates data/candidates.jsonl --out submission/submission.csv
   ```

4. Validate the output format:
   ```bash
   python testing/validate_submission.py submission/submission.csv
   ```
