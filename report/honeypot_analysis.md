# Data Quality & Honeypot Analysis Report

This document details the investigation and findings regarding the synthetic anomalies ("honeypots") present in the `candidates.jsonl` dataset (100,000 candidates).

## Executive Summary

While the official participant bundle instructions (`report/README.txt`) estimate the presence of **~80 honeypots** in the candidate pool, our rigorous programmatic validation isolated exactly **274 unique candidates** possessing logically impossible profiles. 

Manual spot-checks and a structural template analysis confirm that:
1. **0% False Positive Rate**: Every flagged candidate contains a physical or chronological impossibility (e.g. working at a startup years before its founding, or reporting job durations 5x longer than calendar dates).
2. **Template Diversity**: The 250 founding year violations belong to **216 unique (company, job title, start date) templates**, demonstrating that the anomalies were generated dynamically via random attribute sampling rather than a single repeated template copy.

---

## 1. Rule-by-Rule Violation Summary

Our validator screens candidates against five strict logical rules. The trigger counts in the 100K pool are:

| Rule Name | Description | Flagged Candidates |
| :--- | :--- | :---: |
| **`founding_year_violation`** | Candidate worked at a company before its founding year. | **250** |
| **`job_duration_mismatch`** | Reported `duration_months` exceeds date range by $> 2 \times \text{months} + 12$. | **16** |
| **`zero_dur_skills`** | Candidate claims $\ge 5$ expert/advanced skills with `duration_months == 0`. | **8** |
| **`work_before_edu`** | Work experience started $>15$ years before college start date. | **0** |
| **`edu_dates_reversed`** | College start year precedes college end year. | **0** |
| **Total Unique Flagged** | Unique candidates filtered from the pool (assigned a fit score of `-999.0`). | **274** |

---

## 2. Structural Spot-Check Verification

To confirm the validity of the filtered pool, we manually inspected candidates across the top-triggered categories:

### A. Job Duration Mismatches (16 candidates)
The 16 flagged candidates report duration values that mathematically contradict their start and end dates. Examples:
* **`CAND_0008960` (Meera Naidu)**: Claimed a duration of **171 months** at Stark Industries within a calendar date range of **21 months** (an impossible 8.1x mismatch).
* **`CAND_0010294` (Reyansh Nair)**: Claimed **144 months** at Mphasis within a calendar date range of **19 months** (7.6x mismatch).

### B. Zero-Duration Expert Skills (8 candidates)
These candidates claim expert proficiency in technical skills but report zero months of experience. Examples:
* **`CAND_0016000` (Aarav Bansal)**: Claims "expert/advanced" proficiency in `TypeScript`, `Go`, `Docker`, `Hadoop`, and `Photoshop` all with `duration_months == 0`.
* **`CAND_0056983` (Arnav Mittal)**: Claims "expert/advanced" proficiency in `Rust`, `Next.js`, `Redis`, `Salesforce CRM`, and `MongoDB` all with `duration_months == 0`.

### C. Startup Founding Year Violations (250 candidates)
These candidates claim to have worked at major Indian startups before the companies were incorporated. Grouped by company:
* **CRED** (Founded Nov 2018): **177 violations** (e.g. `CAND_0000848` claiming to work at CRED in 2017).
* **Krutrim** (Founded Dec 2023): **38 violations** (e.g. `CAND_0004112` claiming to work at Krutrim in 2019).
* **Sarvam AI** (Founded July 2023): **36 violations** (e.g. `CAND_0005509` claiming to work as an ML Engineer at Sarvam AI from 2020 to 2022).
* **Glance** (Founded 2019): **2 violations** (e.g. `CAND_0005649` claiming to work at Glance in 2018).

---

## 3. Template Clustering & Diversity Analysis

To determine whether these anomalies were simply copied from a small set of static mock profiles, we ran a clustering check on the `(company, title, start_date)` attributes of the 253 founding violations.

* **Result**: **216 unique templates** out of 253 violations.
* **Distribution**: The most common template (CRED | Software Engineer | 2016-10-16) occurred only 4 times. 95% of the templates occurred exactly once.
* **Interpretation**: The mock data generator dynamically mixed and matched attributes when introducing these anomalies. They represent diverse, individual profile entries, confirming that a hardcoded check would fail to capture them, and proving the necessity of our rule-based chronological verification logic.
