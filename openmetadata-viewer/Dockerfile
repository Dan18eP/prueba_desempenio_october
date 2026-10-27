FROM python:3.11-alpine

WORKDIR /app

# No heavy dependencies required - Python standard library handles the lightweight server
COPY server.py /app/server.py
COPY index.html /app/index.html

EXPOSE 8585

CMD ["python", "server.py"]
