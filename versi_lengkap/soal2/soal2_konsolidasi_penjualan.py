"""
Studi Kasus 2: Konsolidasi Multi-Sumber Data Penjualan
------------------------------------------------------
Kasus : Data penjualan ONLINE (file CSV) dan penjualan toko OFFLINE
        (database SQL) perlu disatukan.
Tugas : Proses concat & merge dengan Pandas berdasarkan ID Produk dan
        Tanggal, lalu simpan ke format baru (Excel/CSV).

Langkah:
  1. Muat data online (CSV) & offline (SQLite) -> buat data contoh jika tidak ada
  2. Samakan struktur kolom kedua sumber
  3. CONCAT : tumpuk semua transaksi online + offline (detail)
  4. MERGE  : gabungkan rekap online vs offline per (id_produk, tanggal)
  5. Simpan hasil ke Excel (multi-sheet) & CSV

Jalankan:
  python soal2_konsolidasi_penjualan.py                          # data contoh
  python soal2_konsolidasi_penjualan.py online.csv offline.db    # file sendiri
"""

import sqlite3
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------------------
FILE_ONLINE = "penjualan_online.csv"
FILE_OFFLINE = "penjualan_offline.db"
TABEL_OFFLINE = "penjualan_toko"
KUNCI = ["id_produk", "tanggal"]  # kunci penggabungan
OUTPUT_EXCEL = "konsolidasi_penjualan.xlsx"
OUTPUT_CSV_DETAIL = "konsolidasi_penjualan_detail.csv"
OUTPUT_CSV_REKAP = "konsolidasi_penjualan_rekap.csv"

PRODUK = {
    "P001": "Kopi Bubuk 200g",
    "P002": "Teh Celup 25s",
    "P003": "Gula Pasir 1kg",
    "P004": "Minyak Goreng 2L",
    "P005": "Beras Premium 5kg",
}


# ---------------------------------------------------------------------------
# 1. MUAT DATA (atau buat data contoh)
# ---------------------------------------------------------------------------
def buat_data_contoh(path_csv: str, path_db: str, seed: int = 42) -> None:
    """Membuat file CSV (online) dan database SQLite (offline) contoh.

    Nama kolom kedua sumber sengaja dibuat berbeda, seperti kondisi nyata.
    """
    rng = np.random.default_rng(seed)
    tanggal = pd.date_range("2026-09-01", "2026-09-14", freq="D")
    harga = {"P001": 35_000, "P002": 12_000, "P003": 17_500,
             "P004": 38_000, "P005": 82_000}

    # --- Online (CSV) ---
    n = 120
    id_on = rng.choice(list(PRODUK), n)
    online = pd.DataFrame({
        "order_id": [f"ON-{i:04d}" for i in range(1, n + 1)],
        "product_id": id_on,
        "order_date": rng.choice(tanggal, n).astype("datetime64[ns]"),
        "qty": rng.integers(1, 6, n),
        "price": [harga[p] for p in id_on],
        "platform": rng.choice(["Tokopedia", "Shopee", "Website"], n),
    })
    online["order_date"] = online["order_date"].dt.strftime("%Y-%m-%d")
    online.to_csv(path_csv, index=False)

    # --- Offline (SQL) ---
    n = 100
    id_off = rng.choice(list(PRODUK), n)
    offline = pd.DataFrame({
        "no_struk": [f"OFF-{i:04d}" for i in range(1, n + 1)],
        "kode_produk": id_off,
        "tgl_transaksi": rng.choice(tanggal, n).astype("datetime64[ns]"),
        "jumlah": rng.integers(1, 8, n),
        "harga_satuan": [harga[p] for p in id_off],
        "cabang": rng.choice(["Jakarta", "Bekasi", "Tangerang"], n),
    })
    offline["tgl_transaksi"] = offline["tgl_transaksi"].dt.strftime("%Y-%m-%d")
    with sqlite3.connect(path_db) as conn:
        offline.to_sql(TABEL_OFFLINE, conn, if_exists="replace", index=False)

    print(f"[INFO] Data contoh dibuat: {path_csv}, {path_db}")


def muat_online(path: str) -> pd.DataFrame:
    print(f"[INFO] Memuat data online (CSV): {path}")
    return pd.read_csv(path)


def muat_offline(path: str) -> pd.DataFrame:
    print(f"[INFO] Memuat data offline (SQL): {path} -> tabel {TABEL_OFFLINE}")
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {TABEL_OFFLINE}", conn)


# ---------------------------------------------------------------------------
# 2. SAMAKAN STRUKTUR KOLOM
# ---------------------------------------------------------------------------
def standarisasi_online(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "order_id": "id_transaksi",
        "product_id": "id_produk",
        "order_date": "tanggal",
        "qty": "jumlah",
        "price": "harga_satuan",
        "platform": "lokasi",
    })
    df["kanal"] = "Online"
    return df


def standarisasi_offline(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "no_struk": "id_transaksi",
        "kode_produk": "id_produk",
        "tgl_transaksi": "tanggal",
        "cabang": "lokasi",
    })
    df["kanal"] = "Offline"
    return df


def rapikan_tipe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["id_produk"] = df["id_produk"].astype(str).str.strip().str.upper()
    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.normalize()
    df["jumlah"] = pd.to_numeric(df["jumlah"])
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"])
    df["total"] = df["jumlah"] * df["harga_satuan"]
    return df


# ---------------------------------------------------------------------------
# 3. CONCAT -> data detail gabungan
# ---------------------------------------------------------------------------
def gabung_concat(online: pd.DataFrame, offline: pd.DataFrame) -> pd.DataFrame:
    kolom = ["id_transaksi", "kanal", "lokasi", "id_produk", "tanggal",
             "jumlah", "harga_satuan", "total"]
    detail = pd.concat([online[kolom], offline[kolom]], ignore_index=True)
    detail.insert(4, "nama_produk", detail["id_produk"].map(PRODUK))
    return detail.sort_values(KUNCI + ["kanal"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. MERGE -> rekap online vs offline per (id_produk, tanggal)
# ---------------------------------------------------------------------------
def rekap_per_kunci(df: pd.DataFrame, akhiran: str) -> pd.DataFrame:
    return (df.groupby(KUNCI, as_index=False)
              .agg(jumlah=("jumlah", "sum"), total=("total", "sum"))
              .rename(columns={"jumlah": f"qty_{akhiran}",
                               "total": f"omzet_{akhiran}"}))


def gabung_merge(online: pd.DataFrame, offline: pd.DataFrame) -> pd.DataFrame:
    rekap = pd.merge(
        rekap_per_kunci(online, "online"),
        rekap_per_kunci(offline, "offline"),
        on=KUNCI,
        how="outer",       # pertahankan produk/tanggal yang hanya ada di satu kanal
        indicator="sumber",
    )
    rekap["sumber"] = rekap["sumber"].map({
        "left_only": "Hanya Online", "right_only": "Hanya Offline", "both": "Keduanya",
    })
    kolom_angka = ["qty_online", "omzet_online", "qty_offline", "omzet_offline"]
    rekap[kolom_angka] = rekap[kolom_angka].fillna(0).astype("int64")
    rekap["qty_total"] = rekap["qty_online"] + rekap["qty_offline"]
    rekap["omzet_total"] = rekap["omzet_online"] + rekap["omzet_offline"]
    rekap.insert(1, "nama_produk", rekap["id_produk"].map(PRODUK))
    return rekap.sort_values(KUNCI).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 5. VALIDASI & SIMPAN
# ---------------------------------------------------------------------------
def validasi(online, offline, detail, rekap) -> None:
    assert len(detail) == len(online) + len(offline), "Jumlah baris concat tidak cocok!"
    assert not rekap.duplicated(KUNCI).any(), "Kunci (id_produk, tanggal) duplikat!"
    assert rekap["omzet_total"].sum() == detail["total"].sum(), "Omzet merge != concat!"


def ringkasan_produk(detail: pd.DataFrame) -> pd.DataFrame:
    return (detail.pivot_table(index=["id_produk", "nama_produk"], columns="kanal",
                               values="total", aggfunc="sum", fill_value=0)
                  .assign(Total=lambda x: x.sum(axis=1))
                  .reset_index())


def simpan(detail, rekap, per_produk) -> None:
    for df in (detail, rekap):
        df["tanggal"] = df["tanggal"].dt.strftime("%Y-%m-%d")

    detail.to_csv(OUTPUT_CSV_DETAIL, index=False)
    rekap.to_csv(OUTPUT_CSV_REKAP, index=False)
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        detail.to_excel(writer, sheet_name="Detail (concat)", index=False)
        rekap.to_excel(writer, sheet_name="Rekap (merge)", index=False)
        per_produk.to_excel(writer, sheet_name="Ringkasan Produk", index=False)
    print(f"\n[OK] Disimpan: {OUTPUT_EXCEL}, {OUTPUT_CSV_DETAIL}, {OUTPUT_CSV_REKAP}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    os.chdir(Path(__file__).resolve().parent)  # baca/simpan file di folder ini
    path_csv = sys.argv[1] if len(sys.argv) > 1 else FILE_ONLINE
    path_db = sys.argv[2] if len(sys.argv) > 2 else FILE_OFFLINE
    if not (Path(path_csv).exists() and Path(path_db).exists()):
        print("[INFO] File sumber tidak ditemukan -> membuat data contoh.")
        buat_data_contoh(path_csv, path_db)

    online = rapikan_tipe(standarisasi_online(muat_online(path_csv)))
    offline = rapikan_tipe(standarisasi_offline(muat_offline(path_db)))
    print(f"\nTransaksi online : {len(online):,} baris")
    print(f"Transaksi offline: {len(offline):,} baris")

    detail = gabung_concat(online, offline)
    rekap = gabung_merge(online, offline)
    validasi(online, offline, detail, rekap)
    per_produk = ringkasan_produk(detail)

    print("\n=== HASIL CONCAT (5 baris pertama) ===")
    print(detail.head().to_string(index=False))
    print(f"Total baris detail: {len(detail):,}")

    print("\n=== HASIL MERGE per (id_produk, tanggal) (5 baris pertama) ===")
    print(rekap.head().to_string(index=False))
    print(f"Total baris rekap : {len(rekap):,}")
    print(f"\nSebaran sumber data:\n{rekap['sumber'].value_counts().to_string()}")

    print("\n=== RINGKASAN OMZET PER PRODUK (Rp) ===")
    print(per_produk.to_string(index=False))
    print(f"\nTotal omzet gabungan: Rp {detail['total'].sum():,.0f}")

    simpan(detail, rekap, per_produk)


if __name__ == "__main__":
    main()
