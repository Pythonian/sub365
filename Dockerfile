# Pull official base image
FROM python:3.10.13-bullseye as builder

# set work directory
WORKDIR /usr/src/app

# prevent python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# ensures console output is not buffered by Docker
ENV PYTHONUNBUFFERED 1

# copy requirements.txt
COPY ./requirements.txt .

# install system dependencies and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false

#########
# FINAL #
#########

# pull official base image
FROM python:3.10.13-bullseye

# create directory for the app user
RUN mkdir -p /home/app

# create the app user
RUN groupadd -r app && useradd --no-log-init -r -g app app

# create the appropriate directories
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles

# Set work directory
WORKDIR $APP_HOME

# install dependencies and clean up
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/* \
    && apt-get purge -y --auto-remove curl -o APT::AutoRemove::RecommendsImportant=false

# copy entrypoint.sh
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' $APP_HOME/entrypoint.sh
RUN chmod +x $APP_HOME/entrypoint.sh

# copy project
COPY . $APP_HOME

# chown all the files to the app user
RUN chown -R app:app $APP_HOME

# change to the app user
USER app

ENTRYPOINT ["/home/app/web/entrypoint.sh"]
