# Evaluation only; never installed in the API or web runtime.
FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
RUN apt-get update && apt-get install --no-install-recommends -y \
    tesseract-ocr=5.3.0-2 tesseract-ocr-eng=1:4.1.0-2 \
    && rm -rf /var/lib/apt/lists/*
ENV OMP_THREAD_LIMIT=1
USER 65532:65532
ENTRYPOINT ["timeout", "--signal=KILL", "10s", "tesseract"]
