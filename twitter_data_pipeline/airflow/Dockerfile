FROM puckel/docker-airflow


WORKDIR /app

COPY requirements.txt /app

RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.python.org -r requirements.txt