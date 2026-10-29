FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY container_worker.py /app/container_worker.py
USER 65534:65534
EXPOSE 8080
CMD ["python", "/app/container_worker.py"]
