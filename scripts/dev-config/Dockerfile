FROM dockerfile/python

RUN pip install flake8 && \
    pip install nose && \
    pip install twisted && \
    pip install setuptools

WORKDIR /data

CMD ["bash", "-c", "cd ircdd-git && python setup.py flake8 && python setup.py nosetests && python setup.py install"]
