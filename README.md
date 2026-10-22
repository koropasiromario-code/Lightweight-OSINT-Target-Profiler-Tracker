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
