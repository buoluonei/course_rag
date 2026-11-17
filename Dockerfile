FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.3
RUN python -m pip install --no-cache-dir --timeout 120 --retries 5 --resume-retries 8 torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir --timeout 120 --retries 5 --resume-retries 8 -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]

