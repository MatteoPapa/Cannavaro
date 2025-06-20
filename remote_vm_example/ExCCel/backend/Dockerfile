FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && pip install gunicorn==22.0.0

COPY src .

CMD gunicorn app:app -b 0.0.0.0:5000 -w 8 \
        -e FLASK_SECRET=$FLASK_SECRET \
        -e INSTANCE_PATH=$INSTANCE_PATH \
        -e WORKSHEETS_PATH=$WORKSHEETS_PATH \
        -e PROCESSOR_HOST=$PROCESSOR_HOST \
        -e PROCESSOR_PORT=$PROCESSOR_PORT