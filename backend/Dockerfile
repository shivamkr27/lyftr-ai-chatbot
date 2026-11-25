# syntax=docker/dockerfile:1
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /install /usr/local
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
