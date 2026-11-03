FROM debian:trixie-slim
ENV TZ=Europe/Brussels
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -qqy \
    && apt-get install -qqy --no-install-recommends curl python3 python3-venv texlive-full pandoc \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH"

# Compose runs the container with the host UID, which has no home directory.
ENV HOME=/tmp

VOLUME /storage

WORKDIR /srv

COPY . .

ADD entrypoint.sh /
RUN ["chmod", "+x", "/entrypoint.sh"]

ENV GENERATION_TIMEOUT=120
EXPOSE 6000
HEALTHCHECK --interval=5s --timeout=10s --retries=3 CMD curl -sS --fail 127.0.0.1:6000/healthcheck || exit 1
ENTRYPOINT ["/entrypoint.sh"]
