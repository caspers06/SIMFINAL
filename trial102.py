# streamlit_app.py
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import io
import re

st.set_page_config(page_title="Siklus Akuntansi Dagang", layout="wide")

DATA_FILE = "data_user.json"
AKUN_LIST = [
    "Kas", "Persediaan", "Perlengkapan", "Utang Bank", "Utang Gaji",
    "Modal", "Pendapatan", "Beban Pemeliharaan", "Beban Operasional",
    "Beban Listrik", "Beban Air", "Beban Gaji", "Beban Pengiriman"
]

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def login(username, password):
    data = load_data()
    return username in data and data[username]['password'] == password

def register(username, password):
    data = load_data()
    if username in data:
        return False
    data[username] = {
        "password": password,
        "jurnal": [],
        "jurnal_penyesuaian": []
    }
    save_data(data)
    return True

def buku_besar(df):
    ledger = {}
    if df.empty:
        return ledger
    for akun in df['Akun'].unique():
        df_akun = df[df['Akun'] == akun].copy()
        df_akun.sort_values(by="Tanggal", inplace=True)
        df_akun['Mutasi'] = df_akun['Debit'] - df_akun['Kredit']
        df_akun['Saldo Akhir'] = df_akun['Mutasi'].cumsum()
        ledger[akun] = df_akun
    return ledger

def neraca_saldo(ledger_dict):
    ns = []
    for akun, df in ledger_dict.items():
        akhir = df['Saldo Akhir'].iloc[-1] if not df.empty else 0
        ns.append({"Akun": akun, "Debit": max(akhir, 0), "Kredit": max(-akhir, 0)})
    return pd.DataFrame(ns)

def main_app():
    st.title("📈 Aplikasi Siklus Akuntansi Perusahaan Dagang")

    data = load_data()
    user_data = data[st.session_state.user]
    jurnal = pd.DataFrame(user_data['jurnal']) if user_data['jurnal'] else pd.DataFrame(columns=["Tanggal","Akun","Debit","Kredit","Keterangan"])
    jurnal_penyesuaian = pd.DataFrame(user_data['jurnal_penyesuaian']) if user_data['jurnal_penyesuaian'] else pd.DataFrame(columns=["Tanggal","Akun","Debit","Kredit","Keterangan"])

    st.sidebar.header("📝 Input Transaksi")
    tgl = st.sidebar.date_input("Tanggal", datetime.today())
    akun_debit = st.sidebar.selectbox("Akun Debit", AKUN_LIST)
    jumlah_debit = st.sidebar.number_input("Jumlah Debit", min_value=0.0, format="%.2f")
    akun_kredit = st.sidebar.selectbox("Akun Kredit", AKUN_LIST)
    jumlah_kredit = st.sidebar.number_input("Jumlah Kredit", min_value=0.0, format="%.2f")
    keterangan = st.sidebar.text_input("Keterangan")

    if st.sidebar.button("Tambah Transaksi"):
        if jumlah_debit != jumlah_kredit:
            st.sidebar.error("Jumlah debit dan kredit harus sama.")
        else:
            new_entries = pd.DataFrame([
                {"Tanggal": str(tgl), "Akun": akun_debit, "Debit": jumlah_debit, "Kredit": 0.0, "Keterangan": keterangan},
                {"Tanggal": str(tgl), "Akun": akun_kredit, "Debit": 0.0, "Kredit": jumlah_kredit, "Keterangan": keterangan}
            ])
            jurnal = pd.concat([jurnal, new_entries], ignore_index=True)
            data[st.session_state.user]['jurnal'] = jurnal.to_dict(orient='records')
            save_data(data)
            st.sidebar.success("Transaksi ditambahkan.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ Hapus Transaksi")
    if not jurnal.empty:
        index_to_delete = st.sidebar.selectbox("Pilih Baris Transaksi", jurnal.index)
        if st.sidebar.button("Hapus Baris"):
            jurnal = jurnal.drop(index=index_to_delete).reset_index(drop=True)
            data[st.session_state.user]['jurnal'] = jurnal.to_dict(orient='records')
            save_data(data)
            st.sidebar.success("Baris dihapus.")

    st.subheader("📒 Jurnal Umum")
    st.dataframe(jurnal)

    ledger = buku_besar(jurnal)
    st.subheader("📚 Buku Besar")
    for akun, df in ledger.items():
        with st.expander(f"Akun: {akun}"):
            st.dataframe(df)

    ns_awal = neraca_saldo(ledger)
    st.subheader("📊 Neraca Saldo Awal")
    st.dataframe(ns_awal)

    st.subheader("🔧 Jurnal Penyesuaian")
    with st.expander("Tambah Jurnal Penyesuaian"):
        tgl_adj = st.date_input("Tanggal Penyesuaian", datetime.today(), key='tgl_adj')
        akun_debit_adj = st.selectbox("Akun Debit", AKUN_LIST, key='akun_debit_adj')
        akun_kredit_adj = st.selectbox("Akun Kredit", AKUN_LIST, key='akun_kredit_adj')
        jumlah_adj = st.number_input("Jumlah Penyesuaian", min_value=0.0, format="%.2f", key='jumlah_adj')
        ket_adj = st.text_input("Keterangan Penyesuaian", key='ket_adj')
        if st.button("Tambah Penyesuaian", key='btn_penyesuaian'):
            if jumlah_adj > 0:
                adj_entries = pd.DataFrame([
                    {"Tanggal": str(tgl_adj), "Akun": akun_debit_adj, "Debit": jumlah_adj, "Kredit": 0.0, "Keterangan": ket_adj},
                    {"Tanggal": str(tgl_adj), "Akun": akun_kredit_adj, "Debit": 0.0, "Kredit": jumlah_adj, "Keterangan": ket_adj}
                ])
                jurnal_penyesuaian = pd.concat([jurnal_penyesuaian, adj_entries], ignore_index=True)
                data[st.session_state.user]['jurnal_penyesuaian'] = jurnal_penyesuaian.to_dict(orient='records')
                save_data(data)
                st.success("Penyesuaian ditambahkan.")

    st.dataframe(jurnal_penyesuaian)

    all_journal = pd.concat([jurnal, jurnal_penyesuaian], ignore_index=True)
    ledger_adj = buku_besar(all_journal)
    ns_adj = neraca_saldo(ledger_adj)

    st.subheader("📈 Neraca Saldo Setelah Penyesuaian")
    st.dataframe(ns_adj)

    pendapatan = ns_adj[ns_adj['Akun'].str.contains("Pendapatan", case=False)]['Kredit'].sum()
    beban = ns_adj[ns_adj['Akun'].str.contains("Beban", case=False)]['Debit'].sum()
    laba_bersih = pendapatan - beban

    st.subheader("📉 Laporan Laba Rugi")
    st.write(f"**Pendapatan:** Rp {pendapatan:,.2f}")
    st.write(f"**Beban:** Rp {beban:,.2f}")
    st.write(f"### ➕ Laba Bersih: Rp {laba_bersih:,.2f}")

    st.subheader("🔄 Laporan Perubahan Modal")
    modal_awal = st.number_input("Modal Awal", value=0.0)
    prive = st.number_input("Prive", value=0.0)
    modal_akhir = modal_awal + laba_bersih - prive
    st.write(f"### 🧮 Modal Akhir: Rp {modal_akhir:,.2f}")

    st.subheader("🧾 Neraca")
    aktiva = ns_adj[ns_adj['Akun'].str.contains("Kas|Persediaan|Perlengkapan", case=False)]['Debit'].sum()
    kewajiban = ns_adj[ns_adj['Akun'].str.contains("Utang", case=False)]['Kredit'].sum()
    st.write(f"**Total Aktiva:** Rp {aktiva:,.2f}")
    st.write(f"**Total Kewajiban + Modal:** Rp {kewajiban + modal_akhir:,.2f}")

    st.subheader("🛑 Jurnal Penutup")
    def jurnal_penutup():
        penutup = []
        if pendapatan > 0:
            penutup += [
                {"Akun": "Pendapatan", "Debit": pendapatan, "Kredit": 0.0, "Keterangan": "Tutup pendapatan"},
                {"Akun": "Ikhtisar Laba Rugi", "Debit": 0.0, "Kredit": pendapatan, "Keterangan": "Tutup pendapatan"}
            ]
        if beban > 0:
            penutup += [
                {"Akun": "Ikhtisar Laba Rugi", "Debit": beban, "Kredit": 0.0, "Keterangan": "Tutup beban"},
                {"Akun": "Beban", "Debit": 0.0, "Kredit": beban, "Keterangan": "Tutup beban"}
            ]
        if laba_bersih != 0:
            penutup += [
                {"Akun": "Ikhtisar Laba Rugi", "Debit": laba_bersih, "Kredit": 0.0, "Keterangan": "Tutup laba"},
                {"Akun": "Modal", "Debit": 0.0, "Kredit": laba_bersih, "Keterangan": "Tutup laba ke modal"}
            ]
        return pd.DataFrame(penutup)

    jp = jurnal_penutup()
    st.dataframe(jp)

    st.subheader("📌 Neraca Saldo Setelah Penutupan")
    final_journal = pd.concat([all_journal, jp], ignore_index=True)
    ns_final = neraca_saldo(buku_besar(final_journal))
    st.dataframe(ns_final)

    st.subheader("📤 Ekspor ke Excel")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        jurnal.to_excel(writer, sheet_name="Jurnal Umum", index=False)
        jurnal_penyesuaian.to_excel(writer, sheet_name="Jurnal Penyesuaian", index=False)
        ns_awal.to_excel(writer, sheet_name="Neraca Awal", index=False)
        ns_adj.to_excel(writer, sheet_name="Neraca Disesuaikan", index=False)
        jp.to_excel(writer, sheet_name="Jurnal Penutup", index=False)
        ns_final.to_excel(writer, sheet_name="Neraca Akhir", index=False)

        pd.DataFrame({
            "Keterangan": ["Pendapatan", "Beban", "Laba Bersih"],
            "Jumlah": [pendapatan, beban, laba_bersih]
        }).to_excel(writer, sheet_name="Laba Rugi", index=False)

        pd.DataFrame({
            "Keterangan": ["Modal Awal", "Laba Bersih", "Prive", "Modal Akhir"],
            "Jumlah": [modal_awal, laba_bersih, prive, modal_akhir]
        }).to_excel(writer, sheet_name="Perubahan Modal", index=False)

        pd.DataFrame({
            "Keterangan": ["Aktiva", "Kewajiban + Modal"],
            "Jumlah": [aktiva, kewajiban + modal_akhir]
        }).to_excel(writer, sheet_name="Neraca", index=False)

        used_sheets = set()
        for akun, df in ledger_adj.items():
            safe_sheet = f"Buku - {re.sub(r'[^A-Za-z0-9]', '_', akun)[:25]}"
            suffix = 1
            while safe_sheet.lower() in used_sheets:
                safe_sheet = f"{safe_sheet[:22]}_{suffix}"
                suffix += 1
            used_sheets.add(safe_sheet.lower())
            df.to_excel(writer, sheet_name=safe_sheet, index=False)

        output.seek(0)

    st.download_button(
        label="⬇️ Unduh Excel",
        data=output,
        file_name="laporan_keuangan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.session_state.user = username
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("Username atau password salah.")

    if st.button("Buat Akun Baru"):
        st.session_state.show_register = True

def register_page():
    st.title("🆕 Registrasi")
    username = st.text_input("Username Baru")
    password = st.text_input("Password Baru", type="password")
    if st.button("Daftar"):
        if register(username, password):
            st.success("Berhasil daftar, silakan login.")
            st.session_state.show_register = False
        else:
            st.error("Username sudah digunakan.")
    if st.button("Kembali ke Login"):
        st.session_state.show_register = False

if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_register' not in st.session_state:
    st.session_state.show_register = False

if st.session_state.user:
    main_app()
else:
    if st.session_state.show_register:
        register_page()
    else:
        login_page()
