FROM ubuntu:focal as builder
ENV TZ=Europe/Brussels
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./requirements.txt ./
RUN apt-get update -qqy \
    && apt-get install -qqy libffi-dev python3-pip python3-dev gcc musl-dev \
    && python3 -m pip install --no-cache-dir -r requirements.txt

FROM ubuntu:focal
ENV TZ=Europe/Brussels
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=builder /usr/local/lib/python3.8/ /usr/local/lib/python3.8/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

RUN apt-get update -qqy \
    && apt-get install -qqy --no-install-recommends curl texlive-full pandoc

RUN apt-get install -qqy --no-install-recommends python3-setuptools

VOLUME /storage

WORKDIR /srv

COPY . .

ADD entrypoint.sh /
RUN ["chmod", "+x", "/entrypoint.sh"]

ENV GENERATION_TIMEOUT=120
EXPOSE 6000
HEALTHCHECK --interval=5s --timeout=10s --retries=3 CMD curl -sS --fail 127.0.0.1:6000/healthcheck || exit 1
ENTRYPOINT ["/entrypoint.sh"]