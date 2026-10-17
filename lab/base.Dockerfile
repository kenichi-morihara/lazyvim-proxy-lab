FROM rockylinux:9@sha256:d7be1c094cc5845ee815d4632fe377514ee6ebcf8efaed6892889657e5ddaaa6
RUN dnf -y install epel-release && dnf config-manager --set-enabled crb && dnf -y module enable nodejs:22 \
 && dnf -y install ca-certificates git cmake ninja-build gcc gcc-c++ make gettext \
    unzip tar gzip which procps-ng iproute iptables python3.11 python3.11-pip nodejs npm \
    ripgrep fd-find openssh-server openssh-clients sudo shadow-utils util-linux \
 && dnf clean all \
 && alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.11 100 \
 && useradd -m -u 1000 -s /bin/bash developer \
 && printf 'developer ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/developer \
 && chmod 440 /etc/sudoers.d/developer
ENV LANG=C.UTF-8 TERM=xterm-256color
# Fix package endpoints so the proxy allowlist does not depend on random mirrors.
RUN sed -i -e 's|^mirrorlist=|#mirrorlist=|' -e 's|^#baseurl=http://dl.rockylinux.org/|baseurl=https://dl.rockylinux.org/|' /etc/yum.repos.d/rocky*.repo \
 && sed -i -e 's|^metalink=|#metalink=|' -e 's|^#baseurl=https://download.example/pub/epel/|baseurl=https://dl.fedoraproject.org/pub/epel/|' /etc/yum.repos.d/epel.repo \
 && dnf config-manager --set-disabled epel-cisco-openh264
