FROM dockerfile/ubuntu

RUN git clone https://github.com/kzvezdarov/ircdd \
    cd ircdd \
    python setup.py flake8 &&
    python setup.py nosetests &&
    python setup.py install

VOLUME ["/data"]

WORKDIR /data

CMD ["/usr/bin/bash",]
