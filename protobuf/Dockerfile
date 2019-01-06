FROM centos:7

MAINTAINER "Anton Lytkin" <a.lytkin@worksolutions.ru>

WORKDIR /tmp/otus

RUN yum -y install gcc && \
    yum -y install make && \
    yum -y install protobuf && \
    yum -y install protobuf-c && \
    yum -y install protobuf-c-compiler && \
    yum -y install protobuf-c-devel && \
    yum -y install python-devel && \
    yum -y install python-setuptools && \
    yum -y install zlib-devel && \
    yum -y install gdb

CMD ["/usr/sbin/init"]