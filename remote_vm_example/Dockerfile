FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including pipx and Python tools
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv pipx \
    docker.io curl openssh-server iputils-ping net-tools vim zip rsync git screen && \
    pipx ensurepath && \
    pipx install scapy && \
    pipx inject scapy requests && \
    rm -rf /var/lib/apt/lists/*

# Install Docker Compose v2 plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -SL https://github.com/docker/compose/releases/download/v2.27.1/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Enable root SSH login
RUN echo 'root:rootpassword' | chpasswd && \
    sed -i 's/#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#\?Port.*/Port 2222/' /etc/ssh/sshd_config && \
    mkdir -p /var/run/sshd

# Copy project folders
COPY Notes /root/Notes
COPY Pwnzer0tt1Shop /root/Pwnzer0tt1Shop
COPY PCSS /root/PCSS
COPY Mudarabah /root/Mudarabah
COPY CheesyCheats /root/CheesyCheats
COPY HttpsCustom /root/HttpsCustom

# Expose SSH port
EXPOSE 2222

# Start SSH
CMD ["/usr/sbin/sshd", "-D"]
