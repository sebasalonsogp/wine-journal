from uuid import UUID

from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.orm import Session

from wine_journal.catalog.models import CatalogDefinition, CatalogRelease, CatalogSource
from wine_journal.catalog.references import safe_reference
from wine_journal.catalog.schemas import CatalogDetails, CatalogPage, CatalogReference, CatalogWine
from wine_journal.core.errors import ApiError

MAX_OFFSET = 10_000


def public_wine(definition: CatalogDefinition, release: CatalogRelease) -> CatalogWine:
    return CatalogWine.model_validate(
        {
            "id": release.id,
            "name": definition.name,
            "producer": definition.producer,
            "vintage_status": release.vintage_status,
            "year": release.year,
            "edition": release.edition,
        }
    )


def browse(session: Session, *, q: str, limit: int, offset: int) -> CatalogPage:
    # Bounded work for unauthenticated reads; a larger catalog can add a search index.
    session.execute(text("SET LOCAL statement_timeout = '3s'"))
    statement = select(CatalogDefinition, CatalogRelease).join(
        CatalogRelease, CatalogRelease.definition_id == CatalogDefinition.id
    )
    for token in q.split():
        statement = statement.where(
            or_(
                *(
                    column.icontains(token, autoescape=True)
                    for column in (
                        CatalogDefinition.name,
                        CatalogDefinition.producer,
                        CatalogRelease.edition,
                        cast(CatalogRelease.year, String),
                    )
                )
            )
        )
    rows = session.execute(
        statement.order_by(
            func.lower(CatalogDefinition.producer),
            func.lower(CatalogDefinition.name),
            CatalogRelease.year.desc().nulls_last(),
            CatalogRelease.edition.asc().nulls_last(),
            CatalogRelease.id,
        )
        .offset(offset)
        .limit(limit + 1)
    ).all()
    following = offset + limit
    return CatalogPage(
        items=[public_wine(definition, release) for definition, release in rows[:limit]],
        next_offset=following if len(rows) > limit and following <= MAX_OFFSET else None,
    )


def details(session: Session, release_id: UUID) -> CatalogDetails:
    session.execute(text("SET LOCAL statement_timeout = '3s'"))
    row = session.execute(
        select(CatalogDefinition, CatalogRelease)
        .join(CatalogRelease, CatalogRelease.definition_id == CatalogDefinition.id)
        .where(CatalogRelease.id == release_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "CATALOG_WINE_NOT_FOUND", "This wine is not in the public catalog.")
    # Keep only the latest observation of each URL and cap the outbound reference list.
    observations = session.execute(
        select(CatalogSource.url, func.max(CatalogSource.retrieved_on))
        .where(CatalogSource.release_id == release_id)
        .group_by(CatalogSource.url)
        .order_by(func.max(CatalogSource.retrieved_on).desc(), CatalogSource.url)
        .limit(20)
    )
    sources = []
    for url, retrieved_on in observations:
        try:
            validated = safe_reference(url)
        except ValueError:
            continue
        sources.append(CatalogReference(url=validated, retrieved_on=retrieved_on))
    return CatalogDetails(**public_wine(*row).model_dump(), sources=sources)
