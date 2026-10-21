import re

# canonical skill name -> the ways it is written in resumes and job descriptions.
# Everything is lowercase because we lowercase the text before matching.
SKILLS: dict[str, tuple[str, ...]] = {
    # Languages
    "python": ("python", "python3"),
    "java": ("java",),
    "javascript": ("javascript", "ecmascript", "es6"),
    "typescript": ("typescript",),
    "c++": ("c++",),
    "c#": ("c#", "csharp"),
    "go": ("golang",),
    "rust": ("rust",),
    "kotlin": ("kotlin",),
    "php": ("php",),
    "ruby": ("ruby",),
    "sql": ("sql",),
    "bash": ("bash", "shell scripting"),
    "html": ("html", "html5"),
    "css": ("css", "css3"),
    # Web and backend
    "react": ("react", "react.js", "reactjs"),
    "angular": ("angular", "angularjs"),
    "vue": ("vue", "vue.js", "vuejs"),
    "next.js": ("next.js", "nextjs"),
    "node.js": ("node.js", "nodejs"),
    "django": ("django",),
    "flask": ("flask",),
    "fastapi": ("fastapi",),
    "spring boot": ("spring boot", "springboot"),
    ".net": (".net", "dotnet", "asp.net"),
    "rest api": ("rest api", "rest apis", "restful"),
    "graphql": ("graphql",),
    "microservices": ("microservices", "microservice"),
    "tailwind css": ("tailwind", "tailwindcss"),
    "bootstrap": ("bootstrap",),
    # Databases
    "postgresql": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "mongodb": ("mongodb",),
    "sqlite": ("sqlite",),
    "redis": ("redis",),
    "nosql": ("nosql",),
    "firebase": ("firebase",),
    "elasticsearch": ("elasticsearch",),
    # DevOps and cloud
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud"),
    "git": ("git",),
    "github": ("github",),
    "gitlab": ("gitlab",),
    "ci/cd": ("ci/cd", "cicd", "continuous integration"),
    "jenkins": ("jenkins",),
    "terraform": ("terraform",),
    "linux": ("linux",),
    "nginx": ("nginx",),
    # Data and machine learning
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "scikit-learn": ("scikit-learn", "sklearn", "scikit learn"),
    "tensorflow": ("tensorflow",),
    "pytorch": ("pytorch",),
    "keras": ("keras",),
    "opencv": ("opencv",),
    "matplotlib": ("matplotlib",),
    "machine learning": ("machine learning",),
    "deep learning": ("deep learning",),
    "nlp": ("nlp", "natural language processing"),
    "computer vision": ("computer vision",),
    "data analysis": ("data analysis", "data analytics"),
    "data visualization": ("data visualization", "data visualisation"),
    "power bi": ("power bi", "powerbi"),
    "tableau": ("tableau",),
    "excel": ("microsoft excel", "ms excel"),
    "spark": ("apache spark", "pyspark"),
    "hadoop": ("hadoop",),
    "etl": ("etl",),
    "hugging face": ("hugging face", "huggingface"),
    "llm": ("llm", "llms", "large language models"),
    "langchain": ("langchain",),
    # Computer science fundamentals
    "data structures": ("data structures", "dsa"),
    "algorithms": ("algorithms",),
    "oop": ("oop", "object oriented", "object-oriented"),
    "operating systems": ("operating systems",),
    "dbms": ("dbms", "database management"),
    "computer networks": ("computer networks",),
    "system design": ("system design",),
    # Tools and practices
    "agile": ("agile",),
    "scrum": ("scrum",),
    "jira": ("jira",),
    "postman": ("postman",),
    "figma": ("figma",),
    "pytest": ("pytest",),
    "unit testing": ("unit testing", "unit tests"),
    "selenium": ("selenium",),
}


def _compile(aliases: tuple[str, ...]) -> re.Pattern:
    # Longest alias first, so "react.js" is tried before "react"
    parts = [re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)]
    # The skill must not be glued to other letters or digits on either side.
    # That is what stops "java" matching inside "javascript"
    # and "sql" matching inside "postgresql".
    return re.compile(r"(?<![a-z0-9+#.])(?:" + "|".join(parts) + r")(?![a-z0-9+#])")


_PATTERNS = {name: _compile(aliases) for name, aliases in SKILLS.items()}


def extract_skills(text: str) -> list[str]:
    """Return the sorted list of known skills mentioned in `text`."""
    # Lowercase, and turn line breaks into spaces so "machine\nlearning" still matches
    normalized = re.sub(r"\s+", " ", text.lower())
    return sorted(name for name, pattern in _PATTERNS.items() if pattern.search(normalized))