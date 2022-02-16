
# http://jpetazzo.github.io/2020/03/01/quest-minimal-docker-images-part-2/
FROM openjdk:17-slim as jre-build
WORKDIR /app
# Binutils for objcopy, needed by jlink.
RUN apt-get update && \
    apt-get install -y --no-install-recommends binutils wget tini && \
    wget -q -O HeLI.jar https://zenodo.org/record/5890998/files/HeLI.jar?download=1
RUN jdeps --print-module-deps HeLI.jar > java.modules
RUN jlink --strip-debug  --add-modules $(cat java.modules) --output /java

# https://testdriven.io/blog/docker-best-practices/
FROM python:3.8-slim as venv-build
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.8-slim
COPY --from=jre-build /usr/bin/tini /usr/bin/tini
RUN addgroup --gid 1001 "elg" && adduser --disabled-password --gecos "ELG User,,," --home /elg --ingroup elg --uid 1001 elg && chmod +x /usr/bin/tini
COPY --chown=elg:elg --from=jre-build /java /java
COPY --chown=elg:elg --from=venv-build /opt/venv /opt/venv

# Everything from here down runs as the unprivileged user account
USER elg:elg
WORKDIR /elg
COPY --chown=elg:elg --from=jre-build /app/HeLI.jar /elg/
COPY --chown=elg:elg app.py docker-entrypoint.sh /elg/
ENV PATH="/opt/venv/bin:$PATH"

ENV WORKERS=2
ENV TIMEOUT=60
ENV WORKER_CLASS=sync
ENV LOGURU_LEVEL=INFO
ENV PYTHON_PATH="/opt/venv/bin"

RUN chmod +x ./docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]

# ENTRYPOINT ["/usr/bin/tini", "-s", "-e", "143", "--"]
