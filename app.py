
"""
Studi Kasus: Pembersihan Data Transaksi Ritel
---------------------------------------------
Langkah:
  1. Muat data (atau buat data contoh jika file tidak ada)
  2. Deteksi missing values & duplikat
  3. Hapus baris duplikat
  4. Imputasi: median (numerik), modus (kategorikal)
  5. Validasi & laporan ringkasan data bersih

Jalankan:
  python pembersihan_data_ritel.py                  # memakai data contoh
  python pembersihan_data_ritel.py transaksi.csv    # memakai file sendiri
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# KONFIGURASI (sesuaikan dengan nama kolom dataset Anda)
# ---------------------------------------------------------------------------
KOLOM_NUMERIK = ["harga", "jumlah"]                # diimputasi dengan median
KOLOM_KATEGORIKAL = ["kategori", "metode_bayar"]  # diimputasi dengan modus
KOLOM_GROUP = "kategori"  # median per kategori produk (None = median global)
OUTPUT_CSV = "transaksi_bersih.csv"
OUTPUT_LAPORAN = "laporan_ringkasan.txt"


# ---------------------------------------------------------------------------
# 1. MUAT DATA
# ---------------------------------------------------------------------------
def buat_data_contoh(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Membuat dataset ritel mentah berisi missing value & duplikat."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "id_transaksi": np.arange(1, n + 1),
        "tanggal": pd.date_range("2026-01-01", periods=n, freq="h"),
        "kategori": rng.choice(["Makanan", "Minuman", "Elektronik", "Pakaian"], n),
        "harga": rng.normal(50_000, 15_000, n).round(-2).clip(5_000),
        "jumlah": rng.integers(1, 10, n).astype(float),
        "metode_bayar": rng.choice(["Tunai", "QRIS", "Kartu"], n, p=[0.3, 0.5, 0.2]),
    })
    # Sisipkan missing value (~10%) dan duplikat (~5%)
    for kol in ["harga", "jumlah", "kategori", "metode_bayar"]:
        df.loc[rng.choice(n, int(n * 0.10), replace=False), kol] = np.nan
    duplikat = df.sample(int(n * 0.05), random_state=seed)
    return pd.concat([df, duplikat], ignore_index=True)


def muat_data(path: str | None) -> pd.DataFrame:
    if path and Path(path).exists():
        print(f"[INFO] Memuat data dari: {path}")
        return pd.read_csv(path, parse_dates=["tanggal"], dayfirst=False)
    print("[INFO] File tidak diberikan/ditemukan -> memakai data contoh.")
    return buat_data_contoh()


# ---------------------------------------------------------------------------
# 2. DETEKSI MASALAH
# ---------------------------------------------------------------------------
def deteksi_masalah(df: pd.DataFrame) -> pd.DataFrame:
    """Ringkasan missing value per kolom + jumlah duplikat."""
    ringkasan = pd.DataFrame({
        "jumlah_missing": df.isna().sum(),
        "persen_missing": (df.isna().mean() * 100).round(2),
        "tipe_data": df.dtypes.astype(str),
    })
    print("\n=== DETEKSI MISSING VALUES ===")
    print(ringkasan)
    print(f"\nBaris duplikat (identik penuh): {df.duplicated().sum()}")
    return ringkasan


# ---------------------------------------------------------------------------
# 3. HAPUS DUPLIKAT
# ---------------------------------------------------------------------------
def hapus_duplikat(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Hapus duplikat SEBELUM imputasi agar median/modus tidak bias."""
    sebelum = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    return df, sebelum - len(df)


# ---------------------------------------------------------------------------
# 4. IMPUTASI
# ---------------------------------------------------------------------------
def imputasi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Kategorikal -> modus (nilai paling sering)
    for kol in KOLOM_KATEGORIKAL:
        if kol in df.columns and df[kol].isna().any():
            df[kol] = df[kol].fillna(df[kol].mode().iloc[0])

    # Numerik -> median (tahan terhadap outlier). Jika KOLOM_GROUP diisi,
    # median dihitung per grup (mis. harga per kategori), fallback ke median global.
    for kol in KOLOM_NUMERIK:
        if kol not in df.columns or not df[kol].isna().any():
            continue
        if KOLOM_GROUP and KOLOM_GROUP in df.columns:
            median_grup = df.groupby(KOLOM_GROUP)[kol].transform("median")
            df[kol] = df[kol].fillna(median_grup)
        df[kol] = df[kol].fillna(df[kol].median())

    return df


# ---------------------------------------------------------------------------
# 5. VALIDASI & LAPORAN
# ---------------------------------------------------------------------------
def validasi(df: pd.DataFrame) -> None:
    assert df.isna().sum().sum() == 0, "Masih ada missing value!"
    assert not df.duplicated().any(), "Masih ada duplikat!"
    assert (df["harga"] > 0).all(), "Ada harga <= 0!"
    assert (df["jumlah"] > 0).all(), "Ada jumlah <= 0!"


def buat_laporan(df_mentah, df_bersih, n_duplikat, ringkasan_missing) -> str:
    total_missing = int(ringkasan_missing["jumlah_missing"].sum())
    baris = [
        "=" * 60,
        "LAPORAN RINGKASAN PEMBERSIHAN DATA TRANSAKSI RITEL",
        "=" * 60,
        f"Baris data mentah        : {len(df_mentah):,}",
        f"Duplikat dihapus         : {n_duplikat:,}",
        f"Baris data bersih        : {len(df_bersih):,}",
        f"Total sel missing diisi  : {total_missing:,}",
        "",
        "Missing value per kolom (sebelum pembersihan):",
        ringkasan_missing[ringkasan_missing["jumlah_missing"] > 0].to_string(),
        "",
        "Statistik deskriptif kolom numerik (data bersih):",
        df_bersih[KOLOM_NUMERIK].describe().round(2).to_string(),
        "",
        "Distribusi kolom kategorikal (data bersih):",
    ]
    for kol in KOLOM_KATEGORIKAL:
        baris.append(f"\n{kol}:\n{df_bersih[kol].value_counts().to_string()}")

    if {"harga", "jumlah"}.issubset(df_bersih.columns):
        omzet = (df_bersih["harga"] * df_bersih["jumlah"]).sum()
        baris += ["", f"Total omzet (harga x jumlah): Rp {omzet:,.0f}"]
    return "\n".join(baris)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    df_mentah = muat_data(path)

    ringkasan_missing = deteksi_masalah(df_mentah)
    df, n_duplikat = hapus_duplikat(df_mentah)
    df_bersih = imputasi(df)
    validasi(df_bersih)

    laporan = buat_laporan(df_mentah, df_bersih, n_duplikat, ringkasan_missing)
    print("\n" + laporan)

    df_bersih.to_csv(OUTPUT_CSV, index=False)
    Path(OUTPUT_LAPORAN).write_text(laporan, encoding="utf-8")
    print(f"\n[OK] Disimpan: {OUTPUT_CSV}, {OUTPUT_LAPORAN}")


if __name__ == "__main__":
    main()
