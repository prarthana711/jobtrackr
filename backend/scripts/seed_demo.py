"""Fill the database with demo data.

Run from the backend folder:   python -m scripts.seed_demo
Then log in with demo@example.com / demopass123

For local development only. Never create this account on a deployed database.
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.security import hash_password
from app.services.matcher import match_texts
from app.services.skills import extract_skills

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demopass123"

RESUME_TEXT = """Asha Rao - Information Science Engineering
Skills: Python, SQL, Docker, FastAPI, PostgreSQL, Git and Linux
Projects: built a REST API with FastAPI and PostgreSQL, deployed it with Docker on AWS.
Built a data analysis dashboard using pandas and matplotlib."""

JOBS = [
    ("Backend Intern", "Acme", "Bengaluru", "Python, SQL and REST APIs. Docker is a plus."),
    ("Data Analyst Intern", "Globex", "Mumbai", "SQL, pandas, data visualization, Tableau and Power BI."),
    ("Full Stack Developer", "Initech", "Remote", "React, Node.js, MongoDB and REST APIs."),
    ("Cloud Engineer Intern", "Umbrella", "Pune", "AWS, Docker, Kubernetes, Linux and CI/CD."),
    ("ML Engineer Intern", "Hooli", "Hyderabad", "Python, scikit-learn, TensorFlow, pandas and machine learning."),
    ("Software Engineer", "Stark Tech", "Bengaluru", "Java, Spring Boot, MySQL, microservices and Git."),
    ("DevOps Intern", "Wayne Labs", "Chennai", "Docker, Kubernetes, Jenkins, Linux, Terraform and AWS."),
    ("Python Developer", "Soylent", "Remote", "Python, FastAPI or Django, PostgreSQL, Redis and Docker."),
    ("QA Engineer Intern", "Vandelay", "Bengaluru", "Selenium, pytest, unit testing, Jira and agile."),
    ("Frontend Developer", "Pied Piper", "Remote", "JavaScript, TypeScript, React, HTML, CSS and Tailwind CSS."),
    ("Data Engineer Intern", "Cyberdyne", "Bengaluru", "Python, SQL, Apache Spark, ETL and PostgreSQL."),
    ("Backend Developer", "Oscorp", "Gurugram", "Python, Django, REST APIs, PostgreSQL, Redis and AWS."),
]

# The stages each application walked through (all allowed by the workflow rules)
PATHS = [
    ["saved"],
    ["saved", "applied"],
    ["saved", "applied", "rejected"],
    ["saved", "applied", "online_assessment", "interview"],
    ["saved", "applied", "interview", "offer"],
    ["saved", "applied", "online_assessment", "rejected"],
]


def main() -> None:
    rng = random.Random(42)  # a fixed seed, so every run creates the same data
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with SessionLocal() as db:
        existing = db.scalar(
            select(models.User).where(models.User.email == DEMO_EMAIL)
        )
        if existing is not None:
            print(
                "Demo data already exists. To start fresh: delete jobtrackr.db, "
                "run 'alembic upgrade head', then run this script again."
            )
            return

        user = models.User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        resume = models.Resume(
            user=user,
            original_filename="demo_resume.pdf",
            stored_filename="demo-resume.pdf",  # no real file, so downloading it gives a 404
            size_bytes=0,
            raw_text=RESUME_TEXT,
            parsed_skills=extract_skills(RESUME_TEXT),
        )
        db.add_all([user, resume])
        db.flush()  # gives the user an id, which match results need

        for index, (title, company, location, description) in enumerate(JOBS):
            path = PATHS[index % len(PATHS)]
            start = now - timedelta(days=55 - index * 4, hours=rng.randint(0, 8))

            job = models.Job(
                user=user,
                title=title,
                company=company,
                location=location,
                description=description,
                created_at=start,
            )
            application = models.Application(
                user=user, job=job, status=path[-1], created_at=start
            )

            moment = start
            for previous, new in zip([None] + path[:-1], path):
                application.history.append(
                    models.StatusHistory(
                        from_status=previous, to_status=new, changed_at=moment
                    )
                )
                if new == "applied":
                    application.applied_on = moment.date()
                moment = min(moment + timedelta(days=rng.randint(3, 8)), now)

            outcome = match_texts(RESUME_TEXT, f"{title}\n{description}")
            match = models.MatchResult(
                user_id=user.id,
                resume=resume,
                job=job,
                score=outcome.score,
                skill_score=outcome.skill_score,
                text_score=outcome.text_score,
                matched_skills=outcome.matched_skills,
                missing_skills=outcome.missing_skills,
            )
            db.add_all([job, application, match])

        db.commit()

    print(f"Created demo user {DEMO_EMAIL} (password: {DEMO_PASSWORD})")
    print(f"with {len(JOBS)} jobs, applications at different stages, and match results.")


if __name__ == "__main__":
    main()