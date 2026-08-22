"""GenZ Expression purpose-first Experience catalog.
Kept independent from the SQL schema so new visual styles do not require DB changes.
"""
CATEGORIES = {
    'story': {
        'title': '📖 STORY', 'desc': 'Buat cerita interaktif yang terasa seperti film pendek.',
        'styles': {
            'midnight': ('🌙 Midnight Cinema', 'Cinematic gelap, foto besar, chapter hidup, dan transisi film.'),
            'journal': ('📓 Digital Journal', 'Jurnal modern dengan timeline, catatan, dan foto yang rapi.'),
            'film': ('🎞️ Film Diary', 'Nuansa film dengan frame, grain, dan scene yang berganti halus.'),
        },
        'expiration': 90,
    },
    'letter': {
        'title': '💌 LETTER', 'desc': 'Kirim pesan personal yang dibuka dan dirasakan seperti surat.',
        'styles': {
            'secret': ('🔐 Secret Letter', 'Surat rahasia dengan reveal bertahap.'),
            'midnight': ('🌙 Midnight Message', 'Pesan intim dengan nuansa malam dan minimal.'),
            'postcard': ('📮 Digital Postcard', 'Pesan singkat seperti kartu pos digital modern.'),
        },
        'expiration': 30,
    },
    'event': {
        'title': '🎉 EVENT', 'desc': 'Buat undangan atau halaman acara yang informatif dan interaktif.',
        'styles': {
            'neon': ('⚡ Neon Party', 'Enerjik, glow, countdown, dan tombol RSVP yang menonjol.'),
            'luxury': ('✨ Luxury Event', 'Elegan, bersih, dan premium dengan tipografi besar.'),
            'minimal': ('◻️ Minimal Invite', 'Minimal, cepat dibaca, fokus ke detail acara.'),
        },
        'expiration': 14,
    },
    'memories': {
        'title': '📸 MEMORIES', 'desc': 'Simpan dan jelajahi foto sebagai arsip digital yang hidup.',
        'styles': {
            'archive': ('🗂️ Photo Archive', 'Arsip foto modern dengan grid dinamis dan fullscreen viewer.'),
            'filmroll': ('🎞️ Film Roll', 'Kesan roll film dengan urutan foto yang terasa seperti kamera.'),
            'wall': ('🧩 Memory Wall', 'Dinding foto asimetris yang otomatis menyesuaikan jumlah foto.'),
        },
        'expiration': 90,
    },
    'play': {
        'title': '🎮 PLAY', 'desc': 'Buat Experience yang mengajak orang bermain dan ikut berinteraksi.',
        'styles': {
            'quizshow': ('🏆 Quiz Show', 'Quiz dengan score, submit sekali, dan leaderboard.'),
            'whoknows': ('🧠 Who Knows Me?', 'Tebak seberapa kenal peserta dengan pembuat Experience.'),
            'random': ('🎲 Random Challenge', 'Tantangan interaktif dengan konsep acak.'),
        },
        'expiration': 30,
    },
}

HELP = {
    'quick': ('✨ Quick Create', 'Cara cepat. Isi bagian penting saja; layout, animasi, dan detail visual diatur otomatis oleh template.'),
    'custom': ('🛠️ Custom Create', 'Cara lengkap. Kamu bisa mengatur isi, chapter, foto, audio, layout, dan detail Experience lebih jauh.'),
    'story': ('📖 Story', 'Buat cerita berbentuk chapter. Setiap chapter tampil sebagai scene hidup dan punya tombol Next Chapter.'),
    'letter': ('💌 Letter', 'Buat surat digital dengan reveal pesan, foto pendukung, audio, dan ending personal.'),
    'event': ('🎉 Event', 'Buat undangan dengan tanggal, countdown, lokasi, agenda, RSVP, dan gallery.'),
    'memories': ('📸 Memories', 'Buat arsip foto dengan layout dinamis. Posisi foto otomatis berubah sesuai jumlah dan rasio media.'),
    'play': ('🎮 Play', 'Buat quiz/game. Peserta menjawab lalu submit sekali untuk mendapatkan score dan leaderboard.'),
    'audio': ('🎵 Audio / Soundtrack', 'Bisa memakai Audio Telegram, Voice Note, atau file audio MP3/M4A/WAV/OGG/OPUS/FLAC/AAC.'),
    'media': ('📸 Media', 'Kirim foto sebanyak yang diperlukan. Template akan memilih komposisi yang sesuai agar foto tidak terlihat ditempel asal.'),
    'expiration': ('⏳ Expiration', 'Menentukan berapa lama Experience aktif. Setiap kategori punya default sendiri dan bisa kamu ubah.'),
    'share': ('📤 Share', 'Bagikan Experience melalui link share, Link Telegram, atau buka langsung sebagai Mini App.'),
    'message': ('💌 Message Owner', 'Pesan dari orang yang membuka Experience diteruskan langsung ke pembuat. Bisa dikirim dari shared link.'),
    'quiz': ('🏆 Quiz & Leaderboard', 'Soal bisa ditambah beberapa batch lalu diakhiri /selesai. Peserta hanya bisa submit sekali untuk satu Experience.'),
}

def category_text():
    return '\n'.join(f"{v['title']} — {v['desc']}" for v in CATEGORIES.values())
