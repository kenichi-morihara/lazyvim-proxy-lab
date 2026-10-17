FROM lazyvim-lab-base:locked
RUN printf '[docker-ce-stable]\nname=Docker CE Stable\nbaseurl=https://download.docker.com/linux/centos/9/$basearch/stable\nenabled=1\ngpgcheck=1\ngpgkey=https://download.docker.com/linux/centos/gpg\n' > /etc/yum.repos.d/docker-ce.repo \
 && dnf -y install docker-ce-28.5.1 docker-ce-cli-28.5.1 containerd.io \
 && dnf clean all && usermod -aG docker developer \
 && passwd -d developer \
 && printf 'PasswordAuthentication no\nPermitRootLogin no\nAllowUsers developer\n' > /etc/ssh/sshd_config.d/lab.conf
COPY lab/host/entrypoint /usr/local/bin/lab-entrypoint
COPY lab/host/dev /usr/local/bin/dev
ENTRYPOINT ["/usr/local/bin/lab-entrypoint"]
