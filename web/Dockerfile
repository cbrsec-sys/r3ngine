# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Final Image
FROM ubuntu:22.04

ARG GECKOVERSION=0.36.0
ARG GOVERSION=1.25.0

RUN ARCH=$(dpkg --print-architecture) \ 
    && if [ "${ARCH}" != "arm64" ] && [ "${ARCH}" != "amd64" ]; then \
      echo "reNgine not supported, encountered unknown architecture: ${TARGETPLATFORM}" \
      && exit 1; \
    fi

# Labels and Credits
LABEL \
    name="reNgine" \
    author="Reboot Dev: MistrHyd3 (https://github.com/whiterabb17) \
    Original By: Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is a automated pipeline of recon process, useful for information gathering during web application penetration testing."

# Environment Variables
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV GOROOT="/usr/local/go"
ENV GOPATH=$HOME/go
ENV PATH="${PATH}:${GOROOT}/bin:${GOPATH}/bin"

# Install Python and Ruby
RUN apt update -y && \
    apt install -y \
    python3.10 \
    python3-dev \
    python3-pip \
    python3-venv \
    xvfb \
    libpci-dev \
    libpciaccess-dev \
    libegl-dev \
    libegl1 \
    libcap2-bin \
    libcap2 \
    ruby-full \
    ruby-dev \
    libcurl4-openssl-dev \
    libxml2 \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    liblzma-dev \
    build-essential \
    patch


# Install essential packages
RUN apt install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    libcairo2-dev \
    geoip-bin \
    geoip-database \
    gcc \
    git \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpcap-dev \
    netcat \
    nmap \
    x11-utils \
    xvfb \
    wget \
    curl \
    libcairo2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    libjpeg-dev \
    libopenjp2-7-dev \
    python3-netaddr \
    software-properties-common \
    ike-scan \
    sslscan \
    medusa \
    hydra \
    proxychains4 \
    jq \
    wrk \
    hping3 \
    postgresql-client \
    unzip --fix-missing -y

RUN add-apt-repository ppa:mozillateam/ppa && \
    apt update -y && \
    apt install -y --no-install-recommends \
    firefox \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libasound2 \
    libx11-xcb1 \
    libxt6 

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

RUN ARCH=$(dpkg --print-architecture) \ 
    && curl -L https://go.dev/dl/go${GOVERSION}.linux-${ARCH}.tar.gz | tar -xzC /usr/local

RUN ARCH=$(dpkg --print-architecture) \ 
    && if [ "${ARCH}" = "arm64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux-aarch64.tar.gz"; \
    elif [ "${ARCH}" = "amd64" ]; then \
      GECKOPATH="geckodriver-v${GECKOVERSION}-linux64.tar.gz"; \
    fi \
    && wget https://github.com/mozilla/geckodriver/releases/download/v${GECKOVERSION}/${GECKOPATH} \
    && tar -xvf ${GECKOPATH} \
    && rm ${GECKOPATH} \
    && mv geckodriver /usr/bin

# Install Rust for orjson
RUN set -e; curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip3 install maturin

# Make directory for app
WORKDIR /usr/src/app

ENV GO111MODULE=on 
RUN printf "\
    github.com/jaeles-project/gospider@latest\n\
    github.com/tomnomnom/gf@latest\n\
    github.com/tomnomnom/unfurl@latest\n\
    github.com/tomnomnom/waybackurls@latest\n\
    github.com/projectdiscovery/httpx/cmd/httpx@latest\n\
    github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest\n\
    github.com/projectdiscovery/chaos-client/cmd/chaos@latest\n\
    github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest\n\
    github.com/projectdiscovery/naabu/v2/cmd/naabu@latest\n\
    github.com/hakluke/hakrawler@latest\n\
    github.com/lc/gau/v2/cmd/gau@latest\n\
    github.com/owasp-amass/amass/v3/...@latest\n\
    github.com/ffuf/ffuf@latest\n\
    github.com/projectdiscovery/tlsx/cmd/tlsx@latest\n\
    github.com/hahwul/dalfox/v2@latest\n\
    github.com/projectdiscovery/katana/cmd/katana@latest\n\
    github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest\n\
    github.com/sa7mon/s3scanner@latest\n\
    github.com/zricethezav/gitleaks/v8@latest\n\
    github.com/xalgord/reconx/cmd/reconx@latest\n" | \
    xargs -L1 go install -ldflags="-s -w" -v && \
    rm -rf /go/pkg/* && rm -rf /root/.cache/go-build

# Install Trufflehog
RUN ARCH=$(dpkg --print-architecture) \
    && TRUFFLEHOG_VERSION=$(curl -s https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | jq -r .tag_name | sed 's/v//') \
    && wget https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz \
    && tar -xvf trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz \
    && mv trufflehog /usr/local/bin/ \
    && rm -rf trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz

# Install k6
RUN ARCH=$(dpkg --print-architecture) \
    && K6_VERSION="0.50.0" \
    && if [ "${ARCH}" = "arm64" ]; then K6_ARCH="arm64"; else K6_ARCH="amd64"; fi \
    && wget https://github.com/grafana/k6/releases/download/v${K6_VERSION}/k6-v${K6_VERSION}-linux-${K6_ARCH}.tar.gz \
    && tar -xvf k6-v${K6_VERSION}-linux-${K6_ARCH}.tar.gz \
    && mv k6-v${K6_VERSION}-linux-${K6_ARCH}/k6 /usr/local/bin/ \
    && rm -rf k6-v${K6_VERSION}-linux-${K6_ARCH}*

# Install Aquatone
RUN ARCH=$(dpkg --print-architecture) \
    && wget https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_${ARCH}_1.7.0.zip \
    && unzip -o aquatone_linux_${ARCH}_1.7.0.zip \
    && mv aquatone /usr/local/bin/ \
    && rm -rf aquatone_linux_${ARCH}_1.7.0.zip README.md LICENSE.txt

# Install Arjun, InQL, Netlas, holehe, maigret (needs newer meson for pycairo)
RUN pip3 install --upgrade meson ninja && pip3 install --upgrade arjun inql netlas holehe maigret

# Install Node.js 20 and Retire.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt install -y nodejs && \
    npm install -g retire

# Update Nuclei and Nuclei-Templates
RUN nuclei -update-templates

# update chaos
RUN chaos -update

# Pre-download common wordlists
RUN mkdir -p /usr/src/wordlist && \
    wget https://raw.githubusercontent.com/maurosoria/dirsearch/master/db/dicc.txt -O /usr/src/wordlist/dicc.txt && \
    wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/deepmagic.com-prefixes-top50000.txt -O /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt

# Download Kiterunner Wordlist
RUN mkdir -p /usr/src/wordlist/kr && \
    cd /usr/src/wordlist/kr && \
    wget https://wordlists-cdn.assetnote.io/data/kiterunner/routes-large.kite.tar.gz -O routes-large.kite.tar.gz && \
    tar -xvf routes-large.kite.tar.gz && \
    rm -rf routes-large.kite.tar.gz && \
    wget https://wordlists-cdn.assetnote.io/data/kiterunner/routes-small.kite.tar.gz -O routes-small.kite.tar.gz && \
    tar -xvf routes-small.kite.tar.gz && \
    rm -rf routes-small.kite.tar.gz

# Install WPScan
RUN gem install wpscan --no-document

# Copy requirements
COPY web/requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir --ignore-installed blinker
RUN playwright install-deps chromium && playwright install chromium

# Install Frontend Dependencies (for Dev mode)
RUN mkdir -p /usr/src/app/frontend
WORKDIR /usr/src/app/frontend
COPY frontend/package*.json ./
RUN npm install
WORKDIR /usr/src/app

# Copy source code
COPY web/ /usr/src/app/
#RUN mkdir -p /usr/src/app/custom_engines

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /usr/src/frontend/dist
COPY frontend/templates /usr/src/frontend/templates

# Ensure SPA index.html is available as a Django template
RUN mkdir -p /usr/src/frontend/templates/dashboard && \
    cp /usr/src/frontend/dist/index.html /usr/src/frontend/templates/dashboard/v3_index.html
