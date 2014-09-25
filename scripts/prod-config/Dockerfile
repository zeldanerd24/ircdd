FROM dockerfile/python

RUN \
    git clone https://github.com/kzvezdarov/ircdd /tmp/ircdd-git && \
    cd /tmp/ircdd-git && \
    python setup.py flake8 && \
    python setup.py nosetests && \
    python setup.py install && \
    rm -rf /tmp/ircdd-git

WORKDIR /data

CMD ["/usr/bin/bash"]
