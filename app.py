import json
import streamlit as st
from collector import collect_metadata, TargetValidationError
from database import initialize_database, save_snapshot, get_snapshots
from tracker import compare_with_previous
from analyzer import create_report

st.set_page_config(page_title="Lightweight OSINT Tracker", page_icon="🔎", layout="wide")
initialize_database()

st.title("🔎 Lightweight OSINT Target Profiler")
st.caption("Analisis metadata website publik yang diizinkan. Bukan alat untuk melacak individu.")

with st.sidebar:
    st.header("Tentang")
    st.write("Mengumpulkan metadata HTML dasar, menyimpan snapshot, dan membandingkan perubahan.")
    st.warning("Gunakan hanya pada aset yang Anda miliki atau diizinkan untuk dianalisis.")
    st.write("AI belum diaktifkan pada versi dasar ini.")

target = st.text_input("URL target", value="https://example.com", help="Versi awal membatasi target ke example.com demi keamanan.")
col1, col2 = st.columns([1, 1])
with col1:
    run = st.button("Analisis target", type="primary", use_container_width=True)
with col2:
    show_history = st.button("Muat riwayat", use_container_width=True)

if run:
    try:
        with st.spinner("Mengambil metadata..."):
            result = collect_metadata(target)
            previous = get_snapshots(target, limit=1)
            comparison = compare_with_previous(result, previous[0] if previous else None)
            save_snapshot(target, result)
            report = create_report(result, comparison)

        st.success("Pengumpulan metadata berhasil.")
        a, b, c = st.columns(3)
        a.metric("HTTP status", result["status_code"])
        b.metric("Judul tersedia", "Ya" if result.get("title") else "Tidak")
        c.metric("Field berubah", len(comparison["differences"]))

        st.subheader("Profil target")
        st.json(result)
        st.subheader("Perbandingan dengan snapshot sebelumnya")
        if comparison["previous_exists"]:
            if comparison["differences"]:
                st.json(comparison["differences"])
            else:
                st.info("Tidak ada perubahan pada field yang dipantau.")
        else:
            st.info("Ini adalah snapshot pertama untuk target ini.")

        st.subheader("Laporan")
        st.write(report["summary"])
        st.write("**Temuan:**")
        for item in report["findings"]:
            st.write(f"- {item}")
        st.write("**Keterbatasan:**")
        for item in report["limitations"]:
            st.write(f"- {item}")

        st.download_button(
            "Unduh laporan JSON",
            data=json.dumps({"profile": result, "comparison": comparison, "report": report}, indent=2, ensure_ascii=False),
            file_name="osint_report.json",
            mime="application/json",
        )
    except TargetValidationError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Analisis gagal. Periksa URL, koneksi, dan log server. Detail internal tidak ditampilkan.")

if show_history:
    snapshots = get_snapshots(target, limit=50)
    if snapshots:
        st.subheader("Riwayat snapshot")
        st.dataframe([
            {
                "Waktu UTC": row["collected_at"],
                "Target": row["target"],
                "Judul": row["content"].get("title"),
                "HTTP": row["content"].get("status_code"),
            } for row in snapshots
        ], use_container_width=True)
    else:
        st.info("Belum ada riwayat untuk target ini.")

st.divider()
st.caption("Catatan: snapshot disimpan pada database lokal. Untuk deployment publik, gunakan database persisten dan autentikasi.")
