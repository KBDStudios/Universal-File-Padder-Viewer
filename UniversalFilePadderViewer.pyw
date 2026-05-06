import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import io
import sys
import subprocess
import webbrowser
import threading

# --- Auto-Installer and Bypass Logic ---
PILLOW_AVAILABLE = False
Image = None
ImageTk = None
ImageSequence = None

def try_import_pillow():
    global PILLOW_AVAILABLE, Image, ImageTk, ImageSequence
    try:
        from PIL import Image as PILImage, ImageTk as PILImageTk, ImageSequence as PILImageSequence
        Image = PILImage
        ImageTk = PILImageTk
        ImageSequence = PILImageSequence
        PILLOW_AVAILABLE = True
        
        # HEIC/HEIF Support
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
            
        return True
    except ImportError:
        return False

if not try_import_pillow():
    temp_root = tk.Tk()
    temp_root.withdraw() 
    
    msg = ("The live image preview feature requires the 'Pillow' Python library.\n\n"
           "Would you like to try installing it automatically right now?\n\n"
           "(Click 'No' to bypass this and run the app anyway. You just won't be able to preview images.)")
    
    if messagebox.askyesno("Missing Library (Pillow)", msg):
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "pillow-heif", "--upgrade"], 
                           check=True, capture_output=True, text=True)
            if not try_import_pillow():
                messagebox.showwarning("Fallback", "Installation completed, but Pillow still couldn't be loaded.\n\nThe app will now launch without image previews.")
        except subprocess.CalledProcessError as e:
            messagebox.showwarning("Install Failed", f"Auto-installation failed.\nYou can install it manually later by opening your command prompt and typing:\n\npip install pillow pillow-heif\n\nThe app will now launch without image previews.")
        except Exception as e:
            messagebox.showwarning("Install Failed", f"An unexpected error occurred:\n{e}\n\nThe app will now launch without image previews.")
    
    temp_root.destroy()
# ---------------------------------------

# Modern UI Font Configuration
MAIN_FONT = ("Segoe UI", 10)
BOLD_FONT = ("Segoe UI", 10, "bold")
TITLE_FONT = ("Segoe UI", 14, "bold")

SUPPORTED_IMAGES = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tga', '.webp', '.heic', '.heif', '.avif', '.gif'}
MAX_PAD_BYTES = 5 * 1024**3  # 5 GB Maximum Limit

# --- Full Image Viewer with Zoom & Magnifier ---
class FullImageViewer(tk.Toplevel):
    def __init__(self, parent, file_path, title_text="Full Resolution Viewer"):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("800x650")
        
        try:
            self.original_img = Image.open(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image:\n{e}")
            self.destroy()
            return

        self.scale_factor = 1.0
        
        toolbar = ttk.Frame(self, relief=tk.FLAT, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Button(toolbar, text="Zoom In (+)", command=self.zoom_in, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Zoom Out (-)", command=self.zoom_out, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Reset View", command=self.zoom_reset, width=10).pack(side=tk.LEFT, padx=5)
        
        self.lbl_zoom = ttk.Label(toolbar, text="100%", font=BOLD_FONT)
        self.lbl_zoom.pack(side=tk.LEFT, padx=10)

        frame_canvas = ttk.Frame(self)
        frame_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        vbar = ttk.Scrollbar(frame_canvas, orient=tk.VERTICAL)
        hbar = ttk.Scrollbar(frame_canvas, orient=tk.HORIZONTAL)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(frame_canvas, xscrollcommand=hbar.set, yscrollcommand=vbar.set, cursor="crosshair", bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)
        
        self.lens_size = 200
        self.zoom_factor = 2 
        
        self.img_id = self.canvas.create_image(0, 0, anchor="nw")
        self.lens_id = self.canvas.create_image(0, 0, anchor="center", state="hidden")
        self.lens_rect_id = self.canvas.create_rectangle(0, 0, 0, 0, outline="#00a8ff", width=2, state="hidden")
        self.lens_photo = None
        self.tk_img = None
        
        self.redraw_image()

        self.canvas.bind("<Motion>", self.update_magnifier)
        self.canvas.bind("<Leave>", self.hide_magnifier)
        self.canvas.bind("<Enter>", self.show_magnifier)

    def redraw_image(self):
        new_width = max(1, int(self.original_img.width * self.scale_factor))
        new_height = max(1, int(self.original_img.height * self.scale_factor))
        
        resample_method = Image.Resampling.NEAREST if self.scale_factor >= 1.0 else Image.Resampling.LANCZOS
        resized = self.original_img.resize((new_width, new_height), resample_method)
        
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.img_id, image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.lbl_zoom.config(text=f"{int(self.scale_factor * 100)}%")

    def zoom_in(self):
        self.scale_factor *= 1.25
        self.redraw_image()

    def zoom_out(self):
        self.scale_factor *= 0.8
        self.redraw_image()
        
    def zoom_reset(self):
        self.scale_factor = 1.0
        self.redraw_image()

    def update_magnifier(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        orig_x = cx / self.scale_factor
        orig_y = cy / self.scale_factor
        crop_size = self.lens_size / self.zoom_factor
        half_crop = crop_size / 2
        
        left = orig_x - half_crop
        top = orig_y - half_crop
        right = orig_x + half_crop
        bottom = orig_y + half_crop
        
        try:
            cropped = self.original_img.crop((left, top, right, bottom))
            zoomed = cropped.resize((self.lens_size, self.lens_size), Image.Resampling.NEAREST)
            self.lens_photo = ImageTk.PhotoImage(zoomed)
            self.canvas.itemconfig(self.lens_id, image=self.lens_photo)
            self.canvas.coords(self.lens_id, cx, cy)
            offset = self.lens_size / 2
            self.canvas.coords(self.lens_rect_id, cx - offset, cy - offset, cx + offset, cy + offset)
        except Exception:
            pass 

    def hide_magnifier(self, event):
        self.canvas.itemconfig(self.lens_id, state="hidden")
        self.canvas.itemconfig(self.lens_rect_id, state="hidden")

    def show_magnifier(self, event):
        self.canvas.itemconfig(self.lens_id, state="normal")
        self.canvas.itemconfig(self.lens_rect_id, state="normal")
# ---------------------------------------

class FilePadderApp:
    def __init__(self, root):
        self.root = root
        title = "Universal File Padder & Viewer" if PILLOW_AVAILABLE else "Universal File Padder (Previews Disabled)"
        self.root.title(title)
        self.root.geometry("1300x750")
        
        # Apply modern theme
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        style.configure(".", font=MAIN_FONT)
        style.configure("TButton", padding=5)
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=BOLD_FONT, background="#e1e1e1")
        style.configure("TLabelframe", font=BOLD_FONT)
        style.configure("TLabelframe.Label", font=BOLD_FONT, foreground="#005a9e")
        
        self.files_data = [] 
        
        self.gallery_image_refs = {} 
        self.gallery_frame_widgets = {} 
        self.play_btn_refs = {} 
        
        self.is_syncing = False 
        self.current_unit = "Bytes" 
        
        # Animation States
        self.active_anim_job = None
        self.active_anim_index = None
        self.current_frame = 0
        self.loading_win = None

        self.setup_ui()

    def format_size(self, size_in_bytes):
        """Returns an auto-formatted, user-friendly string format for file sizes."""
        if size_in_bytes < 1024:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1024**2:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024**3:
            return f"{size_in_bytes / 1024**2:.2f} MB"
        else:
            return f"{size_in_bytes / 1024**3:.2f} GB"

    def format_display_size(self, size_in_bytes):
        """Forces the formatting to specific units if the user selected one."""
        unit = self.display_unit_var.get()
        if unit == "Auto":
            return self.format_size(size_in_bytes)
        elif unit == "Bytes":
            return f"{size_in_bytes} B"
        elif unit == "KB":
            return f"{size_in_bytes / 1024:.2f} KB"
        elif unit == "MB":
            return f"{size_in_bytes / 1024**2:.2f} MB"
        elif unit == "GB":
            return f"{size_in_bytes / 1024**3:.2f} GB"

    def setup_ui(self):
        # Top Frame (Toolbar)
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        self.btn_open_folder = ttk.Button(top_frame, text="Open Image Folder", command=self.open_image_folder, width=20)
        self.btn_open_folder.pack(side=tk.LEFT, padx=(0,5))
        
        self.btn_select_files = ttk.Button(top_frame, text="Select File(s)", command=self.select_files, width=15)
        self.btn_select_files.pack(side=tk.LEFT, padx=5)

        self.btn_about = ttk.Button(top_frame, text="About", command=self.show_about, width=10)
        self.btn_about.pack(side=tk.LEFT, padx=5)
        
        self.lbl_file = ttk.Label(top_frame, text="0 files loaded.", foreground="gray")
        self.lbl_file.pack(side=tk.LEFT, padx=15)

        self.btn_export_all = tk.Button(top_frame, text="Export All", command=self.export_all_files, width=15, bg="#0078d7", fg="white", font=BOLD_FONT, relief=tk.FLAT, cursor="hand2")
        self.btn_export_all.pack(side=tk.RIGHT, padx=5)

        self.btn_export_selected = tk.Button(top_frame, text="Export Selected", command=self.export_selected_files, width=18, bg="#2ea043", fg="white", font=BOLD_FONT, relief=tk.FLAT, cursor="hand2")
        self.btn_export_selected.pack(side=tk.RIGHT)

        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # --- LEFT SIDE: Treeview & Padding Controls ---
        list_frame = ttk.Frame(paned_window)
        paned_window.add(list_frame, weight=3)
        
        # Display Unit Control (Right above the Treeview)
        tree_top_frame = ttk.Frame(list_frame)
        tree_top_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.display_unit_var = tk.StringVar(value="Auto")
        self.combo_display_unit = ttk.Combobox(tree_top_frame, textvariable=self.display_unit_var, values=["Auto", "Bytes", "KB", "MB", "GB"], width=8, state="readonly")
        self.combo_display_unit.pack(side=tk.RIGHT)
        self.combo_display_unit.bind("<<ComboboxSelected>>", self.on_display_unit_change)
        ttk.Label(tree_top_frame, text="Final Size Unit:", font=BOLD_FONT).pack(side=tk.RIGHT, padx=(5, 5))

        # 1. Treeview
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("id", "name", "ext", "orig_size", "padding", "final_size")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=tree_scroll.set, selectmode="extended")
        tree_scroll.config(command=self.tree.yview)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="File Name")
        self.tree.heading("ext", text="Type")
        self.tree.heading("orig_size", text="Orig Size")
        self.tree.heading("padding", text="Padding Added")
        self.tree.heading("final_size", text="Final Size")
        
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=200, anchor="w")
        self.tree.column("ext", width=50, anchor="center")
        self.tree.column("orig_size", width=100, anchor="e")
        self.tree.column("padding", width=110, anchor="center")
        self.tree.column("final_size", width=100, anchor="e")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 2. Padding Settings Panel (Moved to Bottom)
        self.settings_frame = ttk.LabelFrame(list_frame, text="Custom Null Padding (Applies to all selected files)", padding=10)
        
        pad_top = ttk.Frame(self.settings_frame)
        pad_top.pack(fill=tk.X)
        ttk.Label(pad_top, text="Amount to Append:").pack(side=tk.LEFT)
        
        # Use DoubleVar to allow decimals like 1.5 MB
        self.pad_var = tk.DoubleVar()
        self.pad_var.trace_add("write", self.on_pad_typed)
        
        self.pad_entry = ttk.Spinbox(pad_top, from_=0, to=MAX_PAD_BYTES, increment=1, textvariable=self.pad_var, width=20)
        self.pad_entry.pack(side=tk.LEFT, padx=10)

        # Unit selection combobox
        self.unit_var = tk.StringVar(value="Bytes")
        self.combo_unit = ttk.Combobox(pad_top, textvariable=self.unit_var, values=["Bytes", "KB", "MB", "GB"], width=8, state="readonly")
        self.combo_unit.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_unit.bind("<<ComboboxSelected>>", self.on_unit_change)

        ttk.Label(self.settings_frame, text="These bytes (\\x00) will be injected at the very end of the selected file(s) when exported.", font=("Segoe UI", 8, "italic"), foreground="gray").pack(pady=(5,5), anchor="w")
        
        # Quick dragging slider
        self.pad_slider = ttk.Scale(self.settings_frame, from_=0, to=MAX_PAD_BYTES, orient=tk.HORIZONTAL, variable=self.pad_var)
        self.pad_slider.pack(fill=tk.X, pady=(0, 5))

        # --- RIGHT SIDE: Scrollable Image Gallery ---
        gallery_outer_frame = ttk.LabelFrame(paned_window, text="Image Gallery (Double-click to expand)", padding=5)
        paned_window.add(gallery_outer_frame, weight=2)

        if not PILLOW_AVAILABLE:
            ttk.Label(gallery_outer_frame, text="Image previews disabled.\n(Pillow library not installed)", justify=tk.CENTER).pack(expand=True)
            self.gallery_canvas = None
        else:
            gallery_scroll = ttk.Scrollbar(gallery_outer_frame, orient=tk.VERTICAL)
            gallery_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.gallery_canvas = tk.Canvas(gallery_outer_frame, bg="#f3f3f3", yscrollcommand=gallery_scroll.set, highlightthickness=0)
            self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            gallery_scroll.config(command=self.gallery_canvas.yview)
            
            self.gallery_inner = ttk.Frame(self.gallery_canvas)
            self.gallery_canvas.create_window((0, 0), window=self.gallery_inner, anchor="nw")
            self.gallery_inner.bind("<Configure>", lambda e: self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox("all")))

        # Context Menu for Treeview
        self.context_menu = tk.Menu(self.root, tearoff=0, font=MAIN_FONT, bg="white", activebackground="#e5f3ff", activeforeground="black")
        self.context_menu.add_command(label="Import File to Match Padding", command=self.import_match_padding)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Properties", command=self.show_properties)

        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Hide settings initially
        self.settings_frame.pack_forget()

    # --- UI Disabling / Loading Screen Logic ---
    def set_ui_state(self, state, ignore_button=None):
        """Grays out or returns all UI to normal, except the given button"""
        tk_state = tk.DISABLED if state == "disabled" else tk.NORMAL
        readonly_state = tk.DISABLED if state == "disabled" else "readonly"
        
        self.btn_open_folder.config(state=tk_state)
        self.btn_select_files.config(state=tk_state)
        self.btn_about.config(state=tk_state)
        self.btn_export_selected.config(state=tk_state)
        self.btn_export_all.config(state=tk_state)
        self.pad_entry.config(state=tk_state)
        self.combo_unit.config(state=readonly_state)
        self.combo_display_unit.config(state=readonly_state)
        self.pad_slider.config(state=tk_state)
        
        # Disable treeview interactions
        if tk_state == tk.DISABLED:
            self.tree.unbind("<<TreeviewSelect>>")
        else:
            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
            
        # Gray out all play buttons in gallery except the active one
        for idx, btn in self.play_btn_refs.items():
            if btn != ignore_button:
                btn.config(state=tk_state)

    def show_loading_screen(self):
        self.loading_win = tk.Toplevel(self.root)
        self.loading_win.title("Loading Animation...")
        self.loading_win.geometry("300x100")
        self.loading_win.transient(self.root) 
        self.loading_win.grab_set() 
        
        self.loading_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 50
        self.loading_win.geometry(f"+{x}+{y}")
        self.loading_win.protocol("WM_DELETE_WINDOW", lambda: None) 
        
        ttk.Label(self.loading_win, text="Preparing frames, please wait...", font=MAIN_FONT).pack(pady=15)
        progress = ttk.Progressbar(self.loading_win, mode='indeterminate')
        progress.pack(fill=tk.X, padx=20)
        progress.start(10)
        self.root.update()

    def hide_loading_screen(self):
        if self.loading_win:
            self.loading_win.grab_release()
            self.loading_win.destroy()
            self.loading_win = None

    # --- Dialogs and Info ---
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About & Technical Info")
        about_win.geometry("500x350")
        about_win.resizable(False, False)
        about_win.transient(self.root)
        about_win.grab_set()

        main_frame = ttk.Frame(about_win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Universal File Padder & Viewer", font=TITLE_FONT, foreground="#005a9e").pack(pady=(0, 5))
        
        link_frame = ttk.Frame(main_frame)
        link_frame.pack(pady=5)
        ttk.Label(link_frame, text="Author: ").pack(side=tk.LEFT)
        lbl_link = tk.Label(link_frame, text="KBDStudios", font=("Segoe UI", 10, "underline"), fg="#0066cc", cursor="hand2", bg=main_frame.master.cget('bg'))
        lbl_link.pack(side=tk.LEFT)
        lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/KBDStudios"))

        info_frame = ttk.LabelFrame(main_frame, text="Description", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        fui_text = (
            "This utility allows you to load any file type and append exact amounts of "
            "binary null padding (\\x00) to the end of the file. \n\n"
            "This is crucial for binary modification workflows (like game modding) where "
            "internal pointers require file blocks to meet exact byte-size requirements to "
            "prevent structure shifts and engine crashes."
        )
        
        lbl_info = ttk.Label(info_frame, text=fui_text, justify=tk.LEFT, wraplength=420, foreground="#333333")
        lbl_info.pack(anchor="w")
        
        ttk.Button(main_frame, text="Close", command=about_win.destroy, width=20).pack(pady=10)

    def show_properties(self):
        selected = self.tree.selection()
        if not selected: return
        
        idx = int(selected[0])
        f_data = self.files_data[idx]
        
        prop_win = tk.Toplevel(self.root)
        prop_win.title(f"Properties - {f_data['filename']}")
        prop_win.geometry("400x400")
        prop_win.resizable(False, False)
        prop_win.transient(self.root)
        
        frame = ttk.Frame(prop_win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=f"File Metadata", font=TITLE_FONT).pack(anchor="w", pady=(0, 15))

        total_size = f_data["orig_size"] + f_data["pad_count"]
        resolution = "N/A"
        mode = "N/A"
        
        if PILLOW_AVAILABLE and f_data["is_image"]:
            try:
                img = Image.open(f_data["path"])
                resolution = f"{img.width} x {img.height} pixels"
                mode = img.mode
            except:
                resolution = "Error reading pixels"

        details = [
            ("File Name:", f_data["filename"]),
            ("Extension:", f_data["ext"]),
            ("Is Image:", str(f_data["is_image"])),
            ("Resolution:", resolution),
            ("Color Mode:", mode),
            ("-", "-"),
            ("Original File Size:", f"{f_data['orig_size']} bytes"),
            ("Null Padding Appended:", f"+{f_data['pad_count']} bytes"),
            ("Final Export Size:", f"{total_size} bytes"),
        ]
        
        grid_frame = ttk.Frame(frame)
        grid_frame.pack(fill=tk.X, expand=True)
        
        for i, (label, val) in enumerate(details):
            if label == "-":
                ttk.Separator(grid_frame, orient=tk.HORIZONTAL).grid(row=i, column=0, columnspan=2, sticky="ew", pady=10)
                continue
            
            ttk.Label(grid_frame, text=label, font=BOLD_FONT, foreground="#555").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 15))
            ttk.Label(grid_frame, text=val).grid(row=i, column=1, sticky="w", pady=4)
            
        ttk.Button(frame, text="Close", command=prop_win.destroy).pack(pady=(20, 0))

    # --- File Loading ---
    def open_image_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder containing Images")
        if not folder_path: return

        new_files = []
        for file in os.listdir(folder_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in SUPPORTED_IMAGES:
                new_files.append(os.path.join(folder_path, file))
                
        if not new_files:
            messagebox.showinfo("No Images", "No supported image formats found in that folder.")
            return
            
        self.process_incoming_files(new_files)

    def select_files(self):
        filepaths = filedialog.askopenfilenames(title="Select File(s)", filetypes=[("All Files", "*.*")])
        if not filepaths: return
        self.process_incoming_files(filepaths)

    def process_incoming_files(self, filepaths):
        for path in filepaths:
            basename = os.path.basename(path)
            ext = os.path.splitext(basename)[1].lower()
            size = os.path.getsize(path)
            
            is_image = ext in SUPPORTED_IMAGES
            is_anim = False
            
            if is_image and PILLOW_AVAILABLE:
                try:
                    img = Image.open(path)
                    is_anim = getattr(img, "is_animated", False)
                except:
                    is_image = False
            
            self.files_data.append({
                "path": path,
                "filename": basename,
                "ext": ext,
                "orig_size": size,
                "pad_count": 0,
                "is_image": is_image,
                "is_anim": is_anim,
                "frames": [], 
                "durations": []
            })
            
        self.lbl_file.config(text=f"{len(self.files_data)} files loaded.")
        self.populate_tree()
        if PILLOW_AVAILABLE:
            self.populate_gallery()

    def populate_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, f in enumerate(self.files_data):
            self.tree.insert("", "end", iid=str(i), values=(
                f"{i+1}", 
                f["filename"], 
                f["ext"], 
                self.format_size(f["orig_size"]), 
                f"+{self.format_size(f['pad_count'])}", 
                self.format_display_size(f["orig_size"] + f["pad_count"])
            ))

    def on_display_unit_change(self, event=None):
        """Redraws the Final Size column to match the explicitly selected unit."""
        for idx_str in self.tree.get_children():
            idx = int(idx_str)
            f_data = self.files_data[idx]
            final_bytes = f_data["orig_size"] + f_data["pad_count"]
            
            vals = list(self.tree.item(idx_str, "values"))
            vals[5] = self.format_display_size(final_bytes)
            self.tree.item(idx_str, values=vals)

    def populate_gallery(self):
        for widget in self.gallery_inner.winfo_children(): widget.destroy()
        self.gallery_image_refs.clear()
        self.gallery_frame_widgets.clear()
        self.play_btn_refs.clear()

        for i in range(len(self.files_data)):
            self.create_gallery_item(i)

    def create_generic_icon(self, ext_text):
        img = Image.new('RGB', (300, 300), color='#e1e1e1')
        return ImageTk.PhotoImage(img)

    def create_gallery_item(self, index):
        if index in self.gallery_frame_widgets:
            self.gallery_frame_widgets[index].destroy()

        f_data = self.files_data[index]

        # Styled Frame for Modern Look
        item_frame = tk.Frame(self.gallery_inner, bg="#f3f3f3", bd=0, highlightbackground="#d1d1d1", highlightthickness=2, highlightcolor="#0078d7")
        item_frame.pack(side=tk.TOP, pady=10, padx=10, fill=tk.X)
        
        lbl_img = tk.Label(item_frame, bg="#ffffff", cursor="hand2")
        lbl_img.pack(padx=2, pady=(2, 0))
        
        if f_data["is_image"]:
            try:
                image = Image.open(f_data["path"])
                # Extract first frame for thumbnail
                if f_data["is_anim"]:
                    image.seek(0)
                    
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.gallery_image_refs[index] = photo 
                lbl_img.config(image=photo)
            except Exception:
                tk.Label(item_frame, text="[ Image Error ]", bg="#333", fg="#ff4444", width=30, height=5, font=BOLD_FONT).pack(padx=2, pady=2)
        else:
            photo = self.create_generic_icon(f_data["ext"])
            self.gallery_image_refs[index] = photo
            lbl_img.config(image=photo)
            # overlay generic text
            tk.Label(item_frame, text=f"📄 FILE\n{f_data['ext'].upper()}", bg="#e1e1e1", font=TITLE_FONT, fg="#333").place(relx=0.5, rely=0.4, anchor=tk.CENTER)

        lbl_img.bind("<Button-1>", lambda e, idx=index: self.on_gallery_select(idx))
        if f_data["is_image"]:
            lbl_img.bind("<Double-1>", lambda e, idx=index: self.open_full_viewer(idx))
            
        lbl_text = tk.Label(item_frame, text=f"{f_data['filename']}", bg="#ffffff", font=BOLD_FONT, fg="#333333")
        lbl_text.pack(fill=tk.X, padx=2, pady=(0, 2), ipady=5)
        lbl_text.bind("<Button-1>", lambda e, idx=index: self.on_gallery_select(idx))
        
        # Add Play Button if Animated
        if f_data["is_anim"]:
            btn_play = ttk.Button(item_frame, text="▶ Play Animation", command=lambda idx=index: self.toggle_animation(idx))
            btn_play.pack(pady=5)
            self.play_btn_refs[index] = btn_play

        # Save reference to update image during animation
        self.gallery_frame_widgets[index] = {"frame": item_frame, "lbl_img": lbl_img}

    # --- Match Padding Logic ---
    def import_match_padding(self):
        selected = self.tree.selection()
        if not selected: return

        match_path = filedialog.askopenfilename(title="Select Source File to Match Size With", filetypes=[("All Files", "*.*")])
        if not match_path: return

        target_size = os.path.getsize(match_path)

        self.is_syncing = True # Prevent spinbox triggers while applying padding loop
        for sel in selected:
            idx = int(sel)
            f_data = self.files_data[idx]
            
            if target_size >= f_data["orig_size"]:
                diff = target_size - f_data["orig_size"]
                
                # Check 5GB absolute max cap
                if diff > MAX_PAD_BYTES:
                    diff = MAX_PAD_BYTES
                    
                f_data["pad_count"] = diff
                
                vals = list(self.tree.item(sel, "values"))
                vals[4] = f"+{self.format_size(diff)}"
                vals[5] = self.format_display_size(f_data["orig_size"] + diff)
                self.tree.item(sel, values=vals)
            else:
                messagebox.showwarning(
                    "Cannot Match Padding", 
                    f"The selected file to match against ({self.format_size(target_size)}) is SMALLER "
                    f"than your original file '{f_data['filename']}' ({self.format_size(f_data['orig_size'])}).\n\n"
                    f"Padding can only APPEND data to increase a file's size. It cannot shrink a file. "
                    f"Skipping this file."
                )
        
        # Sync the UI box back to the first selected item in raw Bytes
        idx0 = int(selected[0])
        self.unit_var.set("Bytes")
        self.current_unit = "Bytes"
        self.pad_entry.config(to=MAX_PAD_BYTES)
        self.pad_slider.config(to=MAX_PAD_BYTES)
        self.pad_var.set(self.files_data[idx0]["pad_count"])
        
        self.is_syncing = False

    # --- Padding Sync Logic ---
    def on_unit_change(self, event=None):
        """Converts the currently typed number into its equivalent across different units."""
        self.is_syncing = True

        new_unit = self.unit_var.get()
        if new_unit != self.current_unit:
            try:
                val = float(self.pad_var.get())
            except ValueError:
                val = 0.0

            multipliers = {"Bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
            old_mult = multipliers[self.current_unit]
            new_mult = multipliers[new_unit]

            # Convert old visual number into raw bytes, then into the new unit size
            raw_bytes = val * old_mult
            new_val = raw_bytes / new_mult
            
            # 8 Decimal Place precision to ensure 100% byte-accurate translation
            new_val = round(new_val, 8) 
            
            self.pad_var.set(new_val)
            self.current_unit = new_unit

            # Update Max Limits of Widgets based on new unit
            max_in_unit = MAX_PAD_BYTES / new_mult
            self.pad_entry.config(to=max_in_unit)
            self.pad_slider.config(to=max_in_unit)

        self.is_syncing = False
        self.update_padding_data()

    def on_pad_typed(self, *args):
        if self.is_syncing: return
        self.update_padding_data()

    def update_padding_data(self):
        selected = self.tree.selection()
        if not selected: return
        
        try:
            val = float(self.pad_var.get())
        except ValueError:
            return 
            
        unit = self.unit_var.get()
        multiplier = {"Bytes": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
        
        # Enforce 5 GB absolute limit
        if val * multiplier > MAX_PAD_BYTES:
            val = MAX_PAD_BYTES / multiplier
            self.is_syncing = True
            self.pad_var.set(round(val, 8))
            self.is_syncing = False

        if val < 0: val = 0
        pad_bytes = int(val * multiplier)
        
        for sel in selected:
            idx = int(sel)
            f_data = self.files_data[idx]
            f_data["pad_count"] = pad_bytes
            
            # Update Tree dynamically with formatted sizes
            vals = list(self.tree.item(sel, "values"))
            vals[4] = f"+{self.format_size(pad_bytes)}"
            vals[5] = self.format_display_size(f_data["orig_size"] + pad_bytes)
            self.tree.item(sel, values=vals)

    # --- Selection Logic ---
    def on_tree_select(self, event):
        if self.is_syncing: return
        selected = self.tree.selection()
        if selected:
            # Update panel to reflect the FIRST selected item to avoid visual conflicts
            idx = int(selected[0])
            self.is_syncing = True
            
            self.settings_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0), padx=10)
            
            # Default back to Bytes for absolute precision when changing file selection
            self.unit_var.set("Bytes")
            self.current_unit = "Bytes"
            self.pad_entry.config(to=MAX_PAD_BYTES)
            self.pad_slider.config(to=MAX_PAD_BYTES)
            self.pad_var.set(self.files_data[idx]["pad_count"])
                
            if PILLOW_AVAILABLE:
                # If multiple are selected, just scroll to the first one in the gallery
                self.highlight_gallery_item(idx)
                
            self.is_syncing = False
        else:
            self.settings_frame.pack_forget()

    def on_gallery_select(self, index):
        if self.is_syncing: return
        self.is_syncing = True
        
        self.highlight_gallery_item(index)
        
        # Clear other selections and set this one
        self.tree.selection_remove(self.tree.selection())
        self.tree.selection_set(str(index))
        self.tree.see(str(index))
        
        self.is_syncing = False
        self.on_tree_select(None)

    def highlight_gallery_item(self, index):
        for idx, widget_data in self.gallery_frame_widgets.items():
            widget_data["frame"].config(highlightbackground="#d1d1d1", highlightthickness=2)
            
        if index in self.gallery_frame_widgets:
            target_frame = self.gallery_frame_widgets[index]["frame"]
            target_frame.config(highlightbackground="#0078d7", highlightthickness=3)
            
            y_pos = target_frame.winfo_y()
            canvas_height = self.gallery_inner.winfo_reqheight()
            if canvas_height > 0:
                fraction = y_pos / canvas_height
                self.gallery_canvas.yview_moveto(fraction)

    # --- Animation Logic ---
    def toggle_animation(self, index):
        f_data = self.files_data[index]
        btn = self.play_btn_refs[index]
        
        # If currently playing this animation, stop it
        if self.active_anim_index == index:
            self.stop_animation()
            return
            
        # If another is playing, stop it first
        if self.active_anim_index is not None:
            self.stop_animation()

        # Start new animation flow
        self.show_loading_screen()
        self.set_ui_state("disabled", ignore_button=btn) 
        btn.config(text="⏹ Stop Animation")
        
        self.active_anim_index = index
        self.current_frame = 0
        
        # Threaded frame extraction to not freeze loading screen
        threading.Thread(target=self._load_frames_thread, args=(index,), daemon=True).start()

    def _load_frames_thread(self, index):
        f_data = self.files_data[index]
        
        # Load only if not cached
        if not f_data["frames"]:
            try:
                img = Image.open(f_data["path"])
                frames = []
                durations = []
                
                for frame in ImageSequence.Iterator(img):
                    f_copy = frame.copy()
                    f_copy.thumbnail((300, 300), Image.Resampling.LANCZOS)
                    frames.append(ImageTk.PhotoImage(f_copy))
                    durations.append(frame.info.get('duration', 100) or 100)
                    
                f_data["frames"] = frames
                f_data["durations"] = durations
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load frames:\n{e}"))
                self.root.after(0, self.stop_animation)
                return

        # Start playback on main thread
        self.root.after(0, self._start_playback)

    def _start_playback(self):
        self.hide_loading_screen()
        if self.active_anim_index is not None:
            self.play_next_frame()

    def play_next_frame(self):
        if self.active_anim_index is None: return
        
        idx = self.active_anim_index
        f_data = self.files_data[idx]
        
        if not f_data["frames"]: return
        
        lbl_img = self.gallery_frame_widgets[idx]["lbl_img"]
        
        self.current_frame = (self.current_frame + 1) % len(f_data["frames"])
        photo = f_data["frames"][self.current_frame]
        lbl_img.config(image=photo)
        
        duration = f_data["durations"][self.current_frame]
        self.active_anim_job = self.root.after(duration, self.play_next_frame)

    def stop_animation(self):
        if self.active_anim_job:
            self.root.after_cancel(self.active_anim_job)
            self.active_anim_job = None
            
        if self.active_anim_index is not None:
            idx = self.active_anim_index
            btn = self.play_btn_refs[idx]
            btn.config(text="▶ Play Animation")
            
            # Reset to frame 0 thumbnail
            f_data = self.files_data[idx]
            if f_data["frames"]:
                lbl_img = self.gallery_frame_widgets[idx]["lbl_img"]
                lbl_img.config(image=f_data["frames"][0])
                
        self.active_anim_index = None
        self.hide_loading_screen() # Just in case it was stuck
        self.set_ui_state("normal")

    # --- Actions ---
    def open_full_viewer(self, index):
        if self.active_anim_index is not None: return # Block if animating
        f_data = self.files_data[index]
        if not f_data["is_image"]: return

        try:
            FullImageViewer(self.root, f_data["path"], title_text=f"Viewing: {f_data['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image viewer: {e}")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            # If right clicking outside of current selection, change selection
            if item not in self.tree.selection():
                self.tree.selection_set(item)
                
            self.context_menu.post(event.x_root, event.y_root)

    def export_selected_files(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No File", "Please select at least one file to export.")
            return
            
        dir_path = filedialog.askdirectory(title="Select Folder to Export Selected Padded Files")
        if not dir_path: return
        
        success_count = 0
        for sel in selected:
            idx = int(sel)
            f_data = self.files_data[idx]
            
            filename = f"Padded_{f_data['filename']}"
            save_path = os.path.join(dir_path, filename)
            
            try:
                with open(f_data["path"], 'rb') as f:
                    raw_bytes = f.read()
                    
                final_bytes = raw_bytes + (b'\x00' * f_data["pad_count"])
                
                with open(save_path, 'wb') as f:
                    f.write(final_bytes)
                success_count += 1
            except Exception as e:
                print(f"Failed to save {filename}: {e}")
                
        messagebox.showinfo("Export Complete", f"Successfully exported {success_count} selected files to:\n{dir_path}")

    def export_all_files(self):
        if not self.files_data:
            messagebox.showwarning("No Data", "No files loaded.")
            return
            
        dir_path = filedialog.askdirectory(title="Select Folder to Export All Padded Files")
        if not dir_path: return
        
        success_count = 0
        for f_data in self.files_data:
            filename = f"Padded_{f_data['filename']}"
            save_path = os.path.join(dir_path, filename)
            
            try:
                with open(f_data["path"], 'rb') as f:
                    raw_bytes = f.read()
                    
                final_bytes = raw_bytes + (b'\x00' * f_data["pad_count"])
                
                with open(save_path, 'wb') as f:
                    f.write(final_bytes)
                success_count += 1
            except Exception as e:
                print(f"Failed to save {filename}: {e}")
                
        messagebox.showinfo("Batch Export Complete", f"Successfully exported {success_count} files to:\n{dir_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FilePadderApp(root)
    root.mainloop()