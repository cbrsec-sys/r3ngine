# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
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

# Install Python
RUN apt update -y && \
    apt install -y \
    python3.10 \
    python3-dev \
    python3-pip \
    libpci-dev \
    libpciaccess-dev \
    libegl-dev \
    libegl1 \
    libcap2-bin \
    libcap2


# Install essential packages
RUN apt install -y --no-install-recommends \
    build-essential \
    cmake \
    geoip-bin \
    geoip-database \
    gcc \
    git \
    libpq-dev \
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
    proxychains4 \
    jq \
    unzip

RUN add-apt-repository ppa:mozillateam/ppa

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
    github.com/zricethezav/gitleaks/v8@latest\n" | \
    xargs -L1 go install -ldflags="-s -w" -v && \
    rm -rf /go/pkg/* && rm -rf /root/.cache/go-build

# Install Trufflehog
RUN ARCH=$(dpkg --print-architecture) \
    && TRUFFLEHOG_VERSION=$(curl -s https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | jq -r .tag_name | sed 's/v//') \
    && wget https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz \
    && tar -xvf trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz \
    && mv trufflehog /usr/local/bin/ \
    && rm -rf trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz

# Install Aquatone
RUN ARCH=$(dpkg --print-architecture) \
    && wget https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_${ARCH}_1.7.0.zip \
    && unzip -o aquatone_linux_${ARCH}_1.7.0.zip \
    && mv aquatone /usr/local/bin/ \
    && rm -rf aquatone_linux_${ARCH}_1.7.0.zip README.md LICENSE.txt

# Install Arjun, InQL, Netlas
RUN pip3 install arjun inql netlas

# Clone and install managed tools
RUN git clone https://github.com/GerbenJavado/LinkFinder.git /usr/src/github/LinkFinder && \
    cd /usr/src/github/LinkFinder && pip3 install -r requirements.txt && python3 setup.py install

RUN git clone https://github.com/devanshbatham/ParamSpider /usr/src/github/ParamSpider && \
    cd /usr/src/github/ParamSpider && pip3 install .

RUN git clone https://github.com/semgrep/semgrep /usr/src/github/semgrep && \
    cd /usr/src/github/semgrep && pip3 install .

RUN git clone https://github.com/aboul3la/Sublist3r /usr/src/github/Sublist3r && \
    cd /usr/src/github/Sublist3r && pip3 install -r requirements.txt

RUN git clone https://github.com/shmilylty/OneForAll /usr/src/github/OneForAll && \
    cd /usr/src/github/OneForAll && pip3 install -r requirements.txt

RUN git clone https://github.com/laramies/theHarvester /usr/src/github/theHarvester && \
    cd /usr/src/github/theHarvester && uv sync

RUN git clone https://github.com/UnaPibaGeek/ctfr /usr/src/github/ctfr && \
    cd /usr/src/github/ctfr && pip3 install -r requirements.txt

RUN ARCH=$(dpkg --print-architecture) \
    && wget https://github.com/assetnote/kiterunner/releases/download/v1.0.2/kiterunner_1.0.2_linux_${ARCH}.tar.gz && \
    tar -xvf kiterunner_1.0.2_linux_${ARCH}.tar.gz && \
    mv kr /usr/local/bin/ && \
    rm -rf kiterunner_1.0.2_linux_${ARCH}.tar.gz

# Install Trivy with checksum verification
RUN ARCH=$(dpkg --print-architecture) \
    && if [ "${ARCH}" = "arm64" ]; then TRIVY_ARCH="ARM64"; else TRIVY_ARCH="64bit"; fi \
    && TRIVY_VERSION="0.59.1" \
    && wget https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz \
    && wget https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_checksums.txt \
    && grep "trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz" trivy_${TRIVY_VERSION}_checksums.txt | sha256sum -c - \
    && tar -xvf trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz \
    && mv trivy /usr/local/bin/ \
    && rm -rf trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz trivy_${TRIVY_VERSION}_checksums.txt

# Download Kiterunner Wordlist
RUN mkdir -p /usr/src/wordlist/kr && \
    cd /usr/src/wordlist/kr && \
    wget https://wordlists-cdn.assetnote.io/data/kiterunner/routes-large.kite.tar.gz -O routes-large.kite.tar.gz && \
    tar -xvf routes-large.kite.tar.gz && \
    rm -rf routes-large.kite.tar.gz && \
    wget https://wordlists-cdn.assetnote.io/data/kiterunner/routes-small.kite.tar.gz -O routes-small.kite.tar.gz && \
    tar -xvf routes-small.kite.tar.gz && \
    rm -rf routes-small.kite.tar.gz

# Install SpiderFoot
RUN git clone https://github.com/smicallef/spiderfoot /usr/src/github/spiderfoot
WORKDIR /usr/src/github/spiderfoot
RUN pip3 install -r requirements.txt
WORKDIR /usr/src/app

# Install Chromium and Retire.js
RUN apt install chromium-driver -y && \
    npm install -g retire

# Setup Eyewitness
RUN git clone https://github.com/RedSiege/EyeWitness /usr/src/github/EyeWitness && \
    cd /usr/src/github/EyeWitness && \
    bash setup/setup.sh

# Update Nuclei and Nuclei-Templates
RUN nuclei -update-templates

# update chaos
RUN chaos -update

# Pre-download common wordlists
RUN mkdir -p /usr/src/wordlist && \
    wget https://raw.githubusercontent.com/maurosoria/dirsearch/master/db/dicc.txt -O /usr/src/wordlist/dicc.txt && \
    wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/deepmagic.com-prefixes-top50000.txt -O /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt

# Pre-clone nmap scripts and other tools
RUN mkdir -p /usr/src/github && \
    git clone https://github.com/scipag/vulscan /usr/src/github/scipag_vulscan && \
    ln -s /usr/src/github/scipag_vulscan /usr/share/nmap/scripts/vulscan && \
    git clone https://github.com/Tuhinshubhra/CMSeeK /usr/src/github/CMSeeK && \
    pip3 install -r /usr/src/github/CMSeeK/requirements.txt && \
    git clone https://github.com/m3n0sd0n4ld/GooFuzz.git /usr/src/github/goofuzz && \
    chmod +x /usr/src/github/goofuzz/GooFuzz

# Copy requirements
COPY web/requirements.txt /tmp/requirements.txt
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r /tmp/requirements.txt --no-cache-dir

# install eyewitness
RUN pip3 install --no-cache-dir fuzzywuzzy \
    selenium==4.9.1 \
    python-Levenshtein \
    pyvirtualdisplay \
    netaddr

# Copy source code
COPY web/ /usr/src/app/
RUN mkdir -p /usr/src/app/custom_engines

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /usr/src/frontend/dist
COPY frontend/templates /usr/src/frontend/templates

# Ensure SPA index.html is available as a Django template
RUN mkdir -p /usr/src/frontend/templates/dashboard && \
    cp /usr/src/frontend/dist/index.html /usr/src/frontend/templates/dashboard/v3_index.html
