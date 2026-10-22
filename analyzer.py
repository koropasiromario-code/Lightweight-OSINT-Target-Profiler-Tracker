"""Deterministic report generation. Findings are observations, not identity attribution."""
from datetime import datetime, timezone


def create_report(profile: dict, comparison: dict, case_name: str | None = None) -> dict:
    findings = [
        {"type": "observation", "field": "status_code", "value": profile.get("status_code"),
         "text": f"HTTP status yang diamati: {profile.get('status_code')}."},
        {"type": "observation", "field": "title", "value": profile.get("title"),
         "text": "Judul halaman tersedia." if profile.get("title") else "Judul halaman tidak ditemukan."},
        {"type": "observation", "field": "description", "value": profile.get("description"),
         "text": "Deskripsi meta tersedia." if profile.get("description") else "Deskripsi meta tidak ditemukan."},
        {"type": "observation", "field": "body_sha256", "value": profile.get("body_sha256"),
         "text": "SHA-256 dihitung atas body respons yang dikumpulkan."},
    ]
    if comparison.get("previous_exists"):
        findings.append({
            "type": "change",
            "field": "differences",
            "value": comparison.get("differences", {}),
            "text": "Perubahan pada field terpantau terdeteksi." if comparison.get("changed")
                    else "Tidak ada perubahan pada field terpantau.",
        })
    else:
        findings.append({"type": "context", "field": "history", "value": None,
                         "text": "Belum ada snapshot sebelumnya untuk dibandingkan."})

    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_name": case_name or "Unspecified case",
        "target": profile.get("target"),
        "collected_at": profile.get("collected_at"),
        "collector_version": profile.get("collector_version"),
        "summary": "Laporan metadata website berdasarkan snapshot yang diamati; bukan verifikasi identitas pemilik situs.",
        "findings": findings,
        "comparison": comparison,
        "limitations": [
            "Metadata dan header dapat tidak lengkap, diubah, atau disediakan oleh perantara.",
            "SHA-256 adalah checksum atas body respons yang diterima, bukan bukti identitas atau keaslian situs.",
            "Redirect tidak diikuti; jika ada, Location hanya dicatat sebagai observasi.",
            "Snapshot menggambarkan satu waktu pengumpulan dan tidak memverifikasi seluruh situs.",
            "Analisis dibuat menggunakan aturan deterministik; tidak ada AI atau atribusi identitas.",
        ],
    }
