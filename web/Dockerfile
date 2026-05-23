# ===========================================================================
# Stage 1: Frontend Builder
# Compiles the React/Vite frontend. Only the /dist output is used downstream.
# ===========================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build


# ===========================================================================
# Stage 2: Go Tools Builder
#
# Compiles all third-party Go security tools in a single RUN statement so the
# module download cache never bloats a committed image layer.
# libpcap-dev is required by naabu (raw packet capture via CGo).
#
# Only /go/bin/* binaries are exported to the final image — the entire Go SDK,
# module cache, and build cache stay inside this ephemeral stage.
# ===========================================================================
FROM golang:1.25-bookworm AS go-tools-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpcap-dev make && \
    rm -rf /var/lib/apt/lists/*

ENV GO111MODULE=on

# All tools in one RUN: single cache-invalidation point, no intermediate layers
# retaining module/build cache. -ldflags="-s -w" strips debug + DWARF symbols.
RUN go install -ldflags="-s -w" -v github.com/ibnaleem/gosearch@5d2e872aac3f && \
    go install -ldflags="-s -w" -v github.com/jaeles-project/gospider@latest && \
    go install -ldflags="-s -w" -v github.com/tomnomnom/gf@dcd4c361f9f5ba302294ed38b8ce278e8ba69006 && \
    go install -ldflags="-s -w" -v github.com/tomnomnom/unfurl@latest && \
    go install -ldflags="-s -w" -v github.com/tomnomnom/waybackurls@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/chaos-client/cmd/chaos@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.3.8 && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest && \
    go install -ldflags="-s -w" -v github.com/hakluke/hakrawler@latest && \
    go install -ldflags="-s -w" -v github.com/lc/gau/v2/cmd/gau@latest && \
    go install -ldflags="-s -w" -v github.com/owasp-amass/amass/v4/...@v4.2.0 && \
    go install -ldflags="-s -w" -v github.com/ffuf/ffuf/v2@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest && \
    go install -ldflags="-s -w" -v github.com/hahwul/dalfox/v2@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install -ldflags="-s -w" -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest && \
    go install -ldflags="-s -w" -v github.com/sa7mon/s3scanner@b6c26d67bc2abe346555dd7010e6065889d66039 && \
    go install -ldflags="-s -w" -v github.com/zricethezav/gitleaks/v8@latest && \
    go install -ldflags="-s -w" -v github.com/xalgord/reconx/cmd/reconx@latest && \
    rm -rf /go/pkg /root/.cache/go-build

# betterleaks has no published go install path — clone and build directly.
RUN git clone --depth 1 https://github.com/betterleaks/betterleaks /tmp/betterleaks && \
    cd /tmp/betterleaks && make build && \
    cp betterleaks /go/bin/betterleaks && \
    rm -rf /tmp/betterleaks


# ===========================================================================
# Stage 3: r3ngine Executor Builder
#
# Compiles the Temporal Go activity worker binary (r3ngine-executor).
# The executor is a pure-Go project (no CGo) so no special libs needed.
# ===========================================================================
FROM golang:1.22-bookworm AS executor-builder

WORKDIR /build
# Copy executor source from the repo root context
COPY web/executor/ ./

RUN go mod download && \
    CGO_ENABLED=0 GO111MODULE=on go build -ldflags="-s -w" -o /usr/local/bin/r3ngine-executor . && \
    rm -rf /root/.cache/go-build /go/pkg


# ===========================================================================
# Stage 4: Runtime Image
#
# Ubuntu 22.04 base. Contains ONLY what r3ngine needs to run:
#   - Python + pip + runtime shared libs
#   - Ruby (WPScan)
#   - Node.js (Retire.js)
#   - Pre-compiled Go tool binaries (copied from go-tools-builder)
#   - r3ngine-executor binary (copied from executor-builder)
#   - Built frontend dist (copied from frontend-builder)
#   - Python-based tools (shallow-cloned, .git stripped)
#   - Playwright Chromium
#
# NOT present: Go SDK, Rust toolchain, build caches, full git histories,
#              nuclei-templates (volume), wordlists (volume).
# ===========================================================================
FROM ubuntu:22.04

# Prevent interactive APT prompts during build
ENV DEBIAN_FRONTEND="noninteractive" \
    DATABASE="postgres" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL \
    name="reNgine" \
    author="Reboot Dev: MistrHyd3 (https://github.com/whiterabb17) \
    Original By: Yogesh Ojha <yogesh.ojha11@gmail.com>" \
    description="reNgine is an automated recon pipeline for web application penetration testing."

# ---------------------------------------------------------------------------
# System packages — single combined RUN to keep the layer count low.
# build-essential is kept because pip installs some packages that compile
# C extensions (cryptography, pycairo, etc.) and gems (wpscan) need gcc.
# ---------------------------------------------------------------------------
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    # Python 3 runtime
    python3.10 \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-netaddr \
    # Ruby (WPScan)
    ruby-full \
    ruby-dev \
    # Shared libraries required by Python C-extension packages
    libcurl4-openssl-dev \
    libxml2 \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    liblzma-dev \
    libpq-dev \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libcairo2-dev \
    libcairo2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    pkg-config \
    shared-mime-info \
    # libpcap runtime lib — needed by naabu binary at runtime
    libpcap-dev \
    # Capability bits for naabu raw sockets
    libcap2-bin \
    libcap2 \
    # EGL/PCI — required by Playwright/Chromium GPU path
    libpci-dev \
    libpciaccess-dev \
    libegl-dev \
    libegl1 \
    # Network and scanning tools
    git \
    wget \
    curl \
    nmap \
    netcat \
    ike-scan \
    sslscan \
    proxychains4 \
    hping3 \
    wrk \
    postgresql-client \
    # Utilities
    jq \
    unzip \
    geoip-bin \
    geoip-database \
    patch \
    # Build tools — required by pip (C extensions) and gem installs
    build-essential \
    cmake \
    ninja-build \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Install uv (fast Python package manager — used by theHarvester)
# ---------------------------------------------------------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# ---------------------------------------------------------------------------
# Node.js 20 + Retire.js (JS dependency vulnerability scanner)
# Node runtime is needed at runtime for `retire` — not just build time.
# ---------------------------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g retire && \
    rm -rf /var/lib/apt/lists/* /root/.npm

# ---------------------------------------------------------------------------
# Copy compiled Go tool binaries from the builder stage.
# The entire Go SDK stays in the builder — only ~100MB of binaries come here.
# ---------------------------------------------------------------------------
COPY --from=go-tools-builder /go/bin/* /usr/local/bin/

# ---------------------------------------------------------------------------
# Copy the r3ngine Temporal executor binary
# ---------------------------------------------------------------------------
COPY --from=executor-builder /usr/local/bin/r3ngine-executor /usr/local/bin/r3ngine-executor

# ---------------------------------------------------------------------------
# Install pre-built binary tools (no compilation needed at runtime)
# ---------------------------------------------------------------------------

# Trufflehog — secret scanning binary
RUN ARCH=$(dpkg --print-architecture) && \
    TRUFFLEHOG_VERSION=$(curl -s https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | jq -r .tag_name | sed 's/v//') && \
    wget -q "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz" && \
    tar -xf "trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz" trufflehog && \
    mv trufflehog /usr/local/bin/ && \
    rm -f "trufflehog_${TRUFFLEHOG_VERSION}_linux_${ARCH}.tar.gz"

# k6 — load/stress testing tool
RUN ARCH=$(dpkg --print-architecture) && \
    K6_VERSION="0.50.0" && \
    if [ "${ARCH}" = "arm64" ]; then K6_ARCH="arm64"; else K6_ARCH="amd64"; fi && \
    wget -q "https://github.com/grafana/k6/releases/download/v${K6_VERSION}/k6-v${K6_VERSION}-linux-${K6_ARCH}.tar.gz" && \
    tar -xf "k6-v${K6_VERSION}-linux-${K6_ARCH}.tar.gz" "k6-v${K6_VERSION}-linux-${K6_ARCH}/k6" && \
    mv "k6-v${K6_VERSION}-linux-${K6_ARCH}/k6" /usr/local/bin/ && \
    rm -rf "k6-v${K6_VERSION}-linux-${K6_ARCH}"*

# Brutus — HTTP brute force tool
RUN curl -L https://github.com/praetorian-inc/brutus/releases/latest/download/brutus-linux-amd64.tar.gz | \
    tar xz && mv brutus /usr/local/bin/

# Aquatone — visual recon / screenshot tool (needs Chromium at runtime)
RUN ARCH=$(dpkg --print-architecture) && \
    wget -q "https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_${ARCH}_1.7.0.zip" && \
    unzip -o "aquatone_linux_${ARCH}_1.7.0.zip" aquatone && \
    mv aquatone /usr/local/bin/ && \
    rm -f "aquatone_linux_${ARCH}_1.7.0.zip"

# WPScan — WordPress vulnerability scanner
RUN gem install wpscan --no-document

# GooFuzz — Google-dork based fuzzer (shell script, no compilation)
RUN mkdir -p /usr/src/github && \
    wget -q -O /tmp/GooFuzz.zip "https://github.com/m3n0sd0n4ld/GooFuzz/releases/download/1.2.6/GooFuzz.v.1.2.6.zip" && \
    unzip -q /tmp/GooFuzz.zip -d /tmp/goofuzz_extract && \
    mv /tmp/goofuzz_extract/GooFuzz.v.1.2.6 /usr/src/github/goofuzz && \
    chmod +x /usr/src/github/goofuzz/GooFuzz && \
    rm -rf /tmp/GooFuzz.zip /tmp/goofuzz_extract

WORKDIR /usr/src/app

# ---------------------------------------------------------------------------
# Clone Python-based security tools
# All clones are shallow (--depth 1) and .git directories are removed after
# installation to eliminate full git history from the image.
# ---------------------------------------------------------------------------
RUN git clone --depth 1 https://github.com/smicallef/spiderfoot /usr/src/github/spiderfoot && \
    pip3 install --no-cache-dir -r /usr/src/github/spiderfoot/requirements.txt && \
    rm -rf /usr/src/github/spiderfoot/.git

RUN git clone --depth 1 https://github.com/assetnote/cpanel2shell-scanner /usr/src/github/cpanel2shell-scanner && \
    pip3 install --no-cache-dir -r /usr/src/github/cpanel2shell-scanner/requirements.txt && \
    rm -rf /usr/src/github/cpanel2shell-scanner/.git

RUN git clone --depth 1 https://github.com/assetnote/react2shell-scanner /usr/src/github/react2shell-scanner && \
    pip3 install --no-cache-dir -r /usr/src/github/react2shell-scanner/requirements.txt && \
    rm -rf /usr/src/github/react2shell-scanner/.git

RUN git clone --depth 1 https://github.com/UnaPibaGeek/ctfr /usr/src/github/ctfr && \
    pip3 install --no-cache-dir -r /usr/src/github/ctfr/requirements.txt && \
    rm -rf /usr/src/github/ctfr/.git

RUN git clone --depth 1 https://github.com/urbanadventurer/username-anarchy /usr/src/github/username-anarchy && \
    ln -sf /usr/src/github/username-anarchy/username-anarchy /usr/local/bin/username-anarchy

RUN git clone --depth 1 https://github.com/WazeHell/acunetix-python /usr/src/github/acunetix-python && \
    pip3 install --no-cache-dir /usr/src/github/acunetix-python && \
    rm -rf /usr/src/github/acunetix-python/.git

RUN git clone --depth 1 https://github.com/shmilylty/OneForAll /usr/src/github/OneForAll && \
    pip3 install --no-cache-dir -r /usr/src/github/OneForAll/requirements.txt && \
    rm -rf /usr/src/github/OneForAll/.git

RUN git clone --depth 1 https://github.com/aboul3la/Sublist3r /usr/src/github/Sublist3r && \
    pip3 install --no-cache-dir -r /usr/src/github/Sublist3r/requirements.txt && \
    rm -rf /usr/src/github/Sublist3r/.git

RUN git clone --depth 1 https://github.com/laramies/theHarvester /usr/src/github/theHarvester && \
    cd /usr/src/github/theHarvester && uv sync && \
    rm -rf /usr/src/github/theHarvester/.git

RUN git clone --depth 1 https://github.com/devanshbatham/ParamSpider /usr/src/github/ParamSpider && \
    cd /usr/src/github/ParamSpider && pip3 install --no-cache-dir . && \
    rm -rf /usr/src/github/ParamSpider/.git

RUN git clone --depth 1 https://github.com/GerbenJavado/LinkFinder.git /usr/src/github/LinkFinder && \
    pip3 install --no-cache-dir -r /usr/src/github/LinkFinder/requirements.txt && \
    cd /usr/src/github/LinkFinder && python3 setup.py install && \
    rm -rf /usr/src/github/LinkFinder/.git

RUN git clone --depth 1 https://github.com/Tuhinshubhra/CMSeeK /usr/src/github/CMSeeK && \
    pip3 install --no-cache-dir -r /usr/src/github/CMSeeK/requirements.txt && \
    rm -rf /usr/src/github/CMSeeK/.git

# ---------------------------------------------------------------------------
# Install Python security tools via pip (no source clone needed)
#
# NOTE: semgrep is installed via pip ONLY. The source clone that was here
# previously was completely redundant (pip handles it) and has been removed.
# ---------------------------------------------------------------------------
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel pyOpenSSL h8mail && \
    pip3 install --no-cache-dir semgrep && \
    pip3 install --no-cache-dir --upgrade meson ninja arjun inql netlas holehe maigret dirsearch

RUN python3 -m pip install --no-cache-dir pipx && \
    pipx install git+https://github.com/blacklanternsecurity/baddns

# ---------------------------------------------------------------------------
# Copy and install the application's Python requirements
# This layer is intentionally placed after tool installs so requirements.txt
# changes don't invalidate the tool-install cache layers above.
# ---------------------------------------------------------------------------
COPY web/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt --ignore-installed blinker

# pip's httpx Python package installs a CLI wrapper at /usr/local/bin/httpx that
# overwrites the ProjectDiscovery Go tool copied earlier. Restore the Go binary.
COPY --from=go-tools-builder /go/bin/httpx /usr/local/bin/httpx

# ---------------------------------------------------------------------------
# Install Playwright Chromium (required for Aquatone screenshot capability)
# ---------------------------------------------------------------------------
RUN playwright install-deps chromium && \
    playwright install chromium && \
    ln -sf /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome /usr/bin/chromium

# ---------------------------------------------------------------------------
# Copy application source (placed last — changes most frequently, so layers
# above this line are fully cached on code-only rebuilds)
# ---------------------------------------------------------------------------
COPY web/ /usr/src/app/

#RUN mkdir -p /usr/src/app/frontend
#COPY frontend/ /usr/src/app/frontend/
#WORKDIR /usr/src/app/frontend
#RUN npm install
#WORKDIR /usr/src/app

# ---------------------------------------------------------------------------
# Copy built frontend from frontend-builder
# ---------------------------------------------------------------------------
COPY --from=frontend-builder /app/frontend/dist /usr/src/frontend/dist

# ---------------------------------------------------------------------------
# Final cleanup: strip Python bytecode and __pycache__ from all tool repos
# to remove files that are regenerated on first import anyway.
# ---------------------------------------------------------------------------
RUN find /usr/src -name "*.pyc" -delete 2>/dev/null; \
    find /usr/src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
    true
