import re #PARA EXPRESIONES REGULARES
import tkinter as tk 
from tkinter import filedialog, ttk
import tkinter.font as tkfont

# --- EXCEPCIONES PERSONALIZADAS ---
#CLASE DE EXCEPCIONES 
class ErrorLexico(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(f"Error léxico {codigo}: {mensaje}") #CONSTRUYE EXCEPCION DEPENDIENDO EL ERROR
        self.codigo = codigo
        self.mensaje = mensaje

class ErrorSintactico(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(f"Error sintáctico {codigo}: {mensaje}") #CONSTRUYE EXCEPCION DEPENDIENDO EL ERROR
        self.codigo = codigo
        self.mensaje = mensaje    

class Lexico:
    def __init__(self, codigo):
        self.codigo = codigo # ALMACENA TODO EL TEXTO A TOKENIZAR
        self.palabrasReservadas = {'ip','set','add','dhcp','ospf','eigrp','ssh','gateway','first','last',
                         'mask','wildcard','range','for','generate','as','area','firstUsable','lastUsable',
                         'name','pool','dns','exclude','print','domain','hostname','subnetwork','networkList',
                         'host','router-id','user','password','modulus','passwordUs'}
        #SE DEFINEN LOS PATRONES DE LOS COMPONENTES LEXICOS
        self.ip_patron = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
        patrones_lexemas = [
            ('NETWORK',   r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
            ('NUMERO',    r"\b\d+\b"),
            ('STRING',    r'"[^\"]*"'),
            ('IGUAL',    r'='),
            ('PUNTOYCOMA',r';'),
            ('COMA',r','),
            ('PUNTO',r'\.'),
            ('LCORCHETE',  r'\['),('RCORCHETE',r'\]'),
            ('MENORQUE',    r'<'),('MAYORQUE',r'>'),
            ('COMENTARIO',   r'//[^\n]*'),
            ('SALTOLINEA',r'\n'),
            ('SALTAR',      r'[ \t]+'),
            ('IDENTIFICADOR',r"\b[A-Za-z_][A-Za-z0-9_-]*\b"),
            ('CARACTER_INVALIDO', r'.')
        ]
        self.errores = []
        self.patron_principal = re.compile('|'.join(f"(?P<{n}>{p})" for n,p in patrones_lexemas)) #ES LA EXPRESION QUE "UNE" TODOS LOS PATRONES
    def tokenize(self):
            # try:
                numero_linea = 1; linea_inicial = 0; tokens = []
                for mo in self.patron_principal.finditer(self.codigo):
                    componente_lexico, lexema = mo.lastgroup, mo.group()
                    col = mo.start() - linea_inicial + 1
                    #SI ES COMENTARIO, IGNORALO
                    if componente_lexico == 'COMENTARIO':
                        tokens.append((componente_lexico, lexema.lower(), numero_linea, col)); continue
                    print(numero_linea)
                    #SI ES NUEVA LINEA, IGNORALA
                    if componente_lexico == 'SALTOLINEA':
                        linea_inicial = mo.end(); numero_linea += 1; continue
                    #SI ES SALTO DE LINEA, IGNORA
                    if componente_lexico == 'SALTAR': continue
                    #SI EL CARACTER ES INVALIDO
                    if componente_lexico == 'CARACTER_INVALIDO':
                        raise ErrorLexico(100, f"Carácter no válido '{lexema}' en línea {numero_linea}, columna {col}")
                    # EXCEPCION PARA IDENTIFICADOR
                    if componente_lexico == 'IDENTIFICADOR':
                        if lexema in self.palabrasReservadas:
                            componente_lexico = lexema
                        elif len(lexema) > 15:
                            raise ErrorLexico(200, f"Identificador demasiado largo '{lexema}' en línea {numero_linea}")
                    # VALIDACION PARA LAS NETWORK, QUE LOS OCTETOS NO SUPEREN LOS 255
                    if componente_lexico == 'NETWORK':
                        octetos = [int(o) for o in self.ip_patron.match(lexema).groups()] #VERIFICACION POR OCTETOS
                        if any(o > 255 for o in octetos): #SI UN OCTETO SUPERA LOS 255 BITS
                            raise ErrorLexico(300, f"IP no puede superar 255 en línea {numero_linea}") 
                    tokens.append((componente_lexico, lexema, numero_linea, col))
                #TOKENS INVALIDOS
                if not tokens:
                    raise ErrorLexico(400, "No se encontraron tokens válidos")
                return tokens
            # except ErrorLexico as e:
            #     self.errores.append(e)

class Parser:
        def __init__(self, tokens):
            self.tokens = tokens
            self.index = 0
            self.current = self.tokens[self.index] if self.tokens else None
            self.previous = None #PRUEBA DEL TOKEN ANTERIOR 
            self.errores = []

        def advance(self):
            self.index += 1
            if self.index < len(self.tokens):
                self.current = self.tokens[self.index]
                self.previous = self.tokens[self.index] 
            else:
                self.current = ('EOF', 'EOF')
        
        def match(self, tipo, valor=None):
            if self.current[0] == tipo and (valor is None or self.current[1] == valor):
                self.advance()
            else:
                token = self.current or self.previous
                linea = token[2] if token and len(token) > 2 else self.previous[2]
                columna = token[3] if token and len(token) > 3 else self.previous [3]              # Según el tipo esperado, lanza un error específico
                if tipo == 'IDENTIFICADOR':
                    raise ErrorSintactico(700, f"Se esperaba un identificador en línea {linea}, columna {columna}")
                elif tipo == 'NUMERO':
                    raise ErrorSintactico(910, f"Se esperaba un número en línea {linea}, columna {columna}")
                elif tipo == 'PUNTOYCOMA':
                    raise ErrorSintactico(932, f"Se esperaba un punto y coma en linea {linea-1} columna {columna} ")
                else:
                    raise ErrorSintactico(1000,f"Se esperaba '{valor or tipo}' en línea {linea}, columna {columna}")

        def parse(self):
            self.errores.clear()
            while self.current[0] != 'EOF':
                try:
                    self.instruccion()
                except ErrorSintactico as e:
                    self.errores.append(e)
                    self.advance()
                except ErrorLexico as e:
                    self.errores.append(e)
                    self.advance()

        def instruccion(self):
            if self.current[0] == 'COMENTARIO':
                print('soy comentario')
                self.advance()
                print(self.current)
            if self.current[1] == 'networkList':
                self.declaracion_red()
            elif self.current[1] == 'print':
                self.advance()
                if self.current[1] == 'subnetwork':
                    self.advance()
                else:
                    raise ErrorSintactico(1800, f"Se esperaba subnetwork en linea {self.current[2]} columna {self.current[3]}")
                if self.current[1] == 'wildcard':
                    self.print_wildcard()
                if self.current[1] == 'range':
                    self.print_range()
                if self.current[1] == 'gateway':
                    self.print_gateway()
            elif self.current[1] == 'set':
                self.advance()
                if self.current[1] == 'gateway':
                    self.config_gateway()
                elif self.current[1] == 'exclude':
                    self.config_exclude()
                elif self.current[1] == 'dns':
                    self.config_dns()
                elif self.current[1] == 'router-id':
                    self.config_routerid()
                else:
                    raise ErrorSintactico(2000,f"Instrucción desconocida después de 'set': {self.current[1]}")
            elif self.current[1] == 'generate':
                self.advance()
                if self.current[1] == 'dhcp':
                    self.generar_dhcp()
                elif self.current[1] == 'ospf':
                    self.generar_ospf()
                elif self.current[1] == 'eigrp':
                    self.generar_eigrp()
                elif self.current[1] == 'ssh':
                    self.generar_ssh()
            else:
                raise ErrorSintactico(1000,f"Inesperado: {self.current[1]} en línea {self.current[2]}, columna {self.current[3]}")

        def declaracion_red(self):
            self.match('networkList')
            self.match('IDENTIFICADOR')
            self.match('IGUAL', '=')
            self.match('ip', 'ip')
            self.match('add', 'add')
            self.match('NETWORK'),
            self.match('host', 'host')
            self.match('MENORQUE', '<')
            self.lista_numeros()
            self.match('MAYORQUE', '>')
            self.match('PUNTOYCOMA', ';')

        def config_gateway(self):
            self.match('gateway', 'gateway')
            if self.current[1] in ('first', 'last'):
                self.advance()
                self.match('PUNTOYCOMA', ';')
            else:
                raise ErrorSintactico(1300,"Se esperaba 'first' o 'last' después de 'set gateway'")

        def config_exclude(self):
            self.match('exclude', 'exclude')
            self.match('IGUAL', '=')
            self.match('LCORCHETE', '[')
            self.lista_networks()
            self.match('RCORCHETE', ']')
            self.match('PUNTOYCOMA', ';')

        def config_dns(self):
            self.match('dns', 'dns')
            self.match('IGUAL', '=')
            self.match('NETWORK')
            self.match('PUNTOYCOMA', ';')

        def generar_dhcp(self):
            self.match('dhcp', 'dhcp')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('PUNTOYCOMA', ';')

        def config_routerid(self):
            self.match('router-id', 'router-id')
            self.match('IGUAL', '=')
            self.match('NETWORK')
            self.match('PUNTOYCOMA', ';')

        def generar_ospf(self):
            self.match('ospf', 'ospf')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('area', 'area')
            self.match('NUMERO')
            self.match('PUNTOYCOMA', ';')

        def generar_eigrp(self):
            self.match('eigrp', 'eigrp')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('as', 'as')
            self.match('NUMERO')
            self.match('PUNTOYCOMA', ';')

        def generar_ssh(self):
            self.match('ssh','ssh')
            self.match('hostname','hostname')
            self.match('STRING')
            self.match('domain','domain')
            self.match('STRING')
            self.match('user','user')
            self.match('STRING')
            self.match('password', 'password')
            self.match('STRING')
            self.match('modulus', 'modulus')
            self.match('NUMERO')
            self.match('PUNTOYCOMA',';')
        
        def print_wildcard(self):
            self.match('wildcard', 'wildcard')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('PUNTOYCOMA', ';')

        def print_range(self):
            self.match('range', 'range')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('PUNTOYCOMA', ';')
            
        def print_gateway(self):
            self.match('gateway', 'gateway')
            self.match('for', 'for')
            self.match('IDENTIFICADOR')
            self.match('PUNTOYCOMA', ';')

        def lista_numeros(self):
            self.match('NUMERO')
            while self.current[1] == ',':
                self.advance()
                self.match('NUMERO')

        def lista_networks(self):
            self.match('NETWORK')
            while self.current[1] == ',':
                self.advance()
                self.match('NETWORK')

# --- INTERFAZ GRÁFICA ---
class NetworkLangEditor:
    def __init__(self):
        self.root = tk.Tk(); self.root.title("Network Config Language")
        self.archivo_actual = None
        self.font = tkfont.Font(family='Courier', size=12)
        from_copy = Lexico('')
        self.tokens_palabras_reservadas = {kw for kw in from_copy.palabrasReservadas}
        self.COMENTARIO_patron = re.compile(r'//[^\n]*')
        # DECLARACION DE TABLAS DE SÍMBOLOS 
        self.tablaSimbolos = []
        self.tablaSimbolosKW = []
        self.tablaSimbolosID = []

        self._build_widgets()
        self.input_text.focus_set()
        self.root.mainloop()

    def _build_widgets(self):
        #BARRA MENU
        menubar = tk.Menu(self.root)
        #SUBMENU ARCHIVO
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Abrir...", command=self.abrir_archivo)
        file_menu.add_command(label="Guardar", command=self.guardar_archivo)
        file_menu.add_command(label="Guardar como...", command=self.guardar_archivo_como)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        #SUBMENU COMPILAR
        comp_menu = tk.Menu(menubar, tearoff=0)
        comp_menu.add_command(label="Compilador Léxico", command=self.ejecutar_lexico)
        comp_menu.add_command(label="Compilador Sintáctico", command=self.compilar_sintactico)
        menubar.add_cascade(label="Compilar", menu=comp_menu)
        #SUBMENU TABLAS
        tablas_menu = tk.Menu(menubar,tearoff=0)
        tablas_menu.add_command(label="Tabla de Simbolos de Palabras Reservadas",command=self.mostrar_tabla_simbolos_kw)
        tablas_menu.add_command(label="Tabla de Simbolos", command=self.mostrar_tabla_simbolos)
        tablas_menu.add_command(label="Tabla de simbolos de identificadores", command=self.mostrar_tabla_simbolos_id)
        menubar.add_cascade(label="Tablas de simbolos", menu=tablas_menu)

        self.root.config(menu=menubar)

        #FRAME PRINCIPAL
        frame = tk.Frame(self.root); frame.pack(fill='both', expand=True) #VENTANA
        self.ln_text = tk.Text(frame, width=4, padx=2, bd=0,
                               bg='#f0f0f0', fg='black', font=self.font, state='disabled') #PANEL DE NUMERO DE LINEA
        self.ln_text.pack(side='left', fill='y')
        scroll = tk.Scrollbar(frame, orient='vertical') #PANEL PARA EL CODIGO SCROLLEABLE
        self.input_text = tk.Text(frame, wrap='none', undo=True,
                                  yscrollcommand=self._on_yscroll, font=self.font) #INPUT TEXT PARA EL CODIGO
        scroll.config(command=self._on_scroll) #CONFIGURACIONES PARA EL SCROLL
        self.input_text.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self.input_text.tag_config('COMENTARIO', foreground='green') #SI ES COMENTARIO, PINTALO DE VERDE
        for seq in ('<KeyRelease>','<MouseWheel>','<Button-1>','<Configure>'):
            self.input_text.bind(seq, lambda e: (self._actualizar_numero_linea(), self._reamarcar_comentarios())) #ACTUALIZAR NUMERO DE LINEA CONSTANTEMENTE

        self.texto_salida = tk.Text(self.root, height=10, state='disabled', font=self.font) #TEXTO DE SALIDA (CONSOLA)
        self.texto_salida.pack(fill='x')
        self._actualizar_numero_linea(); self._reamarcar_comentarios() #ACTUALIZA NUMERO DE LINEA

    #CLASE PARA REMARCAR COMENTARIOS
    def _reamarcar_comentarios(self):
        text = self.input_text.get('1.0', 'end-1c')
        self.input_text.tag_remove('COMENTARIO', '1.0', 'end')
        for m in self.COMENTARIO_patron.finditer(text):
            start = f"1.0+{m.start()}c"; end = f"1.0+{m.end()}c"
            self.input_text.tag_add('COMENTARIO', start, end)

    #MANEJADOR DE SCROLL Y NUMERO DE LINEA
    def _on_scroll(self, *args):
        self.input_text.yview(*args); self.ln_text.yview(*args)

    def _on_yscroll(self, *args):
        self.ln_text.yview_moveto(args[0]); self.texto_salida.yview_moveto(args[0])

    def _actualizar_numero_linea(self):
        self.ln_text.config(state='normal'); self.ln_text.delete('1.0','end')
        total = int(self.input_text.index('end-1c').split('.')[0])
        nums = ''.join(f"{i}\n" for i in range(1, total+1))
        self.ln_text.insert('1.0', nums); self.ln_text.config(state='disabled')
        self.ln_text.yview_moveto(self.input_text.yview()[0])

    #CLASES PARA ARCHIVOS 
    def abrir_archivo(self):
        path = filedialog.askopenfilename(defaultextension='.nle', filetypes=[('Network Lang','*.nle')])
        if not path: return
        txt = open(path, encoding='utf-8').read()
        self.input_text.delete('1.0','end'); self.input_text.insert('1.0', txt)
        self.archivo_actual = path; self.root.title(f"Network Config Language - {path}")
        self._actualizar_numero_linea(); self._reamarcar_comentarios()

    def guardar_archivo(self):
        if not self.archivo_actual: return self.guardar_archivo_como()
        open(self.archivo_actual,'w',encoding='utf-8').write(self.input_text.get('1.0','end-1c'))

    def guardar_archivo_como(self):
        path = filedialog.asksaveasfilename(defaultextension='.nle', filetypes=[('Network Lang','*.nle')])
        if not path: return
        self.archivo_actual = path; self.guardar_archivo(); self.root.title(f"Network Config Language - {path}")

    #CLASE QUE EJECUTA EL ANALIZADOR LÉXICO
    def ejecutar_lexico(self):
        codigo = ""
        codigo = self.input_text.get('1.0','end-1c')
        self.texto_salida.config(state='normal'); self.texto_salida.delete('1.0','end')

        try:
            tokens = Lexico(codigo).tokenize()
            if tokens :
                self._mostrar_tokens(tokens)
        except ErrorLexico as e:
            self._mostrar_salida(str(e), error=True) #CAPTURA DE ERRORES Y COMPARACION CON LOS CREADOS

        # lexer = Lexico(codigo)
        # tokens = lexer.tokenize()

       
            
        # for error in lexer.errores:
        #     self.texto_salida.insert('end', str(error) + '\n')
        # self._mostrar_salida(str(e), error=True) #CAPTURA DE ERRORES Y COMPARACION CON LOS CREADOS
            

    def compilar_sintactico(self):
        # try:
            codigo = self.input_text.get('1.0', 'end-1c')
            self.texto_salida.config(state='normal'); self.texto_salida.delete('1.0','end')
            tokens = Lexico(codigo).tokenize()
            print(tokens)
            parser = Parser(tokens)
            parser.parse()
            self.texto_salida.config(state='normal')
           
            self.tablaSimbolosID.clear()
            self.tablaSimbolosKW.clear()
            self.tablaSimbolos.clear()

            for componente_lexico, val, ln, col in tokens: #IDENTIFICAR A QUE TOKEN PERTENECE Y MOSTRAR LA INFORMACIÓN NECESARIA
                if componente_lexico in self.tokens_palabras_reservadas:
                    tokenTemp = self.Token(ln,col,componente_lexico,val)
                    self.tablaSimbolosKW.append(tokenTemp)
                else:
                    tokenTemp = self.Token(ln,col,componente_lexico,val)
                    if tokenTemp.componenteLexico == 'IDENTIFICADOR':
                        print("soy un identificador")
                        self.tablaSimbolosID.append(tokenTemp)
                    else:
                        self.tablaSimbolos.append(tokenTemp)
            self._mostrar_tablas()
            if not parser.errores:
               self.texto_salida.insert('end', 'SIN ERRORES SINTACTICOS' + '\n') 
            for error in parser.errores:
                self.texto_salida.insert('end', str(error) + '\n')
        # except ErrorLexico as e:
        #     self.texto_salida.insert('end', str(e) + '\n')

    #CLASE QUE MUESTRA LOS TOKENS
    def _mostrar_tokens(self, toks):
        self.texto_salida.config(state='normal'); self.texto_salida.delete('1.0','end') #EL PANEL DE LA (CONSOLA SE ACTIVA PARA ESCRIBIR OUTPUT Y BORRA LO ANTERIOR)
        self.tablaSimbolosID.clear()
        self.tablaSimbolosKW.clear()
        self.tablaSimbolos.clear()
        for componente_lexico, val, ln, col in toks: #IDENTIFICAR A QUE TOKEN PERTENECE Y MOSTRAR LA INFORMACIÓN NECESARIA
            if componente_lexico in self.tokens_palabras_reservadas:
                self.texto_salida.insert('end', f"{ln}:{col} \t{componente_lexico}, {val}\n")
                tokenTemp = self.Token(ln,col,componente_lexico,val)
                self.tablaSimbolosKW.append(tokenTemp)
            else:
                self.texto_salida.insert('end', f"{ln}:{col}\t{componente_lexico}\t{val}    \n")
                tokenTemp = self.Token(ln,col,componente_lexico,val)
                if tokenTemp.componenteLexico == 'IDENTIFICADOR':
                    self.tablaSimbolosID.append(tokenTemp)
                else:
                    self.tablaSimbolos.append(tokenTemp)
        self.texto_salida.config(state='disabled')
        self._mostrar_tablas()
    
    #CLASE PARA MOSTRAR SALIDA. INSERTA TODO LO OBTENIDO DE MOSTRAR TOKENS Y LO PEGA EN EL TEXT AREA DE SALIDA
    def _mostrar_salida(self, msg, error=False):
        self.texto_salida.config(state='normal'); self.texto_salida.delete('1.0','end')
        self.texto_salida.insert('end', msg + '\n'); self.texto_salida.config(state='disabled')

    def _mostrar_tablas(self):
        print("\n--- Tabla de Símbolos: Palabras Reservadas ---")
        for token in self.tablaSimbolosKW:
            print(f"{token.linea}:{token.columna} - {token.componenteLexico} => '{token.lexema}'")

        print("\n--- Tabla de Símbolos: Otros Tokens ---")
        for token in self.tablaSimbolos:
            print(f"{token.linea}:{token.columna} - {token.componenteLexico} => '{token.lexema}'")

    def mostrar_tabla_simbolos(self):
        self._abrir_modal("Tabla de Símbolos", self.tablaSimbolos)

    def mostrar_tabla_simbolos_kw(self):
        self._abrir_modal("Tabla de Palabras Reservadas", self.tablaSimbolosKW)

    def mostrar_tabla_simbolos_id(self):
        self._abrir_modal("Tabla de Símbolos", self.tablaSimbolosID)

    def _abrir_modal(self, title, lista_tokens):
        modal = tk.Toplevel(self.root)
        modal.title(title)
        modal.transient(self.root)
        modal.grab_set()
        cols = ('Línea', 'Columna', 'Comp. Léxico', 'Lexema')

        style = ttk.Style(modal)
        style.configure("Custom.Treeview", rowheight=32)

        tree = ttk.Treeview(modal, columns=cols, show='headings', style="Custom.Treeview")
        vsb = ttk.Scrollbar(modal, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        for c in cols:
            tree.heading(c, text=c, anchor='center')
            tree.column(c, anchor='center', width=250)
        for tok in lista_tokens:
            tree.insert('', 'end', values=(tok.linea, tok.columna, tok.componenteLexico, tok.lexema))
        tree.pack(fill='both', expand=True)
        btn = tk.Button(modal, text="Cerrar", command=modal.destroy)

    class Token:
        def __init__(self,linea,columna,componenteLexico,lexema):
            self.linea = linea
            self.columna = columna
            self.componenteLexico = componenteLexico
            self.lexema = lexema

if __name__=='__main__':
    NetworkLangEditor()
