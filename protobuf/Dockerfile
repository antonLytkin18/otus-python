FROM centos:7

MAINTAINER "Anton Lytkin" <a.lytkin@worksolutions.ru>

ADD . /tmp/otus
WORKDIR /tmp/otus

RUN set -xe \
  && yum install -y gcc \
                    make \
                    protobuf \
                    protobuf-c \
                    protobuf-c-compiler \
                    protobuf-c-devel \
                    python-devel \
                    python-setuptools \
                    gdb \
                    zlib-devel

RUN ulimit -c unlimited

RUN protoc-c --c_out=. deviceapps.proto

RUN python setup.py test