FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY 1_rhel.py /app/1_rhel.py

RUN python -m py_compile /app/1_rhel.py

CMD ["python", "-u", "/app/1_rhel.py"]
