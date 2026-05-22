FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data parquets must be present (built by ingest scripts before image build)
# Secrets passed at runtime via Cloud Run env vars — never baked into image

EXPOSE 8080

CMD ["python", "-m", "streamlit", "run", "ui/streamlit_app.py", \
     "--server.port=8080", "--server.address=0.0.0.0", \
     "--server.headless=true"]
