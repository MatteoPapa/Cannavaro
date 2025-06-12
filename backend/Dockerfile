FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7000

# CMD ["python3", "app.py"]
CMD ["tail", "-f", "/dev/null"]