def create_report(profile: dict, comparison: dict) -> dict:
    """Deterministic report scaffold. This function does not call an AI model."""
    findings = [
        f"HTTP status yang diamati: {profile.get('status_code')}.",
        "Judul halaman tersedia." if profile.get("title") else "Judul halaman tidak ditemukan.",
        "Deskripsi meta tersedia." if profile.get("description") else "Deskripsi meta tidak ditemukan.",
    ]

    if comparison.get("previous_exists"):
        findings.append(
            "Perubahan metadata terdeteksi."
            if comparison.get("changed")
            else "Tidak ada perubahan pada field terpantau."
        )
    else:
        findings.append("Belum ada snapshot sebelumnya untuk dibandingkan.")

    return {
        "summary": "Laporan metadata website berdasarkan satu pengambilan. Ini bukan verifikasi identitas pemilik situs.",
        "findings": findings,
        "limitations": [
            "Metadata HTML tidak mewakili seluruh konten atau keamanan website.",
            "Header Server dapat tidak tersedia atau tidak akurat.",
            "AI belum diaktifkan; laporan ini dibuat menggunakan aturan deterministik.",
            "Waktu dan hasil hanya menggambarkan snapshot yang dikumpulkan.",
        ],
    }
