FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY agents/ agents/
COPY tools/ tools/
COPY api/ api/
COPY ui/auth.py ui/auth.py

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
