FROM python:2

WORKDIR /app

ADD . /app

ENV PHANTOMJS_VERSION 1.9.8


RUN pip install --trusted-host pypi.python.org -r requirements.txt && \
wget -q --no-check-certificate -O /tmp/phantomjs-$PHANTOMJS_VERSION-linux-x86_64.tar.bz2 https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-$PHANTOMJS_VERSION-linux-x86_64.tar.bz2 && \
  tar -xjf /tmp/phantomjs-$PHANTOMJS_VERSION-linux-x86_64.tar.bz2 -C /tmp && \
  rm -f /tmp/phantomjs-$PHANTOMJS_VERSION-linux-x86_64.tar.bz2 && \
  mv /tmp/phantomjs-$PHANTOMJS_VERSION-linux-x86_64/ /usr/local/share/phantomjs && \
ln -s /usr/local/share/phantomjs/bin/phantomjs /usr/local/bin/phantomjs



CMD ["python","dota.py"]
