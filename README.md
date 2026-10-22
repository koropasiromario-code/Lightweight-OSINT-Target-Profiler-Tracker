# Lightweight OSINT Target Profiler Tracker

Aplikasi Streamlit untuk mengumpulkan metadata dari website publik yang diizinkan, menyimpan snapshot, membandingkan perubahan, dan mengekspor laporan. Fokus pada **website/asset**, bukan pelacakan individu atau atribusi identitas.

## Fitur MVP Plus

- Metadata HTTPS: title, description, canonical, Open Graph title, robots meta, bahasa HTML, status HTTP, content type, Server header.
- Timeout dan batas ukuran respons; redirect tidak diikuti; allowlist host dan pemeriksaan DNS untuk IP publik.
- Waktu UTC, waktu respons, ukuran body, SHA-256 body.
- Riwayat snapshot, deteksi perubahan, visualisasi status HTTP, ekspor CSV dan JSON.
- Laporan terstruktur dengan temuan dan batasan.
- SQLite lokal; PostgreSQL via DATABASE_URL untuk hosting.
- Docker, health check, template Render, GitHub Actions.

## Keamanan

1. Gunakan hanya aset yang Anda miliki atau yang secara eksplisit mengizinkan pengumpulan.
2. Default allowlist hanya `example.com,www.example.com`. Set `OSINT_ALLOWED_HOSTS` ke daftar hostname exact-match dipisahkan koma. Jangan membuka target arbitrer tanpa otorisasi.
3. Pemeriksaan DNS tidak sepenuhnya mencegah DNS rebinding antara validasi dan koneksi. Untuk deployment publik, gunakan egress firewall/proxy yang memblokir loopback, private, link-local, multicast, dan metadata IP cloud.
4. Redirect tidak diikuti; header Location hanya dicatat.
5. Autentikasi belum tersedia di aplikasi. Untuk hosting multi-pengguna, gunakan identity-aware proxy/SSO sebelum membuka akses.
6. Gunakan database persisten dan backup untuk hosting. Jangan mengandalkan filesystem ephemeral.
7. Query string digunakan untuk request tetapi tidak disimpan pada target riwayat/laporan. Hindari token/rahasia dalam URL.
8. SHA-256 adalah checksum body yang diterima, bukan bukti identitas atau keaslian situs.
9. Jangan commit secrets, kredensial, atau database.

## Jalankan lokal

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
streamlit run app.py
```

Default hanya mengizinkan `https://example.com` dan `https://www.example.com`.

## Konfigurasi

| Variabel | Default | Keterangan |
|---|---|---|
| `OSINT_ALLOWED_HOSTS` | `example.com,www.example.com` | Host exact-match |
| `OSINT_TIMEOUT_SECONDS` | `8` | Timeout koneksi/baca |
| `OSINT_MAX_RESPONSE_BYTES` | `1000000` | Batas body respons |
| `OSINT_DB_PATH` | `data/osint.db` | Path SQLite lokal |
| `DATABASE_URL` | kosong | URL PostgreSQL untuk hosting persisten |

## Docker

```bash
docker build -t lightweight-osint-tracker .
docker run --rm -p 8501:8501 -e OSINT_ALLOWED_HOSTS=example.com,www.example.com -v osint-data:/app/data lightweight-osint-tracker
```

Untuk hosting online, sediakan PostgreSQL terkelola, atur allowlist sempit, egress controls, dan autentikasi proxy/SSO. `render.yaml` merupakan template awal; buat database PostgreSQL dan atur environment variables di dashboard hosting.

## Pengujian

```bash
pytest -q
```

GitHub Actions menjalankan test suite pada push/PR. CI bukan pengganti peninjauan keamanan dan pengujian egress di hosting.

## Batasan diketahui

- Belum ada autentikasi bawaan, manajemen pengguna, atau multi-tenant isolation.
- Belum ada scheduler/notifikasi.
- Tidak melakukan port scanning, crawling mendalam, pencarian akun, atau atribusi identitas.
- DNS rebinding tetap perlu mitigasi di jaringan/egress layer.
- PostgreSQL perlu disediakan operator dan diuji di lingkungan hosting.


## Daily target monitoring (MVP Plus)

The target registry and scheduler are opt-in. Adding a target does **not** fetch its web page and newly added targets are disabled by default. Only enable a target if you own it or have explicit authorization to monitor it.

### In the Streamlit UI

1. Open **Pemantauan otomatis**.
2. Add one URL per line. The form is prefilled with `https://example.com` and `https://www.example.org` as examples; these are not automatically scanned.
3. Review the host allowlist errors. The app only accepts HTTPS on port 443 and exact hostnames present in `OSINT_ALLOWED_HOSTS`.
4. Tick **Aktifkan** for the target(s) you are authorized to monitor and click **Simpan status**.
5. Use the history page to inspect saved snapshots and export CSV.

### Configure a 24-hour schedule on GitHub Actions

The workflow `.github/workflows/daily-monitor.yml` runs daily at 02:17 UTC and can also be started manually from the Actions tab using `workflow_dispatch`. GitHub scheduled workflows run from the repository's default branch, so merge this branch/PR to the default branch before expecting the daily schedule to execute.

Set these repository configuration values in GitHub:

- **Repository secret** `DATABASE_URL`: connection string for a persistent PostgreSQL database reachable from GitHub-hosted runners. Use a restricted database role and TLS; never put the connection string in code or a public repository variable.
- **Repository variable** `OSINT_ALLOWED_HOSTS`: comma-separated exact hostnames, for example `example.com,www.example.com,example.org,www.example.org`. Include only authorized targets. The workflow intentionally fails if this variable or the database secret is missing.

The scheduled runner reads only enabled rows from `monitored_targets`, revalidates each target against the allowlist and public-IP DNS policy, collects one bounded HTTP response, compares it with the latest saved snapshot, and persists the new snapshot in PostgreSQL. No crawling, port scanning, arbitrary domain discovery, or identity attribution is performed.

### Hosting notes and limitations

- Streamlit Community Cloud does not guarantee a persistent local filesystem. The scheduled runner and web app must share the same PostgreSQL `DATABASE_URL` for a common target registry and history.
- For the Streamlit web app, configure `DATABASE_URL` and `OSINT_ALLOWED_HOSTS` in the hosting environment/secrets as supported by that host, then redeploy.
- GitHub Actions cron is best-effort, not an exact-time guarantee. Daily runs may be delayed and public repositories can have additional scheduling restrictions.
- DNS checks in application code alone cannot completely prevent DNS rebinding. Apply outbound network controls where possible. Do not expose the Streamlit app publicly without authentication at a trusted proxy/SSO layer.
- Adding URLs to the list is not proof of authorization. Operators are responsible for authorization and applicable policies.
