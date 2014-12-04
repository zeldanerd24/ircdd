FROM dockerfile/rethinkdb

RUN wget https://github.com/kelseyhightower/confd/releases/download/v0.6.3/confd-0.6.3-linux-amd64 && \
    mv confd-0.6.3-linux-amd64 /usr/local/bin/confd && \
    chmod +x /usr/local/bin/confd

ADD confd /etc/confd
ADD bin/confd-watch-rethinkdb /usr/local/bin/confd-watch-rethinkdb

WORKDIR /data

CMD ["bash"]

EXPOSE 28015
EXPOSE 29015
EXPOSE 8080
