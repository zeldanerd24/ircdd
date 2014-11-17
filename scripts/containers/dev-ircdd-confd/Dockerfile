FROM dockerfile/python

RUN wget https://github.com/kelseyhightower/confd/releases/download/v0.6.3/confd-0.6.3-linux-amd64 && \
    mv confd-0.6.3-linux-amd64 /usr/local/bin/confd && \
    chmod +x /usr/local/bin/confd

RUN pip install flake8 && \
    pip install nose && \
    pip install twisted && \
    pip install setuptools && \
    pip install rethinkdb

RUN mkdir /etc/ircdd

ADD confd /etc/confd
ADD bin/confd-watch-ircdd /usr/local/bin/confd-watch-ircdd

WORKDIR /data

CMD ["bash"]
