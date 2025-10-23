import os
import math
import logging
import json
import random
from datetime import datetime, time
import pytz

# Import library bot telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# --- KONFIGURASI ---
TELEGRAM_API_TOKEN = "7983435378:AAGHAxg8N9ydVHHiPU0LvnVgvlRTF8x-SYE" # Ganti dengan token Anda
DATA_FILE = "dompet.json"
QRIS_IMAGE_FILE = "qris.jpg" 

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- State untuk ConversationHandler ---
# Dompet
PEMASUKAN_AMOUNT, PEMASUKAN_KETERANGAN, PENGELUARAN_AMOUNT, PENGELUARAN_KETERANGAN, KONFIRMASI_HAPUS = range(10, 15)

# Kalkulator Target
(
    PILIH_UNIT, JUMLAH_PERIODE, HARGA_PRODUK, HARGA_JUAL, BIAYA_VARIABEL_LAIN,
    BIAYA_OPERASIONAL_UTAMA, POTONGAN_PLATFORM_TYPE, POTONGAN_PLATFORM_VALUE,
    BIAYA_OPERASIONAL_LAIN, TARGET_LABA,
) = range(10)


# --- FUNGSI DATA JSON ---
def load_data():
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=4)

# --- FUNGSI BANTUAN ---
def reset_notification_state(user_id: str):
    data = load_data()
    user_id_str = str(user_id)
    if data.get(user_id_str, {}).get("menunggu_input_notif"):
        logger.info(f"Mereset status notifikasi untuk user {user_id_str}")
        data[user_id_str]["menunggu_input_notif"] = False
        save_data(data)
        
def get_main_keyboard():
    # --- PERUBAHAN NAMA TOMBOL ---
    keyboard = [
        [KeyboardButton("📊 Kalkulasi Target"), KeyboardButton("💰 Dompet Saya")],
        [KeyboardButton("👑 Sultan"), KeyboardButton("ℹ️ About")], # Tombol Bantuan diubah
        [KeyboardButton("✨ Mulai / Restart")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- FUNGSI BARU: Mendapatkan Ringkasan Harian ---
def dapatkan_ringkasan_harian(user_id: str) -> str:
    """Menghitung dan memformat total pemasukan/pengeluaran untuk hari ini."""
    data = load_data()
    user_id_str = str(user_id)
    transactions = data.get(user_id_str, {}).get("transactions", [])
    
    pemasukan_hari_ini = 0
    pengeluaran_hari_ini = 0
    today = datetime.now(pytz.timezone("Asia/Jakarta")).date()

    for t in transactions:
        t_date = datetime.fromisoformat(t["timestamp"]).date()
        if t_date == today:
            if t["type"] == "pemasukan":
                pemasukan_hari_ini += t["amount"]
            elif t["type"] == "pengeluaran":
                pengeluaran_hari_ini += t["amount"]
    
    ringkasan = (f"\n\n*📊 Ringkasan Hari Ini:*\n"
                 f"Pemasukan: `Rp {pemasukan_hari_ini:,.0f}`\n"
                 f"Pengeluaran: `Rp {pengeluaran_hari_ini:,.0f}`")
    return ringkasan

# --- FUNGSI-FUNGSI UTAMA BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    reset_notification_state(user.id)
    chat_id = update.effective_chat.id
    
    data = load_data()
    user_id_str = str(user.id)
    if user_id_str not in data:
        data[user_id_str] = {"chat_id": chat_id, "transactions": [], "menunggu_input_notif": False}
        save_data(data)
    
    if update.callback_query:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"<b>Selamat Datang di Kaltain Bot, {user.mention_html()}!</b>\n\nSilakan pilih menu di bawah.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

# --- FUNGSI BANTUAN DIUBAH MENJADI ABOUT ---
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_notification_state(update.effective_user.id)
    
    about_text = (
        "ℹ️ *Tentang Kaltain Bot*\n\n"
        "Halo! Saya adalah Kaltain Bot, asisten pribadi Anda untuk mengelola target bisnis dan keuangan harian.\n\n"
        "Berikut adalah fungsi-fungsi utama yang bisa saya lakukan:\n\n"
        "--- \n\n"
        "📊 **Kalkulasi Target**\n"
        "Fitur ini membantu Anda menghitung target penjualan yang harus dicapai untuk mendapatkan laba bersih yang diinginkan. Saya akan menanyakan beberapa hal seperti:\n"
        "- Periode target (Bulan/Tahun)\n"
        "- Harga modal & harga jual produk\n"
        "- Biaya variabel & operasional\n"
        "- Potongan platform (jika ada)\n"
        "- Target laba bersih Anda\n\n"
        "Setelah itu, saya akan memberikan laporan lengkap mengenai total produk yang harus dijual, rata-rata penjualan harian, hingga proyeksi laba.\n\n"
        "--- \n\n"
        "💰 **Dompet Saya**\n"
        "Gunakan fitur ini untuk mencatat keuangan pribadi atau usaha Anda dengan mudah.\n"
        "- *Tambah Pemasukan/Pengeluaran*: Catat setiap transaksi lengkap dengan keterangannya.\n"
        "- *Ringkasan Otomatis*: Setelah mencatat, Anda akan langsung melihat total pemasukan & pengeluaran *hari ini*.\n"
        "- *Lihat Riwayat*: Lihat 10 transaksi terakhir. Anda bisa memfilternya berdasarkan (Semua, Pemasukan, Pengeluaran).\n"
        "- *Hapus Data*: Opsi untuk mereset seluruh data transaksi Anda.\n\n"
        "--- \n\n"
        "👑 **Menu Sultan**\n"
        "Menu ini didedikasikan bagi Anda yang ingin memberikan dukungan (donasi) untuk pengembangan dan pemeliharaan bot ini agar terus lebih baik.\n\n"
        "--- \n\n"
        "🔔 **Pengingat Harian**\n"
        "Saya akan mengirimkan notifikasi pengingat secara berkala untuk membantu Anda disiplin dalam mencatat keuangan setiap hari.\n\n"
        "--- \n\n"
        "Untuk memulai ulang atau membatalkan proses, tekan tombol *✨ Mulai / Restart*.\n\n"
        "👨‍💻 *Builder*: Itsbad"
    )
    
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def sultan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_notification_state(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    pesan_sultan = (
        "✨ *Sedekah tidak akan mengurangi hartamu.*\n\n"
        "Bagi kamu yang ingin memberikan dukungan untuk pengembangan bot ini, sekecil apapun akan sangat berarti. Semoga rezekimu dilancarkan dan segala urusanmu dipermudah. Aamiin.\n\n"
        "Silakan pindai QRIS di atas untuk berdonasi.\n\n"
        "👨‍💻 Builder: `Itsbad`"
    )

    try:
        with open(QRIS_IMAGE_FILE, 'rb') as photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=pesan_sultan,
                parse_mode='Markdown'
            )
    except FileNotFoundError:
        logger.error(f"File {QRIS_IMAGE_FILE} tidak ditemukan!")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Maaf, file gambar '{QRIS_IMAGE_FILE}' tidak ditemukan. Harap hubungi admin."
        )

# --- FITUR KALKULASI TARGET ---
async def kalkulasi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_notification_state(update.effective_user.id)
    reply_keyboard = [["Bulan", "Tahun"]]
    await update.message.reply_text("Baik, mari mulai kalkulasi target.\n\nPilih satuan periode waktu:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),)
    return PILIH_UNIT
async def pilih_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pilihan = update.message.text.lower()
    context.user_data["unit"] = pilihan
    await update.message.reply_text(f"Anda memilih: <b>{pilihan.capitalize()}</b>\n\nBerapa jumlah {pilihan} yang Anda targetkan? (Contoh: 1)", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
    return JUMLAH_PERIODE
async def jumlah_periode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["jumlah_periode"] = int(update.message.text)
        await update.message.reply_text("Berapa harga beli produk (modal) per item?")
        return HARGA_PRODUK
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return JUMLAH_PERIODE
async def harga_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["harga_produk"] = float(update.message.text)
        await update.message.reply_text("Berapa harga jual produk per item?")
        return HARGA_JUAL
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return HARGA_PRODUK
async def harga_jual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["harga_jual"] = float(update.message.text)
        await update.message.reply_text("Berapa biaya variabel lain per produk? (Contoh: packaging)")
        return BIAYA_VARIABEL_LAIN
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return HARGA_JUAL
async def biaya_variabel_lain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_variabel_lain"] = float(update.message.text)
        await update.message.reply_text("Berapa total biaya operasional utama bulanan? (Contoh: gaji, sewa)")
        return BIAYA_OPERASIONAL_UTAMA
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return BIAYA_VARIABEL_LAIN
async def biaya_operasional_utama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_operasional_utama"] = float(update.message.text)
        reply_keyboard = [["Persen (%)", "Nominal (Rp)"]]
        await update.message.reply_text("Untuk potongan platform, jenisnya apa?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),)
        return POTONGAN_PLATFORM_TYPE
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return BIAYA_OPERASIONAL_UTAMA
async def potongan_platform_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pilihan = update.message.text.lower()
    context.user_data["platform_fee_type"] = pilihan
    if "persen" in pilihan:
        await update.message.reply_text("Berapa persen (%) potongan platform?", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Berapa nominal (Rp) potongan platform per produk?", reply_markup=ReplyKeyboardRemove())
    return POTONGAN_PLATFORM_VALUE
async def potongan_platform_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["platform_fee_value"] = float(update.message.text)
        await update.message.reply_text("Apakah ada biaya operasional tetap lainnya per bulan? (Jika tidak ada, isi 0)")
        return BIAYA_OPERASIONAL_LAIN
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return POTONGAN_PLATFORM_VALUE
async def biaya_operasional_lain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_operasional_lain"] = float(update.message.text)
        await update.message.reply_text("Terakhir, berapa target laba bersih yang Anda inginkan?")
        return TARGET_LABA
    except ValueError:
        await update.message.reply_text("❌ Harap masukkan angka saja.")
        return BIAYA_OPERASIONAL_LAIN
async def target_laba(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["target_laba_bersih"] = float(update.message.text)
        data = context.user_data
        if data["unit"] == "bulan":
            jumlah_hari = data["jumlah_periode"] * 30
            periode_teks = f"{data['jumlah_periode']} Bulan ({jumlah_hari} hari)"
        else: # tahun
            jumlah_hari = data["jumlah_periode"] * 365
            periode_teks = f"{data['jumlah_periode']} Tahun ({jumlah_hari} hari)"
        potongan_platform_per_item = (data["platform_fee_value"] / 100) * data["harga_jual"] if "persen" in data["platform_fee_type"] else data["platform_fee_value"]
        laba_bersih_per_item = data["harga_jual"] - data["harga_produk"] - potongan_platform_per_item - data["biaya_variabel_lain"]
        total_biaya_tetap = (data["biaya_operasional_utama"] + data["biaya_operasional_lain"]) * (jumlah_hari / 30)
        if laba_bersih_per_item <= 0:
            await update.message.reply_text("❗️ TARGET TIDAK MUNGKIN TERCAPAI\nPastikan harga jual lebih tinggi dari total biaya per produk.", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END
        pembilang = data["target_laba_bersih"] + total_biaya_tetap
        total_produk_terjual = math.ceil(pembilang / laba_bersih_per_item) if laba_bersih_per_item > 0 else 0
        produk_per_hari = math.ceil(total_produk_terjual / jumlah_hari) if jumlah_hari > 0 else 0
        produk_untuk_biaya = math.ceil(total_biaya_tetap / laba_bersih_per_item) if laba_bersih_per_item > 0 else 0
        produk_untuk_laba = total_produk_terjual - produk_untuk_biaya
        estimasi_laba_aktual = (laba_bersih_per_item * total_produk_terjual) - total_biaya_tetap
        
        report_text = (f"HASIL PERHITUNGAN TARGET\n"
                       f"═════════════════════════════\n"
                       f"Periode : {periode_teks}\n"
                       f"Target Laba : Rp {data['target_laba_bersih']:,.0f}\n"
                       f"═════════════════════════════\n\n"
                       f"TARGET PENJUALAN\n"
                       f"Total Produk : {total_produk_terjual} unit\n"
                       f"Rata-rata : {produk_per_hari} unit / hari\n\n"
                       f"ANALISIS LABA PER PRODUK\n"
                       f"Harga Jual : Rp {data['harga_jual']:,.0f}\n"
                       f"(-) Modal Beli : Rp {data['harga_produk']:,.0f}\n"
                       f"(-) Potongan Platform : Rp {potongan_platform_per_item:,.0f}\n"
                       f"(-) Biaya Variabel Lain : Rp {data['biaya_variabel_lain']:,.0f}\n"
                       f"--------------------------------------------------\n"
                       f"Laba Bersih/Produk : Rp {laba_bersih_per_item:,.0f}\n\n"
                       f"ALOKASI PENJUALAN\n"
                       f"Untuk BEP (Biaya Tetap) : {produk_untuk_biaya} unit\n"
                       f"Untuk Target Laba : {produk_untuk_laba} unit\n"
                       f"--------------------------------------------------\n"
                       f"Total Produk Dijual : {total_produk_terjual} unit\n\n"
                       f"PROYEKSI FINAL\n"
                       f"Target Laba Awal : Rp {data['target_laba_bersih']:,.0f}\n"
                       f"Estimasi Laba Aktual : Rp {estimasi_laba_aktual:,.0f}")
        
        await update.message.reply_text(
            f"```\n{report_text}\n```",
            parse_mode="MarkdownV2",
            reply_markup=get_main_keyboard()
        )

        context.user_data.clear()
        return ConversationHandler.END
    except (ValueError, ZeroDivisionError) as e:
        logger.error(f"Error pada kalkulasi target: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan dalam perhitungan. Pastikan semua input benar.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

async def restart_percakapan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

# --- FITUR DOMPET SAYA ---
async def dompet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_notification_state(update.effective_user.id)
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    data = load_data()
    if update.callback_query:
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
    if user_id not in data:
        data[user_id] = {"chat_id": chat_id, "transactions": [], "menunggu_input_notif": False}
        save_data(data)
    user_data = data[user_id]
    transactions = user_data.get("transactions", [])
    saldo, pemasukan_bulan_ini, pengeluaran_bulan_ini = 0, 0, 0
    now = datetime.now(pytz.timezone("Asia/Jakarta"))
    for t in transactions:
        t_date = datetime.fromisoformat(t["timestamp"])
        if t["type"] == "pemasukan":
            saldo += t["amount"]
            if t_date.year == now.year and t_date.month == now.month:
                pemasukan_bulan_ini += t["amount"]
        elif t["type"] == "pengeluaran":
            saldo -= t["amount"]
            if t_date.year == now.year and t_date.month == now.month:
                pengeluaran_bulan_ini += t["amount"]
    
    pesan = (f"💰 *Dompet Saya*\n\n"
             f"Saldo Saat Ini: *Rp {saldo:,.0f}*\n"
             f"Pemasukan Bulan Ini: `Rp {pemasukan_bulan_ini:,.0f}`\n"
             f"Pengeluaran Bulan Ini: `Rp {pengeluaran_bulan_ini:,.0f}`")
             
    keyboard_inline = [
        [InlineKeyboardButton("➕ Tambah Pemasukan", callback_data="pemasukan_baru")],
        [InlineKeyboardButton("➖ Tambah Pengeluaran", callback_data="pengeluaran_baru")],
        [InlineKeyboardButton("📜 Lihat Riwayat", callback_data="lihat_riwayat_semua")],
        [InlineKeyboardButton("🗑️ Hapus Seluruh Data", callback_data="hapus_data_konfirmasi")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard_inline)
    if update.callback_query and update.callback_query.data == "kembali_ke_dompet":
         await update.callback_query.edit_message_text(text=pesan, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text=pesan, parse_mode='Markdown', reply_markup=reply_markup)

# FUNGSI YANG DIMODIFIKASI
async def lihat_riwayat_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    filter_type = query.data.split('_')[-1] # 'semua', 'pemasukan', 'pengeluaran'
    user_id = str(update.effective_user.id)
    data = load_data()
    
    all_transactions = data.get(user_id, {}).get("transactions", [])
    all_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    transactions_to_display = []
    
    # --- MODIFIKASI JUDUL ---
    if filter_type == "semua":
        transactions_to_display = all_transactions[:10] # Hanya 10 terakhir untuk tampilan awal
        judul_filter = "Semua (10 Terakhir)"
    else:
        # Filter berdasarkan tipe dan ambil 10 terakhir
        transactions_to_display = [t for t in all_transactions if t.get('type') == filter_type][:10]
        judul_filter = f"{filter_type.capitalize()} (10 Terakhir)"

    pesan_riwayat = f"📜 *Riwayat Transaksi ({judul_filter})*\n\n"
    
    if not transactions_to_display:
        pesan_riwayat += "_Tidak ada riwayat transaksi untuk kategori ini._"
    else:
        for t in transactions_to_display:
            t_date = datetime.fromisoformat(t["timestamp"]).strftime("%d/%m/%y %H:%M")
            t_type = "➕" if t["type"] == "pemasukan" else "➖"
            keterangan = t.get("description", "Tanpa Keterangan")
            pesan_riwayat += f"`{t_type} Rp {t['amount']:,.0f}` - *{keterangan}*\n`({t_date})`\n"

    # --- MODIFIKASI Keyboard ---
    keyboard_inline = [
        [ # Tombol filter
            InlineKeyboardButton("Semua", callback_data="lihat_riwayat_semua"),
            InlineKeyboardButton("Pemasukan", callback_data="lihat_riwayat_pemasukan"),
            InlineKeyboardButton("Pengeluaran", callback_data="lihat_riwayat_pengeluaran"),
        ]
    ]
    
    # --- LOGIKA BARU: Tambahkan tombol arsip bulanan HANYA jika filternya "semua" ---
    if filter_type == "semua":
        pesan_riwayat += "\n*Arsip Bulanan:*" # Tambahkan sub-judul
        
        unique_months = {} # Gunakan dict untuk menyimpan { (tahun, bulan): "Nama Bulan Tahun" }
        # Format nama bulan pendek
        nama_bulan_short = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        
        for t in all_transactions: # Pindai SEMUA transaksi
            t_date = datetime.fromisoformat(t["timestamp"])
            month_key = (t_date.year, t_date.month)
            if month_key not in unique_months:
                # Buat nama tombol, e.g., "Okt 2025"
                month_name = f"{nama_bulan_short[t_date.month - 1]} {t_date.year}"
                unique_months[month_key] = month_name
        
        month_buttons_rows = []
        # Urutkan bulan dari yang terbaru (karena key-nya (tahun, bulan))
        sorted_months_keys = sorted(unique_months.keys(), reverse=True)
        
        row = []
        for month_key in sorted_months_keys:
            year, month = month_key
            month_name = unique_months[month_key]
            callback_data = f"riwayat_bulan_{year}_{month}"
            
            row.append(InlineKeyboardButton(month_name, callback_data=callback_data))
            
            if len(row) == 3: # Buat 3 tombol per baris
                month_buttons_rows.append(row)
                row = []
        if row: # Tambahkan sisa tombol jika ada
            month_buttons_rows.append(row)
        
        # Tambahkan baris tombol bulan ke keyboard utama
        keyboard_inline.extend(month_buttons_rows)
    
    # Tombol Kembali ke Dompet (selalu ada di paling bawah)
    keyboard_inline.append([InlineKeyboardButton("⬅️ Kembali ke Dompet", callback_data="kembali_ke_dompet")])
    # --- Akhir Modifikasi Keyboard ---

    reply_markup = InlineKeyboardMarkup(keyboard_inline)
    # Gunakan edit_message_text untuk memperbarui tampilan
    await query.edit_message_text(text=pesan_riwayat, parse_mode='Markdown', reply_markup=reply_markup)


# --- FUNGSI BARU: Untuk menangani tampilan arsip bulanan ---
async def lihat_riwayat_bulanan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    # Ekstrak tahun dan bulan dari callback_data, e.g., "riwayat_bulan_2025_10"
    try:
        _, _, year_str, month_str = query.data.split('_')
        year = int(year_str)
        month = int(month_str)
    except (ValueError, IndexError):
        await query.edit_message_text("Error: Data riwayat bulanan tidak valid.")
        return

    user_id = str(update.effective_user.id)
    data = load_data()
    all_transactions = data.get(user_id, {}).get("transactions", [])
    
    monthly_transactions = []
    total_pemasukan = 0
    total_pengeluaran = 0
    
    # Filter transaksi HANYA untuk bulan dan tahun yang dipilih
    for t in all_transactions:
        t_date = datetime.fromisoformat(t["timestamp"])
        if t_date.year == year and t_date.month == month:
            monthly_transactions.append(t)
            if t["type"] == "pemasukan":
                total_pemasukan += t["amount"]
            elif t["type"] == "pengeluaran":
                total_pengeluaran += t["amount"]
    
    # Urutkan dari yang terbaru di bulan itu
    monthly_transactions.sort(key=lambda x: x["timestamp"], reverse=True)
    
    # Nama bulan lengkap untuk judul
    nama_bulan_full = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    judul_bulan = f"{nama_bulan_full[month - 1]} {year}"
    
    pesan_riwayat = f"📜 *Arsip Transaksi: {judul_bulan}*\n\n"
    
    if not monthly_transactions:
        pesan_riwayat += "_Tidak ada transaksi di bulan ini._"
    else:
        for t in monthly_transactions:
            # Format tanggal yang lebih ringkas untuk tampilan bulanan
            t_date = datetime.fromisoformat(t["timestamp"]).strftime("%d/%m %H:%M")
            t_type = "➕" if t["type"] == "pemasukan" else "➖"
            keterangan = t.get("description", "Tanpa Keterangan")
            # Format sedikit berbeda agar lebih rapi
            pesan_riwayat += f"`{t_date}` | `{t_type} Rp {t['amount']:,.0f}`\n*{keterangan}*\n\n"
    
    # Tambahkan ringkasan bulanan
    pesan_riwayat += "--- \n"
    pesan_riwayat += f"📊 *Ringkasan Bulan Ini:*\n"
    pesan_riwayat += f"Pemasukan: `Rp {total_pemasukan:,.0f}`\n"
    pesan_riwayat += f"Pengeluaran: `Rp {total_pengeluaran:,.0f}`\n"
    pesan_riwayat += f"Arus Kas: `Rp {total_pemasukan - total_pengeluaran:,.0f}`"

    keyboard_inline = [
        # Tombol ini akan mengembalikan user ke tampilan riwayat (yang 10 terakhir + tombol bulan)
        [InlineKeyboardButton("⬅️ Kembali ke Riwayat", callback_data="lihat_riwayat_semua")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard_inline)
    
    await query.edit_message_text(text=pesan_riwayat, parse_mode='Markdown', reply_markup=reply_markup)


async def pemasukan_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Masukkan jumlah pemasukan baru:")
    return PEMASUKAN_AMOUNT

async def pemasukan_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Jumlah harus lebih dari 0.")
            return PEMASUKAN_AMOUNT
        context.user_data['pemasukan_amount'] = amount
        await update.message.reply_text("Sekarang, masukkan keterangannya (contoh: Gaji):")
        return PEMASUKAN_KETERANGAN
    except ValueError:
        await update.message.reply_text("Format salah. Harap masukkan angka saja.")
        return PEMASUKAN_AMOUNT

async def pemasukan_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount = context.user_data['pemasukan_amount']
    keterangan = update.message.text
    
    data = load_data()
    data[user_id]["transactions"].append({
        "type": "pemasukan", 
        "amount": amount, 
        "description": keterangan,
        "timestamp": datetime.now(pytz.timezone("Asia/Jakarta")).isoformat()
    })
    save_data(data)
    
    ringkasan_harian = dapatkan_ringkasan_harian(user_id)
    pesan_sukses = f"✅ Pemasukan sebesar Rp {amount:,.0f} dengan keterangan '{keterangan}' berhasil ditambahkan."
    await update.message.reply_text(f"{pesan_sukses}{ringkasan_harian}", parse_mode='Markdown')
    
    context.user_data.clear()
    await dompet(update, context) 
    return ConversationHandler.END

async def pengeluaran_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Masukkan jumlah pengeluaran baru:")
    return PENGELUARAN_AMOUNT

async def pengeluaran_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Jumlah harus lebih dari 0.")
            return PENGELUARAN_AMOUNT
        context.user_data['pengeluaran_amount'] = amount
        await update.message.reply_text("Sekarang, masukkan keterangannya (contoh: Beli Kopi):")
        return PENGELUARAN_KETERANGAN
    except ValueError:
        await update.message.reply_text("Format salah. Harap masukkan angka saja.")
        return PENGELUARAN_AMOUNT

async def pengeluaran_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    amount = context.user_data['pengeluaran_amount']
    keterangan = update.message.text
    
    data = load_data()
    data[user_id]["transactions"].append({
        "type": "pengeluaran", 
        "amount": amount, 
        "description": keterangan,
        "timestamp": datetime.now(pytz.timezone("Asia/Jakarta")).isoformat()
    })
    save_data(data)
    
    ringkasan_harian = dapatkan_ringkasan_harian(user_id)
    pesan_sukses = f"✅ Pengeluaran sebesar Rp {amount:,.0f} dengan keterangan '{keterangan}' berhasil ditambahkan."
    await update.message.reply_text(f"{pesan_sukses}{ringkasan_harian}", parse_mode='Markdown')
    
    context.user_data.clear()
    await dompet(update, context)
    return ConversationHandler.END

async def hapus_data_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="⚠️ *PERINGATAN*\nAnda yakin ingin menghapus seluruh data dompet? Ketik `YA` untuk konfirmasi.", parse_mode='Markdown')
    return KONFIRMASI_HAPUS

async def hapus_data_konfirmasi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.upper() == 'YA':
        user_id = str(update.effective_user.id)
        data = load_data()
        if user_id in data:
            data[user_id]["transactions"] = []
            save_data(data)
            await update.message.reply_text("🗑️ Seluruh data dompet Anda telah berhasil dihapus.")
    else:
        await update.message.reply_text("Aksi dibatalkan.")
    await dompet(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Aksi dibatalkan.")
    await start(update, context) 
    return ConversationHandler.END

# --- NOTIFIKASI & INPUT LANGSUNG ---
async def callback_notifikasi(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chat_ids_and_users = {user_info["chat_id"]: user_id for user_id, user_info in data.items() if "chat_id" in user_info}
    kata_kata = ["Ingat, jangan boros! Setiap rupiah yang kamu catat hari ini adalah investasi untuk ketenangan pikiranmu di masa depan.", "Menabung pangkal kaya, mencatat pangkal teratur. Sudahkah kamu mencatat keuanganmu hari ini untuk meraih impianmu?"]
    pesan_acak = random.choice(kata_kata)
    pesan_notif = f"🔔 Pengingat Keuangan:\n\n_{pesan_acak}_\n\nSilakan masukkan jumlah pemasukan sekarang (isi 0 jika tidak ada):"
    for chat_id, user_id in chat_ids_and_users.items():
        try:
            await context.bot.send_message(chat_id=chat_id, text=pesan_notif, parse_mode='Markdown')
            data[user_id]["menunggu_input_notif"] = True
        except Exception as e:
            logger.error(f"Gagal mengirim notifikasi ke {chat_id}: {e}")
    save_data(data)

async def handle_notif_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id in data and data[user_id].get("menunggu_input_notif"):
        try:
            amount = float(update.message.text)
            if amount == 0:
                await update.message.reply_text("Baik, pemasukan 0 dicatat sebagai pengingat.")
            elif amount < 0:
                await update.message.reply_text("Jumlah tidak boleh negatif.")
                return
            else:
                data[user_id]["transactions"].append({"type": "pemasukan", "amount": amount, "description": "Dari Notifikasi", "timestamp": datetime.now(pytz.timezone("Asia/Jakarta")).isoformat()})
                await update.message.reply_text(f"✅ Pemasukan sebesar Rp {amount:,.0f} berhasil ditambahkan.")
            data[user_id]["menunggu_input_notif"] = False
            save_data(data)
        except ValueError:
            await update.message.reply_text("Format salah. Harap masukkan angka saja untuk pemasukan dari notifikasi.")
        except Exception as e:
            logger.error(f"Error di handle_notif_input: {e}")
            data[user_id]["menunggu_input_notif"] = False
            save_data(data)

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()
    job_queue = application.job_queue
    
    universal_fallbacks = [
        MessageHandler(filters.Regex("^✨ Mulai / Restart$"), restart_percakapan),
        CommandHandler("start", restart_percakapan)
    ]

    kalkulasi_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Kalkulasi Target$"), kalkulasi)],
        states={
            PILIH_UNIT: [MessageHandler(filters.Regex("^(Bulan|Tahun)$"), pilih_unit)],
            JUMLAH_PERIODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, jumlah_periode)],
            HARGA_PRODUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, harga_produk)],
            HARGA_JUAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, harga_jual)],
            BIAYA_VARIABEL_LAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, biaya_variabel_lain)],
            BIAYA_OPERASIONAL_UTAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, biaya_operasional_utama)],
            POTONGAN_PLATFORM_TYPE: [MessageHandler(filters.Regex("^(Persen|Nominal)"), potongan_platform_type)],
            POTONGAN_PLATFORM_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, potongan_platform_value)],
            BIAYA_OPERASIONAL_LAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, biaya_operasional_lain)],
            TARGET_LABA: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_laba)],
        },
        fallbacks=universal_fallbacks,
        allow_reentry=True
    )

    pemasukan_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(pemasukan_start, pattern='^pemasukan_baru$')], 
        states={ 
            PEMASUKAN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pemasukan_amount)],
            PEMASUKAN_KETERANGAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pemasukan_keterangan)]
        }, 
        fallbacks=[CallbackQueryHandler(cancel, pattern='^kembali_ke_dompet$')] + universal_fallbacks
    )
    pengeluaran_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(pengeluaran_start, pattern='^pengeluaran_baru$')], 
        states={ 
            PENGELUARAN_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pengeluaran_amount)],
            PENGELUARAN_KETERANGAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pengeluaran_keterangan)]
        }, 
        fallbacks=[CallbackQueryHandler(cancel, pattern='^kembali_ke_dompet$')] + universal_fallbacks
    )
    hapus_data_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(hapus_data_start, pattern='^hapus_data_konfirmasi$')], 
        states={ 
            KONFIRMASI_HAPUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, hapus_data_konfirmasi)] 
        }, 
        fallbacks=[CallbackQueryHandler(cancel, pattern='^kembali_ke_dompet$')] + universal_fallbacks
    )
    
    application.add_handler(kalkulasi_conv)
    application.add_handler(pemasukan_conv)
    application.add_handler(pengeluaran_conv)
    application.add_handler(hapus_data_conv)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^✨ Mulai / Restart$"), start))
    
    # --- HANDLER BANTUAN DIUBAH MENJADI ABOUT ---
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ About$"), about))
    application.add_handler(CommandHandler("about", about))
    
    application.add_handler(MessageHandler(filters.Regex("^💰 Dompet Saya$"), dompet))
    application.add_handler(CommandHandler("dompet", dompet))
    application.add_handler(CommandHandler("sultan", sultan_menu))
    application.add_handler(MessageHandler(filters.Regex("^👑 Sultan$"), sultan_menu))
    
    # --- HANDLER BARU UNTUK RIWAYAT ---
    application.add_handler(CallbackQueryHandler(lihat_riwayat_filter, pattern='^lihat_riwayat_'))
    application.add_handler(CallbackQueryHandler(lihat_riwayat_bulanan, pattern='^riwayat_bulan_'))
    # --- AKHIR HANDLER BARU ---
    
    application.add_handler(CallbackQueryHandler(dompet, pattern='^kembali_ke_dompet$'))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notif_input), group=1)

    timezone_jakarta = pytz.timezone("Asia/Jakarta")
    for hour in range(8, 23):
        job_queue.run_daily(callback_notifikasi, time=time(hour=hour, minute=0, tzinfo=timezone_jakarta))

    print("Bot Kaltain (v13 - Arsip Bulanan) sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    try:
        import pytz
    except ImportError:
        print("Menginstall library 'pytz'...")
        os.system('pip install pytz')
    main()

