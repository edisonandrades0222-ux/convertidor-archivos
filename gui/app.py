import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Asegurar importacion de modulos hermanos
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from converters.cad_converter import dwg_to_pdf, dwg_to_dxf, dxf_to_pdf, dxf_to_dwg, dxf_to_image
from converters.pdf_converter import pdf_to_docx, pdf_to_images, images_to_pdf, pdf_to_text
from converters.image_converter import convert_image

# Configuracion visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONVERSION_MAP = {
    ".pdf": [
        ("Word Editable (.docx)", "docx"),
        ("Imagenes PNG (.png)", "png_batch"),
        ("Imagenes JPG (.jpg)", "jpg_batch"),
        ("Texto plano (.txt)", "txt"),
    ],
    ".dwg": [
        ("Documento PDF Vectorial (.pdf)", "pdf"),
        ("Plano DXF (.dxf)", "dxf"),
    ],
    ".dxf": [
        ("Documento PDF Vectorial (.pdf)", "pdf"),
        ("Plano DWG (.dwg)", "dwg"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen JPG (.jpg)", "jpg"),
    ],
    ".png": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen JPG (.jpg)", "jpg"),
        ("Imagen WEBP (.webp)", "webp"),
        ("Imagen BMP (.bmp)", "bmp"),
        ("Icono (.ico)", "ico"),
    ],
    ".jpg": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen WEBP (.webp)", "webp"),
        ("Imagen BMP (.bmp)", "bmp"),
    ],
    ".jpeg": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen WEBP (.webp)", "webp"),
    ],
    ".webp": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen JPG (.jpg)", "jpg"),
    ],
    ".bmp": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen JPG (.jpg)", "jpg"),
    ],
    ".tiff": [
        ("Documento PDF (.pdf)", "pdf"),
        ("Imagen PNG (.png)", "png"),
        ("Imagen JPG (.jpg)", "jpg"),
    ]
}

class UniversalConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Convertidor Universal de Archivos")
        self.geometry("820x780")
        self.minsize(740, 700)

        self.selected_files = []
        self.output_dir = ""
        self.is_converting = False

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray85", "gray20"))
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_label = ctk.CTkLabel(
            header_frame, 
            text="⚡ Convertidor Universal de Archivos", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w", padx=15, pady=(10, 2))

        subtitle_label = ctk.CTkLabel(
            header_frame, 
            text="PDF ➔ Word | DWG / DXF ➔ PDF (Layout, Monocromo, Hoja) | Imágenes | 100% Autónomo",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray70")
        )
        subtitle_label.pack(anchor="w", padx=15, pady=(0, 10))

        # Card 1: Seleccion de archivos
        file_card = ctk.CTkFrame(self, corner_radius=12)
        file_card.pack(fill="x", padx=20, pady=6)

        file_title = ctk.CTkLabel(file_card, text="1. Selecciona el archivo o archivos a convertir", font=ctk.CTkFont(size=14, weight="bold"))
        file_title.pack(anchor="w", padx=15, pady=(10, 6))

        btn_row = ctk.CTkFrame(file_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 8))

        self.btn_browse_file = ctk.CTkButton(
            btn_row, 
            text="📄 Seleccionar Archivo(s)", 
            command=self._select_files,
            width=180,
            height=34
        )
        self.btn_browse_file.pack(side="left", padx=(0, 10))

        self.btn_clear = ctk.CTkButton(
            btn_row, 
            text="✖ Limpiar", 
            command=self._clear_selection,
            fg_color="gray50",
            hover_color="gray40",
            width=100,
            height=34
        )
        self.btn_clear.pack(side="left")

        self.lbl_selected_file = ctk.CTkLabel(
            file_card, 
            text="Ningún archivo seleccionado todavía.",
            anchor="w",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=("gray50", "gray60")
        )
        self.lbl_selected_file.pack(fill="x", padx=15, pady=(0, 10))

        # Card 2: Formato de salida y destino
        options_card = ctk.CTkFrame(self, corner_radius=12)
        options_card.pack(fill="x", padx=20, pady=6)

        opt_title = ctk.CTkLabel(options_card, text="2. Configuración de Conversión", font=ctk.CTkFont(size=14, weight="bold"))
        opt_title.pack(anchor="w", padx=15, pady=(10, 6))

        opt_row = ctk.CTkFrame(options_card, fg_color="transparent")
        opt_row.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkLabel(opt_row, text="Convertir a formato:", width=130, anchor="w").pack(side="left")
        self.combo_target = ctk.CTkComboBox(
            opt_row, 
            values=["Selecciona primero un archivo"],
            width=280,
            state="readonly",
            command=self._on_target_changed
        )
        self.combo_target.pack(side="left", padx=10)

        # Destino
        dest_row = ctk.CTkFrame(options_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(dest_row, text="Guardar en carpeta:", width=130, anchor="w").pack(side="left")
        self.entry_dest = ctk.CTkEntry(dest_row, placeholder_text="Misma carpeta que el archivo original", width=380)
        self.entry_dest.pack(side="left", padx=(10, 8), fill="x", expand=True)

        self.btn_dest = ctk.CTkButton(
            dest_row, 
            text="Buscar...", 
            width=80, 
            command=self._select_dest_dir
        )
        self.btn_dest.pack(side="left")

        # Card 3: Opciones Avanzadas CAD (DWG / DXF -> PDF)
        self.cad_card = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "gray17"))
        self.cad_card.pack(fill="x", padx=20, pady=6)

        cad_title = ctk.CTkLabel(
            self.cad_card, 
            text="📐 Opciones de Exportación CAD (DWG / DXF ➔ PDF)", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("blue", "#3B8ED0")
        )
        cad_title.pack(anchor="w", padx=15, pady=(10, 6))

        # Fila 1 de opciones CAD: Espacio y Color
        cad_row1 = ctk.CTkFrame(self.cad_card, fg_color="transparent")
        cad_row1.pack(fill="x", padx=15, pady=(0, 6))

        ctk.CTkLabel(cad_row1, text="Extraer:", width=110, anchor="w").pack(side="left")
        self.combo_cad_space = ctk.CTkComboBox(
            cad_row1,
            values=[
                "Todos los Layouts (PDF multipágina)",
                "Lámina / Layout (Presentación)",
                "Espacio Modelo (ModelSpace)"
            ],
            width=240,
            state="readonly"
        )
        self.combo_cad_space.set("Todos los Layouts (PDF multipágina)")
        self.combo_cad_space.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(cad_row1, text="Estilo de Color:", width=100, anchor="w").pack(side="left")
        self.combo_cad_color = ctk.CTkComboBox(
            cad_row1,
            values=[
                "Monocromático (Líneas Negras)",
                "Color (Capas originales)"
            ],
            width=230,
            state="readonly"
        )
        self.combo_cad_color.set("Monocromático (Líneas Negras)")
        self.combo_cad_color.pack(side="left")

        # Fila 2 de opciones CAD: Grosor de linea, Hoja y Orientacion
        cad_row2 = ctk.CTkFrame(self.cad_card, fg_color="transparent")
        cad_row2.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(cad_row2, text="Grosor de Línea:", width=110, anchor="w").pack(side="left")
        self.combo_cad_weight = ctk.CTkComboBox(
            cad_row2,
            values=[
                "Fino (0.50x) - Recomendado",
                "Ultrafino (0.25x)",
                "Normal (1.00x)",
                "Grueso (1.50x)"
            ],
            width=240,
            state="readonly"
        )
        self.combo_cad_weight.set("Fino (0.50x) - Recomendado")
        self.combo_cad_weight.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(cad_row2, text="Tamaño Hoja:", width=100, anchor="w").pack(side="left")
        self.combo_cad_paper = ctk.CTkComboBox(
            cad_row2,
            values=[
                "Auto (Detectar en AutoCAD)",
                "A3 (420 x 297 mm)",
                "A4 (297 x 210 mm)",
                "A2 (594 x 420 mm)",
                "A1 (841 x 594 mm)",
                "A0 (1189 x 841 mm)",
                "Carta / Letter",
                "Oficio / Legal"
            ],
            width=170,
            state="readonly"
        )
        self.combo_cad_paper.set("Auto (Detectar en AutoCAD)")
        self.combo_cad_paper.pack(side="left", padx=(0, 10))

        self.combo_cad_orient = ctk.CTkComboBox(
            cad_row2,
            values=["Horizontal", "Vertical"],
            width=85,
            state="readonly"
        )
        self.combo_cad_orient.set("Horizontal")
        self.combo_cad_orient.pack(side="left")

        # Ocultar o atenuar opciones CAD inicialmente hasta que se seleccione un DWG/DXF
        self._toggle_cad_options(False)

        # Botones de accion
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=8)

        self.btn_convert = ctk.CTkButton(
            action_row, 
            text="🚀 Iniciar Conversión", 
            font=ctk.CTkFont(size=16, weight="bold"),
            height=44,
            command=self._start_conversion_thread,
            state="disabled"
        )
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_open_folder = ctk.CTkButton(
            action_row, 
            text="📂 Abrir Carpeta", 
            height=44,
            width=140,
            command=self._open_output_folder,
            state="disabled",
            fg_color=("gray60", "gray40")
        )
        self.btn_open_folder.pack(side="right")

        # Progreso y Logs
        progress_card = ctk.CTkFrame(self, corner_radius=12)
        progress_card.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.progress_bar = ctk.CTkProgressBar(progress_card)
        self.progress_bar.pack(fill="x", padx=15, pady=(10, 6))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(
            progress_card, 
            text="Listo para convertir.", 
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_status.pack(fill="x", padx=15, pady=(0, 4))

        self.txt_log = ctk.CTkTextbox(progress_card, height=100, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.txt_log.configure(state="disabled")

    def _toggle_cad_options(self, enabled=True):
        state = "normal" if enabled else "disabled"
        self.combo_cad_space.configure(state=state)
        self.combo_cad_color.configure(state=state)
        self.combo_cad_weight.configure(state=state)
        self.combo_cad_paper.configure(state=state)
        self.combo_cad_orient.configure(state=state)

    def _on_target_changed(self, choice):
        is_cad_pdf = False
        if self.selected_files:
            first_ext = Path(self.selected_files[0]).suffix.lower()
            if first_ext in [".dwg", ".dxf"] and "PDF" in choice:
                is_cad_pdf = True
        self._toggle_cad_options(is_cad_pdf)

    def _log(self, message):
        def _append():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", f"{message}\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
            self.lbl_status.configure(text=message)
        self.after(0, _append)

    def _select_files(self):
        filetypes = [
            ("Archivos soportados", "*.pdf;*.dwg;*.dxf;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff"),
            ("Planos AutoCAD DWG (*.dwg)", "*.dwg"),
            ("Planos CAD DXF (*.dxf)", "*.dxf"),
            ("Documentos PDF (*.pdf)", "*.pdf"),
            ("Imágenes (*.png, *.jpg, *.webp)", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff"),
            ("Todos los archivos", "*.*")
        ]
        files = filedialog.askopenfilenames(title="Seleccionar archivo(s) para convertir", filetypes=filetypes)
        if not files:
            return

        self.selected_files = list(files)
        self._update_ui_for_files()

    def _clear_selection(self):
        self.selected_files = []
        self.lbl_selected_file.configure(text="Ningún archivo seleccionado todavía.")
        self.combo_target.configure(values=["Selecciona primero un archivo"])
        self.combo_target.set("Selecciona primero un archivo")
        self.btn_convert.configure(state="disabled")
        self.btn_open_folder.configure(state="disabled")
        self.progress_bar.set(0)
        self._toggle_cad_options(False)
        self._log("Selección borrada.")

    def _update_ui_for_files(self):
        if not self.selected_files:
            return

        first = Path(self.selected_files[0])
        ext = first.suffix.lower()

        if len(self.selected_files) == 1:
            size_kb = first.stat().st_size / 1024
            self.lbl_selected_file.configure(text=f"Seleccionado: {first.name} ({size_kb:.1f} KB)")
        else:
            self.lbl_selected_file.configure(text=f"Seleccionados: {len(self.selected_files)} archivos (ej: {first.name})")

        options = CONVERSION_MAP.get(ext, [])
        if options:
            combo_labels = [opt[0] for opt in options]
            self.combo_target.configure(values=combo_labels)
            self.combo_target.set(combo_labels[0])
            self.btn_convert.configure(state="normal")
            self._log(f"Archivo cargado: {first.name}. Formatos disponibles: {len(combo_labels)}")
            self._on_target_changed(combo_labels[0])
        else:
            self.combo_target.configure(values=["Formato no soportado directamente"])
            self.combo_target.set("Formato no soportado")
            self.btn_convert.configure(state="disabled")
            self._toggle_cad_options(False)

        if not self.entry_dest.get().strip():
            self.output_dir = str(first.parent)
            self.entry_dest.delete(0, "end")
            self.entry_dest.insert(0, self.output_dir)

    def _select_dest_dir(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if d:
            self.output_dir = d
            self.entry_dest.delete(0, "end")
            self.entry_dest.insert(0, d)

    def _open_output_folder(self):
        target_dir = self.output_dir or (str(Path(self.selected_files[0]).parent) if self.selected_files else "")
        if target_dir and os.path.isdir(target_dir):
            os.startfile(target_dir)

    def _start_conversion_thread(self):
        if not self.selected_files or self.is_converting:
            return

        target_label = self.combo_target.get()
        if not target_label or "no soportado" in target_label:
            return

        custom_dest = self.entry_dest.get().strip()
        if custom_dest and os.path.isdir(custom_dest):
            self.output_dir = custom_dest
        else:
            self.output_dir = str(Path(self.selected_files[0]).parent)

        thread = threading.Thread(target=self._run_conversion, args=(target_label,), daemon=True)
        thread.start()

    def _get_cad_params(self):
        # Modo de espacio
        sp = self.combo_cad_space.get()
        if "Todos" in sp:
            space_mode = "all_layouts"
        elif "Modelo" in sp:
            space_mode = "model"
        else:
            space_mode = "layout"

        # Color
        col = self.combo_cad_color.get()
        color_mode = "monochrome" if "Monocromático" in col or "Monocromatico" in col else "color"

        # Grosor
        gw = self.combo_cad_weight.get()
        if "0.25" in gw:
            lineweight_scale = 0.25
        elif "0.50" in gw:
            lineweight_scale = 0.50
        elif "1.50" in gw:
            lineweight_scale = 1.50
        else:
            lineweight_scale = 1.00

        # Tamano papel
        pap = self.combo_cad_paper.get()
        if "Auto" in pap:
            paper_size = "Auto"
        elif "A0" in pap:
            paper_size = "A0"
        elif "A1" in pap:
            paper_size = "A1"
        elif "A2" in pap:
            paper_size = "A2"
        elif "A3" in pap:
            paper_size = "A3"
        elif "A4" in pap:
            paper_size = "A4"
        elif "Carta" in pap:
            paper_size = "Carta"
        elif "Oficio" in pap:
            paper_size = "Oficio"
        else:
            paper_size = "Auto"

        # Orientacion
        orient = "portrait" if "Vertical" in self.combo_cad_orient.get() else "landscape"

        return {
            "space_mode": space_mode,
            "color_mode": color_mode,
            "lineweight_scale": lineweight_scale,
            "paper_size": paper_size,
            "orientation": orient
        }

    def _run_conversion(self, target_label):
        self.is_converting = True
        self.btn_convert.configure(state="disabled")
        self.btn_browse_file.configure(state="disabled")
        self.progress_bar.set(0)

        cad_params = self._get_cad_params()
        total = len(self.selected_files)
        success_count = 0
        self._log(f"Iniciando procesamiento de {total} archivo(s)...")

        # Caso especial: Combinar múltiples imágenes en 1 solo PDF
        if total > 1 and "PDF" in target_label and any(Path(f).suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"] for f in self.selected_files):
            try:
                out_pdf = Path(self.output_dir) / "documento_combinado.pdf"
                self._log(f"Combinando {total} imágenes en un solo PDF...")
                images_to_pdf(self.selected_files, out_pdf, progress_callback=self._log)
                success_count = total
                self.progress_bar.set(1.0)
            except Exception as e:
                self._log(f"Error al combinar imágenes a PDF: {e}")
        else:
            for idx, file_str in enumerate(self.selected_files):
                file_path = Path(file_str)
                ext = file_path.suffix.lower()
                options = CONVERSION_MAP.get(ext, [])
                target_code = None
                for lbl, code in options:
                    if lbl == target_label:
                        target_code = code
                        break

                if not target_code:
                    self._log(f"Omitiendo {file_path.name}: formato no compatible con {target_label}")
                    continue

                try:
                    self._log(f"[{idx+1}/{total}] Procesando {file_path.name}...")
                    
                    # 1. PDF a Word
                    if ext == ".pdf" and target_code == "docx":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.docx"
                        pdf_to_docx(file_path, out_path, progress_callback=self._log)

                    # 2. PDF a Imágenes
                    elif ext == ".pdf" and target_code in ["png_batch", "jpg_batch"]:
                        img_fmt = "png" if "png" in target_code else "jpg"
                        out_folder = Path(self.output_dir) / f"{file_path.stem}_imagenes"
                        pdf_to_images(file_path, out_folder, img_format=img_fmt, progress_callback=self._log)

                    # 3. PDF a Texto
                    elif ext == ".pdf" and target_code == "txt":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.txt"
                        pdf_to_text(file_path, out_path, progress_callback=self._log)

                    # 4. DWG a PDF (Con opciones avanzadas de lámina, monocromo, hoja y grosor)
                    elif ext == ".dwg" and target_code == "pdf":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.pdf"
                        dwg_to_pdf(
                            file_path, 
                            out_path, 
                            space_mode=cad_params["space_mode"],
                            color_mode=cad_params["color_mode"],
                            lineweight_scale=cad_params["lineweight_scale"],
                            paper_size=cad_params["paper_size"],
                            orientation=cad_params["orientation"],
                            progress_callback=self._log
                        )

                    # 5. DWG a DXF
                    elif ext == ".dwg" and target_code == "dxf":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.dxf"
                        dwg_to_dxf(file_path, out_path, progress_callback=self._log)

                    # 6. DXF a PDF (Con opciones avanzadas de lámina, monocromo, hoja y grosor)
                    elif ext == ".dxf" and target_code == "pdf":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.pdf"
                        dxf_to_pdf(
                            file_path, 
                            out_path, 
                            space_mode=cad_params["space_mode"],
                            color_mode=cad_params["color_mode"],
                            lineweight_scale=cad_params["lineweight_scale"],
                            paper_size=cad_params["paper_size"],
                            orientation=cad_params["orientation"],
                            progress_callback=self._log
                        )

                    # 7. DXF a DWG
                    elif ext == ".dxf" and target_code == "dwg":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.dwg"
                        dxf_to_dwg(file_path, out_path, progress_callback=self._log)

                    # 8. DXF a Imagen
                    elif ext == ".dxf" and target_code in ["png", "jpg"]:
                        out_path = Path(self.output_dir) / f"{file_path.stem}.{target_code}"
                        dxf_to_image(file_path, out_path, img_format=target_code, progress_callback=self._log)

                    # 9. Imagen a PDF
                    elif target_code == "pdf":
                        out_path = Path(self.output_dir) / f"{file_path.stem}.pdf"
                        images_to_pdf([file_path], out_path, progress_callback=self._log)

                    # 10. Imagen a Imagen
                    else:
                        out_path = Path(self.output_dir) / f"{file_path.stem}.{target_code}"
                        convert_image(file_path, target_format=target_code, output_path=out_path, progress_callback=self._log)

                    success_count += 1
                except Exception as e:
                    self._log(f"Error procesando {file_path.name}: {e}")

                self.progress_bar.set((idx + 1) / total)

        self._log(f"¡Proceso terminado! {success_count} de {total} archivos convertidos exitosamente.")
        self.is_converting = False
        self.btn_convert.configure(state="normal")
        self.btn_browse_file.configure(state="normal")
        self.btn_open_folder.configure(state="normal")
        messagebox.showinfo("Conversión Finalizada", f"Se completó la conversión de {success_count} archivo(s).\n\nPuedes ver los resultados en la carpeta de destino.")

def main():
    app = UniversalConverterApp()
    app.mainloop()

if __name__ == "__main__":
    main()
