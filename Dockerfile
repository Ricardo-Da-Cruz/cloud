FROM google/cloud-sdk:alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY /src/utils/key.json /usr/src/app/key.json

ENV GOOGLE_APPLICATION_CREDENTIALS=/usr/src/app/key.json

RUN apk --update add python3 python3-dev py3-pip build-base
RUN python3 -m venv venv
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt
RUN gcloud auth activate-service-account auto-scaler@glassy-droplet-304915.iam.gserviceaccount.com --key-file=/usr/src/app/key.json


COPY ./src .

CMD ["venv/bin/python", "./orquestrator.py"]