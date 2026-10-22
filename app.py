import csv
import io
import json
import logging
from urllib.parse import urlsplit, urlunsplit

import streamlit as st

from analyzer import create_report
from collector import CollectionError, TargetValidationError, collect_metadata, validate_target
from database import (
    add_target, get_snapshots, get_targets, initialize_database,
    remove_target, save_snapshot, set_target_enabled,
)
from tracker import compare_with_previous

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("osint_tracker")

st.set_page_config(page_title="Lightweight OSINT Tracker", page_icon="🔎", layout="wide")
initialize_database()

st.title("🔎 Lightweight OSINT Target Profiler")
st.caption("Pemantauan metadata website publik yang diizinkan. Bukan alat untuk melacak individu.")

with st.sidebar:
    st.header("Pengaturan kasus")
    case_name = st.text_input("Nama kasus", value="Website monitoring")
    st.info("Gunakan hanya aset yang Anda miliki atau yang secara eksplisit mengizinkan pengujian.")
    st.caption("Host yang diizinkan dikonfigurasi operator melalui OSINT_ALLOWED_HOSTS.")

target = st.text_input("URL target", value="https://example.com", help="Hanya HTTPS, port 443, dan host yang dikonfigurasi operator.")
run_col, history_col = st.columns(2)
with run_col:
    run = st.button("Analisis target", type="primary", use_container_width=True)
with history_col:
    show_history = st.button("Muat riwayat", use_container_width=True)

if run:
    try:
        with st.spinner("Mengambil metadata..."):
            result = collect_metadata(target)
            previous = get_snapshots(result["target"], limit=1)
            comparison = compare_with_previous(result, previous[0] if previous else None)
            save_snapshot(result["target"], result)
            report = create_report(result, comparison, case_name.strip() or None)
            st.session_state["latest_result"] = result
            st.session_state["latest_comparison"] = comparison
            st.session_state["latest_report"] = report
        st.success("Pengumpulan metadata selesai.")
    except TargetValidationError as exc:
        st.error(str(exc))
    except CollectionError as exc:
        st.error(str(exc))
    except Exception:
        logger.exception("Unexpected collection failure")
        st.error("Analisis gagal karena kesalahan internal. Detail dicatat pada log server.")

result = st.session_state.get("latest_result")
comparison = st.session_state.get("latest_comparison")
report = st.session_state.get("latest_report")
if result and comparison and report:
    st.subheader("Ringkasan")
    a, b, c, d = st.columns(4)
    a.metric("HTTP", result.get("status_code") or "—")
    b.metric("Waktu respons", f'{result.get("response_time_ms", 0)} ms')
    c.metric("Ukuran body", f'{result.get("response_bytes", 0):,} byte')
    d.metric("Field berubah", len(comparison.get("differences", {})))
    st.caption(f"Target: {result['target']} · Dikumpulkan (UTC): {result['collected_at']}")

    tab_profile, tab_changes, tab_report = st.tabs(["Profil", "Perubahan", "Laporan"])
    with tab_profile:
        st.json(result)
    with tab_changes:
        if comparison.get("previous_exists") and comparison.get("differences"):
            st.dataframe([
                {"Field": key, "Sebelumnya": str(value.get("before")), "Sekarang": str(value.get("after"))}
                for key, value in comparison["differences"].items()
            ], use_container_width=True, hide_index=True)
        elif comparison.get("previous_exists"):
            st.success("Tidak ada perubahan pada field yang dipantau.")
        else:
            st.info("Snapshot pertama untuk target ini; belum ada pembanding.")
    with tab_report:
        st.write(report["summary"])
        for item in report["findings"]:
            st.write(f"- **{item['type'].title()} — {item['field']}:** {item['text']}")
        st.write("**Keterbatasan**")
        for item in report["limitations"]:
            st.write(f"- {item}")

    st.download_button(
        "Unduh laporan JSON",
        data=json.dumps({"profile": result, "comparison": comparison, "report": report}, indent=2, ensure_ascii=False),
        file_name="osint_report.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.header("Pemantauan otomatis")
st.write("Tambahkan target yang memang Anda berwenang pantau. Target baru selalu nonaktif sampai Anda mengaktifkannya secara eksplisit.")
st.caption("Pemeriksaan terjadwal berjalan melalui GitHub Actions setiap 24 jam setelah workflow digabungkan ke branch default dan DATABASE_URL dikonfigurasi.")

with st.form("add_monitor_targets"):
    target_lines = st.text_area(
        "Daftar URL (satu URL per baris)",
        value="https://example.com\nhttps://www.example.org",
        help="Contoh awal disediakan untuk konfigurasi. Menambahkannya tidak langsung mengambil halaman web.",
    )
    submitted = st.form_submit_button("Tambahkan ke daftar")
if submitted:
    added = 0
    errors = []
    for line in target_lines.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        try:
            # Validates scheme, exact allowlist and DNS policy; this does not issue an HTTP request.
            normalized = validate_target(candidate)
            parsed = urlsplit(normalized)
            safe_target = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
            add_target(safe_target, 24)
            added += 1
        except (TargetValidationError, ValueError) as exc:
            errors.append(f"{candidate}: {exc}")
    if added:
        st.success(f"{added} URL diproses. Target baru tetap nonaktif sampai diaktifkan di daftar.")
    for error in errors:
        st.warning(error)

targets = get_targets()
if targets:
    st.subheader("Daftar target")
    for item in targets:
        with st.container(border=True):
            left, middle, right = st.columns([5, 2, 2])
            left.write(item["target"])
            left.caption(f"Interval tersimpan: setiap {item['interval_hours']} jam")
            desired = middle.checkbox("Aktifkan", value=bool(item["enabled"]), key=f"monitor_enabled_{item['id']}")
            if right.button("Simpan status", key=f"save_monitor_{item['id']}"):
                set_target_enabled(item["id"], desired)
                st.success("Status target diperbarui.")
                st.rerun()
            if right.button("Hapus", key=f"delete_monitor_{item['id']}"):
                remove_target(item["id"])
                st.rerun()
    enabled_count = sum(bool(item["enabled"]) for item in targets)
    st.caption(f"{enabled_count} dari {len(targets)} target aktif.")
else:
    st.info("Belum ada target. Tambahkan URL di atas untuk membuat daftar monitoring.")

if show_history:
    try:
        normalized = validate_target(target)
        parsed = urlsplit(normalized)
        history_target = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        snapshots = get_snapshots(history_target, limit=100)
        if not snapshots:
            st.info("Belum ada riwayat untuk target ini.")
        else:
            st.subheader("Riwayat snapshot")
            rows = [{
                "ID": row["id"],
                "Waktu UTC": row["collected_at"],
                "Target": row["target"],
                "Judul": row["content"].get("title"),
                "HTTP": row["content"].get("status_code"),
                "SHA-256": row["content"].get("body_sha256"),
            } for row in snapshots]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            chart_data = [{"Waktu": row["collected_at"], "HTTP status": row["content"].get("status_code")} for row in snapshots]
            st.line_chart(chart_data, x="Waktu", y="HTTP status")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            st.download_button("Ekspor riwayat CSV", output.getvalue(), "osint_history.csv", "text/csv")
    except TargetValidationError as exc:
        st.error(str(exc))
    except Exception:
        logger.exception("Unable to load history")
        st.error("Riwayat tidak dapat dimuat. Periksa log server.")

st.divider()
st.caption("Hosting multi-pengguna perlu autentikasi proxy/SSO dan PostgreSQL persisten. Scheduler memproses hanya target yang diaktifkan.")
