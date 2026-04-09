# Huong dan cai pyenv va uv tren Linux Mint de chay Python

## 1) Cai dependency he thong

```bash
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev curl git \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev ca-certificates
```

## 2) Cai pyenv

```bash
curl -fsSL https://pyenv.run | bash
```

Them vao `~/.zshrc`:

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc
```

Reload shell:

```bash
exec zsh
```

Kiem tra:

```bash
pyenv --version
```

## 3) Cai Python bang pyenv

```bash
pyenv install 3.12.4
pyenv global 3.12.4
python --version
```

## 4) Cai uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Neu PATH chua duoc them:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
exec zsh
```

Kiem tra:

```bash
uv --version
```

## 5) Dung pyenv + uv cho project

```bash
mkdir myproj && cd myproj
pyenv local 3.12.4
uv venv
source .venv/bin/activate
uv pip install fastapi
python -V
```

## 6) Meo tranh xung dot

- Khong dung Python system cho project.
- Moi project dung `pyenv local` + `uv venv`.
- Neu `python` chua dung version: `pyenv rehash` roi mo shell moi.

---

Da lam: cung cap huong dan day du cai pyenv + uv + test Python.
Chua lam: chua thuc hien cai dat truc tiep tren may.
