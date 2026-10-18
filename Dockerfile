FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
WORKDIR /srv/cashguard
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY rules ./rules
RUN useradd --uid 10001 --create-home cashguard && mkdir runtime && chown cashguard runtime
USER cashguard
EXPOSE 9017
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","9017","--workers","1","--no-access-log"]
