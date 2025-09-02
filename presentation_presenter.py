import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkFont
import re
import json
import os
from screeninfo import get_monitors
import base64
from PIL import Image, ImageTk
from io import BytesIO
import tkinter.font as tkFont
import json
import os
from tkinterdnd2 import DND_FILES, TkinterDnD

class PresentationEditor:
    def __init__(self, root):
        self.root = root
        bg_color = "#555555"  # nebo tvoje `self.style['mainFrame']['bg']` či něco tmavého
        self.root.configure(bg=bg_color)
        self.style = self.load_gui_style()
        self.fonts = self.load_fonts(self.style['fonts'])
        self.root.title("Editor prezentací")

        self.raw_slides = []
        self.slides = []
        self.current_slide_index = 0
        self.current_raw_index = 0

        self.default_res = {"4:3": (1024, 768), "16:9": (1280, 720)}
        self.current_aspect = tk.StringVar(value="4:3")
        self.monitor_index = tk.IntVar(value=0)
        self.custom_width = tk.StringVar()
        self.custom_height = tk.StringVar()

        self.presentation_dir = os.path.join(os.path.dirname(__file__), "presentations")
        os.makedirs(self.presentation_dir, exist_ok=True)

        self.auto_advance = False
        self.auto_interval = tk.IntVar(value=5)  # výchozí 5 sekund
        self.auto_timer_id = None

        self.loop_presentation = tk.BooleanVar(value=False)
        
        self.allow_all_lines = tk.BooleanVar(value=False)
        self.build_ui()

        self.root.bind("<Left>", lambda e: self.prev_slide())
        self.root.bind("<Right>", lambda e: self.next_slide())
        self.root.bind("<Up>", lambda e: self.prev_slide())
        self.root.bind("<Down>", lambda e: self.next_slide())
        self.root.bind("<Prior>", lambda e: self.prev_slide())  
        self.root.bind("<Next>", lambda e: self.next_slide())
        self.root.bind("<Shift-Left>", lambda e: self.jump_to_prev_block())
        self.root.bind("<Shift-Right>", lambda e: self.jump_to_next_block())
        self.root.bind("<Shift-Prior>", lambda e: self.jump_to_prev_block())  # Shift + PgUp
        self.root.bind("<Shift-Next>", lambda e: self.jump_to_next_block())   # Shift + PgDn
        
        self.allow_all_lines = tk.BooleanVar(value=False)

        self.allow_lines_check.pack()
        
        self.text_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())
        self.link_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())

        self._update_preview_after_id = None
        
        self.slide_images = {}  

        self.root.bind("<F5>", lambda e: self.toggle_presentation())
        self.root.bind("<Control-s>", lambda e: self.save_presentation())         # Uložit
        self.root.bind("<Control-o>", lambda e: self.load_presentation())         # Otevřít
        self.root.bind("<Control-n>", lambda e: self.new_presentation())          # Nová prezentace
        self.root.bind("<Control-p>", lambda e: self.add_image_to_current_slide())# Přidat obrázek
        self.root.bind("<Control-m>", lambda e: self.prepare_new_text_block())    # Nový text
        self.root.bind("<Delete>", lambda e: self.delete_current_content_by_slide())
        self.root.bind("<Control-z>", lambda e: self.undo_delete())
        self.root.bind("<Up>", lambda e: self.prev_raw_slide())
        self.root.bind("<Down>", lambda e: self.next_raw_slide())

        self.bible_data = {}
        self.load_bible_data()
        
        self.undo_stack = []  # 🧠 zásobník pro undo mazání
     
        self.main_frame = tk.Frame(self.root, bg=bg_color)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.left_column = tk.Frame(self.main_frame)
        self.left_column.grid(row=0, column=0, sticky="n")

        self.right_column = tk.Frame(self.main_frame)
        self.right_column.grid(row=0, column=1, sticky="ne", padx=(20, 0))
        
        self.update_monitor_list()
        
        self.text_entry.bind("<Control-Return>", lambda e: self.add_new_text_block())
        
        self.awaiting_new_block = False

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.handle_drop)

        self.hotkey_enabled = tk.BooleanVar(value=False)

    def build_ui(self):
        colors = {
            "bg": "#555555",  # pozadí oken
            "button_bg": "#444444",
            "button_fg": "#ffffff",
            "active_bg": "#666666",
            "active_fg": "#ffffff",
            "entry_bg": "#666666",
            "entry_fg": "#ffffff"
        }
        bg_color = colors['bg']
        btn_bg = colors['button_bg']
        btn_fg = colors['button_fg']
        active_bg = colors['active_bg']
        active_fg = colors['active_fg']
        entry_bg = colors['entry_bg']
        entry_fg = colors['entry_fg']
        btn_style = self.style["mainButton"]
        entry_style = self.style["entryWin"]
        check_style = self.style["checkButton"]
        frame_style = self.style["mainFrame"]

        main = tk.Frame(self.root, bg=bg_color)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=bg_color)
        left.grid(row=0, column=0, sticky="n", padx=10, pady=10)

        right = tk.Frame(main, bg=bg_color)
        right.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        # === HORNÍ TLAČÍTKA ===
        top_controls = tk.Frame(left, bg=bg_color)
        top_controls.pack(anchor="w", pady=(0, 5))

        tk.Button(top_controls, text="➕", command=self.load_presentation,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)
        tk.Button(top_controls, text="🆕 Nová prezentace", command=self.new_presentation,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

        tk.Button(top_controls, text="💾 Uložit", command=self.save_presentation,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)
        
        self.slide_counter_top = tk.Label(top_controls, text="👁 0 / 0",
        font=self.fonts['listfont'], bg=bg_color, fg=btn_fg)
        self.slide_counter_top.pack(side="left", padx=5)

        # === NÁHLED ===
        self.preview_canvas = tk.Canvas(left, bg='black', width=512, height=384, highlightthickness=0)
        self.preview_canvas.pack()

        # Tlačítka pod náhledem
        img_controls = tk.Frame(left, bg=bg_color)
        img_controls.pack(pady=(10, 5))
        tk.Button(img_controls, text="🖼️ Přidat obrázek", command=self.add_image_to_current_slide,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

        tk.Button(img_controls, text="🗑️ Smazat", command=self.delete_current_content_by_slide,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

        tk.Button(img_controls, text="↩ Vrátit", command=self.undo_delete,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)


        top_right = tk.Frame(right, bg=bg_color)
        top_right.pack(anchor="center", pady=(0, 5))  # vystředění

        tk.Button(top_right, text="<", command=self.prev_raw_slide,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg,
                width=3).pack(side="left", padx=3)

        tk.Button(top_right, text=">", command=self.next_raw_slide,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg,
                width=3).pack(side="left", padx=3)
        tk.Button(top_right, text="📖 Přidat verše", command=self.open_bible_import_window,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)
        self.raw_counter = tk.Label(top_right, text="📝 0 / 0",
            font=self.fonts['listfont'],
            bg=bg_color, fg=btn_fg) 
        self.raw_counter.pack(side="left", padx=5)
        tk.Button(top_right, text="Order", command=self.open_slide_reorder_window,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

        self.link_entry = tk.Entry(right, width=50,
                           bg=entry_bg, fg=entry_fg, insertbackground=entry_fg,
                           font=self.fonts['listfont'])
        self.link_entry.insert(0, "Odkaz (např. Jan 3:16)")
        self.link_entry.bind("<FocusIn>", lambda e: self.link_entry.delete(0, "end") if self.link_entry.get() == "Odkaz (např. Jan 3:16)" else None)
        self.link_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())
        self.link_entry.pack(fill="x", pady=(0, 5))

        self.text_entry = tk.Text(right, height=16.5, width=50, wrap="word",
                          bg=entry_bg, fg=entry_fg, insertbackground=entry_fg,
                          font=self.fonts['listfont'])
        self.text_entry.insert("1.0", "Text snímku...")
        self.text_entry.bind("<FocusIn>", lambda e: self.text_entry.delete("1.0", "end") if self.text_entry.get("1.0", "end-1c").strip() == "Text snímku..." else None)
        self.text_entry.bind("<KeyRelease>", lambda e: self.schedule_preview_update())
        self.text_entry.pack(fill="both", expand=False, pady=(0, 5))

        action_btns = tk.Frame(right, bg=bg_color)
        action_btns.pack(pady=5)
        tk.Button(action_btns, text="❌ Smazat slide", command=self.delete_current_raw_slide,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

        tk.Button(action_btns, text="🆕 Nový text", command=self.prepare_new_text_block,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side="left", padx=5)

  
        # === THUMBNAILY === (⬆ přesuneme NAD ovládání)
        self.thumb_outer = tk.Frame(self.root, bg=bg_color, bd=0, highlightthickness=0)
        self.thumb_outer.configure(bg="#222222")
        self.thumb_outer.pack(fill="x", pady=(10, 0))
        self.thumb_canvas = tk.Canvas(self.thumb_outer, height=150, bg="#222222", highlightthickness=0, bd=0)
        self.thumb_scroll = ttk.Scrollbar(self.thumb_outer, orient="horizontal", command=self.thumb_canvas.xview)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TScrollbar",
            troughcolor="#222222", background="#444444",
            bordercolor="#222222", lightcolor="#222222", darkcolor="#222222")

        self.thumb_inner = tk.Frame(self.thumb_canvas, bg="#222222")

        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor="nw")
        self.thumb_canvas.configure(xscrollcommand=self.thumb_scroll.set)
        self.thumb_outer.configure(bg="#222222")

        self.thumb_canvas.pack(side="top", fill="x", expand=True)
        self.thumb_scroll.pack(side="bottom", fill="x")

        self.thumb_canvas.bind("<Enter>", lambda e: self.thumb_canvas.bind_all("<MouseWheel>", self._on_thumb_scroll))
        self.thumb_canvas.bind("<Leave>", lambda e: self.thumb_canvas.unbind_all("<MouseWheel>"))

        # === OVLÁDÁNÍ POD MINI NÁHLEDEM ===
        self.bottom_controls = tk.Frame(self.root, bg=bg_color)
        self.bottom_controls.pack(fill="x", pady=(10, 10))  # ⬅️ Tohle bylo chybějící!

        # LEVÝ BLOK – Poměr stran + monitor + checkbox
        left_block = tk.Frame(self.bottom_controls, bg=bg_color)
        left_block.pack(side="left", padx=20)

        tk.Label(left_block, text="Poměr stran:", font=self.fonts['listfont'], bg=bg_color, fg=btn_fg).pack(anchor="w")
        aspect_menu = ttk.Combobox(left_block, textvariable=self.current_aspect, values=list(self.default_res.keys()), width=5, state='readonly')
        aspect_menu.configure(font=self.fonts['listfont'])
        aspect_menu.pack(anchor="w", pady=(0, 5))

        tk.Label(left_block, text="Monitor:", font=self.fonts['listfont'], bg=bg_color, fg=btn_fg).pack(anchor="w")
        self.monitor_menu = ttk.Combobox(left_block, width=18, state='readonly')
        self.monitor_menu.configure(font=self.fonts['listfont'])
        self.monitor_menu.pack(anchor="w", pady=(0, 5))

        self.allow_lines_check = tk.Checkbutton(left_block,
            text="Povolit více řádků",
            variable=self.allow_all_lines,
            command=self.handle_line_toggle,
            font=self.fonts['listfont'],
            bg=bg_color, fg=btn_fg,
            selectcolor=bg_color, activebackground=bg_color, activeforeground=btn_fg)

        self.allow_lines_check.pack(anchor="w", pady=(0, 5))

        # STŘED (navigace + prezentace) – čisté vycentrování
        center_block = tk.Frame(self.bottom_controls, bg=bg_color)
        center_block.pack(side="left", expand=True, fill="both")

        center_inner = tk.Frame(center_block, bg=bg_color)
        center_inner.place(relx=0.5, rely=0.5, anchor="center")

        nav_controls = tk.Frame(center_inner, bg=bg_color)
        nav_controls.pack()
        tk.Button(nav_controls, text="≪", command=self.jump_to_prev_block, width=5,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side='left', padx=2)

        tk.Button(nav_controls, text="<", command=self.prev_slide, width=5,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side='left', padx=2)
        self.slide_counter = tk.Label(nav_controls, text="👁 0 / 0",
            font=self.fonts['listfont'],
            bg=bg_color, fg=btn_fg)
        self.slide_counter.pack(side='left', padx=10)
        tk.Button(nav_controls, text=">", command=self.next_slide, width=5,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side='left', padx=2)

        tk.Button(nav_controls, text="≫", command=self.jump_to_next_block, width=5,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg).pack(side='left', padx=2)

        run_style = self.style['runOFF']
        self.present_btn = tk.Button(
            center_inner,
            text=run_style['text'],
            bg=run_style['background'],
            fg=run_style['foreground'],
            activebackground=run_style['activebackground'],
            activeforeground=run_style['activeforeground'],
            command=self.toggle_presentation,
            font=self.fonts['buttfont'],
            width=20
        )

        auto_frame = tk.Frame(center_inner, bg=bg_color)
        auto_frame.pack(pady=(10, 0))

        tk.Checkbutton(
            auto_frame,
            text="🔁 Opakovat",
            variable=self.loop_presentation,
            font=self.fonts['listfont'],
            bg=bg_color, fg=btn_fg,
            selectcolor=bg_color,
            activebackground=bg_color,
            activeforeground=btn_fg
        ).pack(side="left", padx=10)
      
        tk.Entry(auto_frame, textvariable=self.auto_interval, width=3,
                font=self.fonts['listfont']).pack(side="left", padx=(0, 10))

        self.auto_button = tk.Button(auto_frame, text="▶ Auto", command=self.toggle_auto_advance,
                font=self.fonts['buttfont'], bg=btn_bg, fg=btn_fg,
                activebackground=active_bg, activeforeground=active_fg)
        self.auto_button.pack(side="left")

        self.present_btn.pack(pady=(5, 0))
    
    def handle_line_toggle(self):
        print("✅ Přepínám režim řádků")
        self.save_current_editor()
        self.generate_preview()

    def add_raw_slide(self):
        link = self.link_entry.get().strip()
        text = self.text_entry.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Prázdný text", "Zadej text snímku před přidáním.")
            return
        self.raw_slides.append({"link": link, "text": text})
        self.current_raw_index = len(self.raw_slides) - 1
        self.generate_preview()

    def add_new_text_block(self):
        self.save_current_editor()
        self.raw_slides.append({"link": "", "text": self.text_entry.get("1.0", "end").strip()})
        self.current_raw_index = len(self.raw_slides) - 1
        self.update_editor_fields()
        self.generate_preview()

    def prev_raw_slide(self):
        self.save_current_editor()
        if self.current_raw_index > 0:
            self.current_raw_index -= 1
            self.update_editor_fields()

    def next_raw_slide(self):
        self.save_current_editor()
        if self.current_raw_index < len(self.raw_slides) - 1:
            self.current_raw_index += 1
            self.update_editor_fields()

    def jump_to_next_block(self):
        i = self.current_slide_index + 1
        while i < len(self.slides):
            if self.slides[i].get("text", "") == "" and not self.slides[i].get("image"):
                self.current_slide_index = i
                self.refresh_preview()
                self.update_thumbnail_bar()
                return
            i += 1

    def jump_to_prev_block(self):
        i = self.current_slide_index - 1
        while i >= 0:
            if self.slides[i].get("text", "") == "" and not self.slides[i].get("image"):
                self.current_slide_index = i
                self.refresh_preview()
                self.update_thumbnail_bar()
                return
            i -= 1

    def save_current_editor(self):
        if 0 <= self.current_raw_index < len(self.raw_slides):
            slide = self.raw_slides[self.current_raw_index]
            if slide.get("image"):
                print("🔍 Obrázkový slide – nic se neukládá")
                return

            link = self.link_entry.get().strip()
            text = self.text_entry.get("1.0", "end").strip()
            slide['link'] = link
            slide['text'] = text
            print(f"✅ Uloženo: {link} | {len(text)} znaků")


    def update_editor_fields(self):
        for widget in [self.link_entry, self.text_entry]:
            widget.config(state="normal")  # obnov editovatelnost

        if 0 <= self.current_raw_index < len(self.raw_slides):
            slide = self.raw_slides[self.current_raw_index]

            if slide.get("image"):
                self.link_entry.delete(0, 'end')
                self.link_entry.insert(0, "[obrázek]")
                self.link_entry.config(state="disabled")

                self.text_entry.delete("1.0", "end")
                self.text_entry.insert("1.0", "🖼 Obrázkový slide")
                self.text_entry.config(state="disabled")
            else:
                self.link_entry.config(state="normal")
                self.text_entry.config(state="normal")

                self.link_entry.delete(0, 'end')
                self.text_entry.delete("1.0", "end")
                self.link_entry.insert(0, slide.get("link", ""))
                self.text_entry.insert("1.0", slide.get("text", ""))

        self.update_counters()
        self.schedule_preview_update()

    def update_counters(self):
        if self.raw_slides:
            raw_text = f"📝 {self.current_raw_index + 1} / {len(self.raw_slides)}"
        else:
            raw_text = "📝 0 / 0"

        if self.slides:
            slide_text = f"👁 {self.current_slide_index + 1} / {len(self.slides)}"
        else:
            slide_text = "👁 0 / 0"

        self.raw_counter.config(text=raw_text)
        self.slide_counter.config(text=slide_text)
        if hasattr(self, 'slide_counter_top'):
            self.slide_counter_top.config(text=slide_text)
            
    def delete_current_content_by_slide(self):
        if not self.slides:
            return

        current = self.slides[self.current_slide_index]

        if current.get("image"):
            self.delete_current_image_slide()
            return

        # 🔲 Pokud je to černý slide (bez textu a obrázku)
        if current.get("text", "") == "" and not current.get("image"):
            import copy
            self.undo_stack.append({
                "raw_slides": copy.deepcopy(self.raw_slides),
                "slide_images": copy.deepcopy(self.slide_images),
                "raw_index": self.current_raw_index,
                "slide_index": self.current_slide_index
            })

            del self.slides[self.current_slide_index]
            del self.slide_to_raw_map[self.current_slide_index]

            if self.current_slide_index >= len(self.slides):
                self.current_slide_index = max(0, len(self.slides) - 1)

            self.refresh_preview()
            self.update_thumbnail_bar()
            return


        # 🔍 Jinak smažeme celý raw blok, ve kterém je tento slide
        raw_index = self.get_raw_index_for_slide(current)
        if raw_index is not None and 0 <= raw_index < len(self.raw_slides):
            self.current_raw_index = raw_index
            self.delete_current_raw_slide()

        
    def refresh_preview(self):
        if not self.slides:
            return

        # Získáme skutečné rozměry prezentace
        pres_width, pres_height = self.get_resolution()
        max_lines = 10 if self.allow_all_lines.get() else 5 # první číslo změní počet řádků při zaškrtnutí
      

        # Stanovíme výšku náhledu (např. 384 px fixně)
        target_height = 384
        aspect_ratio = pres_width / pres_height
        target_width = int(target_height * aspect_ratio)

        # Změníme velikost canvasu podle poměru
        self.preview_canvas.config(width=target_width, height=target_height)
        self.preview_canvas.delete("all")

        # Spočítáme měřítko a vykreslíme scaled náhled
        scale = target_height / pres_height
        scaled_width = int(pres_width * scale)
        scaled_height = int(pres_height * scale)
        offset_x = (target_width - scaled_width) // 2
        offset_y = 0  # protože výška odpovídá, centrovat nemusíme

        max_lines = -1 if self.allow_all_lines.get() else 5

        self.draw_slide_scaled(
            canvas=self.preview_canvas,
            slide=self.slides[self.current_slide_index],
            width=scaled_width,
            height=scaled_height,
            offset_x=offset_x,
            offset_y=offset_y,
            scale=scale,
            max_lines=max_lines
        )

                # Zobraz obrázek (pokud je k dispozici)
        current_slide = self.slides[self.current_slide_index]
        if current_slide.get("image") and current_slide.get("img_data"):
            img_data = base64.b64decode(current_slide["img_data"])

            img = Image.open(BytesIO(img_data))
            margin_x = int(scaled_width * 0.05)
            margin_y = int(scaled_height * 0.05)
            img = img.resize((scaled_width - 2 * margin_x, scaled_height - 2 * margin_y))

            img_tk = ImageTk.PhotoImage(img)
            self.preview_canvas.image = img_tk
            self.preview_canvas.create_image(offset_x + 20, offset_y + 20, anchor="nw", image=img_tk)



        self.update_counters()

    def schedule_preview_update(self):
        print("Aktualizace náhledu...")  # 🧪 debug

        link = self.link_entry.get().strip()
        text = self.text_entry.get("1.0", "end").strip()

        # ✅ 1. Pokud čekáme na nový blok a uživatel něco napsal → vložíme ho
        if self.awaiting_new_block and (link or text):
            print("➕ Vkládám nový blok po psaní...")
            self.awaiting_new_block = False
            self.raw_slides.append({"link": link, "text": text})
            self.current_raw_index = len(self.raw_slides) - 1

        # ✅ 2. Pokud není žádný blok (úplně první psaní) → přidej
        elif not self.raw_slides:
            print("➕ Automaticky přidávám první slide")
            self.raw_slides.append({"link": link, "text": text})
            self.current_raw_index = 0

        # 🔁 3. Zruš předchozí plánovanou aktualizaci
        if self._update_preview_after_id:
            self.root.after_cancel(self._update_preview_after_id)

        # ⏳ 4. Naplánuj novou aktualizaci
        self._update_preview_after_id = self.root.after(300, self.generate_preview)


    def prev_slide(self):
        if self.current_slide_index > 0:
            self.current_slide_index -= 1
            self.refresh_preview()
            self.update_thumbnail_bar()
            if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
                self.fullscreen_canvas.delete("all")
                self.draw_slide(
                    self.slides[self.current_slide_index],
                    self.fullscreen_win.winfo_screenwidth(),
                    self.fullscreen_win.winfo_screenheight(),
                    canvas=self.fullscreen_canvas,
                    fullscreen=True
                )


    def next_slide(self):
        if self.current_slide_index < len(self.slides) - 1:
            self.current_slide_index += 1
            self.refresh_preview()
            self.update_thumbnail_bar()
            if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
                self.fullscreen_canvas.delete("all")
                self.draw_slide(
                    self.slides[self.current_slide_index],
                    self.fullscreen_win.winfo_screenwidth(),
                    self.fullscreen_win.winfo_screenheight(),
                    canvas=self.fullscreen_canvas,
                    fullscreen=True
                )



    def draw_slide_scaled(self, canvas, slide, width, height, offset_x, offset_y, scale, max_lines=5):
        canvas.delete("all")

        font_main = tkFont.Font(family="Calibri", size=int(28 * scale))
        font_link = tkFont.Font(family="Calibri", size=int(24 * scale), slant="italic")

        canvas.create_rectangle(0, 0, canvas.winfo_width(), canvas.winfo_height(), fill="black")

        if slide.get("image") and slide.get("img_data"):
            try:
                img_data = base64.b64decode(slide["img_data"])
                img = Image.open(BytesIO(img_data))

                margin_x = int(width * 0.05)
                margin_y = int(height * 0.05)
                img = img.resize((width - 2 * margin_x, height - 2 * margin_y))
                img_tk = ImageTk.PhotoImage(img)

                canvas.image = img_tk  # udržet referenci
                canvas.create_image(offset_x + margin_x, offset_y + margin_y, anchor="nw", image=img_tk)
            except Exception as e:
                canvas.create_text(
                    offset_x + width // 2,
                    offset_y + height // 2,
                    text="❌ Obrázek nelze načíst",
                    fill="white",
                    font=font_main,
                    anchor="center"
                )
            return

        padding_x = int(40 * scale)
        padding_top = int(height // 6)

        if slide.get("link"):
            canvas.create_text(
                offset_x + width - padding_x,
                offset_y + int(height * 0.08),
                text=slide["link"],
                anchor="ne",  # Zarovnání na pravý okraj
                fill="white",
                font=font_link
            )

        text_lines = slide.get("text", "").split('\n')
        lines = []
        for line in text_lines:
            lines.extend(self.wrap_text(line, font_main, width - 2 * padding_x))

        y = offset_y + padding_top

        visible_lines = lines  # řádkové dělení už provedlo split_text_to_slides

        # Změněné zarovnání na "w" (doleva)
        for line in visible_lines:
            canvas.create_text(
                offset_x + padding_x,  # Změna: přidáme odsazení zleva
                y,
                text=line,
                fill="white",
                font=font_main,
                anchor="w"  # Zarovnání vlevo
            )
            y += font_main.metrics("linespace") + int(4 * scale)

    def draw_slide(self, slide, width, height, canvas, fullscreen=False):
        pres_width, pres_height = self.get_resolution()
        scale = min(width / pres_width, height / pres_height)
        scaled_width = int(pres_width * scale)
        scaled_height = int(pres_height * scale)
        offset_x = (width - scaled_width) // 2
        offset_y = (height - scaled_height) // 2

        max_lines = -1 if self.allow_all_lines.get() else 5
        self.draw_slide_scaled(canvas, slide, scaled_width, scaled_height, offset_x, offset_y, scale, max_lines=max_lines)

    def wrap_text(self, text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            test = current + " " + word if current else word
            # Kontrola, zda aktuální testovací text se vejde do šířky
            if font.measure(test) <= max_width:
                current = test
            else:
                lines.append(current)  # Uložení starého řádku
                current = word  # Nový řádek začíná novým slovem

        if current:
            lines.append(current)  # Přidej poslední řádek

        return lines

    def get_slide_lines(self, slide, font, max_width, max_lines=5):
        text_lines = slide.get("text", "").split('\n')
        lines = []
        for line in text_lines:
            lines.extend(self.wrap_text(line, font, max_width))
        if max_lines > 0:
            lines = lines[:max_lines]
        return lines

    def split_text_to_slides(self, link, text):
        pres_width, _ = self.get_resolution()
        font = tkFont.Font(family="Calibri", size=28)
        max_width = pres_width - 80  # Maximální šířka pro text
        max_lines = 10 if self.allow_all_lines.get() else 5

        def get_wrapped_lines(txt):
            lines = []
            for para in txt.strip().split('\n'):  # Tady už zpracováváme i nové řádky
                wrapped = self.wrap_text(para.strip(), font, max_width)
                lines.extend(wrapped)
            return lines

        slides = []
        current_buffer = ""
        # Zde používáme regulární výraz pro správné dělení po interpunkčních znacích i nových řádcích
        segments = re.split(r'(?<=[.!?,:;])\s+|\n+', text.strip())

        i = 0
        while i < len(segments):
            segment = segments[i].strip()
            if not segment:
                i += 1
                continue

            candidate = f"{current_buffer} {segment}".strip() if current_buffer else segment
            lines = get_wrapped_lines(candidate)

            if len(lines) <= max_lines:
                current_buffer = candidate
                i += 1
            else:
                if current_buffer:
                    slides.append({"link": link, "text": current_buffer.strip()})
                    current_buffer = ""
                else:
                    hard_lines = get_wrapped_lines(segment)
                    for j in range(0, len(hard_lines), max_lines):
                        chunk = " ".join(hard_lines[j:j + max_lines])
                        slides.append({"link": link, "text": chunk})
                    i += 1

        if current_buffer:
            slides.append({"link": link, "text": current_buffer.strip()})

        return slides


    def get_resolution(self):
        return self.default_res[self.current_aspect.get()]

    def start_fullscreen(self):
        if not self.slides or self.current_slide_index >= len(self.slides):
            self.preview_canvas.delete("all")  # 💡 smažeme starý obsah
            return

        self.fullscreen_win = tk.Toplevel(self.root)

        # Získáme vybraný monitor
        selected_index = self.monitor_menu.current()
        if not hasattr(self, 'monitors') or selected_index < 0 or selected_index >= len(self.monitors):
            messagebox.showerror("Chyba", "Nebyl vybrán žádný monitor nebo nelze získat jeho parametry.")
            return

        monitor = self.monitors[selected_index]
        self.fullscreen_win.overrideredirect(True)  # bez rámu
        self.fullscreen_win.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
        self.fullscreen_win.lift()
        self.fullscreen_win.focus_force()
        self.fullscreen_win.bind("<Escape>", lambda e: self.fullscreen_win.destroy())


        self.fullscreen_canvas = tk.Canvas(self.fullscreen_win, bg="black", highlightthickness=0)
        self.fullscreen_canvas.pack(fill="both", expand=True)

        self.draw_slide(self.slides[self.current_slide_index], self.fullscreen_win.winfo_screenwidth(), self.fullscreen_win.winfo_screenheight(), canvas=self.fullscreen_canvas, fullscreen=True)

        self.fullscreen_win.bind("<Escape>", lambda e: self.fullscreen_win.destroy())
        self.fullscreen_win.bind("<Left>", lambda e: self.fullscreen_step(-1))
        self.fullscreen_win.bind("<Right>", lambda e: self.fullscreen_step(1))
        self.fullscreen_win.bind("<Up>", lambda e: self.fullscreen_step(-1))
        self.fullscreen_win.bind("<Down>", lambda e: self.fullscreen_step(1))
        self.fullscreen_win.bind("<Prior>", lambda e: self.fullscreen_step(-1))  # PgUp
        self.fullscreen_win.bind("<Next>", lambda e: self.fullscreen_step(1))    # PgDn
        print("🎬 Fullscreen spuštěn")

    def toggle_presentation(self):
        if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
            # Prezentace běží → zavřeme ji
            self.fullscreen_win.destroy()
            style = self.style['runOFF']
            self.present_btn.config(
                text=style['text'],
                bg=style['background'],
                fg=style['foreground'],
                activebackground=style['activebackground'],
                activeforeground=style['activeforeground']
            )

        else:
            self.start_fullscreen()
            style = self.style['runON']
            self.present_btn.config(
                text=style['text'],
                bg=style['background'],
                fg=style['foreground'],
                activebackground=style['activebackground'],
                activeforeground=style['activeforeground']
            )

    def fullscreen_step(self, direction):
        print(f"📢 fullscreen_step({direction}) byl zavolán")
        print(f"🧪 hotkey_enabled: {self.hotkey_enabled.get()}")

        new_index = self.current_slide_index + direction
        if not (0 <= new_index < len(self.slides)):
            print("❌ Neplatný index, konec")
            return

        prev_slide = self.slides[self.current_slide_index]
        next_slide = self.slides[new_index]

        self.current_slide_index = new_index
        self.draw_slide(
            next_slide,
            self.fullscreen_win.winfo_screenwidth(),
            self.fullscreen_win.winfo_screenheight(),
            canvas=self.fullscreen_canvas,
            fullscreen=True
        )

        def is_black(slide):
            return not slide.get("text") and not slide.get("image")

        from_black = is_black(prev_slide) and not is_black(next_slide)
        to_black = not is_black(prev_slide) and is_black(next_slide)

        print(f"🔎 Předchozí slide je černý: {is_black(prev_slide)}")
        print(f"🔎 Aktuální slide je černý: {is_black(next_slide)}")

        if from_black:
            print("➡️ Přechod z černého na plný")
        elif to_black:
            print("⬅️ Přechod z plného na černý")
        else:
            print("🔁 Jiný přechod (uvnitř bloku)")

    def save_presentation(self):
        self.save_current_editor()
        if not self.raw_slides:
            messagebox.showinfo("Nic k uložení", "Neexistuje žádný obsah k uložení.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.presentation_dir,
            defaultextension=".json",
            filetypes=[("JSON soubory", "*.json")]
        )

        if file_path:
            try:
                # ⬇️ Ujisti se, že img_data je součástí každého obrázkového slidu
                for i, slide in enumerate(self.raw_slides):
                    if slide.get("image"):
                        if i in self.slide_images:
                            slide["img_data"] = self.slide_images[i]

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.raw_slides, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("Uloženo", f"Prezentace byla uložena do {file_path}")

            except Exception as e:
                messagebox.showerror("Chyba při ukládání", str(e))




    def load_presentation(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.presentation_dir,
            filetypes=[("JSON soubory", "*.json")]
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.slides = json.load(f)

                # obnov raw_slides z těchto dat (obnoví i obrázky)
                self.raw_slides = []
                self.slide_images = {}

                for slide in self.slides:
                    if slide.get("image"):
                        self.raw_slides.append({"image": True, "img_data": slide.get("img_data", "")})
                        self.slide_images[len(self.raw_slides) - 1] = slide.get("img_data", "")
                    else:
                        self.raw_slides.append({
                            "link": slide.get("link", ""),
                            "text": slide.get("text", "")
                        })


                self.current_raw_index = 0
                self.update_editor_fields()  # ⬅️ Doplněno!
                self.generate_preview()
                # messagebox.showinfo("Načteno", f"Prezentace byla načtena ze souboru:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Chyba při načítání", str(e))
        image_file = file_path.replace(".json", "_images.json")
        if os.path.exists(image_file):
            with open(image_file, "r", encoding="utf-8") as f:
                self.slide_images = json.load(f)
        else:
            self.slide_images = {}

    def generate_preview(self):
        print("RAW COUNT:", len(self.raw_slides), "| SLIDES COUNT:", len(self.slides))

        self.save_current_editor()  # 🧠 Uloží změny z právě psaného bloku

        self.slide_to_raw_map = []
        self.slides = []
        if not self.raw_slides:
            return

        # Úvodní černý slide
        self.slides.append({"link": "", "text": ""})
        self.slide_to_raw_map.append(None)

        for i, raw in enumerate(self.raw_slides):
            if raw.get("image") and raw.get("img_data"):
                if self.slides and self.slides[-1] != {"link": "", "text": ""}:
                    self.slides.append({"link": "", "text": ""})
                    self.slide_to_raw_map.append(None)

                self.slides.append({
                    "image": True,
                    "img_data": raw["img_data"]
                })
                self.slide_to_raw_map.append(i)

                if i < len(self.raw_slides) - 1:
                    self.slides.append({"link": "", "text": ""})
                    self.slide_to_raw_map.append(None)
                continue

            chunks = self.split_text_to_slides(raw.get("link", ""), raw.get("text", ""))

            if chunks:
                self.slides.extend(chunks)
                self.slide_to_raw_map.extend([i] * len(chunks))
            else:
                self.slides.append({"link": raw.get("link", ""), "text": raw.get("text", "")})
                self.slide_to_raw_map.append(i)





            if i < len(self.raw_slides) - 1:
                self.slides.append({"link": "", "text": ""})
                self.slide_to_raw_map.append(None)

        # Závěrečný černý slide
        self.slides.append({"link": "", "text": ""})
        self.slide_to_raw_map.append(None)

        self.refresh_preview()
        self.update_thumbnail_bar()

        # Pokud je připraven obrázkový slide
        if hasattr(self, '_pending_image_slide'):
            idx, img_slide, encoded = self._pending_image_slide
            self.slides.insert(idx, img_slide)
            self.slide_to_raw_map.insert(idx, idx)  # přidej i do mapy
            self.slide_images[idx] = encoded
            self.current_slide_index = idx
            del self._pending_image_slide

        self.refresh_preview()
        self.update_thumbnail_bar()

        if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
            self.fullscreen_canvas.delete("all")
            self.draw_slide(
                self.slides[self.current_slide_index],
                self.fullscreen_win.winfo_screenwidth(),
                self.fullscreen_win.winfo_screenheight(),
                canvas=self.fullscreen_canvas,
                fullscreen=True
            )

    def update_monitor_list(self):
        from screeninfo import get_monitors
        self.monitors = get_monitors()
        display_list = [
            f"displ {i + 1} ({m.x}, {m.y})"
            for i, m in enumerate(self.monitors)
        ]
        self.monitor_menu['values'] = display_list
        self.monitor_menu.current(1) #  podle čísla vyber výchozí monitor

    def update_thumbnail_bar(self):
        for widget in self.thumb_inner.winfo_children():
            widget.destroy()

        if not self.slides:
            label = tk.Label(
                self.thumb_inner,
                text="Žádné slidy",
                fg="white",
                bg="#222222",
                font=("Calibri", 14, "italic"),
                padx=20, pady=10
            )
            label.pack()
            return


        pres_width, pres_height = self.get_resolution()
        thumb_height = 300
        aspect_ratio = pres_width / pres_height
        thumb_width = int(thumb_height * aspect_ratio)
        self.thumb_canvas.config(height=thumb_height)

        for i, slide in enumerate(self.slides):
            is_active = (i == self.current_slide_index)
            canvas = tk.Canvas(
                self.thumb_inner,
                width=thumb_width,
                height=thumb_height,
                bg="black",
                highlightthickness=2 if is_active else 0,
                highlightbackground="#dbdbdb" if is_active else "#000000",
                bd=0,
                relief="flat"
            )


            canvas.delete("all")  # 💡 smaže starý obsah při přegenerování
            canvas.grid(row=0, column=i, padx=2, pady=2)

            def jump(index=i):
                self.current_slide_index = index
                self.refresh_preview()
                self.update_thumbnail_bar()
                if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
                    self.fullscreen_canvas.delete("all")
                    self.draw_slide(
                        self.slides[self.current_slide_index],
                        self.fullscreen_win.winfo_screenwidth(),
                        self.fullscreen_win.winfo_screenheight(),
                        canvas=self.fullscreen_canvas,
                        fullscreen=True
                    )

            canvas.bind("<Button-1>", lambda e, idx=i: jump(idx))

            # 🖼 Zmenšené vykreslení obsahu slidu (text/obrázek)
            scale = thumb_height / pres_height
            scaled_width = int(pres_width * scale)
            scaled_height = int(pres_height * scale)
            offset_x = (thumb_width - scaled_width) // 2
            offset_y = 0

            self.draw_slide_scaled(
                canvas=canvas,
                slide=slide,
                width=scaled_width,
                height=scaled_height,
                offset_x=offset_x,
                offset_y=offset_y,
                scale=scale,
                max_lines=-1  # zobraz vše
            )


    def get_scaled_slide_dimensions(self, target_height):
        pres_width, pres_height = self.get_resolution()
        scale = target_height / pres_height
        width = int(pres_width * scale)
        height = int(pres_height * scale)
        return width, height, scale

    def add_image_to_current_slide(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if not file_path:
            return

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        image_slide = {"image": True, "img_data": encoded}

        # 🧠 Zjisti, kde v RAW se nachází aktuální slide (včetně těch rozdělených!)
        slide_index = self.current_slide_index
        raw_index = None
        raw_counter = 0

        for i, raw in enumerate(self.raw_slides):
            if raw.get("image"):
                if slide_index == 0:
                    raw_index = i
                    break
                slide_index -= 3  # 1 obrázek = 3 slidy (černý, obrázkový, černý)
            else:
                split = self.split_text_to_slides(raw.get("link", ""), raw.get("text", ""))
                num_slides = len(split) if not self.allow_all_lines.get() else 1
                if slide_index < num_slides:
                    raw_index = i
                    break
                slide_index -= num_slides + 1  # +1 za černý meziblock

        if raw_index is None:
            raw_index = len(self.raw_slides) - 1

        insert_index = raw_index + 1
        self.raw_slides.insert(insert_index, image_slide)
        self.slide_images[insert_index] = encoded
        self.current_raw_index = insert_index

        self.generate_preview()
        self.update_editor_fields()

    def handle_drop(self, event):
        file_path = event.data.strip()
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]  # odeber složené závorky z cesty

        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.insert_image_from_path(file_path)

    def insert_image_from_path(self, file_path):
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        image_slide = {"image": True, "img_data": encoded}
        self.raw_slides.append(image_slide)
        self.current_raw_index = len(self.raw_slides) - 1
        self.slide_images[self.current_raw_index] = encoded
        self.generate_preview()
        self.update_editor_fields()

    def new_presentation(self):
        if messagebox.askyesno("Nová prezentace", "Opravdu chceš vytvořit novou prázdnou prezentaci?"):
            self.raw_slides = []
            self.slides = []
            self.slide_images = {}
            self.current_raw_index = 0
            self.current_slide_index = 0

            # 🧹 vyčisti pole pro úpravu
            self.link_entry.config(state="normal")
            self.text_entry.config(state="normal")
            self.link_entry.delete(0, 'end')
            self.text_entry.delete("1.0", "end")

            # 🧼 zruš pending obrázek, pokud existuje
            if hasattr(self, '_pending_image_slide'):
                del self._pending_image_slide

            # 🌀 obnov UI
            self.refresh_preview()
            self.update_counters()
            self.update_thumbnail_bar()

            self.preview_canvas.delete("all")

    def delete_current_raw_slide(self):
        if 0 <= self.current_raw_index < len(self.raw_slides):
            idx = self.current_raw_index

            # 🧠 Uložit kopii přes deepcopy – jinak to později ukazuje na jiný objekt
            import copy
            deleted = copy.deepcopy(self.raw_slides[idx])

            import copy
            self.undo_stack.append({
                "raw_slides": copy.deepcopy(self.raw_slides),
                "slide_images": copy.deepcopy(self.slide_images),
                "raw_index": self.current_raw_index,
                "slide_index": self.current_slide_index
            })

            del self.raw_slides[idx]

            if not self.raw_slides:
                self.new_presentation()
                return

            if idx >= len(self.raw_slides):
                idx = len(self.raw_slides) - 1

            self.current_raw_index = idx
            self.update_editor_fields()
            self.generate_preview()

    def delete_current_image_slide(self):
        if not self.slides:
            return

        # 🧠 Smažeme celý blok (černý + obrázek + černý)
        index = self.current_slide_index

        # ⬅️ Posuň se na střední obrázkový slide, pokud jsme klikli na černý před/po
        if 0 < index < len(self.slides) - 1:
            if self.slides[index].get("text", "") == "" and not self.slides[index].get("image"):
                # Jsme na černém slidu – zkus najít obrázkový slide vedle
                if self.slides[index + 1].get("image"):
                    index += 1
                elif self.slides[index - 1].get("image"):
                    index -= 1

        # Teď by index měl být obrázkový slide
        if not self.slides[index].get("image"):
            messagebox.showinfo("Nelze smazat", "Tento slide není obrázkový.")
            return

        # 🧼 Smažeme 3 slidy: černý, obrázkový, černý
        start = max(0, index - 1)
        end = min(len(self.slides), index + 2)

        del self.slides[start:end]
        del self.slide_to_raw_map[start:end]

        # 🧹 najdi a smaž raw_slide odpovídající obrázku
        raw_index = self.get_raw_index_for_slide(self.slides[index - 1]) if index - 1 < len(self.slides) else None
        if raw_index is not None and 0 <= raw_index < len(self.raw_slides):
            # 🧠 Ulož do undo zásobníku
            import copy
            self.undo_stack.append({
                "raw_slides": copy.deepcopy(self.raw_slides),
                "slide_images": copy.deepcopy(self.slide_images),
                "raw_index": self.current_raw_index,
                "slide_index": self.current_slide_index
            })

            del self.raw_slides[raw_index]
            self.slide_images.pop(raw_index, None)


        # Posuň aktuální index
        self.current_slide_index = max(0, start)

        # Obnov vše
        self.refresh_preview()
        self.update_thumbnail_bar()
        self.update_editor_fields()


    def open_slide_reorder_window(self):
        colors = {
            "bg": "#444444",
            "fg": "#ffffff",
            "active": "#666666"
        }
        font = self.fonts['listfont']
        def save_and_close():
            if messagebox.askyesno("Uložit změny", "Chceš zachovat nové pořadí slideů?"):
                new_order = [self.raw_slides[i] for i in order]
                self.raw_slides = new_order
                self.current_raw_index = 0
                self.generate_preview()
                self.update_editor_fields()
            reorder_win.destroy()

        reorder_win = tk.Toplevel(self.root)
        reorder_win.title("Přeházet slidy")
        reorder_win.configure(bg=colors["bg"])
        reorder_win.geometry("500x500")

        frame = tk.Frame(reorder_win, bg=colors["bg"])
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame, bg=colors["bg"], highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=colors["bg"])
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.reorder_items = []
        order = list(range(len(self.raw_slides)))
        dragged_index = [None]

        def create_row(idx, text):
            row = tk.Frame(scrollable_frame, bg=colors["bg"], relief="flat", borderwidth=1)
            row.pack(fill="x", pady=2)

            label = tk.Label(row, text=text, bg=colors["bg"], fg=colors["fg"], anchor="w", padx=10, pady=5, font=font)
            label.pack(fill="both", expand=True)

            def on_click(event, i=idx):
                dragged_index[0] = i
                row.config(bg=colors["active"])
                label.config(bg=colors["active"])

            def on_release(event):
                row.config(bg=colors["bg"])
                label.config(bg=colors["bg"])

            def on_drag_motion(e):
                if dragged_index[0] is None:
                    return
                y = row.winfo_pointery() - reorder_win.winfo_rooty()
                for j, widget in enumerate(self.reorder_items):
                    if widget.winfo_y() < y < widget.winfo_y() + widget.winfo_height():
                        if j != dragged_index[0]:
                            order[dragged_index[0]], order[j] = order[j], order[dragged_index[0]]
                            self.reorder_items[dragged_index[0]], self.reorder_items[j] = self.reorder_items[j], self.reorder_items[dragged_index[0]]
                            for widget in self.reorder_items:
                                widget.pack_forget()
                            for widget in self.reorder_items:
                                widget.pack(fill="x", pady=2)
                            dragged_index[0] = j
                        break

            # Bind na oba – na celý řádek i jeho label
            for widget in [row, label]:
                widget.bind("<Button-1>", on_click)
                widget.bind("<ButtonRelease-1>", on_release)
                widget.bind("<B1-Motion>", on_drag_motion)

            return row


        for i, slide in enumerate(self.raw_slides):
            if slide.get("image"):
                txt = f"🖼 Obrázek {i + 1}"
            elif slide.get("link"):
                txt = slide["link"]
            else:
                txt = ' '.join(slide.get("text", "").split()[:5]) + "..."
            self.reorder_items.append(create_row(i, txt))

        reorder_win.protocol("WM_DELETE_WINDOW", save_and_close)

    def get_raw_index_for_slide(self, slide):
        try:
            index = self.slides.index(slide)
            return self.slide_to_raw_map[index]
        except:
            return None


    def close_fullscreen_if_open(self, event=None):
        if hasattr(self, 'fullscreen_win') and self.fullscreen_win.winfo_exists():
            self.fullscreen_win.destroy()
    
    def load_bible_data(self):
        bible_dir = os.path.join(os.path.dirname(__file__), "bible")
        if not os.path.exists(bible_dir):
            return

        for file in os.listdir(bible_dir):
            if file.lower().endswith(".json"):
                translation = os.path.splitext(file)[0].split("_")[-1]
                try:
                    with open(os.path.join(bible_dir, file), "r", encoding="utf-8") as f:
                        self.bible_data[translation] = json.load(f)
                except Exception as e:
                    print(f"Chyba při načítání {file}: {e}")

    def _on_thumb_scroll(self, event):
        direction = -1 if event.delta > 0 else 1  
        self.thumb_canvas.xview_scroll(direction, "units")
    # Tento kód vlož DO TÉTO TŘÍDY (PresentationEditor):

    def open_bible_import_window(self):
        colors = {
            "bg": "#555555",  # pozadí
            "fg": "#ffffff",
            "entry_bg": "#666666",
            "entry_fg": "#ffffff",
            "btn_bg": "#444444",
            "btn_fg": "#ffffff",
            "active_bg": "#666666",
            "active_fg": "#ffffff"
        }
        font = self.fonts["listfont"]

        if getattr(self, "bible_window", None) is not None and self.bible_window.winfo_exists():
            self.bible_window.lift()
            return

        if not self.bible_data:
            messagebox.showerror("Chyba", "Nebyla načtena žádná Bible.")
            return

        win = tk.Toplevel(self.root)
        self.bible_window = win
        win.title("Vložit verš")
        win.configure(bg=colors["bg"])
        main_frame = tk.Frame(win, bg=colors["bg"])
        win.geometry("800x500")
        left_frame = tk.Frame(main_frame, bg=colors["bg"])
        right_frame = tk.Frame(main_frame, bg=colors["bg"])
        bottom = tk.Frame(win, bg=colors["bg"])
        
        def on_bible_window_close():
            self.bible_window = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_bible_window_close)


        main_frame = tk.Frame(win, bg=colors["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.rowconfigure(0, weight=1)

        left_frame = tk.Frame(main_frame, bg=colors["bg"])
        left_frame.grid(row=0, column=0, sticky="nsw")

        right_frame = tk.Frame(main_frame, bg=colors["bg"])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))


        # Lokální proměnné (MUSÍ BÝT PŘED vytvořením comboboxu)
        selected_translation = tk.StringVar(value="CSP" if "CSP" in self.bible_data else list(self.bible_data.keys())[0])
        selected_book = tk.StringVar()
        from_chapter = tk.StringVar()
        to_chapter = tk.StringVar()
        from_verse = tk.StringVar()
        to_verse = tk.StringVar()

        # 📡 Automatické aktualizace výběru + náhledu
        selected_translation.trace_add("write", lambda *a: [update_books(), update_preview()])
        selected_book.trace_add("write", lambda *a: [update_chapter_and_verse_limits(), update_preview()])
        from_chapter.trace_add("write", lambda *a: [update_chapter_and_verse_limits(), update_preview()])
        to_chapter.trace_add("write", lambda *a: [update_chapter_and_verse_limits(), update_preview()])
        from_verse.trace_add("write", lambda *a: [update_verse_limits(), update_preview()])
        to_verse.trace_add("write", lambda *a: [update_verse_limits(), update_preview()])

        # Překlad
        tk.Label(left_frame, bg=colors["bg"], fg=colors["fg"], font=font).pack(anchor="w")
        translation_box = ttk.Combobox(left_frame, textvariable=selected_translation, state="readonly", width=25)
        translation_box['values'] = list(self.bible_data.keys())
        translation_box.configure(font=self.fonts['listfont'])
        translation_box.pack(anchor="w", pady=(0, 10))

        def update_books(*args):
            books = list(self.bible_data[selected_translation.get()].keys())
            book_combobox['values'] = books
            if books:
                selected_book.set(books[0])
                update_chapter_and_verse_limits()

        selected_translation.trace_add("write", update_books)

        # Kniha
        tk.Label(left_frame, bg=colors["bg"], fg=colors["fg"], font=font).pack(anchor="w")
        book_combobox = ttk.Combobox(left_frame, textvariable=selected_book, state="normal", width=25)
        book_combobox.configure(font=self.fonts['listfont'])
        book_combobox.pack(anchor="w", pady=(0, 10))
        placeholder_lbl = tk.Label(
            left_frame,
            text="Vyber knihu",
            fg="gray",
            bg="white",
            font=(self.fonts['listfont'].actual('family'), 9)  # použij stejné písmo, ale menší velikost
        )

        placeholder_lbl.place(in_=book_combobox, relx=0.02, rely=0.15)
        selected_book.trace_add("write", lambda *a: placeholder_lbl.place_forget() if selected_book.get() else placeholder_lbl.place(in_=book_combobox, relx=0.02, rely=0.15))

        # Kapitoly
        tk.Label(left_frame, text="Kapitoly:", bg=colors["bg"], fg=colors["fg"], font=font).pack(anchor="w")
        ch_frame = tk.Frame(left_frame, bg=colors["bg"])
        ch_frame.pack(anchor="w", pady=(0, 10))

        tk.Label(ch_frame, text="Od:", bg=colors["bg"], fg=colors["fg"], font=font).pack(side="left")
        from_chapter_box = ttk.Combobox(ch_frame, textvariable=from_chapter, width=5)
        from_chapter_box.configure(font=self.fonts['listfont'])
        from_chapter_box.pack(side="left", padx=(5, 15))

        tk.Label(ch_frame, text="Do:", bg=colors["bg"], fg=colors["fg"], font=font).pack(side="left")
        to_chapter_box = ttk.Combobox(ch_frame, textvariable=to_chapter, width=5)
        to_chapter_box.configure(font=self.fonts['listfont'])
        to_chapter_box.pack(side="left", padx=(5, 0))

        # Verše
        tk.Label(left_frame, text="Verše:", bg=colors["bg"], fg=colors["fg"], font=font).pack(anchor="w")
        v_frame = tk.Frame(left_frame, bg=colors["bg"])
        v_frame.pack(anchor="w", pady=(0, 10))

        tk.Label(v_frame, text="Od:", bg=colors["bg"], fg=colors["fg"], font=font).pack(side="left")
        from_verse_box = ttk.Combobox(v_frame, textvariable=from_verse, width=5)
        from_verse_box.configure(font=self.fonts['listfont'])
        from_verse_box.pack(side="left", padx=(5, 15))

        tk.Label(v_frame, text="Do:", bg=colors["bg"], fg=colors["fg"], font=font).pack(side="left")
        to_verse_box = ttk.Combobox(v_frame, textvariable=to_verse, width=5)
        to_verse_box.configure(font=self.fonts['listfont'])
        to_verse_box.pack(side="left", padx=(5, 0))

        def hide_placeholder(*args):
            if selected_book.get():
                placeholder_lbl.place_forget()
            else:
                placeholder_lbl.place(in_=book_combobox, relx=0.02, rely=0.15)

        # 📌 Sleduj změny a fokus
        selected_book.trace_add("write", hide_placeholder)
        book_combobox.bind("<FocusIn>", hide_placeholder)
        book_combobox.bind("<FocusOut>", hide_placeholder)

        # 📚 Předvyplň knihy
        book_combobox['values'] = list(self.bible_data[selected_translation.get()].keys())

        def update_chapter_and_verse_limits(*args):
            translation = selected_translation.get()
            book = selected_book.get()
            if translation in self.bible_data and book in self.bible_data[translation]:
                chapters = self.bible_data[translation][book]
                max_ch = max(int(c) for c in chapters)
                ch_values = list(range(1, max_ch + 1))
                from_chapter_box["values"] = ch_values
                to_chapter_box["values"] = ch_values

                # ✅ Odložená kontrola správnosti rozsahu
                def delayed_chapter_check():
                    fc = from_chapter.get()
                    tc = to_chapter.get()

                    if fc.isdigit():
                        fc_val = int(fc)
                        if not tc.isdigit() or int(tc) < fc_val:
                            to_chapter.set(str(fc_val))

                win.after(200, delayed_chapter_check)


                update_verse_limits()


        def update_verse_limits(*args):
            translation = selected_translation.get()
            book = selected_book.get()
            fc = from_chapter.get()
            tc = to_chapter.get()

            if translation in self.bible_data and book in self.bible_data[translation] and fc.isdigit():
                chapter_data = self.bible_data[translation][book]
                verses = chapter_data.get(fc, {})
                max_verse = max(map(int, verses.keys())) if verses else 1
                verse_values = list(range(1, max_verse + 1))
                from_verse_box["values"] = verse_values
                to_verse_box["values"] = verse_values

            def delayed_verse_check():
                fv = from_verse.get()
                tv = to_verse.get()
                fc = from_chapter.get()
                tc = to_chapter.get()

                if fv.isdigit():
                    fv_val = int(fv)
                    same_chapter = fc == tc

                    if not tv.isdigit():
                        if same_chapter:
                            to_verse.set(str(fv_val))
                        else:
                            to_verse.set("1")

                    elif same_chapter and int(tv) < fv_val:
                        to_verse.set(str(fv_val))

            win.after(200, delayed_verse_check)


        def set_defaults():
            first_book = list(self.bible_data[selected_translation.get()].keys())[0]
            book_combobox.set(first_book)
            selected_book.set(first_book)
            from_chapter.set("1")
            to_chapter.set("1")
            from_verse.set("1")
            to_verse.set("1")
            update_chapter_and_verse_limits()

        # Bindy na změny
        selected_book.trace_add("write", update_chapter_and_verse_limits)
        from_chapter.trace_add("write", update_verse_limits)
        to_chapter.trace_add("write", update_verse_limits)

        # ⬇️ Zavoláme výchozí nastavení
        # set_defaults()


        from_chapter.trace_add("write", update_verse_limits)
        to_chapter.trace_add("write", update_verse_limits)

        preview = tk.Text(
            right_frame,
            height=18,
            wrap="word",
            bg=colors["entry_bg"],     # ✅ tmavé pozadí
            fg=colors["entry_fg"],
            insertbackground=colors["entry_fg"],
            selectbackground="#888888",
            selectforeground="#ffffff",
            font=font
        )
        preview.pack(fill="both", expand=True)


        bottom = tk.Frame(win, bg=colors["bg"])
        bottom.pack(fill="x", pady=(10, 10))

        def add_to_slides():
            try:
                translation = selected_translation.get()
                book = selected_book.get()
                fc, tc = int(from_chapter.get()), int(to_chapter.get())
                fv, tv = int(from_verse.get()), int(to_verse.get())
                raw_text = preview.get("1.0", "end").strip()
                text = raw_text
                if not keep_verse_numbers.get():
                    # Odstraní čísla veršů typu "1:1", "2:5" na začátku řádku nebo věty
                    text = re.sub(r"\b\d+:\d+\s*", "", raw_text)


                # Odstranění nových řádků → spojení do jednoho odstavce
                joined_text = " ".join(raw_text.splitlines())

                # ODKAZ (bez mezer)
                if fc == tc:
                    link = f"{book} {fc}:{fv}-{tv}"
                else:
                    link = f"{book} {fc}:{fv}–{tc}:{tv}"

                self.save_current_editor()  # 🛠️ Ulož rozpracované pole

                self.raw_slides.append({
                    "link": link,
                    "text": " ".join(text.splitlines())
                })

                self.current_raw_index = len(self.raw_slides) - 1
                self.update_editor_fields()
                self.generate_preview()
                self.update_editor_fields()
                win.destroy()

            except Exception as e:
                messagebox.showerror("Chyba", str(e))

        keep_verse_numbers = tk.BooleanVar(value=False) # True = zaškrtnuto, False = opak kdyby byla preference mít čísla veršů
        tk.Checkbutton(
            bottom,
            text="Zobrazit čísla veršů",
            variable=keep_verse_numbers,
            bg=colors["bg"],
            fg=colors["fg"],
            selectcolor=colors["bg"],
            activebackground=colors["active_bg"],
            activeforeground=colors["active_fg"],
            font=font
        ).pack(anchor="center")

        
        tk.Button(bottom, text="Vložit jako nový slide", command=add_to_slides,
            font=self.fonts['buttfont'], bg="#444444", fg="#ffffff",
            activebackground="#666666", activeforeground="#ffffff").pack(anchor="center")      

        def update_preview():
            try:
                # Kontrola, zda jsou všechna čísla vyplněná
                if not (from_chapter.get().isdigit() and to_chapter.get().isdigit() and
                        from_verse.get().isdigit() and to_verse.get().isdigit()):
                    preview.delete("1.0", "end")
                    preview.insert("1.0", "Zadej výběr kapitol a veršů.")
                    return

                translation = selected_translation.get()
                book = selected_book.get()
                fc, tc = int(from_chapter.get()), int(to_chapter.get())
                fv, tv = int(from_verse.get()), int(to_verse.get())

                chapters = self.bible_data[translation][book]

                result = []
                for c in range(fc, tc + 1):
                    verses = chapters.get(str(c), {})
                    for v in sorted(verses, key=lambda x: int(x)):
                        num = int(v)
                        if (c == fc and num < fv) or (c == tc and num > tv):
                            continue
                        result.append(f"{c}:{v} {verses[v]}")
                preview.delete("1.0", "end")
                preview.insert("1.0", "\n".join(result))
            except Exception as e:
                preview.delete("1.0", "end")
                preview.insert("1.0", f"Chyba: {e}")

        def copy_to_clipboard():
            text = preview.get("1.0", "end").strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()

        # Tlačítka pod verše (vlevo)
        btns = tk.Frame(left_frame, bg=colors["bg"], bd=0, highlightthickness=0)
        btns.pack(anchor="w", pady=(0, 10))

        tk.Button(btns, text="📋 Zkopírovat do schránky", command=copy_to_clipboard,
            font=self.fonts['buttfont'], bg=colors["btn_bg"], fg=colors["btn_fg"],
            activebackground=colors["active_bg"], activeforeground=colors["active_fg"],
            bd=0, highlightthickness=0).pack(anchor="w", pady=2)


    def undo_delete(self):
        if not self.undo_stack:
            return

        last = self.undo_stack.pop()

        self.raw_slides = last["raw_slides"]
        self.slide_images = last["slide_images"]
        self.current_raw_index = last.get("raw_index", 0)
        self.current_slide_index = last.get("slide_index", 0)

        self.update_editor_fields()
        self.generate_preview()

    def prepare_new_text_block(self):
        self.awaiting_new_block = True

        self.link_entry.config(state="normal")
        self.text_entry.config(state="normal")
        self.link_entry.delete(0, 'end')
        self.text_entry.delete("1.0", "end")

        self.current_raw_index = len(self.raw_slides)  # ještě neexistuje, ale takhle budeme vědět, kam jej případně vložit
        self.update_counters()

    def load_gui_style(self):
        path = os.path.join(os.path.dirname(__file__), "gui_style.json")
        with open(path, 'r', encoding='utf-8') as f:
            dta = json.load(f)
            return dta[dta["def_style"]]

    def load_fonts(self, fonts_config):
        fonts = {}
        for font in fonts_config:
            fonts[font['name']] = tkFont.Font(
                family=font['family'],
                size=font['size'],
                weight=font['weight']
            )
        return fonts

    def toggle_auto_advance(self):
        self.auto_advance = not self.auto_advance

        if self.auto_advance:
            self.auto_button.config(text="⏹ Stop")
            self.schedule_auto_advance()
        else:
            if self.auto_timer_id:
                self.root.after_cancel(self.auto_timer_id)
                self.auto_timer_id = None
            self.auto_button.config(text="▶ Auto")

    def schedule_auto_advance(self):
        if not self.auto_advance:
            return

        if self.current_slide_index < len(self.slides) - 1:
            self.next_slide()
            self.auto_timer_id = self.root.after(self.auto_interval.get() * 1000, self.schedule_auto_advance)
        else:
            if self.loop_presentation.get():
                self.current_slide_index = 0
                self.refresh_preview()
                self.auto_timer_id = self.root.after(self.auto_interval.get() * 1000, self.schedule_auto_advance)
            else:
                self.auto_advance = False
                self.auto_timer_id = None
                self.auto_button.config(text="▶ Auto")

    def is_black_slide(self, slide):
        return not slide.get("text") and not slide.get("image")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = PresentationEditor(root)
    root.mainloop()