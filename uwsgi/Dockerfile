FROM centos:7

MAINTAINER "Anton Lytkin" <a.lytkin@worksolutions.ru>

WORKDIR /tmp/bin/uwsgi

RUN yum -y install epel-release && \
    yum -y install nginx && \
    yum -y install git && \
    yum -y install rpm-build && \
    yum -y install python36 && \
    yum -y install https://centos7.iuscommunity.org/ius-release.rpm && \
    yum -y install python36u-pip && \
    yum -y groupinstall 'Development Tools' && \
    yum -y install python36-devel && \
    yum clean all

RUN systemctl enable nginx.service

ADD requirements.txt .

RUN pip3.6 install --upgrade pip
RUN pip3.6 install -r requirements.txt

RUN rm -f /usr/bin/python && ln -s /usr/bin/python3.6 /usr/bin/python

COPY .gitconfig /root/.gitconfig

EXPOSE 80

CMD ["/usr/sbin/init"]