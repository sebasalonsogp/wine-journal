FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

COPY requirements.txt /build/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: --require-hashes -r /build/requirements.txt
COPY photos.py photo_protocol.py /app/wine_journal/media/
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65532:65532
WORKDIR /app
ENTRYPOINT ["timeout", "--signal=KILL", "20s", "python", "-m", "wine_journal.media.photos"]
