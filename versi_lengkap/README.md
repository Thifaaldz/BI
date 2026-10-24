# Versi Lengkap — Soal 2 & Soal 3

Folder ini berisi penyelesaian **Studi Kasus 2** dan **Studi Kasus 3** dalam versi
lengkap. Strukturnya sama seperti `app.py` (docstring langkah → `KONFIGURASI` → fungsi
bernomor → `main()`), tetapi dengan fitur tambahan:

- **membuat data contoh** otomatis kalau file input tidak ada,
- bisa memakai **file sendiri** lewat argumen command line,
- **merapikan tipe data** sebelum diproses,
- **validasi** dengan `assert` supaya hasil yang salah tidak ikut tersimpan,
- **laporan ringkasan** tambahan di layar dan di Excel.

Versi yang lebih singkat ada di folder
[`../versi_sederhana`](../versi_sederhana/README.md). Angka hasil akhir kedua versi
**sama persis**.

---

## Struktur Folder

```
versi_lengkap/
├── README.md
├── soal2/                                Konsolidasi Multi-Sumber Data Penjualan
│   ├── soal2_konsolidasi_penjualan.py    ← script
│   ├── penjualan_online.csv              ← input (online, CSV)
│   ├── penjualan_offline.db              ← input (offline, SQLite, tabel penjualan_toko)
│   ├── konsolidasi_penjualan_detail.csv  ← output (hasil concat)
│   ├── konsolidasi_penjualan_rekap.csv   ← output (hasil merge)
│   └── konsolidasi_penjualan.xlsx        ← output (3 sheet)
└── soal3/                                Standarisasi Tanggal & Konversi Mata Uang
    ├── soal3_standarisasi_tanggal_kurs.py← script
    ├── transaksi_global.csv              ← input (format tanggal campuran)
    ├── kurs_harian.csv                   ← input (kurs harian ke IDR)
    ├── transaksi_global_idr.csv          ← output
    └── transaksi_global_idr.xlsx         ← output (2 sheet)
```

## Cara Menjalankan

Dari folder utama proyek (`bi/`):

```bash
pip install -r requirements.txt      # pandas, numpy, openpyxl

# memakai data di folder masing-masing
python versi_lengkap/soal2/soal2_konsolidasi_penjualan.py
python versi_lengkap/soal3/soal3_standarisasi_tanggal_kurs.py

# memakai file sendiri (path dihitung dari folder script)
python versi_lengkap/soal2/soal2_konsolidasi_penjualan.py online.csv offline.db
python versi_lengkap/soal3/soal3_standarisasi_tanggal_kurs.py transaksi.csv kurs.csv
```

Baris pertama `main()` adalah `os.chdir(Path(__file__).resolve().parent)`. Artinya,
script selalu bekerja di foldernya sendiri. File input dibaca dari sana, hasil juga
disimpan di sana, dan path file yang diberikan lewat argumen juga dihitung dari folder
tersebut.

Kalau file input **tidak ditemukan**, script otomatis membuat data contoh dengan
`numpy` (seed 42, jadi hasilnya selalu sama). Script tetap bisa dicoba walaupun belum
ada data.

---

## Soal 2 — Konsolidasi Multi-Sumber Data Penjualan

### Kasus

> Perusahaan memiliki data penjualan **online (format CSV)** dan data penjualan toko
> **offline (dari database SQL)**.
>
> **Tugas Python:** Lakukan proses *merge* dan *concat* menggunakan Pandas untuk
> menyatukan kedua sumber data tersebut berdasarkan **ID Produk dan Tanggal**, lalu
> simpan ke format baru (Excel/CSV).

### Data Input

**`penjualan_online.csv`**: 120 transaksi dari Tokopedia, Shopee, dan Website

| order_id | product_id | order_date | qty | price | platform |
|----------|------------|------------|-----|-------|----------|
| ON-0001  | P001       | 2026-09-07 | 1   | 35000 | Website  |

**`penjualan_offline.db`**, tabel `penjualan_toko`: 100 transaksi dari cabang
Jakarta, Bekasi, dan Tangerang

| no_struk | kode_produk | tgl_transaksi | jumlah | harga_satuan | cabang    |
|----------|-------------|---------------|--------|--------------|-----------|
| OFF-0001 | P002        | 2026-09-02    | 6      | 12000        | Tangerang |

Ada 5 produk (P001–P005) dengan periode 1–14 September 2026.

### Konfigurasi

```python
FILE_ONLINE = "penjualan_online.csv"
FILE_OFFLINE = "penjualan_offline.db"
TABEL_OFFLINE = "penjualan_toko"
KUNCI = ["id_produk", "tanggal"]
OUTPUT_EXCEL = "konsolidasi_penjualan.xlsx"
OUTPUT_CSV_DETAIL = "konsolidasi_penjualan_detail.csv"
OUTPUT_CSV_REKAP = "konsolidasi_penjualan_rekap.csv"

PRODUK = {"P001": "Kopi Bubuk 200g", "P002": "Teh Celup 25s", ...}
```

`PRODUK` adalah tabel referensi (master produk) yang dipakai untuk menambahkan nama
produk ke hasil.

### Penjelasan Fungsi per Langkah

#### 1. Muat data

| Fungsi | Isi |
|---|---|
| `buat_data_contoh()` | Membuat CSV & database SQLite contoh kalau file belum ada. Nama kolomnya sengaja dibuat berbeda antar sumber, seperti kondisi nyata. Data offline ditulis ke database dengan `DataFrame.to_sql()`. |
| `muat_online()` | `pd.read_csv(path)` |
| `muat_offline()` | Membuka database dengan `sqlite3.connect()`, lalu `pd.read_sql_query("SELECT * FROM penjualan_toko", conn)` |

#### 2. Samakan struktur kolom

`standarisasi_online()` dan `standarisasi_offline()` mengganti nama kolom dengan
`rename()`, lalu menambah kolom `kanal`:

| Online (CSV) | Offline (SQL) | Nama baru |
|---|---|---|
| order_id | no_struk | id_transaksi |
| product_id | kode_produk | id_produk |
| order_date | tgl_transaksi | tanggal |
| qty | jumlah | jumlah |
| price | harga_satuan | harga_satuan |
| platform | cabang | lokasi |
| – | – | kanal (`Online` / `Offline`) |

`rapikan_tipe()` memastikan kunci penggabungan benar-benar cocok:

```python
df["id_produk"] = df["id_produk"].astype(str).str.strip().str.upper()  # " p001" -> "P001"
df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.normalize()          # teks -> tanggal, jam dibuang
df["jumlah"] = pd.to_numeric(df["jumlah"])
df["harga_satuan"] = pd.to_numeric(df["harga_satuan"])
df["total"] = df["jumlah"] * df["harga_satuan"]
```

Ini penting karena merge hanya mencocokkan nilai yang **persis sama**. Contohnya,
`"p001 "` tidak akan cocok dengan `"P001"`, dan tanggal yang masih mengandung jam tidak
akan cocok dengan tanggal yang tidak ada jamnya.

#### 3. CONCAT — `gabung_concat()`

```python
detail = pd.concat([online[kolom], offline[kolom]], ignore_index=True)
detail.insert(4, "nama_produk", detail["id_produk"].map(PRODUK))
```

- Menumpuk transaksi online dan offline **ke bawah**: 120 + 100 = **220 baris**.
- `map(PRODUK)` menambahkan nama produk berdasarkan ID-nya.
- Hasilnya diurutkan per ID Produk → Tanggal → Kanal.

Contoh isi `konsolidasi_penjualan_detail.csv`:

```
id_transaksi,kanal,lokasi,id_produk,nama_produk,tanggal,jumlah,harga_satuan,total
ON-0018,Online,Website,P001,Kopi Bubuk 200g,2026-09-01,1,35000,35000
OFF-0094,Offline,Jakarta,P001,Kopi Bubuk 200g,2026-09-02,6,35000,210000
```

#### 4. MERGE — `rekap_per_kunci()` + `gabung_merge()`

```python
rekap = pd.merge(
    rekap_per_kunci(online, "online"),
    rekap_per_kunci(offline, "offline"),
    on=KUNCI,
    how="outer",
    indicator="sumber",
)
```

1. **`rekap_per_kunci()`** menjumlahkan `jumlah` dan `total` per (id_produk, tanggal)
   untuk tiap kanal, lalu mengganti namanya menjadi `qty_online`/`omzet_online` atau
   `qty_offline`/`omzet_offline`. Tujuannya supaya setiap kunci unik dan merge tidak
   menghasilkan baris berlipat (*many-to-many*).
2. **`how="outer"`**: semua kombinasi produk-tanggal dari kedua kanal tetap disimpan.
3. **`indicator="sumber"`**: pandas menambah kolom yang menunjukkan asal tiap baris.
   Nilainya diterjemahkan:
   - `both` → **Keduanya**: produk terjual di online dan offline pada hari itu
   - `left_only` → **Hanya Online**
   - `right_only` → **Hanya Offline**
4. Nilai kosong diisi 0, lalu dihitung `qty_total` dan `omzet_total`.

Contoh isi `konsolidasi_penjualan_rekap.csv`:

```
id_produk,nama_produk,tanggal,qty_online,omzet_online,qty_offline,omzet_offline,sumber,qty_total,omzet_total
P001,Kopi Bubuk 200g,2026-09-01,1,35000,0,0,Hanya Online,1,35000
P001,Kopi Bubuk 200g,2026-09-02,6,210000,6,210000,Keduanya,12,420000
```

#### 5. Validasi & simpan

`validasi()` memeriksa tiga hal. Kalau salah satu gagal, program berhenti:

```python
assert len(detail) == len(online) + len(offline)       # concat tidak kehilangan baris
assert not rekap.duplicated(KUNCI).any()                # tiap (produk, tanggal) unik
assert rekap["omzet_total"].sum() == detail["total"].sum()  # total omzet merge = concat
```

Pemeriksaan ketiga memastikan tidak ada omzet yang hilang atau terhitung dua kali saat
merge.

`ringkasan_produk()` membuat **pivot table**: omzet per produk dengan kolom Offline,
Online, dan Total.

`simpan()` menulis:
- `konsolidasi_penjualan_detail.csv`: hasil concat
- `konsolidasi_penjualan_rekap.csv`: hasil merge
- `konsolidasi_penjualan.xlsx`, berisi 3 sheet: **Detail (concat)**, **Rekap (merge)**,
  **Ringkasan Produk**

### Ringkasan Hasil

| Keterangan | Nilai |
|---|---|
| Transaksi online / offline | 120 / 100 |
| Baris hasil concat | 220 |
| Baris hasil merge | 66 |
| Sumber: Keduanya / Hanya Online / Hanya Offline | 49 / 8 / 9 |

**Omzet per produk (Rp):**

| ID | Produk | Offline | Online | Total |
|---|---|---:|---:|---:|
| P001 | Kopi Bubuk 200g | 3.640.000 | 2.100.000 | 5.740.000 |
| P002 | Teh Celup 25s | 1.056.000 | 576.000 | 1.632.000 |
| P003 | Gula Pasir 1kg | 1.330.000 | 1.435.000 | 2.765.000 |
| P004 | Minyak Goreng 2L | 2.128.000 | 3.458.000 | 5.586.000 |
| P005 | Beras Premium 5kg | 8.446.000 | 5.248.000 | 13.694.000 |
| | **Total** | | | **29.417.000** |

---

## Soal 3 — Standarisasi Format Tanggal & Konversi Mata Uang

### Kasus

> Data transaksi global perusahaan menggunakan berbagai format tanggal
> (**DD-MM-YYYY** vs **YYYY/MM/DD**) dan mata uang asing (**USD, EUR, SGD**).
>
> **Tugas Python:** Ubah seluruh kolom tanggal ke standar **ISO (YYYY-MM-DD)** dan
> konversikan seluruh mata uang ke **Rupiah (IDR)** berdasarkan tabel kurs harian yang
> tersedia.

### Data Input

**`transaksi_global.csv`**: 60 transaksi (30 berformat DD-MM-YYYY, 30 berformat
YYYY/MM/DD)

| id_transaksi | tanggal | negara | mata_uang | nominal |
|---|---|---|---|---|
| TRX-001 | 14-09-2026 | Singapura | SGD | 296.21 |
| TRX-002 | 2026/09/03 | Indonesia | IDR | 3284000.0 |

**`kurs_harian.csv`**: kurs ke Rupiah, **hanya hari kerja** (30 baris = 10 hari × USD,
EUR, SGD)

| tanggal | mata_uang | kurs_idr |
|---|---|---|
| 2026-09-01 | USD | 16319.87 |

Format file sendiri harus mengikuti kolom di atas:
- transaksi: `id_transaksi, tanggal, negara, mata_uang, nominal`
- kurs: `tanggal, mata_uang, kurs_idr`

### Konfigurasi

```python
FORMAT_TANGGAL = [
    (r"^\d{2}-\d{2}-\d{4}$", "%d-%m-%Y"),   # DD-MM-YYYY
    (r"^\d{4}/\d{2}/\d{2}$", "%Y/%m/%d"),   # YYYY/MM/DD
    (r"^\d{4}-\d{2}-\d{2}$", "%Y-%m-%d"),   # sudah ISO
]
```

Daftar ini memasangkan **pola regex** dengan **format `strptime`**. Kalau nanti ada
format baru (misalnya `DD/MM/YYYY`), cukup tambahkan satu baris di sini.

### Penjelasan Fungsi per Langkah

#### 1. Muat data

- `buat_data_contoh()` membuat tabel kurs untuk hari kerja saja, plus 60 transaksi yang
  format tanggalnya diselang-seling (baris genap DD-MM-YYYY, baris ganjil YYYY/MM/DD).
- `muat_data()` membaca kolom `tanggal` dengan `dtype=str` supaya pandas **tidak
  menebak** formatnya sendiri.

#### 2. Standarisasi tanggal ke ISO

| Fungsi | Isi |
|---|---|
| `deteksi_format()` | Memberi label format asli tiap baris (`%d-%m-%Y`, `%Y/%m/%d`, `%Y-%m-%d`, atau `TIDAK DIKENALI`) untuk laporan |
| `ke_iso()` | Untuk tiap pola, pilih baris yang cocok (`str.match`), lalu parse **hanya baris itu** dengan format yang tepat |
| `standarisasi_tanggal()` | Menyimpan `tanggal_asli` dan `format_asli`, mengubah kolom `tanggal`, lalu mencetak peringatan kalau ada yang gagal |

```python
for pola, fmt in FORMAT_TANGGAL:
    cocok = teks.str.match(pola)
    hasil[cocok] = pd.to_datetime(teks[cocok], format=fmt, errors="coerce")
```

**Kenapa tidak cukup `pd.to_datetime()` saja?** Tanpa format yang jelas, pandas
menebak. `03-09-2026` bisa terbaca sebagai **9 Maret** (gaya Amerika), padahal
maksudnya **3 September**. Dengan mencocokkan pola dulu, setiap baris pasti dibaca
dengan format yang benar.

#### 3. Konversi ke Rupiah

`siapkan_kurs()` merapikan tabel kurs: tanggal diubah ke ISO, kode mata uang dijadikan
huruf besar, lalu diurutkan per tanggal.

`konversi_ke_idr()`:

```python
df = pd.merge_asof(
    df.sort_values("tanggal"),
    kurs.rename(columns={"tanggal": "tanggal_kurs"}).sort_values("tanggal_kurs"),
    left_on="tanggal", right_on="tanggal_kurs",
    by="mata_uang", direction="backward",
)
```

- **`merge_asof`** dipakai karena tabel kurs tidak punya data Sabtu/Minggu. Dengan
  `direction="backward"`, transaksi akhir pekan otomatis memakai **kurs hari kerja
  terakhir** (Jumat).
- **`by="mata_uang"`** memastikan USD hanya dicocokkan dengan kurs USD, dan seterusnya.
- Kolom kurs diganti namanya menjadi **`tanggal_kurs`**, jadi di hasil terlihat kurs
  tanggal berapa yang dipakai. Kalau `tanggal ≠ tanggal_kurs`, berarti transaksi itu
  memakai kurs hari sebelumnya.
- Kolom bantu `_urut` mengembalikan urutan baris seperti semula setelah diurutkan untuk
  `merge_asof`.
- Transaksi **IDR** diberi `kurs_idr = 1` dan `tanggal_kurs = tanggal`.
- `nominal_idr = nominal × kurs_idr`, dibulatkan ke rupiah.

#### 4. Validasi & simpan

```python
assert df["tanggal"].notna().all()     # semua tanggal berhasil diubah
assert tanpa_kurs.empty                # semua transaksi mendapat kurs (menampilkan yang bermasalah)
assert (df["nominal_idr"] > 0).all()   # tidak ada nominal nol/negatif
```

`susun_output()` mengatur urutan kolom dan menulis tanggal sebagai teks ISO
`YYYY-MM-DD`.

Kolom output `transaksi_global_idr.csv`:

| Kolom | Arti |
|---|---|
| id_transaksi | ID transaksi |
| tanggal_asli | Tanggal sebelum diubah (apa adanya) |
| format_asli | Format yang terdeteksi |
| tanggal | Tanggal format ISO |
| negara, mata_uang, nominal | Data asli |
| tanggal_kurs | Tanggal kurs yang dipakai |
| kurs_idr | Nilai kurs |
| nominal_idr | Hasil konversi ke Rupiah |

Contoh:

```
TRX-007,03-09-2026,%d-%m-%Y,2026-09-03,Amerika Serikat,USD,171.63,2026-09-03,16308.34,2799000.0
```

171,63 USD × 16.308,34 = **Rp 2.799.000**

Excel `transaksi_global_idr.xlsx` berisi 2 sheet: **Transaksi IDR** dan
**Ringkasan Mata Uang**.

### Ringkasan Hasil

| Keterangan | Nilai |
|---|---|
| Format `DD-MM-YYYY` / `YYYY/MM/DD` | 30 / 30 |
| Transaksi memakai kurs hari sebelumnya (akhir pekan) | 13 |

| Mata uang | Transaksi | Total nominal asli | Rata-rata kurs | Total Rupiah |
|---|---:|---:|---:|---:|
| EUR | 17 | 4.497,23 | 17.722,84 | 79.718.936 |
| IDR | 2 | 4.512.000,00 | 1,00 | 4.512.000 |
| SGD | 19 | 5.362,65 | 12.613,11 | 67.648.380 |
| USD | 22 | 4.476,10 | 16.288,20 | 72.889.652 |
| **Total** | **60** | | | **224.768.968** |

---

## Library yang Dipakai

| Library | Fungsi |
|---|---|
| `pandas` | Membaca CSV/SQL, concat, merge, merge_asof, groupby, pivot_table, menulis CSV/Excel |
| `numpy` | Membuat data contoh acak (`default_rng`) |
| `sqlite3` | (bawaan Python) Membaca & menulis database `.db` |
| `openpyxl` | Mesin untuk menulis file `.xlsx` multi-sheet |
| `sys`, `os`, `pathlib` | (bawaan Python) Argumen command line, cek file ada/tidak, pindah ke folder script |

## Perbedaan dengan Versi Sederhana

| Fitur | Sederhana | Lengkap |
|---|---|---|
| Panjang kode (soal 2 & soal 3) | ±115 & ±90 baris | ±250 & ±240 baris |
| Membuat data contoh otomatis | ✗ | ✓ |
| Input file sendiri lewat argumen | ✗ | ✓ |
| Soal 2: rapikan tipe data sebelum merge | ✗ | ✓ |
| Soal 2: nama produk & lokasi | ✗ | ✓ |
| Soal 2: kolom `sumber` dari `indicator` | ✗ | ✓ |
| Soal 2: sheet Ringkasan Produk (pivot) | ✗ | ✓ |
| Soal 3: deteksi format per baris (regex) + mendukung ISO | ✗ (2 format, pakai `fillna`) | ✓ |
| Soal 3: kolom `tanggal_kurs` & `format_asli` | ✗ | ✓ |
| Soal 3: sheet Ringkasan Mata Uang | ✗ | ✓ |
| Validasi `assert` | Soal 3 saja | Soal 2 & 3 |
| **Hasil angka akhir** | **Sama** | **Sama** |
