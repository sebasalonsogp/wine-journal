import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import WineDefinition, WineRelease
from wine_journal.core.auth import Principal
from wine_journal.core.database import database_engine
from wine_journal.journal.models import DrinkingEntry, UserWine
from wine_journal.journal.queries import filtered_wine_query
from wine_journal.journal.wine_filters import WineFilters


def test_query_plans_on_a_multi_account_library(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    migrator = database_engine(database_urls["migration"], role="wine_migrator")
    reports = []
    try:
        with Session(engine, expire_on_commit=False) as session:
            owners = [
                bootstrap_account(session, Principal("https://plans.test", uuid4())).id
                for _ in range(5)
            ]
            definitions = []
            releases = []
            wines = []
            entries = []
            for owner in owners:
                for index in range(200):
                    definition, release, wine = uuid4(), uuid4(), uuid4()
                    definitions.append(
                        {
                            "id": definition,
                            "owner_id": owner,
                            "name": f"Cellar {index:03}",
                            "producer": "Synthetic estate",
                        }
                    )
                    releases.append(
                        {
                            "id": release,
                            "owner_id": owner,
                            "definition_id": definition,
                            "vintage_status": "YEAR",
                            "year": 2021 + index % 4,
                        }
                    )
                    wines.append(
                        {
                            "id": wine,
                            "owner_id": owner,
                            "release_id": release,
                            "rating_units": None if index % 3 == 0 else 6 + index % 5,
                        }
                    )
                    for day in range(1, 4):
                        entries.append(
                            {
                                "owner_id": owner,
                                "user_wine_id": wine,
                                "consumed_date": date(2026, 9, day),
                            }
                        )
            with session.begin():
                session.execute(insert(WineDefinition), definitions)
                session.execute(insert(WineRelease), releases)
                session.execute(insert(UserWine), wines)
                session.execute(insert(DrinkingEntry), entries)
        with migrator.begin() as connection:
            for table in ["wine_definitions", "wine_releases", "user_wines", "drinking_entries"]:
                connection.execute(text(f"ANALYZE app.{table}"))
        with Session(engine) as session:
            for filters in [
                WineFilters(),
                WineFilters(q="estate 2022"),
                WineFilters(sort="NAME"),
                WineFilters(sort="RATING", rating="RATED"),
            ]:
                statement = filtered_wine_query(owners[0], filters)
                key = statement.selected_columns.sort_value
                order = key.asc() if filters.sort == "NAME" else key.desc()
                statement = statement.order_by(order.nulls_last(), UserWine.id).limit(21)
                sql = str(statement.compile(engine, compile_kwargs={"literal_binds": True}))
                plan = session.execute(
                    text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
                ).scalar_one()[0]
                assert plan["Plan"]["Actual Rows"] == 21
                reports.append(
                    {
                        "filters": filters.model_dump(),
                        "executionMs": plan["Execution Time"],
                        "plan": plan["Plan"],
                    }
                )
        output = Path("test-results/wine-query-plans.json")
        output.parent.mkdir(exist_ok=True)
        output.write_text(
            json.dumps(
                {"accounts": 5, "wines": 1000, "entries": 3000, "reports": reports}, indent=2
            ),
            encoding="utf-8",
        )
    finally:
        engine.dispose()
        migrator.dispose()
