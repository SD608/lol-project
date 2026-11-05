FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 10001 api
COPY backend /app/backend
COPY rift/__init__.py /app/rift/__init__.py
COPY rift/database.py /app/rift/database.py
USER api
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
