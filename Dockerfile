FROM public.ecr.aws/docker/library/python:3.9-slim

WORKDIR /app

COPY webapp/requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt
COPY webapp/ .

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
