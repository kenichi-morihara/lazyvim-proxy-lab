FROM lazyvim-lab-base:locked
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
COPY ca.crt /etc/pki/ca-trust/source/anchors/lab.crt
RUN update-ca-trust
ENV HTTP_PROXY=http://10.203.77.2:8080 HTTPS_PROXY=http://10.203.77.2:8080 \
    http_proxy=http://10.203.77.2:8080 https_proxy=http://10.203.77.2:8080 \
    NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
    SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt \
    REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt \
    NODE_EXTRA_CA_CERTS=/etc/pki/tls/certs/ca-bundle.crt \
    PIP_CERT=/etc/pki/tls/certs/ca-bundle.crt \
    PATH=/home/developer/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
USER developer
WORKDIR /workspace
CMD ["sleep", "infinity"]
