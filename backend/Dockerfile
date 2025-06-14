FROM python:3.10-slim

WORKDIR /app

# Install ssh-keygen and other required dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7000

CMD ["python3", "app.py"]
# CMD ["tail", "-f", "/dev/null"]