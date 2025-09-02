import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
import unicodedata
import re


class SongEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor písní")
        self.root.geometry("900x800")

        self.sections = []
        self.repetition_entry = None
        self.file_path = None
        self.original_title = None
        self.current_variant = "čeština"

        self.songs_dir = os.path.join(os.path.dirname(__file__), 'songs')
        os.makedirs(self.songs_dir, exist_ok=True)

        self.bg_color = "#555555"
        self.entry_bg = "#505050"
        self.text_bg = "#666666"
        self.button_bg = "#444444"

        self.repetitions = {}

        self.apply_base_style()
        self.build_ui()

        self.manual_repetition_edit = False

    def apply_base_style(self):
        self.root.configure(bg=self.bg_color)
        self.root.option_add("*Background", self.bg_color)
        self.root.option_add("*Foreground", "white")
        self.root.option_add("*Entry.Background", self.entry_bg)
        self.root.option_add("*Entry.Foreground", "white")
        self.root.option_add("*Text.Background", self.text_bg)
        self.root.option_add("*Text.Foreground", "white")
        self.root.option_add("*Button.Background", self.button_bg)
        self.root.option_add("*Button.Foreground", "white")
        self.root.option_add("*LabelFrame.Background", self.bg_color)
        self.root.option_add("*LabelFrame.Foreground", "white")
        self.root.option_add("*Label.Background", self.bg_color)
        self.root.option_add("*Label.Foreground", "white")
        self.font = ("Courier New", 13)

    def build_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill='x', pady=(5, 0))

        tk.Button(top_frame, text=" + ", command=self.load_file, font=self.font).pack(side='left', padx=5)
        tk.Button(top_frame, text="Nová píseň", command=self.new_song, font=self.font).pack(side='left', padx=5)

        tk.Label(top_frame, text="Název:", font=self.font).pack(side='left')
        self.title_entry = tk.Entry(top_frame, width=50, font=self.font)
        self.title_entry.pack(side='left', fill='x', expand=True, padx=5)

        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * int(e.delta / 120), "units"))

        self.sections_frame = self.scrollable_frame

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        for label, typ in [("Sloka", 'v'), ("Refrén", 'r'), ("Bridge", 'b')]:
            tk.Button(btn_frame, text=label, command=lambda t=typ: self.add_section_to_all_languages(t), font=self.font).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Přidat jazyk", command=self.open_language_dialog, font=self.font).pack(side='left', padx=10)

        header_frame = tk.Frame(self.root)
        header_frame.pack(anchor='w', padx=5, pady=(10, 0))
        tk.Label(header_frame, text="Opakování:", font=self.font).pack(side='left')
        tk.Button(header_frame, text=" + ", command=self.add_repetition_prompt, font=self.font).pack(side='left', padx=10)

        self.repetition_frames = {}
        self.repetition_vars = {}

        self.repetition_container = tk.Frame(self.root, bg=self.bg_color)
        self.repetition_container.pack(fill='x', padx=5)

        tk.Label(self.root,
                 text="v = Sloka, r = Refrén, b = Bridge | (v) = 1 Opakování | (v)*x = x Opakování | v.x = Pouze x řádek",
                 font=('Courier New', 10, 'italic'), fg='white', bg=self.bg_color).pack(anchor='w', padx=5)

        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=10)
        tk.Button(ctrl_frame, text="Uložit", command=self.save_file, font=self.font).pack(side='left', padx=5)

        self.add_repetition("default")
        self.repetition_entry = self.repetition_vars["default"]

        # 🔧 Tlačítko pro opravu XML souborů
        fix_frame = tk.Frame(self.root, bg=self.bg_color)
        fix_frame.pack(anchor="sw", side="bottom", pady=5, padx=5)

        tk.Button(fix_frame, text="Error Fix", font=self.font,
                  bg=self.button_bg, fg="white",
                  command=self.run_error_fix).pack(anchor="sw")


    def get_existing_languages(self):
        return list(set(s['lang'] for s in self.sections)) or ["čeština"]

    def get_next_section_number(self, sec_type):
        existing = [s['num'] for s in self.sections if s['type'] == sec_type]
        return max(existing, default=0) + 1

    def add_section_to_all_languages(self, sec_type):
        num = self.get_next_section_number(sec_type)
        for lang in self.get_existing_languages():
            self.add_section(sec_type, num, "", lang)

    def add_section(self, sec_type, num=None, content="", lang="čeština"):
        if num is None:
            num = self.get_next_section_number(sec_type)

        label = f"{'Sloka' if sec_type == 'v' else 'Refrén' if sec_type == 'r' else 'Bridge'} {num}"
        if lang != "čeština":
            label += f" – {lang}"

        frame = tk.LabelFrame(self.sections_frame, text=label, font=self.font)

        inserted = False
        for s in self.sections:
            if s['type'] == sec_type and s['num'] == num:
                if lang == "čeština":
                    frame.pack(fill='x', padx=5, pady=3, before=s['frame'])
                else:
                    frame.pack(fill='x', padx=20, pady=1, after=s['frame'])
                inserted = True
                break

        if not inserted:
            frame.pack(fill='x', padx=5, pady=3)

        header = tk.Frame(frame)
        header.pack(fill='x')
        remove_btn = tk.Button(header, text=' - ', command=lambda: self.remove_section(frame), font=self.font)
        remove_btn.pack(side='right', padx=5)

        text = tk.Text(frame, height=1, font=self.font)
        text.insert('end', content)
        text.pack(fill='x')

        def resize_text(event):
            lines = text.get("1.0", "end-1c").split("\n")
            text.configure(height=max(1, len(lines)))

        text.bind("<KeyRelease>", resize_text)
        resize_text(None)

        if not self.manual_repetition_edit and lang == "čeština":
            ordered = [f"{s['type']}{s['num']}" for s in self.sections if s['lang'] == "čeština"]
            ordered.append(f"{sec_type}{num}")
            self.repetition_entry.set(" ".join(ordered))

        self.sections.append({'type': sec_type, 'num': num, 'widget': text, 'frame': frame, 'lang': lang})

    def open_language_dialog(self):
        lang_win = tk.Toplevel(self.root)
        lang_win.title("Přidat jazyk")
        lang_win.geometry("300x130")
        lang_win.configure(bg=self.bg_color)

        tk.Label(lang_win, text="Vyber nebo zadej jazyk:", font=self.font, bg=self.bg_color, fg="white").pack(pady=5)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TCombobox", fieldbackground=self.entry_bg, background=self.entry_bg, foreground="white")

        combo = ttk.Combobox(lang_win, values=["angličtina", "український - auto", "slovenština", "hebrejština", "hebrejština - transkript"], font=self.font)
        combo.pack(pady=5)
        combo.set("angličtina")

        def confirm():
            val = combo.get().strip()
            if not val:
                lang_win.destroy()
                return
            self.create_language_variant(val)
            lang_win.destroy()

        tk.Button(lang_win, text="Přidat", command=confirm, font=self.font).pack(pady=5)

    def create_language_variant(self, lang):
        original = [s for s in self.sections if s['lang'] == "čeština"]
        self.current_variant = lang
        for s in original:
            content = s['widget'].get("1.0", "end").strip()
            self.add_section(s['type'], s['num'], content, lang)

    def remove_section(self, frame):
        for s in self.sections:
            if s['frame'] == frame:
                s['frame'].destroy()
                self.sections.remove(s)
                break

    def new_song(self):
        self.title_entry.delete(0, 'end')
        for s in self.sections:
            s['widget'].master.destroy()
        self.sections = []
        self.repetition_entry.set("")
        self.file_path = None
        self.original_title = None
        self.current_variant = "čeština"

    def mark_repetition_as_manual(self):
        self.manual_repetition_edit = True

    def add_repetition_prompt(self):
        name = simpledialog.askstring("Nové opakování", "Zadej název opakování:", parent=self.root)
        if name and name not in self.repetitions:
            self.add_repetition(name)

    def add_repetition(self, name, value=""):
        frame = tk.Frame(self.repetition_container, bg=self.bg_color)
        frame.pack(fill='x', pady=2)
        tk.Label(frame, text=name, font=self.font, bg=self.bg_color, fg='white').pack(side='left')

        var = tk.StringVar()
        var.set(value)
        entry = tk.Entry(frame, textvariable=var, font=self.font, width=50)
        entry.pack(side='left', padx=5, expand=True, fill='x')

        if name == "default":
            entry.bind("<Key>", lambda e: self.mark_repetition_as_manual())

        btn = tk.Button(frame, text=' − ', font=self.font, command=lambda: self.remove_repetition(name, frame))
        btn.pack(side='right', padx=5)

        self.repetition_frames[name] = frame
        self.repetition_vars[name] = var
        self.repetitions[name] = value

    def remove_repetition(self, name, frame):
        if name in self.repetition_frames:
            frame.destroy()
            del self.repetition_frames[name]
            del self.repetition_vars[name]
            del self.repetitions[name]

    def nazev_na_soubor(self, text):
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
        text = text.lower()
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[^a-z0-9_]', '', text)
        return text + '.xml'

    def validate_line_counts(self):
        section_map = {}
        for s in self.sections:
            key = (s['type'], s['num'])
            lines = s['widget'].get("1.0", "end").strip().split('\n')
            count = len(lines)
            if key not in section_map:
                section_map[key] = count
            else:
                if section_map[key] != count:
                    return False, key, section_map[key], count
        return True, None, None, None

    def save_file(self):
        valid, key, expected, actual = self.validate_line_counts()
        if not valid:
            section_type = {'v': 'Sloka', 'r': 'Refrén', 'b': 'Bridge'}.get(key[0], key[0])
            messagebox.showerror("Chyba", f"{section_type} {key[1]} má různý počet řádků mezi variantami!\nOčekáváno: {expected}, nalezeno: {actual}")
            return

        current_title = self.title_entry.get()
        new_filename = self.nazev_na_soubor(current_title)

        if self.original_title == current_title and self.file_path:
            save_path = self.file_path
        else:
            save_path = os.path.join(self.songs_dir, new_filename)

        slide = ET.Element("slide")
        slide.set("name", current_title)

        variants = {}
        for s in self.sections:
            lang = s['lang']
            if lang not in variants:
                variants[lang] = []
            variants[lang].append(s)

        for lang, items in variants.items():
            variant = ET.SubElement(slide, "variant")
            variant.set("name", lang)
            for s in items:
                sec = ET.SubElement(variant, "section")
                sec.set("name", f"{s['type']}{s['num']}")
                sec.text = "\n" + s['widget'].get("1.0", "end").strip() + "\n"

        for name, var in self.repetition_vars.items():
            repetition = ET.SubElement(slide, "repetition")
            repetition.set("name", name)
            repetition.text = var.get()

        try:
            xml_str = ET.tostring(slide, encoding='utf-8')
            parsed = xml.dom.minidom.parseString(xml_str)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(parsed.toprettyxml(indent='    '))

            messagebox.showinfo("Uloženo", f"Soubor byl uložen jako:\n{os.path.basename(save_path)}")
            self.file_path = save_path
            self.original_title = current_title
        except Exception as e:
            messagebox.showerror("Chyba", f"Nepodařilo se uložit soubor:\n{e}")

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("XML soubory", "*.xml")])
        if not file_path:
            return

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            self.file_path = file_path
            self.original_title = root.attrib.get('name', '')
            self.title_entry.delete(0, 'end')
            for s in self.sections:
                s['widget'].master.destroy()
            self.sections = []
            self.repetition_entry.set("")
            self.title_entry.insert(0, self.original_title)

            for variant in root.findall("variant"):
                lang = variant.attrib.get("name", "čeština")
                for section in variant.findall("section"):
                    sid = section.attrib.get('name')
                    if not sid:
                        continue
                    typ = sid[0]
                    num = int(sid[1:])
                    content = section.text.strip() if section.text else ""
                    self.add_section(typ, num, content, lang)

            repetitions_sorted = sorted(root.findall("repetition"), key=lambda r: 0 if r.attrib.get("name") == "default" else 1)
            for r in repetitions_sorted:
                name = r.attrib.get("name", "default")
                value = r.text.strip() if r.text else ""
                if name == "default":
                    self.repetition_entry.set(value)
                else:
                    self.add_repetition(name, value)


            self.current_variant = "čeština"

        except Exception as e:
            messagebox.showerror("Chyba", f"Nepodařilo se načíst soubor:\n{e}")

    def run_error_fix(self):
        import subprocess
        import sys
        path = os.path.join(os.path.dirname(__file__), 'oprava_xml_tagu.py')
        subprocess.Popen([sys.executable, path])


if __name__ == "__main__":
    root = tk.Tk()
    app = SongEditor(root)
    root.mainloop()
