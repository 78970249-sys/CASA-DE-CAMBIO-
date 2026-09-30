# -*- coding: utf-8 -*-
"""Interfaz gráfica (tkinter) de CasaDeCambio (Célula 3 · GUI demo).

La GUI consume únicamente la fachada :class:`AppService`; ningún caso de
uso vive aquí. Organizada en pestañas:

    1) Operar ....... compra/venta al instante + ticket
    2) Tasas ........ cotizaciones y gestión de monedas
    3) Clientes ..... listado, registro y búsqueda
    4) Historial .... todas las operaciones
    5) Caja ......... arqueo del día y reporte
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import List, Optional

from src.domain.models import Cliente, Moneda
from src.services.app_service import AppService

# ----------------------------------------------------------------------
# Paleta y estilos
# ----------------------------------------------------------------------
COLOR_FONDO = "#0b1f3a"
COLOR_PANEL = "#12284a"
COLOR_ACENTO = "#24c6dc"
COLOR_DORADO = "#f7b731"
COLOR_TEXTO = "#eaf2fb"
COLOR_VERDE = "#2dd4a7"
COLOR_ROJO = "#ff6b6b"
FUENTE_TITULO = ("Segoe UI", 20, "bold")
FUENTE_SUB = ("Segoe UI", 11)
FUENTE_TEXTO = ("Segoe UI", 10)
FUENTE_MONO = ("Consolas", 9)


class CasaDeCambioApp:
    """Ventana principal de la casa de cambio."""

    def __init__(self, servicio: AppService) -> None:
        self._s = servicio
        self._raiz = tk.Tk()
        self._raiz.title("CasaDeCambio · Servicio profesional de divisas")
        self._raiz.geometry("1080x680")
        self._raiz.configure(bg=COLOR_FONDO)
        self._liquidar_reloj()

        self._monedas: List[Moneda] = self._s.monedas
        self._clientes: List[Cliente] = self._s.clientes
        self._cliente_ops = {"PÚBLICO (sin cliente)": None}

        self._construir_estilos()
        self._construir_cabecera()
        self._construir_pestanas()
        self.refrescar_todo()

    # ------------------------------------------------------------------
    # Bitácoras y reloj
    # ------------------------------------------------------------------
    def _liquidar_reloj(self) -> None:
        self._raiz.after(1000, self._tick_reloj)

    def _tick_reloj(self) -> None:
        ahora = datetime.now()
        if hasattr(self, "_lbl_reloj"):
            self._lbl_reloj.config(
                text=f"{ahora:%Y-%m-%d}  {ahora:%H:%M:%S}")
        self._raiz.after(1000, self._tick_reloj)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _construir_estilos(self) -> None:
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TNotebook", background=COLOR_FONDO,
                         borderwidth=0)
        estilo.configure("TNotebook.Tab", font=FUENTE_SUB,
                         padding=(18, 8), background=COLOR_PANEL,
                         foreground=COLOR_TEXTO)
        estilo.map("TNotebook.Tab",
                   background=[("selected", COLOR_ACENTO)],
                   foreground=[("selected", "#04203a")])

    def _construir_cabecera(self) -> None:
        marco = tk.Frame(self._raiz, bg=COLOR_FONDO)
        marco.pack(fill=tk.X, padx=18, pady=(14, 4))
        tk.Label(marco, text="CasaDeCambio", bg=COLOR_FONDO,
                 fg=COLOR_DORADO, font=FUENTE_TITULO).pack(side=tk.LEFT)
        tk.Label(marco, text="Divisas contra USD", bg=COLOR_FONDO,
                 fg=COLOR_ACENTO, font=FUENTE_SUB)\
            .pack(side=tk.LEFT, padx=(12, 0), pady=(8, 0))
        self._lbl_reloj = tk.Label(marco, text="", bg=COLOR_FONDO,
                                   fg=COLOR_TEXTO, font=FUENTE_MONO)
        self._lbl_reloj.pack(side=tk.RIGHT)
        tk.Label(marco, text="Operador: mantiene sus tasas con margen "
                             "(compra < venta)", bg=COLOR_FONDO,
                 fg="#9fb3c8", font=("Segoe UI", 9))\
            .pack(side=tk.RIGHT, padx=(0, 14))

        linea = tk.Frame(self._raiz, bg=COLOR_ACENTO, height=2)
        linea.pack(fill=tk.X)

    def _construir_pestanas(self) -> None:
        self._pestanas = ttk.Notebook(self._raiz)
        self._pestanas.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 6))

        self._f_operar = self._pestana("Operar")
        self._f_tasas = self._pestana("Tasas")
        self._f_clientes = self._pestana("Clientes")
        self._f_historial = self._pestana("Historial")
        self._f_caja = self._pestana("Caja")

        self._construir_operar()
        self._construir_tasas()
        self._construir_clientes()
        self._construir_historial()
        self._construir_caja()

    def _pestana(self, titulo: str) -> tk.Frame:
        marco = tk.Frame(self._pestanas, bg=COLOR_PANEL)
        self._pestanas.add(marco, text=titulo)
        return marco

    # ------------------------------------------------------------------
    # Pestana 1 · Operar
    # ------------------------------------------------------------------
    def _construir_operar(self) -> None:
        m = self._f_operar
        izquierda = tk.Frame(m, bg=COLOR_PANEL)
        izquierda.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                       padx=16, pady=16)
        derecha = tk.Frame(m, bg="#0e223c")
        derecha.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True,
                     padx=16, pady=16)

        tk.Label(izquierda, text="Nueva operación", bg=COLOR_PANEL,
                 fg=COLOR_DORADO, font=("Segoe UI", 15, "bold"))\
            .pack(anchor=tk.W)

        self._var_tipo = tk.StringVar(value="COMPRA")
        for texto, valor in (("La casa COMPRA divisa", "COMPRA"),
                             ("La casa VENDE divisa", "VENTA")):
            tk.Radiobutton(izquierda, text=texto, value=valor,
                           variable=self._var_tipo, bg=COLOR_PANEL,
                           fg=COLOR_TEXTO, selectcolor=COLOR_PANEL,
                           activebackground=COLOR_PANEL,
                           activeforeground=COLOR_ACENTO,
                           font=FUENTE_TEXTO)\
                .pack(anchor=tk.W, pady=3)

        tk.Label(izquierda, text="Divisa:", bg=COLOR_PANEL,
                 fg=COLOR_TEXTO, font=FUENTE_SUB).pack(anchor=tk.W,
                                                       pady=(12, 2))
        self._cmb_operar_moneda = ttk.Combobox(
            izquierda, state="readonly", width=34, font=FUENTE_TEXTO)
        self._cmb_operar_moneda.pack(fill=tk.X)
        self._cmb_operar_moneda.bind("<<ComboboxSelected>>",
                                     self._pintar_tasa_operar)

        tk.Label(izquierda, text="Cliente:", bg=COLOR_PANEL,
                 fg=COLOR_TEXTO, font=FUENTE_SUB).pack(anchor=tk.W,
                                                       pady=(12, 2))
        self._cmb_operar_cliente = ttk.Combobox(
            izquierda, state="readonly", width=34, font=FUENTE_TEXTO)
        self._cmb_operar_cliente.pack(fill=tk.X)

        tk.Label(izquierda, text="Monto en la divisa (US$ x unidad):",
                 bg=COLOR_PANEL, fg=COLOR_TEXTO, font=FUENTE_SUB)\
            .pack(anchor=tk.W, pady=(12, 2))
        self._ent_monto = tk.Entry(izquierda, font=("Segoe UI", 14),
                                   bg="#eaf2fb", fg="#04203a",
                                   justify=tk.RIGHT, relief=tk.FLAT)
        self._ent_monto.pack(fill=tk.X, ipady=6)
        self._ent_monto.insert(0, "100.00")

        self._lbl_tasa = tk.Label(izquierda, text="", bg=COLOR_PANEL,
                                  fg=COLOR_ACENTO, font=FUENTE_MONO)
        self._lbl_tasa.pack(anchor=tk.W, pady=(10, 0))

        boton = tk.Button(izquierda, text="EJECUTAR OPERACIÓN",
                          bg=COLOR_ACENTO, fg="#04203a",
                          activebackground=COLOR_DORADO,
                          font=("Segoe UI", 13, "bold"), relief=tk.FLAT,
                          command=self._ejecutar_operacion, cursor="hand2")
        boton.pack(fill=tk.X, pady=(14, 0), ipady=10)

        tk.Label(derecha, text="Ticket / Confirmación", bg="#0e223c",
                 fg=COLOR_DORADO, font=("Segoe UI", 13, "bold"))\
            .pack(anchor=tk.W)
        self._txt_ticket = tk.Text(derecha, width=44, bg="#0e223c",
                                   fg=COLOR_VERDE, font=FUENTE_MONO,
                                   relief=tk.FLAT, padx=12, pady=10)
        self._txt_ticket.pack(fill=tk.BOTH, expand=True, pady=(6, 8))
        self._txt_ticket.insert(tk.END, "Aquí se mostrará el ticket de "
                                        "la operación.\n")
        self._txt_ticket.config(state=tk.DISABLED)

        fila = tk.Frame(derecha, bg="#0e223c")
        fila.pack(fill=tk.X)
        tk.Button(fila, text="Guardar ticket en data/Tickets",
                  bg=COLOR_PANEL, fg=COLOR_TEXTO, relief=tk.FLAT,
                  command=self._guardar_ticket_actual, cursor="hand2")\
            .pack(side=tk.LEFT)
        self._ultima_tx = None

    def _pintar_tasa_operar(self, _event=None) -> None:
        moneda = self._moneda_seleccionada()
        if not moneda:
            self._lbl_tasa.config(text="")
            return
        if self._var_tipo.get() == "COMPRA":
            tasa = moneda.compra
            texto = (f"La casa pagará {tasa:.4f} US$ por cada "
                     f"{moneda.codigo}")
        else:
            tasa = moneda.venta
            texto = (f"La casa cobrará {tasa:.4f} US$ por cada "
                     f"{moneda.codigo}")
        self._lbl_tasa.config(text=texto)

    def _moneda_seleccionada(self) -> Optional[Moneda]:
        sel = self._cmb_operar_moneda.get()
        for moneda in self._monedas:
            if f"{moneda.codigo} · {moneda.nombre}" == sel:
                return moneda
        return None

    def _cliente_seleccionado(self) -> Optional[Cliente]:
        nombre = self._cmb_operar_cliente.get().strip()
        for cliente in self._clientes:
            if cliente.codigo in nombre:
                return cliente
        return None

    def _ejecutar_operacion(self) -> None:
        moneda = self._moneda_seleccionada()
        if not moneda:
            messagebox.showerror("CasaDeCambio",
                                 "Selecciona una divisa primero.")
            return
        try:
            monto = self._s.validar_monto(self._ent_monto.get())
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        cliente = self._cliente_seleccionado()
        try:
            if self._var_tipo.get() == "COMPRA":
                tx = self._s.comprar(moneda.codigo, monto, cliente)
            else:
                tx = self._s.vender(moneda.codigo, monto, cliente)
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        self._ultima_tx = tx
        self._mostrar_ticket(tx)
        self.refrescar_historial_y_caja()
        messagebox.showinfo("CasaDeCambio",
                            f"Operación registrada: folio {tx.folio}",
                            parent=self._raiz)

    def _mostrar_ticket(self, tx) -> None:
        self._txt_ticket.config(state=tk.NORMAL)
        self._txt_ticket.delete("1.0", tk.END)
        self._txt_ticket.insert(tk.END, self._s.ticket(tx))
        self._txt_ticket.config(state=tk.DISABLED)

    def _guardar_ticket_actual(self) -> None:
        if self._ultima_tx is None:
            messagebox.showinfo("CasaDeCambio",
                                "Primero ejecuta una operación.")
            return
        ruta = self._s.guardar_ticket(self._ultima_tx)
        messagebox.showinfo("CasaDeCambio",
                            f"Ticket guardado en:\n{ruta}")

    # ------------------------------------------------------------------
    # Pestana 2 · Tasas
    # ------------------------------------------------------------------
    def _construir_tasas(self) -> None:
        m = self._f_tasas
        tk.Label(m, text="Cotización de divisas (US$ por unidad)",
                 bg=COLOR_PANEL, fg=COLOR_DORADO,
                 font=("Segoe UI", 14, "bold")).pack(anchor=tk.W,
                                                     padx=16, pady=(12, 4))

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self._tabla_tasas = ttk.Treeview(
            contenedor, columns=("codigo", "nombre", "simbolo", "compra",
                                 "venta", "spread"),
            show="headings", height=10)
        anc, alinear = {"codigo": 70, "nombre": 200, "simbolo": 60,
                        "compra": 110, "venta": 110, "spread": 100}, "e"
        for col, ancho in anc.items():
            self._tabla_tasas.heading(col, text=col.upper(),
                                      anchor=tk.CENTER)
            self._tabla_tasas.column(col, width=ancho, anchor=tk.CENTER)
        self._tabla_tasas.tag_configure("base",
                                        background="#1c3a5e", foreground=COLOR_DORADO)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_tasas.yview)
        self._tabla_tasas.configure(yscrollcommand=scroll_y.set)
        self._tabla_tasas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        fila = tk.Frame(m, bg=COLOR_PANEL)
        fila.pack(fill=tk.X, padx=16, pady=(4, 14))
        tk.Button(fila, text="Actualizar tasa", bg=COLOR_ACENTO,
                  fg="#04203a", font=FUENTE_SUB, relief=tk.FLAT,
                  command=self._editar_tasa_gui, cursor="hand2")\
            .pack(side=tk.LEFT, padx=(0, 8), ipadx=8, ipady=5)
        tk.Button(fila, text="Agregar moneda", bg=COLOR_PANEL,
                  fg=COLOR_TEXTO, relief=tk.FLAT, command=self._agregar_moneda_gui)\
            .pack(side=tk.LEFT, padx=(0, 8), ipadx=8, ipady=5)
        tk.Button(fila, text="Eliminar moneda", bg=COLOR_PANEL,
                  fg=COLOR_ROJO, relief=tk.FLAT,
                  command=self._eliminar_moneda_gui)\
            .pack(side=tk.LEFT, ipadx=8, ipady=5)

    def _editar_tasa_gui(self) -> None:
        sel = self._seleccion_tabla(self._tabla_tasas)
        if not sel:
            messagebox.showinfo("CasaDeCambio", "Selecciona una moneda.")
            return
        moneda = self._s.obtener_moneda(sel["codigo"])
        if moneda.es_base:
            messagebox.showinfo("CasaDeCambio",
                                "USD siempre cotiza 1.0000 a 1.0000.")
            return
        ventana = tk.Toplevel(self._raiz)
        ventana.title(f"Actualizar tasa {moneda.codigo}")
        ventana.configure(bg=COLOR_PANEL)
        ventana.resizable(False, False)
        entrada = {}
        tex = ttk.Frame(ventana); tex.pack(padx=18, pady=14)
        ttk.Label(tex, text=moneda.nombre).grid(row=0, column=0,
                                                columnspan=2)
        for i, lbl in (("compra", "Tipo de compra"),
                       ("venta", "Tipo de venta")):
            ttk.Label(tex, text=lbl).grid(row=i + 1, column=0,
                                          sticky=tk.W, pady=3)
            entrada[lbl] = ttk.Entry(tex, width=16)
            entrada[lbl].insert(0, f"{getattr(moneda, i):.4f}")
            entrada[lbl].grid(row=i + 1, column=1, padx=8, pady=3)
        t = ttk.Frame(ventana); t.pack(pady=(0, 14))

        def guardar() -> None:
            try:
                compra = float(entrada["Tipo de compra"].get())
                venta = float(entrada["Tipo de venta"].get())
                self._s.actualizar_tasa(moneda.codigo, compra, venta)
            except Exception as err:
                messagebox.showerror("CasaDeCambio", str(err))
                return
            ventana.destroy()
            self.refrescar_todo()

        ttk.Button(t, text="Guardar", command=guardar)\
            .pack(side=tk.LEFT, padx=6)
        ttk.Button(t, text="Cancelar", command=ventana.destroy)\
            .pack(side=tk.LEFT, padx=6)

    def _agregar_moneda_gui(self) -> None:
        ventana = tk.Toplevel(self._raiz)
        ventana.title("Agregar moneda")
        ventana.configure(bg=COLOR_PANEL)
        ventana.resizable(False, False)
        campos = {}
        cuerpo = ttk.Frame(ventana); cuerpo.pack(padx=18, pady=14)
        etiquetas = ["Código (3 letras)", "Nombre", "Símbolo",
                     "Tipo de compra", "Tipo de venta"]
        for fila, texto in enumerate(etiquetas):
            ttk.Label(cuerpo, text=texto).grid(row=fila, column=0,
                                               sticky=tk.W, pady=3)
            campos[texto] = ttk.Entry(cuerpo, width=18)
            campos[texto].grid(row=fila, column=1, padx=8, pady=3)
        t = ttk.Frame(ventana); t.pack(pady=(0, 14))

        def guardar() -> None:
            try:
                compra = float(campos["Tipo de compra"].get())
                venta = float(campos["Tipo de venta"].get())
                self._s.crear_moneda(campos["Código (3 letras)"].get(),
                                     campos["Nombre"].get(),
                                     campos["Símbolo"].get(), compra, venta)
            except Exception as err:
                messagebox.showerror("CasaDeCambio", str(err))
                return
            ventana.destroy()
            self.refrescar_todo()

        ttk.Button(t, text="Guardar", command=guardar)\
            .pack(side=tk.LEFT, padx=6)
        ttk.Button(t, text="Cancelar", command=ventana.destroy)\
            .pack(side=tk.LEFT, padx=6)

    def _eliminar_moneda_gui(self) -> None:
        sel = self._seleccion_tabla(self._tabla_tasas)
        if not sel:
            messagebox.showinfo("CasaDeCambio", "Selecciona una moneda.")
            return
        if sel["codigo"] == "USD":
            messagebox.showerror("CasaDeCambio",
                                 "La moneda base no puede eliminarse.")
            return
        if not messagebox.askyesno(
                "CasaDeCambio",
                f"¿Eliminar {sel['codigo']} ({sel['nombre']})?"):
            return
        try:
            self._s.eliminar_moneda(sel["codigo"])
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
        else:
            self.refrescar_todo()

    # ------------------------------------------------------------------
    # Pestana 3 · Clientes
    # ------------------------------------------------------------------
    def _construir_clientes(self) -> None:
        m = self._f_clientes
        form = tk.Frame(m, bg=COLOR_PANEL)
        form.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(form, text="Registrar cliente", bg=COLOR_PANEL,
                 fg=COLOR_DORADO, font=("Segoe UI", 13, "bold"))\
            .grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 6))
        self._lc = {}
        for i, (clave, texto, ancho) in enumerate([
                ("nombre", "Nombre completo", 26),
                ("documento", "Documento (DUI/RFC/pasaporte)", 22),
                ("telefono", "Teléfono", 16),
                ("email", "Correo", 24)]):
            etiqueta = tk.Label(form, text=texto, bg=COLOR_PANEL,
                                fg=COLOR_TEXTO, font=("Segoe UI", 9))
            etiqueta.grid(row=1, column=i * 2, sticky=tk.W, padx=(0, 4))
            self._lc[clave] = tk.Entry(form, width=ancho,
                                       bg="#eaf2fb", fg="#04203a")
            self._lc[clave].grid(row=2, column=i * 2, padx=(0, 10),
                                 sticky=tk.W)
        ttk.Button(form, text="Registrar", command=self._registrar_cliente_gui)\
            .grid(row=1, column=8, rowspan=2, sticky=tk.S, padx=6)
        ttk.Button(form, text="Limpiar", command=self._limpiar_form_cliente)\
            .grid(row=1, column=9, rowspan=2, sticky=tk.S)

        busqueda = tk.Frame(m, bg=COLOR_PANEL)
        busqueda.pack(fill=tk.X, padx=16, pady=(0, 6))
        ttk.Label(busqueda, text="Buscar: ").pack(side=tk.LEFT)
        self._ent_buscar = ttk.Entry(busqueda, width=40)
        self._ent_buscar.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(busqueda, text="Buscar", command=self._buscar_clientes_gui)\
            .pack(side=tk.LEFT)
        ttk.Button(busqueda, text="Mostrar todos", command=self.refrescar_todo)\
            .pack(side=tk.LEFT, padx=8)

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self._tabla_clientes = ttk.Treeview(
            contenedor, columns=("codigo", "nombre", "documento",
                                 "telefono", "email"), show="headings")
        for col, ancho in (("codigo", 80), ("nombre", 220),
                           ("documento", 180), ("telefono", 130),
                           ("email", 200)):
            self._tabla_clientes.heading(col, text=col.upper(),
                                         anchor=tk.CENTER)
            self._tabla_clientes.column(col, width=ancho,
                                        anchor=tk.CENTER)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_clientes.yview)
        self._tabla_clientes.configure(yscrollcommand=scroll_y.set)
        self._tabla_clientes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _registrar_cliente_gui(self) -> None:
        try:
            cliente = self._s.crear_cliente(
                self._lc["nombre"].get(), self._lc["documento"].get(),
                self._lc["telefono"].get(), self._lc["email"].get())
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        self._limpiar_form_cliente()
        self.refrescar_todo()
        messagebox.showinfo("CasaDeCambio",
                            f"Cliente registrado: {cliente.codigo}")

    def _limpiar_form_cliente(self) -> None:
        for clave in ("nombre", "documento", "telefono", "email"):
            self._lc[clave].delete(0, tk.END)

    def _buscar_clientes_gui(self) -> None:
        cliente = self._s.buscar_clientes(self._ent_buscar.get())
        self._pintar_clientes(cliente)

    def _pintar_clientes(self, clientes: List[Cliente]) -> None:
        self._tabla_clientes.delete(*self._tabla_clientes.get_children())
        for c in clientes:
            self._tabla_clientes.insert("", tk.END, values=(
                c.codigo, c.nombre, c.documento, c.telefono or "-",
                c.email or "-"))

    # ------------------------------------------------------------------
    # Pestana 4 · Historial
    # ------------------------------------------------------------------
    def _construir_historial(self) -> None:
        m = self._f_historial

        filtros = tk.Frame(m, bg=COLOR_PANEL)
        filtros.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(filtros, text="Ver:", bg=COLOR_PANEL, fg=COLOR_TEXTO)\
            .pack(side=tk.LEFT)
        self._var_hist = tk.StringVar(value="TODOS")
        self._cmb_hist = ttk.Combobox(filtros, textvariable=self._var_hist,
                                      state="readonly", width=18,
                                      values=("TODOS", "COMPRA", "VENTA"))
        self._cmb_hist.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Button(filtros, text="Filtrar",
                   command=self._refrescar_historial).pack(side=tk.LEFT)
        tk.Label(filtros, text=f"   {len(self._s.transacciones)} "
                  "operaciones en total", bg=COLOR_PANEL,
                  fg=COLOR_TEXTO).pack(side=tk.RIGHT)

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        columnas = ("folio", "fecha", "tipo", "moneda", "monto", "local",
                    "tasa", "cliente")
        self._tabla_hist = ttk.Treeview(contenedor, columns=columnas,
                                        show="headings")
        for col, ancho in (("folio", 170), ("fecha", 150), ("tipo", 90),
                           ("moneda", 70), ("monto", 90), ("local", 90),
                           ("tasa", 80), ("cliente", 180)):
            self._tabla_hist.heading(col, text=col.upper(),
                                     anchor=tk.CENTER)
            self._tabla_hist.column(col, width=ancho, anchor=tk.CENTER)
        self._tabla_hist.tag_configure("COMPRA", foreground=COLOR_VERDE)
        self._tabla_hist.tag_configure("VENTA", foreground=COLOR_ROJO)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_hist.yview)
        self._tabla_hist.configure(yscrollcommand=scroll_y.set)
        self._tabla_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _refrescar_historial(self) -> None:
        lista = reversed(self._s.transacciones)
        filtro = self._var_hist.get() if hasattr(self, "_var_hist") else \
            "TODOS"
        self._tabla_hist.delete(*self._tabla_hist.get_children())
        for tx in lista:
            if filtro != "TODOS" and tx.tipo != filtro:
                continue
            self._tabla_hist.insert("", tk.END, tags=(tx.tipo,), values=(
                tx.folio, f"{tx.fecha:%Y-%m-%d %H:%M}", tx.tipo,
                tx.moneda, f"{tx.monto_divisa:,.2f}",
                f"{tx.monto_local:,.2f}", f"{tx.tasa:.4f}", tx.cliente))

    def _refrescar_historial_y_caja(self) -> None:
        self._refrescar_historial()
        self._refrescar_caja()

    # ------------------------------------------------------------------
    # Pestana 5 · Caja
    # ------------------------------------------------------------------
    def _construir_caja(self) -> None:
        m = self._f_caja
        encabezado = tk.Frame(m, bg=COLOR_PANEL)
        encabezado.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(encabezado, text="Cierre de caja (arqueo del día)",
                 bg=COLOR_PANEL, fg=COLOR_DORADO,
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(encabezado, text="Generar arqueo",
                   command=self._actualizar_caja).pack(side=tk.RIGHT)
        ttk.Button(encabezado, text="Guardar reporte",
                   command=self._guardar_arqueo_gui).pack(side=tk.RIGHT,
                                                          padx=8)

        contenedor = tk.Frame(m, bg="#0e223c")
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        self._txt_caja = tk.Text(contenedor, bg="#0e223c", fg=COLOR_VERDE,
                                 font=FUENTE_MONO, relief=tk.FLAT,
                                 padx=14, pady=12)
        self._txt_caja.pack(fill=tk.BOTH, expand=True)
        self._txt_caja.insert(tk.END, "Genera el arqueo para ver el "
                                      "resumen del día.\n")
        self._txt_caja.config(state=tk.DISABLED)

    def _actualizar_caja(self) -> None:
        self._refrescar_caja()

    def _refrescar_caja(self) -> None:
        try:
            arqueo = self._s.generar_arqueo()
        except Exception as err:
            return
        self._txt_caja.config(state=tk.NORMAL)
        self._txt_caja.delete("1.0", tk.END)
        self._txt_caja.insert(tk.END, arqueo.texto())
        self._txt_caja.config(state=tk.DISABLED)

    def _guardar_arqueo_gui(self) -> None:
        try:
            ruta = self._s.guardar_arqueo()
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        messagebox.showinfo("CasaDeCambio",
                            f"Reporte guardado en:\n{ruta}")

    # ------------------------------------------------------------------
    # Refrescos globales
    # ------------------------------------------------------------------
    @staticmethod
    def _seleccion_tabla(tabla: ttk.Treeview) -> dict:
        sel = tabla.selection()
        if not sel:
            return {}
        valores = tabla.item(sel[0])["values"]
        if not sel:
            return {}
        valores = tabla.item(sel[0])["values"]
        return {col: valores[i]
                for i, col in enumerate(tabla["columns"])}

    def _refrescar_tasas(self) -> None:
        self._tabla_tasas.delete(*self._tabla_tasas.get_children())
        for moneda in self._s.monedas:
            spread = moneda.venta - moneda.compra
            etiqueta = "base" if moneda.es_base else ""
            self._tabla_tasas.insert("", tk.END, tags=(etiqueta,), values=(
                moneda.codigo, moneda.nombre, moneda.simbolo,
                f"{moneda.compra:.4f}", f"{moneda.venta:.4f}",
                f"{spread:.4f}"))

    def _refrescar_combos(self) -> None:
        self._monedas = self._s.monedas
        self._clientes = self._s.clientes
        opciones_moneda = [f"{m.codigo} · {m.nombre}" for m in self._monedas
                           if not m.es_base]
        self._cmb_operar_moneda["values"] = opciones_moneda
        if opciones_moneda and not self._cmb_operar_moneda.get():
            self._cmb_operar_moneda.current(0)

        opciones_cliente = ["PÚBLICO (sin cliente)"] + [
            f"{c.codigo} · {c.nombre}" for c in self._clientes]
        self._cmb_operar_cliente["values"] = opciones_cliente
        if opciones_cliente and not self._cmb_operar_cliente.get():
            self._cmb_operar_cliente.current(0)
        self._pintar_tasa_operar()

    def refrescar_todo(self) -> None:
        if hasattr(self, "_tabla_tasas"):
            self._refrescar_tasas()
        if hasattr(self, "_tabla_clientes"):
            self._pintar_clientes(self._s.clientes)
        if hasattr(self, "_tabla_hist"):
            self._refrescar_historial()
        if hasattr(self, "_txt_caja"):
            self._refrescar_caja()
        if hasattr(self, "_cmb_operar_moneda"):
            self._refrescar_combos()

    def iniciar(self) -> None:
        self._raiz.mainloop()
