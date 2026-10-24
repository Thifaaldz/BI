# Versi Sederhana — Soal 2 & Soal 3

Folder ini berisi penyelesaian **Studi Kasus 2** dan **Studi Kasus 3** dengan kode yang
dibuat sesingkat mungkin, mengikuti gaya `app.py` (contoh dari kelas):

- docstring di atas berisi daftar langkah,
- bagian `KONFIGURASI` untuk nama file/kolom,
- satu fungsi untuk tiap langkah, diberi nomor,
- fungsi `main()` yang memanggil semuanya secara berurutan.

Versi yang lebih lengkap (dengan validasi, data contoh, dan laporan tambahan) ada di
folder [`../versi_lengkap`](../versi_lengkap/README.md).

---

## Struktur Folder

```
versi_sederhana/
├── README.md
├── soal2/                          Konsolidasi Multi-Sumber Data Penjualan
│   ├── main.py                     ← script
│   ├── penjualan_online.csv        ← input (penjualan online, format CSV)
│   ├── penjualan_offline.db        ← input (penjualan toko, database SQLite)
│   ├── konsolidasi_sederhana.csv   ← output (hasil merge)
│   └── konsolidasi_sederhana.xlsx  ← output (sheet "Concat" & "Merge")
└── soal3/                          Standarisasi Tanggal & Konversi Mata Uang
    ├── main.py                     ← script
    ├── transaksi_global.csv        ← input (transaksi dengan format tanggal campuran)
    ├── kurs_harian.csv             ← input (tabel kurs harian ke IDR)
    ├── transaksi_idr_sederhana.csv ← output
    └── transaksi_idr_sederhana.xlsx← output
```

## Cara Menjalankan

Dari folder utama proyek (`bi/`):

```bash
pip install -r requirements.txt      # pandas, numpy, openpyxl

python versi_sederhana/soal2/main.py
python versi_sederhana/soal3/main.py
```

Script bisa dijalankan dari folder mana saja. Baris pertama `main()` adalah:

```python
os.chdir(os.path.dirname(os.path.abspath(__file__)))
```

Artinya, file input selalu dibaca dari folder script itu sendiri, dan hasilnya juga
disimpan di sana.

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

**`penjualan_online.csv`**: 120 transaksi online

| order_id | product_id | order_date | qty | price | platform  |
|----------|------------|------------|-----|-------|-----------|
| ON-0001  | P001       | 2026-09-07 | 1   | 35000 | Website   |
| ON-0002  | P004       | 2026-09-10 | 3   | 38000 | Website   |

**`penjualan_offline.db`**, tabel `penjualan_toko`: 100 transaksi toko

| no_struk | kode_produk | tgl_transaksi | jumlah | harga_satuan | cabang    |
|----------|-------------|---------------|--------|--------------|-----------|
| OFF-0001 | P002        | 2026-09-02    | 6      | 12000        | Tangerang |
| OFF-0002 | P005        | 2026-09-12    | 1      | 82000        | Bekasi    |

Nama kolom kedua sumber **berbeda** (`product_id` vs `kode_produk`, `order_date` vs
`tgl_transaksi`, dst.). Kondisi seperti ini sering terjadi di dunia nyata, jadi kolomnya
harus disamakan dulu sebelum digabung.

### Penjelasan Kode per Langkah

#### Konfigurasi

```python
FILE_ONLINE = "penjualan_online.csv"
FILE_OFFLINE = "penjualan_offline.db"
TABEL_OFFLINE = "penjualan_toko"
KUNCI = ["id_produk", "tanggal"]  # kunci penggabungan
OUTPUT_EXCEL = "konsolidasi_sederhana.xlsx"
OUTPUT_CSV = "konsolidasi_sederhana.csv"
```

`KUNCI` adalah kolom yang dipakai untuk menggabungkan data, yaitu **ID Produk + Tanggal**
sesuai soal.

#### 1. Muat data — `muat_data()`

```python
online = pd.read_csv(FILE_ONLINE)
with sqlite3.connect(FILE_OFFLINE) as conn:
    offline = pd.read_sql_query(f"SELECT * FROM {TABEL_OFFLINE}", conn)
```

- CSV dibaca dengan `pd.read_csv`.
- Database SQL dibuka dengan modul bawaan Python `sqlite3`. Isi tabelnya diambil dengan
  query `SELECT *` lewat `pd.read_sql_query`, sehingga hasilnya langsung berupa
  DataFrame.

#### 2. Samakan nama kolom — `samakan_kolom()`

```python
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
```

- `rename` mengganti nama kolom supaya kedua tabel punya struktur yang sama.
- Kolom baru `kanal` menandai asal tiap baris (Online/Offline), supaya setelah digabung
  sumbernya masih bisa dibedakan.
- Hanya kolom yang dibutuhkan yang diambil, lalu ditambah kolom
  `total = jumlah × harga_satuan`.

| Online (CSV) | Offline (SQL)   | Nama baru      |
|--------------|-----------------|----------------|
| order_id     | no_struk        | id_transaksi   |
| product_id   | kode_produk     | id_produk      |
| order_date   | tgl_transaksi   | tanggal        |
| qty          | jumlah          | jumlah         |
| price        | harga_satuan    | harga_satuan   |
| –            | –               | kanal (baru)   |
| –            | –               | total (baru)   |

#### 3. CONCAT — `gabung_concat()`

```python
pd.concat([online, offline], ignore_index=True).sort_values(KUNCI)
```

**Concat** menumpuk dua tabel **ke bawah** (baris ditambah, kolom tetap).
120 baris online + 100 baris offline = **220 baris**. Hasilnya diurutkan berdasarkan
ID Produk dan Tanggal. `ignore_index=True` membuat ulang nomor index dari 0.

```
id_transaksi   kanal id_produk    tanggal  jumlah  harga_satuan  total
     ON-0018  Online      P001 2026-09-01       1         35000  35000
     ON-0007  Online      P001 2026-09-02       4         35000 140000
    OFF-0094 Offline      P001 2026-09-02       6         35000 210000
```

#### 4. MERGE — `gabung_merge()`

```python
rekap_online = online.groupby(KUNCI, as_index=False)[["jumlah", "total"]].sum()
rekap_offline = offline.groupby(KUNCI, as_index=False)[["jumlah", "total"]].sum()

rekap = pd.merge(rekap_online, rekap_offline, on=KUNCI, how="outer",
                 suffixes=("_online", "_offline"))
```

**Merge** menggabungkan dua tabel **ke samping** (kolom ditambah) berdasarkan kunci
yang sama.

1. **`groupby` dulu.** Satu produk bisa terjual beberapa kali di hari yang sama. Kalau
   langsung di-merge, baris akan berlipat ganda. Karena itu tiap kanal dijumlahkan dulu
   per (id_produk, tanggal), sehingga tiap kunci hanya punya satu baris.
2. **`how="outer"`.** Semua kombinasi produk-tanggal tetap dipakai, termasuk yang hanya
   ada di salah satu kanal. Kalau memakai `inner`, data yang hanya ada di satu kanal
   akan hilang.
3. **`suffixes`.** Kedua tabel sama-sama punya kolom `jumlah` & `total`, jadi diberi
   akhiran `_online` / `_offline` supaya tidak bentrok.
4. **`fillna(0)`.** Kombinasi yang tidak ada di salah satu kanal bernilai kosong (NaN),
   lalu diisi 0 dan diubah ke `int`.
5. Kolom `total_omzet = total_online + total_offline`.

Hasil: **66 baris** (5 produk × 14 hari, dikurangi kombinasi yang tidak ada penjualan).

```
id_produk    tanggal  jumlah_online  total_online  jumlah_offline  total_offline  total_omzet
     P001 2026-09-01              1         35000               0              0        35000
     P001 2026-09-02              6        210000               6         210000       420000
     P001 2026-09-05              0             0               9         315000       315000
```

#### 5. Simpan

```python
rekap.to_csv(OUTPUT_CSV, index=False)
with pd.ExcelWriter(OUTPUT_EXCEL) as writer:
    detail.to_excel(writer, sheet_name="Concat", index=False)
    rekap.to_excel(writer, sheet_name="Merge", index=False)
```

- **CSV** berisi hasil merge (rekap).
- **Excel** berisi 2 sheet: `Concat` (220 transaksi detail) dan `Merge` (66 baris rekap).

### Ringkasan Hasil

| Keterangan            | Nilai             |
|-----------------------|-------------------|
| Baris online          | 120               |
| Baris offline         | 100               |
| Baris hasil concat    | 220               |
| Baris hasil merge     | 66                |
| Total omzet gabungan  | **Rp 29.417.000** |

### Perbedaan Concat vs Merge

| | `pd.concat` | `pd.merge` |
|---|---|---|
| Arah | Ke bawah (menambah baris) | Ke samping (menambah kolom) |
| Syarat | Nama kolom harus sama | Harus ada kolom kunci yang sama |
| Dipakai untuk | Menyatukan semua transaksi jadi satu daftar | Membandingkan online vs offline per produk & tanggal |
| Hasil di soal ini | 220 baris transaksi | 66 baris rekap |

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

**`transaksi_global.csv`**: 60 transaksi, format tanggalnya campuran

| id_transaksi | tanggal        | negara          | mata_uang | nominal   |
|--------------|----------------|-----------------|-----------|-----------|
| TRX-001      | **14-09-2026** | Singapura       | SGD       | 296.21    |
| TRX-002      | **2026/09/03** | Indonesia       | IDR       | 3284000.0 |
| TRX-003      | **07-09-2026** | Amerika Serikat | USD       | 51.38     |

**`kurs_harian.csv`**: kurs 1 unit mata uang asing ke Rupiah, **hanya untuk hari kerja**
(Senin–Jumat). Isinya 10 hari × 3 mata uang = 30 baris.

| tanggal    | mata_uang | kurs_idr |
|------------|-----------|----------|
| 2026-09-01 | USD       | 16319.87 |
| 2026-09-01 | EUR       | 17626.37 |
| 2026-09-01 | SGD       | 12637.82 |

### Penjelasan Kode per Langkah

#### Konfigurasi

```python
FILE_TRANSAKSI = "transaksi_global.csv"
FILE_KURS = "kurs_harian.csv"
OUTPUT_CSV = "transaksi_idr_sederhana.csv"
OUTPUT_EXCEL = "transaksi_idr_sederhana.xlsx"
```

#### 1. Muat data — `muat_data()`

```python
trx = pd.read_csv(FILE_TRANSAKSI, dtype={"tanggal": str})
kurs = pd.read_csv(FILE_KURS, parse_dates=["tanggal"])
```

- Kolom `tanggal` transaksi sengaja dibaca sebagai **teks** (`dtype=str`) supaya pandas
  tidak menebak formatnya sendiri. Kalau dibiarkan menebak, `03-09-2026` bisa terbaca
  sebagai **9 Maret**, padahal maksudnya **3 September**.
- Tanggal di tabel kurs sudah dalam format ISO, jadi langsung diubah ke tipe tanggal
  dengan `parse_dates`.

#### 2. Standarisasi tanggal ke ISO — `ke_iso()`

```python
format1 = pd.to_datetime(tanggal, format="%d-%m-%Y", errors="coerce")  # DD-MM-YYYY
format2 = pd.to_datetime(tanggal, format="%Y/%m/%d", errors="coerce")  # YYYY/MM/DD
return format1.fillna(format2)
```

Cara kerjanya:

1. Semua tanggal dicoba dibaca dengan format **DD-MM-YYYY**. Yang tidak cocok
   (misalnya `2026/09/03`) menjadi kosong (`NaT`) karena `errors="coerce"`.
2. Semua tanggal juga dicoba dibaca dengan format **YYYY/MM/DD**.
3. `fillna` mengisi yang kosong di percobaan pertama dengan hasil percobaan kedua.

| tanggal_asli | format1 (`%d-%m-%Y`) | format2 (`%Y/%m/%d`) | hasil      |
|--------------|----------------------|----------------------|------------|
| 14-09-2026   | 2026-09-14           | NaT                  | 2026-09-14 |
| 2026/09/03   | NaT                  | 2026-09-03           | 2026-09-03 |

Saat disimpan, tanggal ditulis ulang dengan `dt.strftime("%Y-%m-%d")`, yaitu format ISO.
Kolom `tanggal_asli` tetap disimpan sebagai pembanding.

#### 3. Konversi ke Rupiah — `konversi_ke_idr()`

```python
df = pd.merge_asof(trx.sort_values("tanggal"), kurs.sort_values("tanggal"),
                   on="tanggal", by="mata_uang", direction="backward")
df.loc[df["mata_uang"] == "IDR", "kurs_idr"] = 1
df["nominal_idr"] = (df["nominal"] * df["kurs_idr"]).round(0)
```

**Masalahnya:** tabel kurs hanya berisi hari kerja, sedangkan ada transaksi di hari
Sabtu/Minggu. Kalau memakai `pd.merge` biasa, transaksi akhir pekan tidak akan
mendapat kurs (NaN).

**Solusinya, `pd.merge_asof`:**
- `on="tanggal"`: dicocokkan berdasarkan tanggal.
- `by="mata_uang"`: USD dicocokkan dengan kurs USD, EUR dengan kurs EUR, dan seterusnya.
- `direction="backward"`: kalau tanggal yang sama tidak ada, dipakai **kurs terakhir
  sebelumnya**. Transaksi hari Sabtu 5 Sep atau Minggu 6 Sep jadi memakai kurs Jumat
  4 Sep. Cara ini lazim dipakai dalam akuntansi.
- Syarat `merge_asof`: kedua tabel harus **diurutkan** berdasarkan tanggal. Karena itu
  ada `sort_values`. Setelah selesai, hasilnya diurutkan kembali per `id_transaksi`.

Transaksi yang sudah dalam **IDR** tidak punya kurs di tabel, jadi kursnya diisi `1`.

Rumus akhir: `nominal_idr = nominal × kurs_idr`, dibulatkan ke rupiah terdekat.

Contoh: TRX-007, 171.63 USD pada 03-09-2026, kurs 16.308,34
→ 171,63 × 16.308,34 = **Rp 2.799.000**.

#### 4. Validasi & simpan

```python
assert df["tanggal"].notna().all(), "Ada tanggal yang gagal diubah!"
assert df["kurs_idr"].notna().all(), "Ada transaksi tanpa kurs!"
```

`assert` menghentikan program dengan pesan error kalau masih ada tanggal yang gagal
diubah, atau ada transaksi yang tidak mendapat kurs. Dengan begitu hasil yang salah
tidak ikut tersimpan.

Setelah itu data disimpan ke `transaksi_idr_sederhana.csv` dan `.xlsx` dengan kolom:

`id_transaksi, tanggal_asli, tanggal, negara, mata_uang, nominal, kurs_idr, nominal_idr`

### Ringkasan Hasil

| Mata uang | Jumlah transaksi | Total dalam Rupiah |
|-----------|------------------|--------------------|
| EUR       | 17               | Rp 79.718.936      |
| IDR       | 2                | Rp 4.512.000       |
| SGD       | 19               | Rp 67.648.380      |
| USD       | 22               | Rp 72.889.652      |
| **Total** | **60**           | **Rp 224.768.968** |

---

## Library yang Dipakai

| Library    | Fungsi |
|------------|--------|
| `pandas`   | Membaca CSV/SQL, concat, merge, merge_asof, groupby, menulis CSV/Excel |
| `sqlite3`  | (bawaan Python) Membuka database `.db` di Soal 2 |
| `openpyxl` | Mesin yang dipakai pandas untuk menulis file `.xlsx` |
| `os`       | (bawaan Python) Pindah ke folder script agar path file selalu benar |

## Perbedaan dengan Versi Lengkap

| Fitur | Sederhana | Lengkap |
|---|---|---|
| Panjang kode (soal 2 & soal 3) | ±115 & ±90 baris | ±250 & ±240 baris |
| Membuat data contoh otomatis jika file tidak ada | ✗ | ✓ |
| Input file sendiri lewat argumen command line | ✗ | ✓ |
| Soal 2: rapikan tipe data (huruf besar ID, spasi, angka) | ✗ | ✓ |
| Soal 2: nama produk & lokasi (cabang/platform) | ✗ | ✓ |
| Soal 2: kolom `sumber` (Keduanya / Hanya Online / Hanya Offline) | ✗ | ✓ |
| Soal 2: sheet ringkasan omzet per produk | ✗ | ✓ |
| Soal 3: deteksi format tanggal per baris + mendukung yang sudah ISO | ✗ | ✓ |
| Soal 3: kolom `tanggal_kurs` (kurs tanggal berapa yang dipakai) | ✗ | ✓ |
| Soal 3: sheet ringkasan per mata uang | ✗ | ✓ |
| Validasi dengan `assert` | Soal 3 saja | Soal 2 & 3 |
| **Hasil angka akhir** | **Sama** | **Sama** |
