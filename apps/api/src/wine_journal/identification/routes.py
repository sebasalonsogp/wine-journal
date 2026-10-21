from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from wine_journal.catalog.schemas import CatalogDetails
from wine_journal.core.database import database_session
from wine_journal.core.errors import ApiError, ErrorResponse
from wine_journal.identification import barcodes
from wine_journal.identification.schemas import BarcodeConfirmation, BarcodeLookup, BarcodeRequest

router = APIRouter(
    prefix="/identification",
    tags=["identification"],
    responses={status: {"model": ErrorResponse} for status in (408, 409, 413, 422, 429, 500, 503)},
)


@router.post("/barcode-lookups", response_model=BarcodeLookup)
def lookup_barcode(
    body: BarcodeRequest,
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> BarcodeLookup:
    response.headers["Cache-Control"] = "no-store"
    try:
        return barcodes.lookup(session, body.gtin)
    except SQLAlchemyError:
        raise ApiError(
            503, "BARCODE_LOOKUP_UNAVAILABLE", "Wine lookup is temporarily unavailable.", 5
        ) from None


@router.post("/barcode-confirmations", response_model=CatalogDetails)
def confirm_barcode(
    body: BarcodeConfirmation,
    session: Annotated[Session, Depends(database_session)],
    response: Response,
) -> CatalogDetails:
    response.headers["Cache-Control"] = "no-store"
    try:
        return barcodes.confirm(session, body)
    except SQLAlchemyError:
        raise ApiError(
            503, "BARCODE_LOOKUP_UNAVAILABLE", "Wine lookup is temporarily unavailable.", 5
        ) from None
