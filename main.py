import os
import math
import logging

# Import library bot telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# --- KONFIGURASI ---
TELEGRAM_API_TOKEN = "7983435378:AAGHAxg8N9ydVHHiPU0LvnVgvlRTF8x-SYE"

# Aktifkan logging untuk melihat error
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Tahapan baru dalam percakapan
(
    PILIH_UNIT,
    JUMLAH_PERIODE,
    HARGA_PRODUK,
    HARGA_JUAL,
    BIAYA_VARIABEL_LAIN,
    BIAYA_OPERASIONAL_UTAMA,
    POTONGAN_PLATFORM_TYPE,
    POTONGAN_PLATFORM_VALUE,
    BIAYA_OPERASIONAL_LAIN,
    TARGET_LABA,
) = range(10)


# --- FUNGSI PERINTAH BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Halo {user.mention_html()}! 👋\n\n"
        "Saya adalah Kaltain Bot, asisten Anda untuk menghitung target penjualan.\n\n"
        "Kirim /kalkulasi untuk memulai perhitungan baru.\n"
        "Kirim /bantuan untuk melihat info bantuan."
    )

async def bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Cara Penggunaan Bot:\n\n"
        "1. Kirim perintah /kalkulasi.\n"
        "2. Bot akan menanyakan data satu per satu.\n"
        "3. Jawab setiap pertanyaan dengan angka yang sesuai.\n"
        "4. Setelah semua data terisi, bot akan mengirimkan laporan hasil perhitungan.\n\n"
        "Untuk membatalkan perhitungan di tengah jalan, kirim /batal."
    )

async def kalkulasi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Bulan", "Tahun"]]
    await update.message.reply_text(
        "Mari kita mulai! Saya akan menanyakan beberapa data.\n\n"
        "Pertama, pilih satuan periode waktu untuk target Anda.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Pilih Bulan atau Tahun?"
        ),
    )
    return PILIH_UNIT


# --- FUNGSI-FUNGSI DALAM ALUR PERCAKAPAN ---

async def pilih_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pilihan = update.message.text.lower()
    context.user_data["unit"] = pilihan
    await update.message.reply_text(
        f"Anda memilih: {pilihan.capitalize()}\n\n"
        f"Sekarang, masukkan berapa jumlah {pilihan} yang Anda targetkan? (Contoh: 1)",
        reply_markup=ReplyKeyboardRemove(),
    )
    return JUMLAH_PERIODE

async def jumlah_periode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["jumlah_periode"] = int(update.message.text)
        await update.message.reply_text("Berapa harga beli produk (modal) per item?")
        return HARGA_PRODUK
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return JUMLAH_PERIODE
        
async def harga_produk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["harga_produk"] = float(update.message.text)
        await update.message.reply_text("Berapa harga jual produk per item?")
        return HARGA_JUAL
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return HARGA_PRODUK

async def harga_jual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["harga_jual"] = float(update.message.text)
        await update.message.reply_text("Berapa biaya variabel lain per produk? (Contoh: packaging, stiker, dll)")
        return BIAYA_VARIABEL_LAIN
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return HARGA_JUAL

async def biaya_variabel_lain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_variabel_lain"] = float(update.message.text)
        await update.message.reply_text("Berapa total biaya operasional utama bulanan? (Contoh: gaji, sewa, listrik)")
        return BIAYA_OPERASIONAL_UTAMA
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return BIAYA_VARIABEL_LAIN

async def biaya_operasional_utama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_operasional_utama"] = float(update.message.text)
        reply_keyboard = [["Persen (%)", "Nominal (Rp)"]]
        await update.message.reply_text(
            "Untuk potongan platform (misal: Tokopedia, Shopee), jenisnya apa?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return POTONGAN_PLATFORM_TYPE
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
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
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return POTONGAN_PLATFORM_VALUE

async def biaya_operasional_lain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["biaya_operasional_lain"] = float(update.message.text)
        await update.message.reply_text("Terakhir, berapa target laba bersih yang Anda inginkan?")
        return TARGET_LABA
    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return BIAYA_OPERASIONAL_LAIN

async def target_laba(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["target_laba_bersih"] = float(update.message.text)
        data = context.user_data
        
        # --- Proses Kalkulasi ---
        if data["unit"] == "bulan":
            jumlah_hari = data["jumlah_periode"] * 30
            periode_teks = f"{data['jumlah_periode']} Bulan ({jumlah_hari} hari)"
        else:
            jumlah_hari = data["jumlah_periode"] * 365
            periode_teks = f"{data['jumlah_periode']} Tahun ({jumlah_hari} hari)"
        
        potongan_platform_per_item = 0
        if "persen" in data["platform_fee_type"]:
            potongan_platform_per_item = (data["platform_fee_value"] / 100) * data["harga_jual"]
        else:
            potongan_platform_per_item = data["platform_fee_value"]

        modal_dan_biaya_per_produk = data["harga_produk"] + data["biaya_variabel_lain"] + potongan_platform_per_item
        laba_bersih_per_item = data["harga_jual"] - modal_dan_biaya_per_produk
        total_biaya_tetap = (data["biaya_operasional_utama"] + data["biaya_operasional_lain"]) * (jumlah_hari / 30)
        
        total_produk_terjual = 0
        if laba_bersih_per_item <= 0:
            total_produk_terjual = -1
        else:
            pembilang = data["target_laba_bersih"] + total_biaya_tetap
            total_produk_terjual = math.ceil(pembilang / laba_bersih_per_item)

        produk_per_hari = 0
        if total_produk_terjual > 0 and jumlah_hari > 0:
            produk_per_hari = math.ceil(total_produk_terjual / jumlah_hari)
            
        # --- Membuat Teks Laporan ---
        report_text = "╔═════════════════════════════╗\n"
        report_text += "║     HASIL PERHITUNGAN TARGET     ║\n"
        report_text += "╚═════════════════════════════╝\n\n"
        
        if total_produk_terjual == -1:
            report_text += "❗️ *TARGET TIDAK MUNGKIN TERCAPAI*\nPastikan harga jual lebih tinggi dari total modal dan biaya per produk."
        else:
            report_text += "🎯 *RINGKASAN*\n"
            report_text += f"├─ Periode: {periode_teks}\n"
            report_text += f"├─ Target Laba: Rp {data['target_laba_bersih']:,.0f}\n"
            report_text += f"└─ Penjualan: *{total_produk_terjual} Produk* (≈ {produk_per_hari} / hari)\n\n"
            
            report_text += "📈 *RINCIAN PERHITUNGAN*\n\n"
            
            report_text += "*1. Analisis Laba per Produk*\n"
            report_text += f"  Harga Jual: Rp {data['harga_jual']:,.0f}\n"
            report_text += f"  (-) Modal Beli: Rp {data['harga_produk']:,.0f}\n"
            report_text += f"  (-) Potongan Platform: Rp {potongan_platform_per_item:,.0f}\n"
            report_text += f"  (-) Biaya Variabel Lain: Rp {data['biaya_variabel_lain']:,.0f}\n"
            report_text += "  ---------------------------------------\n"
            report_text += f"  ✅ *Laba Bersih / Produk: Rp {laba_bersih_per_item:,.0f}*\n\n"
            
            produk_untuk_biaya = math.ceil(total_biaya_tetap / laba_bersih_per_item) if laba_bersih_per_item > 0 else 0
            produk_untuk_laba = math.ceil(data['target_laba_bersih'] / laba_bersih_per_item) if laba_bersih_per_item > 0 else 0
            
            report_text += "*2. Analisis Biaya Tetap*\n"
            report_text += f"  Operasional Utama: Rp {data['biaya_operasional_utama']:,.0f}\n"
            report_text += f"  Operasional Lainnya: Rp {data['biaya_operasional_lain']:,.0f}\n"
            report_text += "  ---------------------------------------\n"
            report_text += f"  💵 *Total Biaya Tetap: Rp {total_biaya_tetap:,.0f}*\n\n"

            report_text += "*3. Alokasi Penjualan*\n"
            report_text += f"  Untuk Tutup Biaya Tetap: *{produk_untuk_biaya} unit*\n"
            report_text += f"  Untuk Capai Target Laba: *{produk_untuk_laba} unit*\n"
            report_text += "  ---------------------------------------\n"
            report_text += f"  📦 *TOTAL PRODUK DIJUAL: {total_produk_terjual} unit*\n\n"
            
            estimasi_laba_aktual = (laba_bersih_per_item * total_produk_terjual) - total_biaya_tetap
            report_text += "*4. Proyeksi Final*\n"
            report_text += f"  Target Laba Awal: Rp {data['target_laba_bersih']:,.0f}\n"
            report_text += f"  ✨ *Estimasi Laba Aktual: Rp {estimasi_laba_aktual:,.0f}*"

        await update.message.reply_text(report_text, parse_mode='Markdown')
        context.user_data.clear()
        return ConversationHandler.END

    except (ValueError):
        await update.message.reply_text("Harap masukkan angka saja. Coba lagi.")
        return TARGET_LABA

async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Perhitungan dibatalkan.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- FUNGSI UTAMA UNTUK MENJALANKAN BOT ---

def main() -> None:
    application = Application.builder().token(TELEGRAM_API_TOKEN).job_queue(None).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("kalkulasi", kalkulasi)],
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
        fallbacks=[CommandHandler("batal", batal)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bantuan", bantuan))
    application.add_handler(conv_handler)

    print("Bot Kaltain versi lengkap sedang berjalan... Tekan Ctrl+C untuk berhenti.")
    application.run_polling()


if __name__ == "__main__":
    try:
        import requests
        import pytz
    except ImportError:
        print("Memeriksa & menginstall library yang dibutuhkan...")
        os.system('pip install python-telegram-bot "httpx<0.26.0" pytz --upgrade')
        print("Instalasi selesai. Silakan jalankan kembali program.")
        
    main()
