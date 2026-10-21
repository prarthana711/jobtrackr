from app.services.skills import extract_skills


def test_finds_common_skills():
    assert extract_skills("Skills: Python, SQL and Docker.") == ["docker", "python", "sql"]


def test_matching_ignores_case_and_duplicates():
    assert extract_skills("PYTHON, Python and python3") == ["python"]


def test_java_is_not_javascript():
    assert extract_skills("Frontend work in JavaScript") == ["javascript"]
    assert extract_skills("Backend in Java") == ["java"]


def test_sql_is_not_found_inside_postgresql():
    assert extract_skills("Used PostgreSQL daily") == ["postgresql"]


def test_git_is_not_found_inside_github():
    assert extract_skills("Hosted code on GitHub") == ["github"]


def test_words_that_merely_contain_a_skill_are_ignored():
    assert extract_skills("Digital legitimate pythonic laws") == []


def test_symbols_in_skill_names():
    assert extract_skills("Wrote C++ and C# code, plus Node.js services") == [
        "c#",
        "c++",
        "node.js",
    ]


def test_aliases_map_to_one_name():
    assert extract_skills("Trained models with sklearn and K8s") == [
        "kubernetes",
        "scikit-learn",
    ]


def test_digits_after_a_skill_name():
    assert extract_skills("Built pages with HTML5 and CSS3") == ["css", "html"]


def test_skill_split_across_lines():
    assert extract_skills("Worked on machine\nlearning projects") == ["machine learning"]


def test_ci_cd():
    assert extract_skills("Set up CI/CD pipelines") == ["ci/cd"]


def test_empty_text_gives_no_skills():
    assert extract_skills("") == []