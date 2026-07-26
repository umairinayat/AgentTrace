FROM python:3.11-slim

WORKDIR /app

# scipy/sklearn/numpy ship manylinux wheels, but sentence-transformers -> torch
# -> tokenizers can fall back to a source build on some platforms; install the
# toolchain so a source build succeeds if no matching wheel is found.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better Docker layer caching.
COPY pyproject.toml ./
COPY detector ./detector
RUN pip install --no-cache-dir .

CMD ["python", "-m", "detector.main"]
