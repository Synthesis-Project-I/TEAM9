FROM python:3.11.15-trixie

WORKDIR /app

COPY requirements.txt ./
# COPY to_db.py ./
# COPY data/260223_GrauIAI_data_mock.xlsx ./

RUN pip install --no-cache-dir -r requirements.txt
# RUN python to_db.py

EXPOSE 8000
