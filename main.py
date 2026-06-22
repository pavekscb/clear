import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import webbrowser
import ctypes # Используем для прямого обращения к Windows API (фикс корзины)

# --- КОНФИГУРАЦИЯ ПУТЕЙ К МУСОРУ ---
USER_PROFILE = os.path.expanduser("~")

PATHS = {
    "temp": [
        os.path.join(USER_PROFILE, r"AppData\Local\Temp"),
        r"C:\Windows\Temp"
    ],
    "chrome": [
        os.path.join(USER_PROFILE, r"AppData\Local\Google\Chrome\User Data\Default\Cache"),
        os.path.join(USER_PROFILE, r"AppData\Local\Google\Chrome\User Data\Default\Code Cache\js"),
        os.path.join(USER_PROFILE, r"AppData\Local\Google\Chrome\User Data\Default\GPUCache")
    ],
    "logs": [
        r"C:\Windows\Logs",
        os.path.join(USER_PROFILE, r"AppData\Local\Microsoft\Windows\WER")
    ]
}

# Структура для получения данных о Корзине через WinAPI
class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("i64Size", ctypes.c_longlong),
        ("i64NumItems", ctypes.c_longlong)
    ]

class CleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("P Experiments - PC Cleaner")
        
        # Центрирование окна на экране
        window_width = 520
        window_height = 510
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f6fa")
        
        self.sizes = {"temp": 0.0, "chrome": 0.0, "trash": 0.0}
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Загрузка иконок
        try:
            self.img_temp = tk.PhotoImage(file=os.path.join(current_dir, "icon_temp.png"))
            self.img_chrome = tk.PhotoImage(file=os.path.join(current_dir, "icon_chrome.png"))
            self.img_trash = tk.PhotoImage(file=os.path.join(current_dir, "icon_trash.png"))
            self.img_all = tk.PhotoImage(file=os.path.join(current_dir, "icon_all.png"))
            self.img_refresh = tk.PhotoImage(file=os.path.join(current_dir, "icon_refresh.png"))
            self.img_logo = tk.PhotoImage(file=os.path.join(current_dir, "logo.png"))
            print("Иконки успешно загружены!")
        except Exception as e:
            print(f"Ошибка загрузки иконок: {e}")
            self.img_temp = self.img_chrome = self.img_trash = self.img_all = self.img_refresh = self.img_logo = None

        self.create_widgets()
        
        # Первичное сканирование при запуске
        self.start_full_scan()

    def create_widgets(self):
        # Шапка
        self.header = tk.Label(self.root, text="Найдено мусора на ПК:", font=("Arial", 13), bg="#f5f6fa", fg="#7f8c8d")
        self.header.pack(pady=(15, 2))
        
        # Контейнер для счетчика и кнопки Обновить
        score_frame = tk.Frame(self.root, bg="#f5f6fa")
        score_frame.pack(pady=2)
        
        # Большой счетчик
        self.size_label = tk.Label(score_frame, text="Сканирование...", font=("Arial", 26, "bold"), fg="#2c3e50", bg="#f5f6fa")
        self.size_label.pack(side="left", padx=10)
        
        # Кнопка ОБНОВИТЬ
        self.refresh_btn = tk.Button(
            score_frame, 
            image=self.img_refresh,
            text=" Обновить" if not self.img_refresh else "",
            compound="left",
            bg="#f5f6fa", 
            activebackground="#dcdde1", 
            relief="flat", 
            cursor="hand2",
            command=self.start_full_scan
        )
        self.refresh_btn.pack(side="left", padx=5)

        # Разделитель
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=40, pady=15)

        # Строки очистки
        self.frame_temp, self.lbl_temp, self.btn_temp = self.create_clean_row(
            "Временные файлы Windows", self.img_temp, lambda: self.start_single_clean("temp", self.clean_temp)
        )
        self.frame_chrome, self.lbl_chrome, self.btn_chrome = self.create_clean_row(
            "Кэш Google Chrome", self.img_chrome, lambda: self.start_single_clean("chrome", self.clean_chrome)
        )
        self.frame_trash, self.lbl_trash, self.btn_trash = self.create_clean_row(
            "Очистить Корзину", self.img_trash, lambda: self.start_single_clean("trash", self.clean_trash)
        )

        # Лоадер (скрыт по умолчанию)
        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=360)
        
        # Кнопка ОЧИСТИТЬ ВЕСЬ МУСОР
        self.full_btn = tk.Button(
            self.root, 
            text="  ОЧИСТИТЬ ВЕСЬ МУСОР", 
            font=("Arial", 12, "bold"), 
            image=self.img_all, 
            compound="left", 
            bg="#e74c3c", 
            fg="white", 
            activebackground="#c0392b",
            activeforeground="white",
            padx=20, 
            pady=10, 
            cursor="hand2",
            command=self.clean_all
        )
        self.full_btn.pack(side="bottom", pady=(10, 15))

        # --- ПОДВАЛ (ФУТЕР) С ЛОГОТИПОМ И ССЫЛКАМИ ---
        footer_frame = tk.Frame(self.root, bg="#f5f6fa")
        footer_frame.pack(side="bottom", pady=(0, 10))

        # Кликабельный логотип YouTube канала
        if self.img_logo:
            self.logo_label = tk.Label(footer_frame, image=self.img_logo, bg="#f5f6fa", cursor="hand2")
            self.logo_label.pack(side="left", padx=10)
            self.logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.youtube.com/@P.EXPERIMENTs"))

        # Кликабельная ссылка на GitHub
        self.github_link = tk.Label(
            footer_frame, 
            text="Исходный код на GitHub", 
            font=("Arial", 9, "underline"), 
            fg="#3498db", 
            bg="#f5f6fa", 
            cursor="hand2"
        )
        self.github_link.pack(side="left", padx=10)
        self.github_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/pavekscb/clear"))

    def create_clean_row(self, text, icon, command):
        frame = tk.Frame(self.root, bg="#f5f6fa")
        frame.pack(fill='x', padx=40, pady=6)
        
        lbl = tk.Label(frame, text=f"{text} (считаем...)", font=("Arial", 10), bg="#f5f6fa", fg="#34495e", image=icon, compound="left", padx=10)
        lbl.pack(side="left")
        
        btn = tk.Button(frame, text="Очистить", font=("Arial", 9, "bold"), bg="#dcdde1", fg="#2f3640", 
                        activebackground="#b2bec3", relief="flat", padx=10, pady=4, cursor="hand2", command=command)
        btn.pack(side="right")
        
        return frame, lbl, btn

    # --- ЛОГИКА СЧЕТЧИКОВ ---

    def get_dir_size(self, path):
        total_size = 0
        if not os.path.exists(path): return 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
        except Exception: pass
        return total_size

    def get_trash_size(self):
        # Новая безотказная логика подсчета через официальный Windows API (работает в .exe на 100%)
        try:
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            
            # Вызываем функцию из shell32.dll
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0: # 0 означает S_OK (успешно)
                return rb_info.i64Size
        except Exception: pass
        return 0

    def update_ui_sizes(self):
        self.lbl_temp.config(text=f"Временные файлы Windows ({self.sizes['temp']:.2f} MB)")
        self.lbl_chrome.config(text=f"Кэш Google Chrome ({self.sizes['chrome']:.2f} MB)")
        self.lbl_trash.config(text=f"Очистить Корзину ({self.sizes['trash']:.2f} MB)")
        
        total = sum(self.sizes.values())
        self.size_label.config(text=f"{total:.2f} MB")

    def set_buttons_state(self, state):
        self.refresh_btn.config(state=state)
        self.btn_temp.config(state=state)
        self.btn_chrome.config(state=state)
        self.btn_trash.config(state=state)
        self.full_btn.config(state=state)

    def start_full_scan(self):
        def scan():
            self.set_buttons_state("disabled")
            self.start_loading()
            self.size_label.config(text="Считаем...")
            
            t_size = sum(self.get_dir_size(p) for p in PATHS['temp'])
            self.sizes['temp'] = t_size / (1024 * 1024)
            
            c_size = sum(self.get_dir_size(p) for p in PATHS['chrome'])
            self.sizes['chrome'] = c_size / (1024 * 1024)
            
            self.sizes['trash'] = self.get_trash_size() / (1024 * 1024)
            
            self.root.after(0, self.update_ui_sizes)
            self.stop_loading()
            self.set_buttons_state("normal")
            
        threading.Thread(target=scan, daemon=True).start()

    # --- УПРАВЛЕНИЕ ЛОАДЕРОМ ---

    def start_loading(self):
        self.progress.pack(pady=5)
        self.progress.start(15)
        self.root.update()

    def stop_loading(self):
        self.progress.stop()
        self.progress.pack_forget()

    # --- МЕХАНИКА УДАЛЕНИЯ ---

    def clean_folder(self, path):
        if not os.path.exists(path): return
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception: pass

    def clean_temp(self):
        for p in PATHS['temp']: self.clean_folder(p)
        self.sizes['temp'] = 0.0

    def clean_chrome(self):
        for p in PATHS['chrome']: self.clean_folder(p)
        self.sizes['chrome'] = 0.0

    def clean_trash(self):
        try:
            subprocess.run(["powershell", "Clear-RecycleBin -Confirm:$false"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception: pass
        self.sizes['trash'] = 0.0

    def start_single_clean(self, key, clean_func):
        def run():
            self.set_buttons_state("disabled")
            self.start_loading()
            clean_func()
            
            if key == "temp":
                self.sizes['temp'] = sum(self.get_dir_size(p) for p in PATHS['temp']) / (1024 * 1024)
            elif key == "chrome":
                self.sizes['chrome'] = sum(self.get_dir_size(p) for p in PATHS['chrome']) / (1024 * 1024)
            elif key == "trash":
                self.sizes['trash'] = self.get_trash_size() / (1024 * 1024)
                
            self.root.after(0, self.update_ui_sizes)
            self.stop_loading()
            self.set_buttons_state("normal")
        threading.Thread(target=run, daemon=True).start()

    def clean_all(self):
        def task():
            self.set_buttons_state("disabled")
            self.start_loading()
            
            initial_total = sum(self.sizes.values())
            
            self.clean_temp()
            self.clean_chrome()
            self.clean_trash()
            
            self.sizes['temp'] = sum(self.get_dir_size(p) for p in PATHS['temp']) / (1024 * 1024)
            self.sizes['chrome'] = sum(self.get_dir_size(p) for p in PATHS['chrome']) / (1024 * 1024)
            self.sizes['trash'] = self.get_trash_size() / (1024 * 1024)
            
            final_total = sum(self.sizes.values())
            cleaned_amount = initial_total - final_total
            if cleaned_amount < 0: cleaned_amount = 0
            
            self.root.after(0, self.update_ui_sizes)
            self.stop_loading()
            self.set_buttons_state("normal")
            
            messagebox.showinfo("P Experiments", f"Очистка завершена!\nОсвобождено: {cleaned_amount:.2f} MB")

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = CleanerApp(root)
    root.mainloop()
