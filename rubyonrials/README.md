# Rails Chat UI

Rails serves the browser UI and proxies chat requests to the Python SI-1 service. It does not import Python modules into Ruby.

## Prerequisites

- Ruby and Bundler compatible with Rails 7.0, installed on `PATH`
- Python 3.10+ and the project dependencies from the repository root
- Lucifer and Obi `llama-server` processes reachable at the configured SI-1 URLs

## antiX 26 Linux Setup

Open a terminal from the repository root. Install the system packages needed by
Ruby native gems, SQLite, Python virtual environments, and the Python runtime:

```bash
sudo apt update
sudo apt install -y ruby-full ruby-dev bundler build-essential pkg-config \
	libsqlite3-dev libyaml-dev libffi-dev libssl-dev zlib1g-dev \
	python3 python3-venv python3-pip
```

Check that Ruby is new enough for Rails 7 and that Bundler is available:

```bash
ruby --version
gem --version
bundle --version
```

Create a Linux Python environment at the repository root. Do not reuse a
Windows `.venv-1` or copy a virtual environment between operating systems.

```bash
cd /path/to/finalSI1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export SI1_ROOT="$PWD"
```

Start the two model servers in separate terminals using the GGUF files and
llama.cpp build available on this machine. They must listen on the endpoints
configured by SI-1 (defaults shown):

```text
Lucifer: 127.0.0.1:666
Obi:     127.0.0.1:999
```

Start the Python HTTP adapter from the repository root:

```bash
source .venv/bin/activate
export SI1_ROOT="$PWD"
python rubyonrials/backend.py
```

In another terminal, confirm the adapter is ready, then set the backend URL and
prepare Bundler for Linux. The checked-in `Gemfile.lock` was generated on
Windows; adding the Linux platform lets Bundler resolve Linux-native gems while
preserving the Windows platform entry.

```bash
curl --fail http://127.0.0.1:5000/health
cd /path/to/finalSI1/rubyonrials
bundle lock --add-platform x86_64-linux
bundle install
bundle exec rails db:prepare
export SI1_PYTHON_BACKEND_URL="http://127.0.0.1:5000/chat"
bundle exec rails server -b 127.0.0.1 -p 3000
```

Open `http://127.0.0.1:3000`. Keep the model servers and Python adapter running
while using Rails. For deployments reachable from other machines, configure the
bind address and firewall deliberately; the default commands bind locally.

## Start the Python service

From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SI1_ROOT = (Get-Location).Path
python rubyonrials\backend.py
```

The API listens on `http://127.0.0.1:5000` by default. Check `GET /health` before opening Rails.

## Start Rails

In a second PowerShell terminal:

```powershell
cd rubyonrials
bundle install
$env:SI1_PYTHON_BACKEND_URL = "http://127.0.0.1:5000/chat"
bundle exec rails server -b 127.0.0.1 -p 3000
```

Open `http://127.0.0.1:3000`. To use another Python API address, set `SI1_PYTHON_BACKEND_URL` before starting Rails. Model execution can take several minutes; the proxy read timeout is 3600 seconds.

Rails 7.0.10 boot, route loading, and basic HTTP responses were verified on
Windows with Ruby 3.3.12. antiX 26 setup is documented here but has not been run
on antiX in this workspace. A live duel still requires working Lucifer and Obi
model servers.
