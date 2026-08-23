ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nut-client nut-server python3 python3-serial \
    && rm -rf /var/lib/apt/lists/*

COPY run.sh /run.sh
COPY odroid_m1s_ups.py /usr/local/bin/odroid-m1s-ups
COPY render_nut_config.py /usr/local/bin/render-nut-config
RUN chmod a+x /run.sh /usr/local/bin/odroid-m1s-ups /usr/local/bin/render-nut-config

CMD [ "/run.sh" ]
