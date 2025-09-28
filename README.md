# Setup

```bash

mkdir .streamlit
touch .streamlit/secrets.toml

uv init --python 3.13
uv add 'streamlit==1.50.0'
uv add 'pandas==2.3.0'
uv add 'supabase==2.16'

source .venv/bin/activate
which python3
python3 --version

uv export --format requirements-txt --output-file requirements.txt

```
