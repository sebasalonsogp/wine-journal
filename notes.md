# Wine Journal

## Overview

A personal wine-tracking application that identifies bottles and builds a searchable history of wines and tasting experiences. Its strongest signal is thoughtful product engineering: reliable capture, clean data modeling, and a useful personal history.

## Technical core

- Use barcode scanning as the primary identification path.
- Fall back to label photography, OCR, and candidate matching when barcode lookup fails.
- Separate canonical wine/bottle metadata from personal tasting experiences.
- Store photos, notes, ratings, likes/dislikes, date, location or context, and repeat encounters.
- Design for authentication, privacy, external API failures, and manual correction.

## MVP

1. Create wine, producer, bottle/vintage, and tasting-entry data models.
2. Add manual entry and searchable history first.
3. Integrate barcode capture and one metadata source.
4. Add image/OCR-assisted candidate matching as a fallback.
5. Show all previous tasting experiences for the same wine.

## Suggested stack

TypeScript with React/Next.js or a mobile-friendly frontend, FastAPI or a TypeScript backend, PostgreSQL, object storage, a barcode library, and an OCR service.

## Demo target

Scan a bottle, confirm the identified wine, add a tasting experience, and later view the complete history for that wine.

## First implementation milestone

Design the relational schema and implement manual wine and tasting entry end to end; add automated identification only after the core journal workflow is solid.
