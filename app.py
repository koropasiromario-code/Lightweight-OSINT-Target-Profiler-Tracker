import csv
import io
import json
import logging
from urllib.parse import urlsplit, urlunsplit

import streamlit as st

from analyzer import create_report
from collector import CollectionError, TargetValidationError, collect_metadata, validate_target
from database import get_snapshots, initialize_database, save_snapshot
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
st.caption("Untuk hosting multi-pengguna, aktifkan autentikasi di lapisan hosting/proxy dan gunakan PostgreSQL persisten. Jangan mengekspos aplikasi tanpa kontrol akses.")
