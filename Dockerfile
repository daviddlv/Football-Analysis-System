FROM --platform=linux/amd64 python:3-slim-buster

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --upgrade --no-cache-dir -r requirements.txt

CMD [ "python", "./main.py" ]
