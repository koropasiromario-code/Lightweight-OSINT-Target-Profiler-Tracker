# Lightweight OSINT Target Profiler Tracker

Aplikasi Streamlit untuk mengumpulkan metadata HTML dasar dari website publik yang diizinkan, menyimpan snapshot SQLite, membandingkan perubahan, dan mengekspor laporan JSON.

## Fitur
- Input URL HTTPS (versi awal dibatasi ke `example.com`)
- Pengambilan title, meta description, status HTTP, content type, dan header Server
- Riwayat snapshot SQLite
- Perbandingan perubahan metadata
- Ekspor laporan JSON
- AI belum diaktifkan; `analyzer.py` menghasilkan laporan berbasis aturan

## Jalankan lokal
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy online
1. Unggah file proyek ke repositori GitHub.
2. Buat aplikasi baru di Streamlit Community Cloud.
3. Pilih repo, branch, dan `app.py`.
4. Deploy.

## Penting untuk produksi
- Versi demo mengizinkan hanya `example.com` dan `www.example.com`.
- Jangan menghapus allowlist tanpa menggantinya dengan kontrol otorisasi target, validasi DNS/IP yang kuat, dan egress firewall/proxy.
- Redirect dinonaktifkan.
- SQLite lokal tidak menjamin persistensi pada hosting dengan filesystem sementara. Gunakan PostgreSQL terkelola untuk penggunaan produksi.
- Tambahkan autentikasi, rate limiting, audit logging, kebijakan retensi data, dan pemantauan dependensi.
- Jangan commit API keys, data sensitif, atau database ke repositori publik.
