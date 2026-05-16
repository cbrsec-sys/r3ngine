#!/bin/bash
# Ensure OpenSSL compatibility before running any management commands
pip3 install --upgrade --no-cache-dir pyOpenSSL>=24.0.0

# apply existing migrations
python3 manage.py migrate

# make migrations for specific apps
apps=(
    "targetApp"
    "scanEngine"
    "startScan"
    "dashboard"
    "recon_note"
    "plugins"
    "apme"
)

create_migrations() {
    local app=$1
    echo "Creating migrations for $app..."
    python3 manage.py makemigrations $app
    echo "Finished creating migrations for $app"
    echo "----------------------------------------"
}

echo "Starting migration creation process..."

for app in "${apps[@]}"
do
    create_migrations $app
done

echo "Migration creation process completed."

# apply migrations again
echo "Applying migrations..."
python3 manage.py migrate
echo "Migration process completed."


python3 manage.py collectstatic --no-input --clear

# Load default engines, keywords, and external tools
python3 manage.py loaddata fixtures/default_scan_engines.yaml --app scanEngine.EngineType
python3 manage.py loaddata fixtures/default_keywords.yaml --app scanEngine.InterestingLookupModel
python3 manage.py loaddata fixtures/external_tools.yaml --app scanEngine.InstalledExternalTool

# TEMPORARY FIX FOR langchain
pip install requests==2.32.3 "urllib3>=1.26.0,<3.0.0" "charset-normalizer>=3.0.0,<4.0.0" "chardet>=5.0.0,<6.0.0"
pip install tenacity==8.2.2

# install firefox https://askubuntu.com/a/1404401
echo '
Package: *
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 1001

Package: firefox
Pin: version 1:1snap1-0ubuntu2
Pin-Priority: -1
' | tee /etc/apt/preferences.d/mozilla-firefox
apt update
apt install firefox -y

# Temporary fix for whatportis bug - See https://github.com/yogeshojha/rengine/issues/984
sed -i 's/purge()/truncate()/g' /usr/local/lib/python3.10/dist-packages/whatportis/cli.py

# update whatportis
yes | whatportis --update

# clone dirsearch default wordlist
if [ ! -d "/usr/src/wordlist" ]
then
  echo "Making Wordlist directory"
  mkdir /usr/src/wordlist
fi

if [ ! -f "/usr/src/wordlist/" ]
then
  echo "Downloading Default Directory Bruteforce Wordlist"
  wget https://raw.githubusercontent.com/maurosoria/dirsearch/master/db/dicc.txt -O /usr/src/wordlist/dicc.txt
fi

# check if default wordlist for amass exists
if [ ! -f /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt ];
then
  echo "Downloading Deepmagic top 50000 Wordlist"
  wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/deepmagic.com-prefixes-top50000.txt -O /usr/src/wordlist/deepmagic.com-prefixes-top50000.txt
fi

# Setup Auth Brute-Force Wordlists
if [ ! -d "/usr/src/wordlist/auth" ];
then
  echo "Making Auth Wordlist directory"
  mkdir -p /usr/src/wordlist/auth
fi
echo "Copying Auth Wordlists"
cp -r /usr/src/app/wordlist/auth/* /usr/src/wordlist/auth/

# vulscan is a special case (nmap script)
if [ ! -d "/usr/src/github/scipag_vulscan" ];
then
  echo "Cloning Nmap Vulscan script"
  git clone https://github.com/scipag/vulscan /usr/src/github/scipag_vulscan
  echo "Symlinking to nmap script dir"
  ln -s /usr/src/github/scipag_vulscan /usr/share/nmap/scripts/vulscan
  echo "Usage in reNgine, set vulscan/vulscan.nse in nmap_script scanEngine port_scan config parameter"
fi

if [ ! -f '/usr/local/bin/kr' ];
then
  echo "Installing kiterunner"
  cd /usr/src/github
  ARCH=$(dpkg --print-architecture) && \
  wget https://github.com/assetnote/kiterunner/releases/download/v1.0.2/kiterunner_1.0.2_linux_${ARCH}.tar.gz && \
  tar -xvf kiterunner_1.0.2_linux_${ARCH}.tar.gz && \
  mv kr /usr/local/bin/ && \
  rm -rf kiterunner_1.0.2_linux_${ARCH}.tar.gz
  cd /usr/src/app
fi

# Install CMSeeK
# if [ ! -d '/usr/src/github/CMSeeK' ];
# then
#   echo "Cloning CMSeeK"
#   git clone https://github.com/Tuhinshubhra/CMSeeK /usr/src/github/CMSeeK
# fi
# pip3 install -r /usr/src/github/CMSeeK/requirements.txt

# Install LinkFinder
# if [ ! -d '/usr/src/github/LinkFinder' ];
# then
#   echo "Cloning LinkFinder"
#   git clone https://github.com/GerbenJavado/LinkFinder.git /usr/src/github/LinkFinder
# fi
# pip3 install -r /usr/src/github/LinkFinder/requirements.txt
# cd /usr/src/github/LinkFinder
# python3 setup.py install
# cd /usr/src/app

# Install ParamSpider
# if [ ! -d '/usr/src/github/ParamSpider' ];
# then
#   echo "Cloning ParamSpider"
#   git clone https://github.com/devanshbatham/ParamSpider /usr/src/github/ParamSpider
# fi
# cd /usr/src/github/ParamSpider && pip3 install . && python3 setup.py install
# cd /usr/src/app

# Install Semgrep
# if [ ! -d '/usr/src/github/semgrep' ];
# then
#   echo "Cloning Semgrep"
#   git clone https://github.com/semgrep/semgrep /usr/src/github/semgrep
# fi
# cd /usr/src/github/semgrep
# pip3 install .
# cd /usr/src/app

# if [ ! -d '/usr/src/github/Sublist3r' ];
# then
#   echo "Cloning Sublist3r"
#   git clone https://github.com/aboul3la/Sublist3r /usr/src/github/Sublist3r
# fi
# pip3 install -r /usr/src/github/Sublist3r/requirements.txt

# if [ ! -d '/usr/src/github/OneForAll' ];
# then
#   echo "Cloning OneForAll"
#   git clone https://github.com/shmilylty/OneForAll /usr/src/github/OneForAll
# fi
# pip3 install -r /usr/src/github/OneForAll/requirements.txt

# if [ ! -d '/usr/src/github/theHarvester' ];
# then
#   echo "Cloning theHarvester"
#   git clone https://github.com/laramies/theHarvester /usr/src/github/theHarvester
# fi
# cd /usr/src/github/theHarvester && uv sync
# cd /usr/src/app

# if [ ! -d '/usr/src/github/ctfr' ];
# then
#   echo "Cloning ctfr"
#   git clone https://github.com/UnaPibaGeek/ctfr /usr/src/github/ctfr
# fi
# pip3 install -r /usr/src/github/ctfr/requirements.txt

# if [ ! -d '/usr/src/github/acunetix-python' ];
# then
#   echo "Cloning acunetix-python"
#   git clone https://github.com/WazeHell/acunetix-python /usr/src/github/acunetix-python
# fi
# pip3 install /usr/src/github/acunetix-python
# pip3 install -r /usr/src/github/acunetix-python/requirements.txt

# if [ ! -d '/usr/src/github/goofuzz' ];
# then
#   echo "Cloning GooFuzz"
#   DIR=$(pwd)
#   cd /usr/src/github
#   wget https://github.com/m3n0sd0n4ld/GooFuzz/releases/download/1.2.6/GooFuzz.v.1.2.6.zip
#   unzip GooFuzz.v.1.2.6.zip
#   mv GooFuzz.v.1.2.6 goofuzz
#   chmod +x goofuzz/GooFuzz
#   rm GooFuzz.v.1.2.6.zip
#   cd $DIR
# fi

# if [ ! -d '/usr/src/github/spiderfoot' ];
# then
#   echo "Cloning spiderfoot"
#   git clone https://github.com/smicallef/spiderfoot /usr/src/github/spiderfoot
# fi
# pip3 install -r /usr/src/github/spiderfoot/requirements.txt

# if [ ! -d '/usr/src/github/cpanel2shell-scanner' ];
# then
#   echo "Cloning cpanel2shell-scanner"
#   git clone https://github.com/assetnote/cpanel2shell-scanner /usr/src/github/cpanel2shell-scanner
# fi
# pip3 install -r /usr/src/github/cpanel2shell-scanner/requirements.txt

# if [ ! -d '/usr/src/github/react2shell-scanner' ];
# then
#   echo "Cloning react2shell-scanner"
#   git clone https://github.com/assetnote/react2shell-scanner /usr/src/github/react2shell-scanner
# fi
# pip3 install -r /usr/src/github/react2shell-scanner/requirements.txt

# Create a robust cPanel username wordlist
if [ ! -f '/usr/src/wordlist/cpanel_users.txt' ]; then
  echo "Fetching cPanel2Shell wordlist"
  mkdir -p /usr/src/wordlist
  wget -qO- https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt >> /usr/src/wordlist/cpanel_users.txt
  sort -u /usr/src/wordlist/cpanel_users.txt -o /usr/src/wordlist/cpanel_users.txt
fi

# Setup betterleaks
# if [ ! -f '/usr/local/bin/betterleaks' ]; then
#   echo "Setting up betterleaks..."
#   if [ ! -d '/usr/src/github/betterleaks' ]; then
#     git clone https://github.com/betterleaks/betterleaks /usr/src/github/betterleaks
#   fi
#   cd /usr/src/github/betterleaks && make build
#   ln -sf /usr/src/github/betterleaks/betterleaks /usr/local/bin/betterleaks
# fi

# Setup username-anarchy
# if [ ! -f '/usr/local/bin/username-anarchy' ]; then
#   echo "Cloning username-anarchy..."
#   if [ ! -d '/usr/src/github/username-anarchy' ]; then
#     git clone https://github.com/urbanadventurer/username-anarchy /usr/src/github/username-anarchy
#   fi
#   ln -sf /usr/src/github/username-anarchy/username-anarchy /usr/local/bin/username-anarchy
# fi

cd /usr/src/app
# install h8mail
# python3 -m pip install h8mail

# install gf patterns
if [ ! -d "/root/Gf-Patterns" ];
then
  echo "Installing GF Patterns"
  mkdir ~/.gf
  cp -r $GOPATH/src/github.com/tomnomnom/gf/examples/*.json ~/.gf
  git clone https://github.com/1ndianl33t/Gf-Patterns ~/Gf-Patterns
  mv ~/Gf-Patterns/*.json ~/.gf
fi

# store scan_results
if [ ! -d "/usr/src/scan_results" ]
then
  mkdir /usr/src/scan_results
fi

# test tools, required for configuration
naabu && subfinder && amass
nuclei

if [ ! -d "/root/nuclei-templates/geeknik_nuclei_templates" ];
then
  echo "Installing Geeknik Nuclei templates"
  git clone https://github.com/geeknik/the-nuclei-templates.git ~/nuclei-templates/geeknik_nuclei_templates
else
  echo "Removing old Geeknik Nuclei templates and updating new one"
  rm -rf ~/nuclei-templates/geeknik_nuclei_templates
  git clone https://github.com/geeknik/the-nuclei-templates.git ~/nuclei-templates/geeknik_nuclei_templates
fi

if [ ! -f ~/nuclei-templates/ssrf_nagli.yaml ];
then
  echo "Downloading ssrf_nagli for Nuclei"
  wget https://raw.githubusercontent.com/NagliNagli/BountyTricks/main/ssrf.yaml -O ~/nuclei-templates/ssrf_nagli.yaml
fi

# AI Map Templates
echo "Checking for AI Map Templates"
if [ ! -f ~/nuclei-templates/langserve-detect.yaml ];
then
  echo "Downloading langserve-detect for Nuclei"
  wget https://raw.githubusercontent.com/BishopFox/aimap/refs/heads/main/templates/langserve-detect.yaml -O ~/nuclei-templates/langserve-detect.yaml
fi

if [ ! -f ~/nuclei-templates/mcp-server-detect.yaml ];
then
  echo "Downloading mcp-server-detect for Nuclei"
  wget https://github.com/BishopFox/aimap/raw/refs/heads/main/templates/mcp-server-detect.yaml -O ~/nuclei-templates/mcp-server-detect.yaml
fi

if [ ! -f ~/nuclei-templates/mcp-tool-enum.yaml ];
then
  echo "Downloading mcp-tool-enum for Nuclei"
  wget https://github.com/BishopFox/aimap/raw/refs/heads/main/templates/mcp-tool-enum.yaml -O ~/nuclei-templates/mcp-tool-enum.yaml
fi

if [ ! -f ~/nuclei-templates/openai-compat-detect.yaml ];
then
  echo "Downloading openai-compat-detect for Nuclei"
  wget https://github.com/BishopFox/aimap/raw/refs/heads/main/templates/openai-compat-detect.yaml -O ~/nuclei-templates/openai-compat-detect.yaml
fi

if [ ! -f ~/nuclei-templates/prompt-leak.yaml ];
then
  echo "Downloading prompt-leak for Nuclei"
  wget https://github.com/BishopFox/aimap/raw/refs/heads/main/templates/prompt-leak.yaml -O ~/nuclei-templates/prompt-leak.yaml
fi

# httpx seems to have issue, use alias instead!!!
echo 'alias httpx="/go/bin/httpx"' >> ~/.bashrc

# TEMPORARY FIX, httpcore is causing issues with celery, removing it as temp fix
#python3 -m pip uninstall -y httpcore

# TEMPORARY FIX FOR langchain
pip install requests==2.32.3 "urllib3>=1.26.0,<3.0.0" "charset-normalizer>=3.0.0,<4.0.0" "chardet>=5.0.0,<6.0.0"
pip3 install tenacity==8.2.2

loglevel='warning'
if [ "$DEBUG" == "1" ]; then
    loglevel='debug'
fi

echo "Starting Consolidated Celery Workers..."

# 1. Main Scan & Tool Worker (Prefork pool for stoppable tasks)
# Listens to: main_scan_queue, initiate_scan_queue, subscan_queue, run_command_queue, osint_queue, spiderfoot_queue
echo "Starting Core Scan & Tool Worker..."
STOPPABLE_QUEUES="main_scan_queue,initiate_scan_queue,subscan_queue,run_command_queue,osint_queue,spiderfoot_queue"
celery -A reNgine.tasks worker --loglevel=$loglevel --optimization=fair --autoscale=$MAX_CONCURRENCY,$MIN_CONCURRENCY -Q $STOPPABLE_QUEUES -n core_scan_worker &

# 2. Service Worker (Gevent pool for high-concurrency I/O tasks)
# Listens to: api_queue, report_queue, send_notif_queue, etc.
SERVICE_QUEUES="api_queue,report_queue,send_notif_queue,send_task_notif_queue,send_file_to_discord_queue,send_hackerone_report_queue,parse_nmap_results_queue,geo_localize_queue,query_whois_queue,remove_duplicate_endpoints_queue,query_reverse_whois_queue,query_ip_history_queue,send_scan_notif_queue"
echo "Starting Service Worker Group..."
celery -A reNgine worker --pool=gevent --concurrency=100 --optimization=fair --loglevel=$loglevel -Q $SERVICE_QUEUES -n service_worker &

# 3. LLM Worker (Gevent pool for AI/LLM tasks)
# Listens to: llm_queue
echo "Starting LLM Worker..."
celery -A reNgine.tasks worker --pool=gevent --concurrency=20 --optimization=fair --loglevel=$loglevel -Q llm_queue -n llm_worker &

wait