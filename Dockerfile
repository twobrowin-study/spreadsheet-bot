FROM python:3.10-slim-buster

WORKDIR /python-docker

COPY requirenments.txt .
RUN pip3 install -r requirenments.txt

ENV BOT_TOKEN ''
ENV SHEETS_ACC_JSON ''
ENV SHEETS_LINK ''
ENV SWITCH_UPDATE_TIME ''
ENV SETTINGS_UPDATE_TIME ''

RUN  mkdir ./sheets
COPY python/sheets/*.py ./sheets/
COPY python/*.py ./

CMD [ "python3", "-u", "main.py"]