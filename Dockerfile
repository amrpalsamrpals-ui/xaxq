FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        wget \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY run_1_local_ubuntu.sh /app/
COPY 1_rhel.py /app/

RUN chmod +x /app/run_1_local_ubuntu.sh

CMD ["/app/run_1_local_ubuntu.sh"]
