# Honeypot & Data Quality Analysis

We ran a validation check across the full `candidates.jsonl` dataset (100,000 profiles) to clean out synthetic test candidates ("honeypots"). 

## Summary

The official participant bundle instructions (`report/README.txt`) mention that the candidate pool contains **~80 honeypots**. However, our checks flagged exactly **274 unique candidates** with chronological or logical contradictions. 

We manually checked these profiles to ensure we weren't throwing out legitimate candidates:
1. **0% False Positives**: Every single flagged profile has a clear logical error (like claiming to work at Krutrim/Sarvam years before they existed, or working 15 years at a company in a 3-year window).
2. **Diverse Anomalies**: The 250 founding year violations belong to **216 unique combinations of (company, job title, start date)**. This shows that the synthetic data generator randomly generated these profiles instead of copying a single static template, meaning a generic, chronological validation rule is required to catch them.

---

## Rule Triggers Breakdown

Here's how many candidates were caught by each of our validation rules:

| Rule Name | What it checks | Trigger Count |
| :--- | :--- | :---: |
| **`founding_year_violation`** | Candidate started working before the company was founded. | **250** |
| **`job_duration_mismatch`** | Reported experience duration exceeds date range by $> 2 \times \text{months} + 12$. | **16** |
| **`zero_dur_skills`** | Candidate claims $\ge 5$ expert/advanced skills but lists 0 months of experience. | **8** |
| **`work_before_edu`** | Career history started $>15$ years before college start date. | **0** |
| **`edu_dates_reversed`** | Graduation year precedes college entry year. | **0** |
| **Total Flagged** | Unique candidates filtered from our final ranking (assigned a score of `-999.0`). | **274** |

---

## Spot-Check Verification

We pulled details for candidates in the top violation categories to confirm the logical gaps:

### A. Job Duration Mismatch (16 candidates)
These profiles list experience durations that are physically impossible for their date ranges. For example:
* **`CAND_0008960` (Meera Naidu)**: Lists **171 months** of experience at Stark Industries in a calendar window of **21 months** (~8x mismatch).
* **`CAND_0010294` (Reyansh Nair)**: Lists **144 months** of experience at Mphasis in a window of **19 months** (~7.6x mismatch).

### B. Expert Skills with Zero Duration (8 candidates)
These candidates claim expert/advanced proficiency in multiple tech skills but list 0 months of experience. For example:
* **`CAND_0016000` (Aarav Bansal)**: Lists expert/advanced proficiency in `TypeScript`, `Go`, `Docker`, `Hadoop`, and `Photoshop` all with `duration_months == 0`.
* **`CAND_0056983` (Arnav Mittal)**: Lists expert/advanced proficiency in `Rust`, `Next.js`, `Redis`, `Salesforce CRM`, and `MongoDB` all with `duration_months == 0`.

### C. Startup Founding Year Conflicts (250 candidates)
Candidates claiming work history at major startups before their launch dates. By company:
* **CRED** (Launched Nov 2018): **177 violations** (e.g., `CAND_0000848` starting at CRED in 2017).
* **Krutrim** (Launched Dec 2023): **38 violations** (e.g., `CAND_0004112` starting at Krutrim in 2019).
* **Sarvam AI** (Launched July 2023): **36 violations** (e.g., `CAND_0005509` starting at Sarvam AI in 2020).
* **Glance** (Launched 2019): **2 violations** (e.g., `CAND_0005649` starting at Glance in 2018).

---

## Pattern Analysis

We checked the `(company, title, start_date)` of the 253 founding violations to see if they were copies of a few test profiles:
* **Result**: **216 unique templates** out of 253 violations.
* **Distribution**: The most common template (CRED | Software Engineer | 2016-10-16) occurred only 4 times. 95% of templates were entirely unique.
* **Takeaway**: The data generator randomized start dates and titles when injecting these honeypots. Since they don't follow a single static template, we need dynamic logical checks (like comparing startup launch dates) rather than simple profile ID filters.
