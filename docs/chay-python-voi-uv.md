# Huong dan chay file Python voi uv

## 1) Chay nhanh mot file Python

```bash
uv run main.py
```

Lenh nay se tu xu ly moi truong can thiet de chay file.

## 2) Chay voi version Python cu the

```bash
uv run --python 3.12 main.py
```

Neu ban dang dung `pyenv`, co the dat version rieng cho project:

```bash
pyenv local 3.12.4
uv run main.py
```

## 3) Chay file co dependency ngoai

### Cach khuyen dung cho project

```bash
uv init
uv add requests
uv run main.py
```

### Chay nhanh voi dependency tam thoi

```bash
uv run --with requests main.py
```

## 4) Vi du day du

```bash
mkdir demo-uv && cd demo-uv
echo 'import requests; print("ok")' > main.py
uv init
uv add requests
uv run main.py
```

---

Da lam: tao huong dan day du cach chay file Python voi uv theo cac tinh huong pho bien.
Chua lam: chua chay verify truc tiep tren may cua ban.
