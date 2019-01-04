FROM centos:7

MAINTAINER "Your Name" <you@example.com>
RUN yum -y install epel-release && \
    yum -y install nginx && \
    yum -y install git && \
    yum -y install rpm-build && \
    yum -y install python36 && \
    yum clean all

RUN systemctl enable nginx.service

COPY .gitconfig /root/.gitconfig

EXPOSE 80

CMD ["/usr/sbin/init"]