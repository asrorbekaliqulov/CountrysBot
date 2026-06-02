# CI/CD — GitHub → Server

`main` branchga push qilinganda GitHub Actions serverda avtomatik deploy qiladi.

## Server

| Parametr | Qiymat |
|----------|--------|
| Loyiha joyi | `/var/www/CountrysBot` |
| Servislar | `gunicorn`, `telegram_bot` |
| Domen | `https://n-medhomelab.uz` |

`.env` fayli gitda yo'q — deploy paytida **o'zgarmaydi** (faqat zaxira nusxa olinadi).

## GitHub Secrets (majburiy)

Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Misol | Tavsif |
|--------|-------|--------|
| `DEPLOY_HOST` | `77.237.245.1` yoki `n-medhomelab.uz` | Server IP yoki domen |
| `DEPLOY_USER` | `root` | SSH foydalanuvchi |
| `DEPLOY_SSH_KEY` | (private key) | Quyidagi SSH kalit |
| `DEPLOY_PATH` | `/var/www/CountrysBot` | Ixtiyoriy, default shu |
| `DEPLOY_PORT` | `22` | Ixtiyoriy |

### SSH kalit yaratish (serverda bir marta)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "github-actions-countrysbot"
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/github_deploy ~/.ssh/authorized_keys
cat ~/.ssh/github_deploy   # chiqishni DEPLOY_SSH_KEY ga nusxalang
```

## Qo'lda deploy

```bash
cd /var/www/CountrysBot
bash scripts/deploy.sh
```

## Tekshirish

Push qilgandan keyin: GitHub → **Actions** → **Deploy to production** workflow yashil bo'lishi kerak.
