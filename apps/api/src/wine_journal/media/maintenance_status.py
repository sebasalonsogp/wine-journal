"""Aggregate operator diagnostics; never expose owner IDs or storage identities."""

from sqlalchemy import Engine, text


def hold_summary(engine: Engine) -> dict[str, int]:
    # A held asset can still have active references. These totals are diagnostic,
    # not a count of files eligible for deletion. A row with both holds counts once.
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET LOCAL statement_timeout = '5s'"))
        row = connection.execute(
            text("""
            SELECT count(*) FILTER (WHERE unsettled_grants > 0 OR unsettled_writes > 0),
                   count(*) FILTER (WHERE unsettled_grants > 0),
                   count(*) FILTER (WHERE unsettled_writes > 0),
                   coalesce(sum(reserved_bytes) FILTER
                     (WHERE unsettled_grants > 0 OR unsettled_writes > 0), 0)
            FROM app.upload_assets WHERE quota_released_at IS NULL
        """)
        ).one()
    return dict(
        zip(
            ("heldAssets", "signingHeldAssets", "writeHeldAssets", "heldReservedBytes"),
            (int(value) for value in row),
            strict=True,
        )
    )
