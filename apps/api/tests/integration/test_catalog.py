from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wine_journal.accounts.service import bootstrap_account
from wine_journal.catalog.models import WineRelease
from wine_journal.catalog.schemas import ManualWine
from wine_journal.catalog.service import create_manual_release, read_owned_release
from wine_journal.core.auth import Principal
from wine_journal.core.database import database_engine
from wine_journal.core.errors import ApiError


def test_release_distinctions_and_owner_constraints(database_urls: dict[str, SecretStr]) -> None:
    engine = database_engine(database_urls["runtime"])
    try:
        with Session(engine, expire_on_commit=False) as session:
            owner = bootstrap_account(session, Principal("https://test.example", uuid4()))
            other = bootstrap_account(session, Principal("https://test.example", uuid4()))
            with session.begin():
                releases = [
                    create_manual_release(session, owner.id, ManualWine.model_validate(data))
                    for data in [
                        {"name": "Calculated Risk", "vintageStatus": "YEAR", "year": 2021},
                        {"name": "Calculated Risk", "vintageStatus": "YEAR", "year": 2022},
                        {"name": "Calculated Risk", "edition": "Reserve"},
                        {"name": "Calculated Risk", "vintageStatus": "NON_VINTAGE"},
                        {"name": "Calculated Risk", "vintageStatus": "MULTI_VINTAGE"},
                    ]
                ]
            assert len({wine.id for wine in releases}) == 5
            assert releases[2].vintage_status == "UNKNOWN"
            with session.begin(), pytest.raises(ApiError) as error:
                read_owned_release(session, other.id, releases[0].id)
            assert error.value.status == 404
            definition_id = releases[0].definition_id
            owner_id, other_id = owner.id, other.id
            for values in [
                {"owner_id": other_id, "vintage_status": "UNKNOWN", "year": None},
                {"owner_id": owner_id, "vintage_status": "YEAR", "year": None},
                {"owner_id": owner_id, "vintage_status": "UNKNOWN", "year": 2020},
            ]:
                with pytest.raises(IntegrityError), session.begin():
                    session.add(WineRelease(definition_id=definition_id, **values))
                    session.flush()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "  "},
        {"name": "Wine", "year": 2020},
        {"name": "Wine", "vintageStatus": "YEAR"},
        {"name": "Wine", "vintageStatus": "NON_VINTAGE", "year": 2020},
        {"name": "Wine", "ownerId": str(uuid4())},
    ],
)
def test_manual_identity_validation(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ManualWine.model_validate(fields)
