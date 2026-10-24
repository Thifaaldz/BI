"""
Studi Kasus 3: Standarisasi Format Tanggal dan Konversi Mata Uang
-----------------------------------------------------------------
Kasus : Data transaksi global memakai berbagai format tanggal
        (DD-MM-YYYY vs YYYY/MM/DD) dan mata uang asing (USD, EUR, SGD).
Tugas : Ubah seluruh kolom tanggal ke standar ISO (YYYY-MM-DD) dan
        konversikan seluruh mata uang ke Rupiah (IDR) berdasarkan tabel
        kurs harian yang tersedia.

Langkah:
  1. Muat data transaksi & tabel kurs (atau buat data contoh)
  2. Standarisasi tanggal -> ISO YYYY-MM-DD (deteksi format per baris)
  3. Konversi nominal -> IDR memakai kurs harian
     (jika kurs tanggal itu tidak ada, pakai kurs terakhir sebelumnya)
  4. Validasi & simpan hasil

Jalankan:
  python soal3_standarisasi_tanggal_kurs.py                        # data contoh
  python soal3_standarisasi_tanggal_kurs.py transaksi.csv kurs.csv # file sendiri

Format file sendiri:
  transaksi.csv : id_transaksi, tanggal, negara, mata_uang, nominal
  kurs.csv      : tanggal (YYYY-MM-DD), mata_uang, kurs_idr
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------------------
FILE_TRANSAKSI = "transaksi_global.csv"
FILE_KURS = "kurs_harian.csv"
OUTPUT_CSV = "transaksi_global_idr.csv"
OUTPUT_EXCEL = "transaksi_global_idr.xlsx"

# Pola format tanggal yang dikenali: (regex, format strptime)
FORMAT_TANGGAL = [
    (r"^\d{2}-\d{2}-\d{4}$", "%d-%m-%Y"),   # DD-MM-YYYY
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),   # YYYY/MM/DD
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),   # sudah ISO
]

KURS_DASAR = {"USD": 16_300, "EUR": 17_700, "SGD": 12_600}  # untuk data contoh
NEGARA = {"USD": "Amerika Serikat", "EUR": "Jerman", "SGD": "Singapura",
          "IDR": "Indonesia"}


# ---------------------------------------------------------------------------
# 1. MUAT DATA (atau buat data contoh)
# ---------------------------------------------------------------------------
def buat_data_contoh(path_trx: str, path_kurs: str, n: int = 60, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    hari = pd.date_range("2026-09-01", "2026-09-14", freq="D")

    # Tabel kurs harian: hanya hari kerja (Sabtu/Minggu tidak ada kurs)
    hari_kerja = hari[hari.dayofweek < 5]
    kurs = pd.DataFrame([
        {"tanggal": t.strftime("%Y-%m-%d"), "mata_uang": mu,
         "kurs_idr": round(dasar * (1 + rng.normal(0, 0.004)), 2)}
        for t in hari_kerja for mu, dasar in KURS_DASAR.items()
    ])
    kurs.to_csv(path_kurs, index=False)

    # Transaksi dengan format tanggal campuran
    mata_uang = rng.choice(["USD", "EUR", "SGD", "IDR"], n, p=[0.35, 0.25, 0.25, 0.15])
    tgl = rng.choice(hari, n)
    nominal = [
        round(rng.uniform(100_000, 5_000_000), -3) if mu == "IDR"
        else round(rng.uniform(10, 500), 2)
        for mu in mata_uang
    ]
    teks_tgl = [
        pd.Timestamp(t).strftime("%d-%m-%Y" if i % 2 == 0 else "%Y/%m/%d")
        for i, t in enumerate(tgl)
    ]
    trx = pd.DataFrame({
        "id_transaksi": [f"TRX-{i:03d}" for i in range(1, n + 1)],
        "tanggal": teks_tgl,
        "negara": [NEGARA[mu] for mu in mata_uang],
        "mata_uang": mata_uang,
        "nominal": nominal,
    })
    trx.to_csv(path_trx, index=False)
    print(f"[INFO] Data contoh dibuat: {path_trx}, {path_kurs}")


def muat_data(path_trx: str, path_kurs: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f"[INFO] Memuat transaksi: {path_trx}")
    print(f"[INFO] Memuat kurs harian: {path_kurs}")
    # dtype=str agar tanggal tidak ditebak otomatis oleh pandas
    trx = pd.read_csv(path_trx, dtype={"tanggal": str})
    kurs = pd.read_csv(path_kurs, dtype={"tanggal": str})
    return trx, kurs


# ---------------------------------------------------------------------------
# 2. STANDARISASI TANGGAL -> ISO (YYYY-MM-DD)
# ---------------------------------------------------------------------------
def deteksi_format(teks: pd.Series) -> pd.Series:
    """Label format tanggal tiap baris (untuk laporan)."""
    label = pd.Series("TIDAK DIKENALI", index=teks.index)
    for pola, fmt in FORMAT_TANGGAL:
        label[teks.str.match(pola)] = fmt
    return label


def ke_iso(teks: pd.Series) -> pd.Series:
    """Parse tiap baris sesuai polanya; tidak memakai tebakan otomatis
    agar 03-09-2026 tidak tertukar menjadi 9 Maret."""
    teks = teks.astype(str).str.strip()
    hasil = pd.Series(pd.NaT, index=teks.index, dtype="datetime64[ns]")
    for pola, fmt in FORMAT_TANGGAL:
        cocok = teks.str.match(pola)
        hasil[cocok] = pd.to_datetime(teks[cocok], format=fmt, errors="coerce")
    return hasil


def standarisasi_tanggal(df: pd.DataFrame, kolom: str = "tanggal") -> pd.DataFrame:
    df = df.copy()
    df["tanggal_asli"] = df[kolom]
    df["format_asli"] = deteksi_format(df[kolom].astype(str).str.strip())
    df[kolom] = ke_iso(df[kolom])
    gagal = df[kolom].isna().sum()
    if gagal:
        print(f"[PERINGATAN] {gagal} tanggal tidak dapat diparse:")
        print(df.loc[df[kolom].isna(), ["id_transaksi", "tanggal_asli"]].to_string(index=False))
    return df


# ---------------------------------------------------------------------------
# 3. KONVERSI MATA UANG -> IDR
# ---------------------------------------------------------------------------
def siapkan_kurs(kurs: pd.DataFrame) -> pd.DataFrame:
    kurs = kurs.copy()
    kurs["tanggal"] = ke_iso(kurs["tanggal"])
    kurs["mata_uang"] = kurs["mata_uang"].str.strip().str.upper()
    return kurs.dropna(subset=["tanggal"]).sort_values("tanggal")


def konversi_ke_idr(df: pd.DataFrame, kurs: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["mata_uang"] = df["mata_uang"].str.strip().str.upper()
    df["_urut"] = np.arange(len(df))

    # merge_asof: ambil kurs pada tanggal transaksi, atau kurs terakhir
    # sebelumnya (mis. transaksi hari Sabtu/Minggu memakai kurs Jumat)
    df = pd.merge_asof(
        df.sort_values("tanggal"),
        kurs.rename(columns={"tanggal": "tanggal_kurs"}).sort_values("tanggal_kurs"),
        left_on="tanggal", right_on="tanggal_kurs",
        by="mata_uang", direction="backward",
    ).sort_values("_urut").drop(columns="_urut")

    # IDR tidak perlu dikonversi
    idr = df["mata_uang"] == "IDR"
    df.loc[idr, "kurs_idr"] = 1.0
    df.loc[idr, "tanggal_kurs"] = df.loc[idr, "tanggal"]

    df["nominal_idr"] = (df["nominal"] * df["kurs_idr"]).round(0)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. VALIDASI & SIMPAN
# ---------------------------------------------------------------------------
def validasi(df: pd.DataFrame) -> None:
    assert df["tanggal"].notna().all(), "Masih ada tanggal yang gagal diparse!"
    tanpa_kurs = df[df["kurs_idr"].isna()]
    assert tanpa_kurs.empty, (
        "Kurs tidak tersedia untuk:\n"
        + tanpa_kurs[["id_transaksi", "tanggal", "mata_uang"]].to_string(index=False)
    )
    assert (df["nominal_idr"] > 0).all(), "Ada nominal IDR <= 0!"


def susun_output(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["id_transaksi", "tanggal_asli", "format_asli", "tanggal", "negara",
              "mata_uang", "nominal", "tanggal_kurs", "kurs_idr", "nominal_idr"]].copy()
    out["tanggal"] = out["tanggal"].dt.strftime("%Y-%m-%d")
    out["tanggal_kurs"] = out["tanggal_kurs"].dt.strftime("%Y-%m-%d")
    return out


def simpan(out: pd.DataFrame, ringkasan: pd.DataFrame) -> None:
    out.to_csv(OUTPUT_CSV, index=False)
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        out.to_excel(writer, sheet_name="Transaksi IDR", index=False)
        ringkasan.to_excel(writer, sheet_name="Ringkasan Mata Uang")
    print(f"\n[OK] Disimpan: {OUTPUT_CSV}, {OUTPUT_EXCEL}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    os.chdir(Path(__file__).resolve().parent)  # baca/simpan file di folder ini
    path_trx = sys.argv[1] if len(sys.argv) > 1 else FILE_TRANSAKSI
    path_kurs = sys.argv[2] if len(sys.argv) > 2 else FILE_KURS
    if not (Path(path_trx).exists() and Path(path_kurs).exists()):
        print("[INFO] File sumber tidak ditemukan -> membuat data contoh.")
        buat_data_contoh(path_trx, path_kurs)

    trx, kurs = muat_data(path_trx, path_kurs)

    df = standarisasi_tanggal(trx)
    print("\n=== FORMAT TANGGAL YANG TERDETEKSI ===")
    print(df["format_asli"].value_counts().to_string())

    df = konversi_ke_idr(df, siapkan_kurs(kurs))
    validasi(df)
    out = susun_output(df)

    pakai_kurs_sebelumnya = (out["tanggal"] != out["tanggal_kurs"]).sum()
    print(f"\nTransaksi memakai kurs hari sebelumnya (akhir pekan/libur): "
          f"{pakai_kurs_sebelumnya}")

    print("\n=== CONTOH HASIL (10 baris pertama) ===")
    print(out.head(10).to_string(index=False))

    ringkasan = (out.groupby("mata_uang")
                    .agg(jumlah_transaksi=("id_transaksi", "count"),
                         total_nominal_asli=("nominal", "sum"),
                         rata_rata_kurs=("kurs_idr", "mean"),
                         total_idr=("nominal_idr", "sum"))
                    .round(2))
    print("\n=== RINGKASAN PER MATA UANG ===")
    print(ringkasan.to_string())
    print(f"\nTotal seluruh transaksi: Rp {out['nominal_idr'].sum():,.0f}")

    simpan(out, ringkasan)


if __name__ == "__main__":
    main()
