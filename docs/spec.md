# JobTrackr Specification

## 1. Problem
Job searching requires applicants to manually track dozens of applications across disparate hiring stages, often without a clear understanding of why certain resumes receive responses while others do not. JobTrackr solves this by providing a unified workflow tracking engine that logs status transitions, notes, and reminders for every application. Additionally, it features an intelligent resume-matching system that compares candidate profiles against job descriptions to extract keyword gaps, deliver match scores, and highlight skill deficiencies across target applications.

## 2. Users
* **Students & New Graduates:** Individuals seeking entry-level roles or internships who apply to high volumes of positions simultaneously.
* **Job Seekers & Career Changers:** Professionals actively applying to multiple positions who need to manage multi-stage application pipelines and optimize their resume skills for target roles.

## 3. MVP Features
1. **User Authentication & Authorization:** Register and log in using email and password with JWT-based security.
2. **Resume Management:** Upload PDF resumes and automatically parse extracted text and skills.
3. **Job Description Management:** Add and save target job descriptions manually or by pasting job posting text.
4. **Application Pipeline Tracking:** Create and manage applications linked to target jobs across defined stages (`Saved` → `Applied` → `Online Assessment` → `Interview` → `Offer` / `Rejected`).
5. **Workflow Rules Engine:** Enforce valid application status transitions (preventing invalid jumps like `Saved` directly to `Offer`).
6. **Status Transition History:** Record every status change with a timestamp for detailed tracking.
7. **Resume-to-Job Matching:** Compute match scores between an uploaded resume and a specific job posting using skill overlap and text similarity algorithms.
8. **Missing Skills Analysis:** Identify and display specific missing skills for individual job postings and aggregate skill "weak spots" across all targeted jobs.
9. **Analytics Dashboard:** Display application metrics including weekly application volume, funnel progression rates, and overall response rates.
10. **Application Follow-Up Reminders:** Schedule and trigger email reminders for application follow-ups.

## 4. Out of Scope
1. **Mobile Native Applications:** Only a responsive web-based application will be supported for MVP.
2. **LinkedIn / Job Board Scraping & Integration:** Direct auto-importing or browser extension scraping from external job sites will not be supported.
3. **LLM-Based Resume Rewriting:** Automatic AI generation or rewriting of resume content will not be included.
4. **Calendar Sync Integrations:** Direct sync with external calendars (e.g., Google Calendar or Outlook) for interview scheduling is out of scope.