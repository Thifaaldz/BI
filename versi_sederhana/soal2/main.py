"""
Studi Kasus 2: Konsolidasi Multi-Sumber Data Penjualan (versi sederhana)
-----------------------------------------------------------------------
Langkah:
  1. Muat data online (CSV) & offline (database SQL)
  2. Samakan nama kolom kedua sumber
  3. CONCAT: tumpuk semua transaksi online + offline
  4. MERGE : gabungkan rekap online vs offline per ID Produk & Tanggal
  5. Simpan hasil ke Excel & CSV

Jalankan:
  python versi_sederhana/soal2/main.py
"""

import os
import sqlite3

import pandas as pd

# ---------------------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------------------
FILE_ONLINE = "penjualan_online.csv"
FILE_OFFLINE = "penjualan_offline.db"
TABEL_OFFLINE = "penjualan_toko"
KUNCI = ["id_produk", "tanggal"]  # kunci penggabungan
OUTPUT_EXCEL = "konsolidasi_sederhana.xlsx"
OUTPUT_CSV = "konsolidasi_sederhana.csv"


# ---------------------------------------------------------------------------
# 1. MUAT DATA
# ---------------------------------------------------------------------------
def muat_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    online = pd.read_csv(FILE_ONLINE)
    with sqlite3.connect(FILE_OFFLINE) as conn:
        offline = pd.read_sql_query(f"SELECT * FROM {TABEL_OFFLINE}", conn)
    print(f"[INFO] Online : {len(online)} baris ({FILE_ONLINE})")
    print(f"[INFO] Offline: {len(offline)} baris ({FILE_OFFLINE})")
    return online, offline


# ---------------------------------------------------------------------------
# 2. SAMAKAN NAMA KOLOM
# ---------------------------------------------------------------------------
def samakan_kolom(online: pd.DataFrame, offline: pd.DataFrame):
    online = online.rename(columns={
        "order_id": "id_transaksi", "product_id": "id_produk",
        "order_date": "tanggal", "qty": "jumlah", "price": "harga_satuan",
    })
    offline = offline.rename(columns={
        "no_struk": "id_transaksi", "kode_produk": "id_produk",
        "tgl_transaksi": "tanggal",
    })
    online["kanal"] = "Online"
    offline["kanal"] = "Offline"

    kolom = ["id_transaksi", "kanal", "id_produk", "tanggal", "jumlah", "harga_satuan"]
    online, offline = online[kolom], offline[kolom]
    for df in (online, offline):
        df["total"] = df["jumlah"] * df["harga_satuan"]
    return online, offline


# ---------------------------------------------------------------------------
# 3. CONCAT
# ---------------------------------------------------------------------------
def gabung_concat(online: pd.DataFrame, offline: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([online, offline], ignore_index=True).sort_values(KUNCI)


# ---------------------------------------------------------------------------
# 4. MERGE
# ---------------------------------------------------------------------------
def gabung_merge(online: pd.DataFrame, offline: pd.DataFrame) -> pd.DataFrame:
    rekap_online = online.groupby(KUNCI, as_index=False)[["jumlah", "total"]].sum()
    rekap_offline = offline.groupby(KUNCI, as_index=False)[["jumlah", "total"]].sum()

    # how="outer" agar produk/tanggal yang hanya ada di satu kanal tetap ikut
    rekap = pd.merge(rekap_online, rekap_offline, on=KUNCI, how="outer",
                     suffixes=("_online", "_offline"))
    angka = rekap.columns[2:]
    rekap[angka] = rekap[angka].fillna(0).astype(int)
    rekap["total_omzet"] = rekap["total_online"] + rekap["total_offline"]
    return rekap.sort_values(KUNCI)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # baca/simpan file di folder ini
    online, offline = samakan_kolom(*muat_data())

    detail = gabung_concat(online, offline)
    rekap = gabung_merge(online, offline)

    print("\n=== HASIL CONCAT (5 baris pertama) ===")
    print(detail.head().to_string(index=False))
    print(f"Total baris: {len(detail)}")

    print("\n=== HASIL MERGE per ID Produk & Tanggal (5 baris pertama) ===")
    print(rekap.head().to_string(index=False))
    print(f"Total baris: {len(rekap)}")
    print(f"\nTotal omzet gabungan: Rp {detail['total'].sum():,.0f}")

    # 5. SIMPAN
    rekap.to_csv(OUTPUT_CSV, index=False)
    with pd.ExcelWriter(OUTPUT_EXCEL) as writer:
        detail.to_excel(writer, sheet_name="Concat", index=False)
        rekap.to_excel(writer, sheet_name="Merge", index=False)
    print(f"\n[OK] Disimpan: {OUTPUT_EXCEL}, {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
