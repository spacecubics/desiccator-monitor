FROM python:3.9

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y apt-utils && apt-get install -y bluez && apt-get clean

COPY switchbotmeterbt.py .
ENV macaddr="EC:4B:05:BD:B8:6D"