FROM apache/spark:3.5.1

USER root

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tshark \
    && rm -rf /var/lib/apt/lists/*

USER spark

RUN tshark -v >/dev/null
