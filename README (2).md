# JobTrackr

> Track job and internship applications, and see how well your resume matches each role.

![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-70%25%2B-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

**Live demo:** `<your-deployed-url>`  |  **API docs:** `<your-deployed-url>/docs`  |  **Demo video:** `<link>`

<!-- Add a hero screenshot or GIF here: docs/images/dashboard.png -->

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Architecture](#architecture)
5. [Database Design](#database-design)
6. [Resume Matching Engine](#resume-matching-engine)
7. [API Reference](#api-reference)
8. [Getting Started](#getting-started)
9. [Project Structure](#project-structure)
10. [Testing](#testing)
11. [Deployment](#deployment)
12. [Design Decisions and Challenges](#design-decisions-and-challenges)
13. [Roadmap](#roadmap)
14. [Author](#author)

---

## Overview

Job searching means juggling dozens of applications across many stages, with no clear idea of why some resumes get replies and others don't. JobTrackr solves two problems:

1. **Tracking:** manage every application through a defined workflow, with notes, history, reminders, and analytics.
2. **Matching:** upload a resume, compare it to any job description, and see a match score plus the skills you're missing.

**Target users:** students and job seekers applying to many roles at once.

## Features

### Application Tracker
- Add jobs manually or by pasting a job description
- Status workflow: `Saved → Applied → Online Assessment → Interview → Offer / Rejected`
- Workflow rules (e.g. a job cannot jump from `Saved` straight to `Offer`)
- Full status history for every application
- Notes per application
- Search, filter by status, and pagination
- Email reminders ("follow up in 7 days")

### Resume Matcher
- Upload a PDF resume and extract its text and skills
- Match score against any saved job description
- Matched skills and **missing skills** for each job
- Three matching strategies compared: keyword, TF-IDF, and semantic embeddings
- "Weak spots" view: skills missing most often across all your target jobs

### Analytics Dashboard
- Applications per week
- Stage funnel (Applied → Interview → Offer)
- Response rate

### Engineering Features
- JWT authentication with hashed passwords
- Input validation and file upload limits (type and size)
- Rate limiting on sensitive endpoints
- Background jobs for reminders and resume processing
- Database migrations with Alembic
- Automated tests and CI pipeline
- Dockerized, with a live deployment

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Frontend | React (Vite), Tailwind CSS, Recharts |
| Background jobs | Celery + Redis |
| NLP | spaCy, scikit-learn, sentence-transformers |
| PDF parsing | pdfplumber (or PyPDF2) |
| Testing | pytest, httpx, pytest-cov |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Hosting | Render / Railway (`<your choice>`) |

## Architecture

```
┌────────────┐      HTTPS       ┌──────────────┐      ┌──────────────┐
│   React    │ ───────────────► │   FastAPI    │ ───► │  PostgreSQL  │
│  Frontend  │ ◄─────────────── │   Backend    │ ◄─── │              │
└────────────┘      JSON        └──────┬───────┘      └──────────────┘
                                       │
                          enqueue jobs │
                                       ▼
                                ┌──────────────┐      ┌──────────────┐
                                │    Redis     │ ───► │ Celery Worker│
                                │   (broker)   │      │ reminders,   │
                                └──────────────┘      │ resume parse │
                                                      └──────────────┘
```

<!-- Replace with a proper diagram: docs/images/architecture.png -->

**Request flow example (match a resume to a job):**
1. User calls `POST /match` with a `resume_id` and `job_id`.
2. The API loads both texts from PostgreSQL.
3. The matcher service computes skill overlap, TF-IDF similarity, and embedding similarity.
4. The combined score and the missing skills are saved to `match_results` and returned.

## Database Design

<!-- Add ER diagram: docs/images/er-diagram.png -->

| Table | Purpose |
|---|---|
| `users` | Accounts (email, password hash) |
| `resumes` | Uploaded resumes, extracted text, parsed skills (JSON) |
| `jobs` | Job postings saved by a user |
| `applications` | A user's application to a job, with current status |
| `status_history` | Every status change with a timestamp (powers the funnel) |
| `reminders` | Scheduled follow-ups and whether they've been sent |
| `match_results` | Cached match scores and skill gaps per resume and job |

**Key decisions**
- `status_history` is a separate table so analytics can reconstruct how applications moved over time.
- Indexes on `applications(user_id, status)` and `jobs(user_id)` for list and filter queries.
- Match results are cached so the same resume and job pair isn't recomputed.

## Resume Matching Engine

The matcher is built in three levels, each one improving on the last.

| Level | Method | Strength | Weakness |
|---|---|---|---|
| 1 | Keyword skill overlap | Fast, explainable | Misses synonyms |
| 2 | TF-IDF + cosine similarity | Captures overall term relevance | No semantic understanding |
| 3 | Sentence embeddings | Understands meaning ("built REST APIs" ≈ "backend development") | Heavier, less explainable |

**Final score**

```
final_score = 0.5 * skill_overlap + 0.5 * semantic_similarity
```

**Evaluation:** I tested all three levels on 10 real job descriptions and compared the results.

| Job | Keyword | TF-IDF | Embedding | Combined |
|---|---|---|---|---|
| _fill in_ | | | | |

_Add 2 to 3 lines of analysis here about what you observed._

## API Reference

Interactive docs are available at `/docs` (Swagger) and `/redoc`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Get a JWT access token |
| POST | `/resumes` | Upload a PDF resume |
| GET | `/resumes` | List your resumes |
| POST | `/jobs` | Save a job (paste a description) |
| GET | `/jobs?search=&status=&page=` | Search, filter, and paginate jobs |
| POST | `/applications` | Create an application |
| PATCH | `/applications/{id}/status` | Move an application to a new stage |
| GET | `/applications/{id}/history` | View status history |
| POST | `/match` | Match a resume against a job |
| GET | `/analytics/funnel` | Funnel and response-rate data |
| GET | `/analytics/weak-spots` | Most frequently missing skills |

**Example**

```bash
curl -X POST http://localhost:8000/match \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"resume_id": 1, "job_id": 4}'
```

```json
{
  "score": 0.72,
  "matched_skills": ["python", "sql", "rest"],
  "missing_skills": ["docker", "kubernetes"]
}
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- (Optional, for local development without Docker) Python 3.11+, Node 18+

### Run with Docker (recommended)

```bash
git clone https://github.com/<your-username>/jobtrackr.git
cd jobtrackr
cp .env.example .env        # fill in your values
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Run locally without Docker

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Worker**
```bash
celery -A app.worker worker --loglevel=info
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Secret used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime |
| `REDIS_URL` | Redis connection string |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Email settings for reminders |
| `MAX_UPLOAD_MB` | Maximum resume file size |

## Project Structure

```
jobtrackr/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routers/             # auth, jobs, applications, resumes, match, analytics
│   │   ├── services/            # matcher.py, resume_parser.py, workflow.py
│   │   └── worker.py            # Celery tasks
│   ├── alembic/                 # migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
├── docs/
│   ├── spec.md
│   ├── user-stories.md
│   └── images/
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .env.example
└── README.md
```

## Testing

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

- **Unit tests:** workflow rules, skill extraction, scoring functions
- **Integration tests:** auth flow, CRUD endpoints, match endpoint (using a test database)
- **CI:** GitHub Actions runs the test suite on every push and pull request

## Deployment

- **Backend and worker:** `<Render / Railway>`
- **Database:** managed PostgreSQL
- **Frontend:** `<Vercel / Netlify / same host>`
- **CI/CD:** GitHub Actions runs tests, then builds the Docker image

_Add a short note on how you deployed it and any gotchas you hit._

## Design Decisions and Challenges

_This section matters most to interviewers. Fill it in as you build._

- **Why FastAPI?** Async support, automatic validation, and auto-generated API docs.
- **Why PostgreSQL over SQLite?** Concurrent access, proper constraints, and production parity.
- **Why a separate `status_history` table?** Enables funnel analytics without losing past states.
- **Why three matching levels?** Each one is explainable on its own, and combining them beats any single one.
- **Challenge:** _e.g. PDF text extraction returned broken text for two-column resumes. How did you fix it?_
- **Challenge:** _e.g. Embedding model made the container large. What did you change?_
- **What I'd do differently:** _be honest here._

## Roadmap

- [x] Authentication and roles
- [x] Application workflow with history
- [x] Resume parsing and matching
- [x] Dashboard and analytics
- [ ] Browser extension to save jobs in one click
- [ ] Resume improvement suggestions using an LLM
- [ ] Import jobs from LinkedIn or job boards
- [ ] Calendar integration for interviews

## Author

**Your Name**
- GitHub: [@your-username](https://github.com/your-username)
- LinkedIn: [your-profile](https://linkedin.com/in/your-profile)
- Email: your.email@example.com

## License

Distributed under the MIT License. See `LICENSE` for details.
