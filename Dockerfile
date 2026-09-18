FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY 1_rhel.py /app/1_rhel.py
COPY run_1_local_ubuntu.sh /app/run_1_local_ubuntu.sh

RUN chmod +x /app/run_1_local_ubuntu.sh && \
    python3 -m py_compile /app/1_rhel.py

CMD ["/app/run_1_local_ubuntu.sh"]
