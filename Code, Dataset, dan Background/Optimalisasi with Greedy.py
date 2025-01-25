import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import pandas as pd
import ast
from PIL import Image, ImageTk
from typing import List, Dict, Tuple
import time

def input_terjemahan(input_pengguna: str, peta_terjemahan: Dict[str, str]) -> List[str]:
    """Menerjemahkan daftar nama peralatan dalam Bahasa Indonesia ke Bahasa Inggris menggunakan mapping."""
    return [peta_terjemahan.get(item.strip(), item.strip()) for item in input_pengguna.split(',')]

def hari_terjemahan(input_pengguna: List[str], peta_terjemahan: Dict[str, str]) -> List[str]:
    """Menerjemahkan daftar nama hari dalam Bahasa Indonesia ke Bahasa Inggris menggunakan mapping."""
    return [peta_terjemahan.get(hari.strip(), hari.strip()) for hari in input_pengguna]

peta_terjemahan = {
    'Kulkas': 'Refrigerator',
    'Mesin pencuci piring': 'Dishwasher',
    'Lampu': 'Lighting',
    'Elektronik': 'Electronics',
    'Mesin cuci': 'Washing Machine',
    'Ac': 'HVAC', 
    'AC': 'HVAC'
}

peta_terjemahan_hari = {
    'Senin': 'Monday',
    'Selasa': 'Tuesday',
    'Rabu': 'Wednesday',
    'Kamis': 'Thursday',
    'Jumat': 'Friday',
    'Sabtu': 'Saturday',
    'Minggu': 'Sunday'
}

# --- Backend PenjadwalDaya ---
class PenjadwalDaya:
    def __init__(self, data_csv: pd.DataFrame, harga_per_kwh: float = 1400):
        self.data = data_csv
        self.harga_per_kwh = harga_per_kwh
        self.hari = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        self.jam = [f"{str(h).zfill(2)}:00" for h in range(24)]
        self.memo_konsumsi = {}  # Memoization cache

    def konsumsi_harian(self, peralatan: str, hari: str) -> Dict[str, float]:
        """Mengambil konsumsi per jam untuk peralatan tertentu pada hari tertentu dengan memoization."""
        cache_key = (peralatan, hari)
        if cache_key in self.memo_konsumsi:
            return self.memo_konsumsi[cache_key]
        
        data_harian = self.data[(
            self.data['appliance'] == peralatan) & 
            (self.data['day_of_week'] == hari)
        ]
        result = dict(zip(data_harian['time'].str.slice(0, 5), data_harian['energy_consumption_kWh']))
        self.memo_konsumsi[cache_key] = result  # Simpan hasil ke cache
        return result
    
    def hitung_penggunaan_prioritas(self, peralatan_list: List[str], mulai_jam: int, akhir_jam: int) -> Dict[str, Tuple[float, List[str], List[str]]]:
        """Menghitung total konsumsi untuk jam prioritas sepanjang minggu dengan beberapa peralatan."""
        penggunaan_prioritas = {}
        rentang_jam = []
        
        if mulai_jam > akhir_jam:
            rentang_jam = list(range(mulai_jam, 24)) + list(range(0, akhir_jam + 1))
        else:
            rentang_jam = list(range(mulai_jam, akhir_jam + 1))
            
        for peralatan in peralatan_list:
            for hari in self.hari:
                data_harian = self.konsumsi_harian(peralatan, hari)
                total = 0
                jam_terpakai = []
                for h in rentang_jam:
                    jam_str = f"{str(h).zfill(2)}:00"
                    if jam_str in data_harian:
                        total += data_harian[jam_str]
                        jam_terpakai.append(jam_str)
                
                if hari not in penggunaan_prioritas:
                    penggunaan_prioritas[hari] = (0, [], [])
                
                # Gabungkan total konsumsi, jam terpakai, dan peralatan untuk setiap hari
                penggunaan_prioritas[hari] = (
                    penggunaan_prioritas[hari][0] + total,
                    penggunaan_prioritas[hari][1] + jam_terpakai,
                    penggunaan_prioritas[hari][2] + [peralatan]
                )
        
        return penggunaan_prioritas

    
    def temukan_penggunaan_terjadwal(self, peralatan: List[str], hari_terjadwal: List[str], jam_dibutuhkan: int = 2) -> Dict[str, List[Tuple[str, float, str]]]:
        """Menemukan jam optimal untuk penggunaan terjadwal"""
        penggunaan_terjadwal = {}
        
        for alat in peralatan:
            for hari in hari_terjadwal:
                konsumsi_harian = self.konsumsi_harian(alat, hari)
                
                daftar_konsumsi = [(jam, konsumsi, alat) for jam, konsumsi in konsumsi_harian.items()]
                
                n = len(daftar_konsumsi)
                if n < jam_dibutuhkan:
                    continue
                    
                min_konsumsi = float('inf')
                jam_optimal = []
                
                for i in range(n - jam_dibutuhkan + 1):
                    total_saat_ini = sum(cons for _, cons, _ in daftar_konsumsi[i:i+jam_dibutuhkan])
                    if total_saat_ini < min_konsumsi:
                        min_konsumsi = total_saat_ini
                        jam_optimal = daftar_konsumsi[i:i+jam_dibutuhkan]
                
                if hari not in penggunaan_terjadwal:
                    penggunaan_terjadwal[hari] = []
                penggunaan_terjadwal[hari].extend(jam_optimal)
            
        return penggunaan_terjadwal
    
    def temukan_penggunaan_tambahan(self, peralatan: List[str], batas_anggaran: float, 
                                    biaya_prioritas: float, biaya_terjadwal: float) -> Dict[str, List[Tuple[str, float, str]]]:
        """Menemukan penggunaan tambahan optimal dengan menggunakan greedy knapsack untuk berbagai peralatan"""
        start_greedy = time.time()
        anggaran_sisa = batas_anggaran - (biaya_prioritas + biaya_terjadwal)
        penggunaan_tambahan = {}
        
        semua_jam = []
        for alat in peralatan:
            for hari in self.hari:
                konsumsi_harian = self.konsumsi_harian(alat, hari)
                for jam, konsumsi in konsumsi_harian.items():
                    biaya = konsumsi * self.harga_per_kwh
                    if biaya <= anggaran_sisa:
                        semua_jam.append((hari, jam, konsumsi, biaya, alat))
        
        semua_jam.sort(key=lambda x: x[2])
        
        biaya_sekarang = 0
        for hari, jam, konsumsi, biaya, alat in semua_jam:
            if biaya_sekarang + biaya <= anggaran_sisa:
                if hari not in penggunaan_tambahan:
                    penggunaan_tambahan[hari] = []
                penggunaan_tambahan[hari].append((jam, konsumsi, alat))
                biaya_sekarang += biaya
        for hari in penggunaan_tambahan:
            penggunaan_tambahan[hari].sort(key=lambda x: x[0])  
        end_greedy = time.time()
        print(f"Waktu Eksekusi Greedy: {end_greedy - start_greedy:.4f} detik")         
        return penggunaan_tambahan


    
    def optimalkan_jadwal(self, peralatan_prioritas: List[str], prioritas_mulai: int, prioritas_selesai: int,
                          peralatan_terjadwal: List[str], hari_terjadwal: List[str],
                          peralatan_tambahan: List[str], anggaran_bulanan: float) -> Dict:
        penggunaan_prioritas = self.hitung_penggunaan_prioritas(peralatan_prioritas, prioritas_mulai, prioritas_selesai)
        biaya_prioritas = sum(pemakaian[0] * self.harga_per_kwh for pemakaian in penggunaan_prioritas.values())
        
        penggunaan_terjadwal = self.temukan_penggunaan_terjadwal(peralatan_terjadwal, hari_terjadwal)
        biaya_terjadwal = sum(
            sum(konsumsi for _, konsumsi, _ in jam)
            for jam in penggunaan_terjadwal.values()
        ) * self.harga_per_kwh
        
        penggunaan_tambahan = self.temukan_penggunaan_tambahan(
            peralatan_tambahan, anggaran_bulanan, biaya_prioritas, biaya_terjadwal
        )
        
        return {
            'penggunaan_prioritas': penggunaan_prioritas,
            'penggunaan_terjadwal': penggunaan_terjadwal,
            'penggunaan_tambahan': penggunaan_tambahan,
            'total_biaya': biaya_prioritas + biaya_terjadwal + sum(
                sum(konsumsi for _, konsumsi, _ in jam)
                for jam in penggunaan_tambahan.values()
            ) * self.harga_per_kwh
        }
    
    def format_jadwal(self, jadwal: Dict, anggaran_bulanan: float) -> str:
        """Format jadwal menjadi string yang mudah dibaca sesuai format yang diinginkan"""
        output = []
        for hari in self.hari:
            output.append(f"\n{hari}:")
            
            # Penggunaan Prioritas
            if hari in jadwal['penggunaan_prioritas']:
                penggunaan, jam_terpakai, alat = jadwal['penggunaan_prioritas'][hari]
                if jam_terpakai:
                    alat_str = ', '.join(set(alat))  # Pastikan tidak ada alat yang terduplikasi
                    # Memecah jam terpakai setiap 5 elemen per baris
                    jam_terformat = []
                    for i in range(0, len(jam_terpakai), 5):
                        jam_terformat.append(", ".join(jam_terpakai[i:i + 5]))
                    # Tambahkan indentasi ekstra untuk setiap baris baru
                    jam_str = "\n            ".join(jam_terformat)
                    output.append(f"-> Penggunaan Prioritas: {alat_str}")
                    output.append(f"    Total Energi: {penggunaan:.2f} kWh")
                    output.append(f"    Jam: {jam_str}")

            # Penggunaan Terjadwal
            if hari in jadwal['penggunaan_terjadwal']:
                jam_terjadwal = jadwal['penggunaan_terjadwal'][hari]
                if jam_terjadwal:
                    total_terjadwal = sum(konsumsi for _, konsumsi, _ in jam_terjadwal)
                    output.append(f"-> Penggunaan Terjadwal: {total_terjadwal:.2f} kWh")
                    for waktu, konsumsi, alat in jam_terjadwal:
                        output.append(f"    {waktu} - {alat} ({konsumsi:.2f} kWh)")

            # Penggunaan Tambahan
            if hari in jadwal['penggunaan_tambahan']:
                jam_tambahan = jadwal['penggunaan_tambahan'][hari]
                if jam_tambahan:
                    total_tambahan = sum(konsumsi for _, konsumsi, _ in jam_tambahan)
                    output.append(f"-> Penggunaan Tambahan: {total_tambahan:.2f} kWh")
                    for waktu, konsumsi, alat in jam_tambahan:
                        output.append(f"    {waktu} - {alat} ({konsumsi:.2f} kWh)")
        return "\n".join(output)
    
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Penjadwal Daya")
        self.geometry("1537x835")
        self.frames = {}
        self.shared_data = {}  # Untuk menyimpan data yang dibagikan antar halaman

        # Pastikan frame merespons perubahan ukuran jendela
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tambahkan semua frame
        for F in (LoginPage, RegistrationPage, MainPage, InputPage, ResultPage, RulesPage, HitungPage):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")  # Sesuaikan frame dengan jendela

        self.show_frame("LoginPage")  # Mulai dari halaman login

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_login.png")
        self.bg_photo = None
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        self.bind("<Configure>", self.resize_background)

        self.create_widgets()

    def create_widgets(self):
        # Input nama pengguna
        def on_enter(e):
            if user.get() == 'Username':
                user.delete(0, 'end')

        def on_leave(e):
            if user.get() == '':
                user.insert(0, 'Username')

        user = tk.Entry(self, width=20, fg='#737373', border=0, bg='#FFBD59', font=('Poppins', 17))
        user.place(x=1022, y=298)
        user.insert(0, 'Username')
        user.bind('<FocusIn>', on_enter)
        user.bind('<FocusOut>', on_leave)

        # Input kata sandi
        def on_enter(e):
            if code.get() == 'Password':
                code.delete(0, 'end')
                code.config(show="*")  # Sembunyikan teks dengan '*'

        def on_leave(e):
            if code.get() == '':
                code.insert(0, 'Password')
                code.config(show="")  # Tampilkan kembali teks placeholder

        code = tk.Entry(self, width=20, fg='#737373', border=0, bg='#FFBD59', font=('Poppins', 17))
        code.place(x=1022, y=384)
        code.insert(0, 'Password')  # Teks placeholder awal
        code.bind('<FocusIn>', on_enter)
        code.bind('<FocusOut>', on_leave)

        # Fungsi validasi login
        def login():
            username = user.get()
            password = code.get()

            try:
                with open(r'C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\databest.txt', 'r') as file:
                    data = file.read()
                    users = ast.literal_eval(data) if data else {}
                    
                    if username in users and users[username]["password"] == password:
                        messagebox.showinfo("Login", "Login berhasil")
                        self.controller.show_frame("MainPage")
                    else:
                        messagebox.showerror("Login Gagal", "Username atau Password salah")
            except FileNotFoundError:
                messagebox.showerror("Error", "File databest.txt tidak ditemukan")
            except Exception as e:
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}")

        # Tombol Login
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        self.result_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_login.png", width=410, height=74, command=login
        )
        self.result_button.place(x=942, y=491)

        # Teks dan tombol registrasi
        label = tk.Label(self, text="Belum memiliki akun?", fg='#737373', bg='#E2F0F7', font=('Poppins', 12))
        label.place(x=1025, y=575)

        tk.Button(self, width=8, text='Registrasi', border=0, bg='#E2F0F7', cursor='hand2', fg='Red',font=('Poppins', 12), command=lambda: self.controller.show_frame("RegistrationPage")).place(x=1190, y=572)

    def resize_background(self, event):
        resized_image = self.bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)


class RegistrationPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_register.png")
        self.bg_photo = None
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        self.bind("<Configure>", self.resize_background)

        self.create_widgets()

    def create_widgets(self):
        def registrasi():
            namapengguna = user.get()
            katakunci = code.get()
            email = email_entry.get()

            if not namapengguna or not katakunci or not email:
                messagebox.showerror('Invalid', 'Semua bidang harus diisi')
                return

            try:
                with open(r'C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\databest.txt', 'r+') as file:
                    data = file.read()
                    users = ast.literal_eval(data) if data else {}
                    users[namapengguna] = {"password": katakunci, "email": email}
                    file.seek(0)
                    file.write(str(users))
                    file.truncate()

                messagebox.showinfo('Signup', 'Registrasi berhasil')
                self.controller.show_frame("LoginPage")
            except Exception as e:
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}")

        # Entry Email
        def on_enter(e):
            if email_entry.get() == 'Email':
                email_entry.delete(0, 'end')

        def on_leave(e):
            if email_entry.get() == '':
                email_entry.insert(0, 'Email')

        email_entry = tk.Entry(self, width=20, fg='#737373', border=0, bg='#FFBD59', font=('Poppins', 17))
        email_entry.place(x=1022, y=210)
        email_entry.insert(0, 'Email')
        email_entry.bind('<FocusIn>', on_enter)
        email_entry.bind('<FocusOut>', on_leave)

        # Entry Username
        def on_enter(e):
            if user.get() == 'Username':
                user.delete(0, 'end')

        def on_leave(e):
            if user.get() == '':
                user.insert(0, 'Username')

        user = tk.Entry(self, width=20, fg='#737373', border=0, bg='#FFBD59', font=('Poppins', 17))
        user.place(x=1022, y=298)
        user.insert(0, "Username")
        user.bind('<FocusIn>', on_enter)
        user.bind('<FocusOut>', on_leave)

        # Entry Password
        def on_enter(e):
            if code.get() == 'Password':
                code.delete(0, 'end')
                code.config(show="*")  # Ubah karakter menjadi '*'

        def on_leave(e):
            if code.get() == '':
                code.insert(0, 'Password')
                code.config(show="")
                
        code = tk.Entry(self, width=20, fg='#737373', border=0, bg='#FFBD59', font=('Poppins', 17))
        code.place(x=1022, y=384)
        code.insert(0, 'Password')
        code.bind('<FocusIn>', on_enter)
        code.bind('<FocusOut>', on_leave)

        # Tombol Registrasi
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button
        
        self.result_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_signin.png", width=410, height=74, command=registrasi)
        self.result_button.place(x=942, y=491)

    def resize_background(self, event):
        resized_image = self.bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)

class MainPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Simpan referensi gambar
        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_halaman utama.png")
        self.bg_photo = None
        self.bg_label = tk.Label(self)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.create_widgets()

        # Bind event perubahan ukuran jendela
        self.bind("<Configure>", self.resize_background)

    def create_widgets(self):
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            # Buka gambar dan ubah ukuran
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)

            # Buat tombol
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        self.button_labeladmin = create_image_button(self,image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_click.png",width=220,height=70, command=lambda: self.controller.show_frame("InputPage"))
        self.button_labeladmin.place(x=657, y=591)

        # Tombol Aturan Penggunaan
        self.rules_button = create_image_button(self,image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_click.png",width=220,height=70, command=lambda: self.controller.show_frame("RulesPage"))
        self.rules_button.place(x=311, y=591)

        # Tombol Lihat Hasil
        self.result_button = create_image_button(self,image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_click.png", width=220,height=70, command=lambda: self.controller.show_frame("HitungPage"))
        self.result_button.place(x=1004, y=591)

    def resize_background(self, event):
        # Resize gambar sesuai ukuran jendela
        resized_image = self.bg_image.resize((1537,835), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)

class RulesPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Simpan referensi gambar
        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_aturan.png")
        self.bg_photo = None

        # Label untuk gambar latar
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        # Bind event resize
        self.bind("<Configure>", self.resize_background)

        self.create_widgets()

    def create_widgets(self):
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            # Buka gambar dan ubah ukuran
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)

            # Buat tombol
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        self.back_button = create_image_button(self,image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_kembali.png",width=220,height=70, command=lambda: self.controller.show_frame("MainPage"))
        self.back_button.place(x=1260, y= 40)


    def resize_background(self, event):
        # Resize gambar sesuai ukuran jendela
        resized_image = self.bg_image.resize((1537,835), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)


class InputPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        # Simpan referensi gambar
        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_optimalan.png")
        self.bg_photo = None

        # Label untuk gambar latar
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        # Bind event resize
        self.bind("<Configure>", self.resize_background)

        self.create_widgets()

    def create_widgets(self):
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            # Buka gambar dan ubah ukuran
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)

            # Buat tombol
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        # Peralatan Prioritas
        self.prioritas_peralatan = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.prioritas_peralatan.place(x=423,y=210)

        # Jam Prioritas
        self.prioritas_mulai = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.prioritas_mulai.place(x=423,y=283)

        self.prioritas_selesai = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.prioritas_selesai.place(x=423,y=355)

        # Peralatan Terjadwal
        self.peralatan_terjadwal = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.peralatan_terjadwal.place(x=423,y= 429)

        # Hari Terjadwal
        self.hari_terjadwal = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.hari_terjadwal.place(x=423,y=500)

        # Peralatan Tambahan
        self.peralatan_tambahan = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.peralatan_tambahan.place(x=423,y=573)

        # Anggaran Mingguan
        self.anggaran_bulanan = tk.Entry(self, width=28, font=("Arial", 20), bg ="#FFB300")
        self.anggaran_bulanan.place(x=423,y=645)

        # Tombol Submit
        self.submit_button = create_image_button(self,image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_submit.png", width=220,height=70, command=self.submit_data)
        self.submit_button.place(x= 650, y=735)


    def submit_data(self):
        try:
            # Simpan data ke shared_data
            self.controller.shared_data["prioritas_peralatan"] = self.prioritas_peralatan.get()
            self.controller.shared_data["prioritas_mulai"] = int(self.prioritas_mulai.get())
            self.controller.shared_data["prioritas_selesai"] = int(self.prioritas_selesai.get())
            self.controller.shared_data["peralatan_terjadwal"] = self.peralatan_terjadwal.get()
            self.controller.shared_data["hari_terjadwal"] = self.hari_terjadwal.get()
            self.controller.shared_data["peralatan_tambahan"] = self.peralatan_tambahan.get()
            self.controller.shared_data["anggaran_bulanan"] = float(self.anggaran_bulanan.get())
            
            # Pindah ke halaman hasil
            self.controller.show_frame("ResultPage")
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan: anda belum menginputkan apapun")

    
    def resize_background(self, event):
        # Resize gambar sesuai ukuran jendela
        resized_image = self.bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)

class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Simpan referensi gambar
        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_hasil.png")
        self.bg_photo = None

        # Label untuk gambar latar
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        # Bind event resize
        self.bind("<Configure>", self.resize_background)

        # Inisialisasi peringatan_label3
        self.peringatan_label3 = None

        self.create_widgets()

    def create_widgets(self):
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            # Buka gambar dan ubah ukuran
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)

            # Buat tombol
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        # Area teks hasil
        self.result_text = tk.Text(self, wrap="word", width=80, height=30, bg="#DCE9F0", border=0, borderwidth=0)
        self.result_text.place(x=340, y=160, width=555, height=520)

        # Label untuk total biaya
        self.total_biaya_label = tk.Label(self, text="", font=("Arial", 18, "bold"), bg="#FFBD59", anchor="w")
        self.total_biaya_label.place(x=1000, y=300, width=165, height=40)

        # Label untuk peringatan
        self.peringatan_label = tk.Label(self, text="", font=("Arial", 16), bg="#CAE0EC", anchor="w")
        self.peringatan_label.place(x=1010, y=380, width=150, height=25)

        self.peringatan_label2 = tk.Label(self, text="", font=("Arial", 16), bg="#CAE0EC", anchor="w")
        self.peringatan_label2.place(x=945, y=410, width=300, height=25)

        self.peringatan_label3 = tk.Label(self, text="", font=("Arial", 16), bg="#CAE0EC", anchor="w")
        self.peringatan_label3.place(x=1005, y=440, width=165, height=25)

        # Tombol Kembali
        self.back_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_kembali.png", width=220, height=70,
            command=self.handle_back  # Panggil fungsi handle_back
        )
        self.back_button.place(x=1260, y=48)

        # Tombol Home
        self.home_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_home.png", width=220, height=70,
            command=lambda: self.controller.show_frame("MainPage"),
        )
        self.home_button.place(x=124, y=48)

    def handle_back(self):
        """Fungsi untuk menangani tombol kembali."""
        # Kosongkan teks label peringatan jika ada
        if self.peringatan_label3:
            self.peringatan_label3.config(text="")
        # Berpindah ke frame "InputPage"
        self.controller.show_frame("InputPage")


    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)

        # Proses data dan tampilkan hasil
        try:
            df = pd.read_csv(r'C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\data bersih.csv')  # Load data CSV
            penjadwal = PenjadwalDaya(df)

            # Ambil data dari shared_data
            prioritas_peralatan = input_terjemahan(self.controller.shared_data["prioritas_peralatan"], peta_terjemahan)
            prioritas_mulai = self.controller.shared_data["prioritas_mulai"]
            prioritas_selesai = self.controller.shared_data["prioritas_selesai"]
            peralatan_terjadwal = input_terjemahan(self.controller.shared_data["peralatan_terjadwal"], peta_terjemahan)
            hari_terjadwal = hari_terjemahan(self.controller.shared_data["hari_terjadwal"].split(', '), peta_terjemahan_hari)
            peralatan_tambahan = input_terjemahan(self.controller.shared_data["peralatan_tambahan"], peta_terjemahan)
            anggaran_bulanan = self.controller.shared_data["anggaran_bulanan"]

            # Jalankan jadwal optimasi
            jadwal_teroptimasi = penjadwal.optimalkan_jadwal(
                peralatan_prioritas=prioritas_peralatan,
                prioritas_mulai=prioritas_mulai,
                prioritas_selesai=prioritas_selesai,
                peralatan_terjadwal=peralatan_terjadwal,
                hari_terjadwal=hari_terjadwal,
                peralatan_tambahan=peralatan_tambahan,
                anggaran_bulanan=anggaran_bulanan
            )

            # Format hasil dengan anggaran
            hasil = penjadwal.format_jadwal(jadwal_teroptimasi, anggaran_bulanan)

            # Bersihkan teks sebelumnya
            self.result_text.delete(1.0, tk.END)

            # Mengatur font, ukuran, dan warna
            self.result_text.tag_configure("default", font=("Arial", 20), foreground="black")

            # Tambahkan hasil dengan tag default
            self.result_text.insert(tk.END, hasil, "default")

            # Tampilkan total biaya dan peringatan
            total_biaya = jadwal_teroptimasi['total_biaya']
            self.total_biaya_label.config(text=f"Rp.{total_biaya:,.2f}")

            if total_biaya > anggaran_bulanan:
                kelebihan = total_biaya - anggaran_bulanan
                self.peringatan_label.config(text=f"PERINGATAN:", fg="red")
                self.peringatan_label2.config(text=f"Melebihii anggaran sebesar", fg="red")
                self.peringatan_label3.config(text=f"Rp. {kelebihan:,.2f}.", fg="red")
            else:
                self.peringatan_label.config(text=f"AMANNNNNNN", fg="green")
                self.peringatan_label2.config(text="Biaya listrik dalam anggaran.", fg="green")

        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan saat memproses data: {e}")

    def resize_background(self, event):
        # Resize gambar sesuai ukuran jendela
        resized_image = self.bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)


class HitungPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Simpan referensi gambar latar belakang
        self.bg_image = Image.open(r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\bg_hitung.png")
        self.bg_photo = None
        self.bg_label = tk.Label(self)
        self.bg_label.place(relwidth=1, relheight=1)

        # Bind event resize
        self.bind("<Configure>", self.resize_background)

        # Elemen UI
        self.create_widgets()

    def create_widgets(self):
        def create_image_button(parent, image_path, width, height, command):
            """Helper untuk membuat tombol dengan gambar."""
            img = Image.open(image_path).resize((width, height), Image.LANCZOS)
            img_photo = ImageTk.PhotoImage(img)
            button = tk.Button(parent, image=img_photo, command=command, borderwidth=0)
            button.image = img_photo  # Simpan referensi gambar agar tidak dihapus
            return button

        # Label dan Entry untuk input
        self.entry_daya = tk.Entry(self, font=("Poppins", 20), width=23, bg="#FFB300")
        self.entry_daya.place(x=503, y=200)

        self.entry_harga = tk.Entry(self, font=("Poppins", 20), width=23, bg="#FFB300")
        self.entry_harga.place(x=503, y=272)

        self.entry_durasi = tk.Entry(self, font=("Poppins", 20), width=23, bg="#FFB300")
        self.entry_durasi.place(x=503, y=346)
        # Tabel hasil
        columns = ("Waktu", "Konsumsi (kWh)", "Biaya (Rp)")
        self.table = ttk.Treeview(self, columns=columns, show="headings", height=5)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview.Heading", font=("Poppins", 20, "bold"), foreground='#384766')
        style.configure("Treeview", font=("Poppins", 16), foreground="#384766", rowheight=33, background="#FFB300")
        style.map("Treeview", background=[("selected", "#384766")], foreground=[("selected", "black")])
        self.table.heading("Waktu", text="Waktu",)
        self.table.heading("Konsumsi (kWh)", text="Konsumsi (kWh)")
        self.table.heading("Biaya (Rp)", text="Biaya (Rp)")
        self.table.place(x=130, y=500, width=750, height=170)

        for _ in range(5):  # 5 baris kosong
            self.table.insert("", "end", values=("", "", ""))

        # Tombol Hitung
        self.calculate_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_hitung.png", width=220, height=70, command=self.hitung_konsumsi_listrik
        )
        self.calculate_button.place(x=390, y=405)

        # Tombol Kembali ke Halaman Utama
        self.back_button = create_image_button(
            self, image_path=r"C:\Users\Muhammad Zaky T A\Downloads\Projek DAA\tbl_kembali.png", width=220, height=70, command=lambda: self.controller.show_frame("MainPage")
        )
        self.back_button.place(x=1260, y=48)

    def hitung_konsumsi_listrik(self):
        try:
            # Ambil input dari entri
            daya = float(self.entry_daya.get())
            harga_per_kwh = float(self.entry_harga.get())
            durasi_per_hari = float(self.entry_durasi.get())

            # Konversi watt ke kWh
            konsumsi_per_jam_kwh = daya / 1000  # 1 kWh = 1000 watt

            # Perhitungan konsumsi dan biaya
            konsumsi_per_hari_kwh = konsumsi_per_jam_kwh * durasi_per_hari
            konsumsi_per_bulan_kwh = konsumsi_per_hari_kwh * 30
            konsumsi_per_tahun_kwh = konsumsi_per_hari_kwh * 365

            biaya_per_jam = konsumsi_per_jam_kwh * harga_per_kwh
            biaya_per_hari = konsumsi_per_hari_kwh * harga_per_kwh
            biaya_per_bulan = konsumsi_per_bulan_kwh * harga_per_kwh
            biaya_per_tahun = konsumsi_per_tahun_kwh * harga_per_kwh

            # Hapus data lama di tabel
            for row in self.table.get_children():
                self.table.delete(row)

            # Tambahkan hasil perhitungan ke tabel
            self.table.insert("", "end", values=("Per Jam", f"{konsumsi_per_jam_kwh:.2f} kWh", f"Rp {biaya_per_jam:,.2f}"))
            self.table.insert("", "end", values=("Per Hari", f"{konsumsi_per_hari_kwh:.2f} kWh", f"Rp {biaya_per_hari:,.2f}"))
            self.table.insert("", "end", values=("Per Bulan", f"{konsumsi_per_bulan_kwh:.2f} kWh", f"Rp {biaya_per_bulan:,.2f}"))
            self.table.insert("", "end", values=("Per Tahun", f"{konsumsi_per_tahun_kwh:.2f} kWh", f"Rp {biaya_per_tahun:,.2f}"))
        except ValueError:
            messagebox.showerror("Input Error", "Harap masukkan angka yang valid!")

    def resize_background(self, event):
        # Resize gambar sesuai ukuran jendela
        resized_image = self.bg_image.resize((event.width, event.height), Image.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(resized_image)
        self.bg_label.config(image=self.bg_photo)


# Jalankan Aplikasi
if __name__ == "__main__":
    app = App()
    app.mainloop()

