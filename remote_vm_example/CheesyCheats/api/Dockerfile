FROM ubuntu:22.04

RUN apt update \
    && DEBIAN_FRONTEND="noninteractive" apt install -y python3 python3-dev python3-pip

COPY requirements.txt /srv/app/
RUN pip3 install --no-cache-dir -r /srv/app/requirements.txt 


COPY . /srv/app/

WORKDIR /srv/app/

CMD ["python3", "main.py"]
