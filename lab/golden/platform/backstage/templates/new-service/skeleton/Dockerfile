FROM python:3.12-slim
WORKDIR /app
RUN useradd --uid 10001 --no-create-home app
COPY app.py .
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
