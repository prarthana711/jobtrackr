from app.config import Settings


def test_plain_postgres_urls_get_the_psycopg_driver():
    expected = "postgresql+psycopg://u:p@db:5432/app"
    assert Settings(database_url="postgres://u:p@db:5432/app").database_url == expected
    assert Settings(database_url="postgresql://u:p@db:5432/app").database_url == expected


def test_urls_that_already_name_a_driver_are_left_alone():
    url = "postgresql+psycopg://u:p@db:5432/app"
    assert Settings(database_url=url).database_url == url


def test_sqlite_urls_are_left_alone():
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


def test_cors_origins_are_split_and_trimmed():
    settings = Settings(cors_origins=" http://a.example , http://b.example ,")
    assert settings.cors_origin_list == ["http://a.example", "http://b.example"]