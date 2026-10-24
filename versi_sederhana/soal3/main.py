"""
Studi Kasus 3: Standarisasi Format Tanggal & Konversi Mata Uang (versi sederhana)
--------------------------------------------------------------------------------
Langkah:
  1. Muat data transaksi & tabel kurs harian
  2. Ubah semua tanggal (DD-MM-YYYY / YYYY/MM/DD) ke ISO YYYY-MM-DD
  3. Konversi nominal ke Rupiah (IDR) memakai kurs harian
     (akhir pekan tidak ada kurs -> pakai kurs hari kerja terakhir)
  4. Simpan hasil ke CSV & Excel

Jalankan:
  python versi_sederhana/soal3/main.py
"""

import os

import pandas as pd

# ---------------------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------------------
FILE_TRANSAKSI = "transaksi_global.csv"
FILE_KURS = "kurs_harian.csv"
OUTPUT_CSV = "transaksi_idr_sederhana.csv"
OUTPUT_EXCEL = "transaksi_idr_sederhana.xlsx"


# ---------------------------------------------------------------------------
# 1. MUAT DATA
# ---------------------------------------------------------------------------
def muat_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    # dtype=str agar pandas tidak menebak format tanggal sendiri
    trx = pd.read_csv(FILE_TRANSAKSI, dtype={"tanggal": str})
    kurs = pd.read_csv(FILE_KURS, parse_dates=["tanggal"])
    print(f"[INFO] Transaksi: {len(trx)} baris, Kurs: {len(kurs)} baris")
    return trx, kurs


# ---------------------------------------------------------------------------
# 2. STANDARISASI TANGGAL -> ISO
# ---------------------------------------------------------------------------
def ke_iso(tanggal: pd.Series) -> pd.Series:
    format1 = pd.to_datetime(tanggal, format="%d-%m-%Y", errors="coerce")  # DD-MM-YYYY
    format2 = pd.to_datetime(tanggal, format="%Y/%m/%d", errors="coerce")  # YYYY/MM/DD
    return format1.fillna(format2)


# ---------------------------------------------------------------------------
# 3. KONVERSI KE IDR
# ---------------------------------------------------------------------------
def konversi_ke_idr(trx: pd.DataFrame, kurs: pd.DataFrame) -> pd.DataFrame:
    # merge_asof: ambil kurs di tanggal itu, atau kurs terakhir sebelumnya
    df = pd.merge_asof(trx.sort_values("tanggal"), kurs.sort_values("tanggal"),
                       on="tanggal", by="mata_uang", direction="backward")
    df.loc[df["mata_uang"] == "IDR", "kurs_idr"] = 1  # Rupiah tidak dikonversi
    df["nominal_idr"] = (df["nominal"] * df["kurs_idr"]).round(0)
    return df.sort_values("id_transaksi")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # baca/simpan file di folder ini
    trx, kurs = muat_data()

    trx["tanggal_asli"] = trx["tanggal"]
    trx["tanggal"] = ke_iso(trx["tanggal"])
    df = konversi_ke_idr(trx, kurs)

    assert df["tanggal"].notna().all(), "Ada tanggal yang gagal diubah!"
    assert df["kurs_idr"].notna().all(), "Ada transaksi tanpa kurs!"

    df["tanggal"] = df["tanggal"].dt.strftime("%Y-%m-%d")
    df = df[["id_transaksi", "tanggal_asli", "tanggal", "negara",
             "mata_uang", "nominal", "kurs_idr", "nominal_idr"]]

    print("\n=== HASIL (10 baris pertama) ===")
    print(df.head(10).to_string(index=False))
    print("\n=== TOTAL PER MATA UANG (Rp) ===")
    print(df.groupby("mata_uang")["nominal_idr"].sum().to_string())
    print(f"\nTotal seluruh transaksi: Rp {df['nominal_idr'].sum():,.0f}")

    # 4. SIMPAN
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n[OK] Disimpan: {OUTPUT_CSV}, {OUTPUT_EXCEL}")


if __name__ == "__main__":
    main()
