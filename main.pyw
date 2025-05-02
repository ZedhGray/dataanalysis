import sys
import re
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib
import math
matplotlib.use('QtAgg')  # Use a more generic Qt backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFrame, QComboBox,
                           QTableWidget, QTableWidgetItem, QHeaderView, 
                           QTabWidget, QSplitter, QMessageBox,
                           QDateEdit, QCheckBox)
from PyQt6.QtCore import Qt, QDate, QDateTime
from PyQt6.QtGui import QColor
from database import get_ventas_data

class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MatplotlibCanvas, self).__init__(self.fig)


class TireAnalysisTab(QWidget):
    def __init__(self, dataframe=None):
        super().__init__()
        self.df = dataframe
        self.current_page = 0
        self.tires_per_page = 10
        self.total_tires = 0
        self.top_tires_df = None
        self.total_pages = 0
        self.init_ui()
        
    def init_ui(self):
        # Layout principal
        main_layout = QVBoxLayout()
        
        # Título
        title_label = QLabel("Análisis de Llantas Más Vendidas")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Información de la vista actual
        self.info_layout = QHBoxLayout()
        self.page_info_label = QLabel("Mostrando llantas 0-0 de 0")
        self.info_layout.addWidget(self.page_info_label)
        self.info_layout.addStretch()
        main_layout.addLayout(self.info_layout)
        
        # Contenedor para el gráfico
        self.chart_frame = QFrame()
        self.chart_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.chart_frame.setMinimumHeight(400)
        self.chart_layout = QVBoxLayout(self.chart_frame)
        main_layout.addWidget(self.chart_frame)
        
        # Botones de navegación
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        
        self.prev_button = QPushButton("← Anterior")
        self.prev_button.clicked.connect(self.previous_page)
        self.prev_button.setEnabled(False)
        
        self.next_button = QPushButton("Siguiente →")
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        main_layout.addLayout(nav_layout)
        
        # Tabla de datos
        self.table_label = QLabel("Detalle de Llantas Más Vendidas:")
        self.table_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(self.table_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Modelo", "Cantidad Vendida", "Ingresos Totales", "Precio Promedio"])
        
        # Fixed: Proper PyQt6 way to set section resize mode
        header = self.table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)
        
        self.setLayout(main_layout)
        
    def actualizar_analisis(self, dataframe=None):
        """Actualiza el análisis con el nuevo dataframe filtrado"""
        # Si se proporciona un dataframe, lo usamos, si no, obtenemos los datos
        if dataframe is not None:
            self.df = dataframe
            
            # Mostrar un indicador de progreso
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt
            
            progress = QProgressDialog("Analizando datos de llantas...", "Cancelar", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(10)
            
            try:
                # Extraer ventas filtradas
                ventas_filtradas = {}
                
                if 'Folio' in self.df.columns:
                    # Convertir el dataframe filtrado a un diccionario de ventas
                    for _, row in self.df.iterrows():
                        folio = row['Folio']
                        venta_dict = row.to_dict()
                        ventas_filtradas[folio] = venta_dict
                
                progress.setValue(30)
                
                # Si no hay ventas después del filtrado, mostrar mensaje y limpiar
                if not ventas_filtradas:
                    self.clear_analysis()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Sin datos", 
                                        "No hay datos de ventas en el período seleccionado.")
                    progress.setValue(100)
                    return
                
                # Extraer información de llantas desde los datos de ventas filtradas
                llantas_agrupadas = self.extraer_y_agrupar_llantas(ventas_filtradas)
                progress.setValue(70)
                
                # Convertir a DataFrame para su visualización
                import pandas as pd
                if llantas_agrupadas:
                    # Convertir a DataFrame
                    llantas_df = pd.DataFrame(list(llantas_agrupadas.values()))
                    
                    # Ordenar por cantidad vendida (de mayor a menor)
                    llantas_df = llantas_df.sort_values('cantidad', ascending=False)
                    
                    # Tomar las top 100 o todas si hay menos de 100
                    self.total_tires = min(100, len(llantas_df))
                    self.top_tires_df = llantas_df.head(self.total_tires)
                    
                    # Calcular número de páginas
                    import math
                    self.total_pages = math.ceil(self.total_tires / self.tires_per_page)
                    
                    # Mostrar la primera página
                    self.current_page = 0
                    self.mostrar_pagina_actual()
                    
                    progress.setValue(100)
                else:
                    self.clear_analysis()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Sin datos", 
                                    "No se encontraron datos de llantas en las ventas del período seleccionado.")
                    progress.setValue(100)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error al procesar datos de llantas: {str(e)}")
                progress.setValue(100)
                self.clear_analysis()
        else:
            # Si no hay dataframe proporcionado, intentamos obtener los datos de todos modos
            # Obtener datos directamente usando get_ventas_data
            try:
                from database import get_ventas_data
                ventas_data = get_ventas_data()
                if not ventas_data:
                    self.clear_analysis()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Sin datos", 
                                    "No se pudieron obtener datos de ventas del sistema.")
                    return
                
                # Extraer información de llantas desde los datos de ventas
                llantas_agrupadas = self.extraer_y_agrupar_llantas(ventas_data)
                
                # Convertir a DataFrame para su visualización
                import pandas as pd
                if llantas_agrupadas:
                    # Convertir a DataFrame
                    llantas_df = pd.DataFrame(list(llantas_agrupadas.values()))
                    
                    # Ordenar por cantidad vendida (de mayor a menor)
                    llantas_df = llantas_df.sort_values('cantidad', ascending=False)
                    
                    # Tomar las top 100 o todas si hay menos de 100
                    self.total_tires = min(100, len(llantas_df))
                    self.top_tires_df = llantas_df.head(self.total_tires)
                    
                    # Calcular número de páginas
                    import math
                    self.total_pages = math.ceil(self.total_tires / self.tires_per_page)
                    
                    # Mostrar la primera página
                    self.current_page = 0
                    self.mostrar_pagina_actual()
                else:
                    self.clear_analysis()
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Sin datos", 
                                    "No se encontraron datos de llantas en las ventas.")
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error al obtener datos de ventas: {str(e)}")
                self.clear_analysis()
    
    def extraer_y_agrupar_llantas(self, ventas_data):
        """
        Extrae información de llantas desde los campos de ventas y las agrupa por modelo
        """
        # Keywords para exclusión
        keywords_no_llanta = [
            'CAMARA', 'VÁLVULA', 'VALVULA', 'PARCHE', 'SENSOR', 'TPMS', 'RELLENADO', 'RELLENAR',
            'MONTAJE', 'BALANCEO', 'BALANCEAR', 'REPARACION', 'REPARAR', 'ROTACION',
            'DESMONTAJE', 'DESMONTAR', 'SECCION', 'CALIBRACION', 'CALIBRANDO', 'CORBATA',
            'CORBATAS', 'REVISION', 'CALIBRAR', 'RIN', 'RINES', 'INSTALACION', 'TALACHA', 
            'USADAS', 'USADA', 'GALLO', 'GALLITOS', 'GALLOS', 'REPARACION', 'REPARAR', 
            'DIFERENCIA EN PRECIO', 'GALLOS', 'REPARCION', 'COMPLEMENTO'
        ]
        
        # Lista para almacenar todas las llantas encontradas
        todas_llantas = []
        
        # Contadores para diagnóstico
        ventas_procesadas = 0
        ventas_con_llantas = 0
        total_llantas_encontradas = 0
        
        # Procesar cada venta
        for folio, venta in ventas_data.items():
            ventas_procesadas += 1
            llantas_encontradas = False
            
            # Saltarse ventas canceladas
            if venta.get('estado', '') == 'CANCELADA':
                continue
            
            # Campos donde buscar llantas
            campos_a_revisar = ['articulos', 'bitacora', 'ticket']
            
            for campo in campos_a_revisar:
                if campo in venta and venta[campo]:
                    texto = venta[campo]
                    
                    # Verificar que el texto sea una cadena
                    if not isinstance(texto, str):
                        continue
                    
                    # Dividir por líneas para un mejor procesamiento
                    lineas = texto.split('\n')
                    
                    # MEJORADO: Buscar bloques de información en formato de ticket
                    # Donde primero aparece cantidad, luego descripción y luego importe
                    in_item_section = False
                    for i, linea in enumerate(lineas):
                        linea_upper = linea.upper().strip()
                        
                        # Detectar si estamos en la sección de artículos del ticket
                        if "CANT" in linea_upper and "DESCRIPCION" in linea_upper and "IMPORTE" in linea_upper:
                            in_item_section = True
                            continue
                        
                        # Si encontramos la línea de totales, salimos de la sección de artículos
                        if in_item_section and ("ARTICULOS" in linea_upper and "IMPORTE:" in linea_upper):
                            in_item_section = False
                            continue
                        
                        # Procesar líneas dentro de la sección de artículos
                        if in_item_section and linea.strip() and not linea.startswith("---"):
                            # Procesar sólo si contiene "LLANTA" y no contiene palabras clave de exclusión
                            if "LLANTA" in linea_upper and not any(keyword in linea_upper for keyword in keywords_no_llanta):
                                # MEJORADO: Extracción más precisa de la cantidad en formato de ticket
                                import re
                                
                                # El formato típico en ticket es: cantidad al inicio de línea
                                match_cantidad = re.match(r'^\s*(\d+\.?\d*)\s+', linea)
                                cantidad = 0
                                
                                if match_cantidad:
                                    try:
                                        cantidad = float(match_cantidad.group(1))
                                    except ValueError:
                                        cantidad = 0
                                
                                # Si no encontramos cantidad al inicio, buscamos en el siguiente patrón común
                                if cantidad == 0:
                                    # Buscar patrones como "@ $1,900.00" donde 1,900.00 es el precio unitario
                                    precio_match = re.search(r'@\s*\$\s*([\d,]+\.\d+|\d+,\d+|\d+)', linea)
                                    if precio_match:
                                        precio_unitario_str = precio_match.group(1).replace(',', '')
                                        try:
                                            precio_unitario = float(precio_unitario_str)
                                            
                                            # Buscar el importe total para calcular la cantidad
                                            importe_match = re.search(r'\$\s*([\d,]+\.\d+|\d+,\d+|\d+)(?!\s*@)', linea)
                                            if importe_match:
                                                importe_total_str = importe_match.group(1).replace(',', '')
                                                try:
                                                    importe_total = float(importe_total_str)
                                                    if precio_unitario > 0:
                                                        cantidad = round(importe_total / precio_unitario)
                                                except ValueError:
                                                    pass
                                        except ValueError:
                                            pass
                                
                                # Si todo falla, buscar en las dos líneas anteriores por si la cantidad está separada
                                if cantidad == 0 and i > 0:
                                    for j in range(max(0, i-2), i):
                                        anterior = lineas[j].strip()
                                        if anterior and anterior[0].isdigit():
                                            cantidad_match = re.match(r'^\s*(\d+\.?\d*)\s+', anterior)
                                            if cantidad_match:
                                                try:
                                                    cantidad = float(cantidad_match.group(1))
                                                    break
                                                except ValueError:
                                                    pass
                                
                                # Si aún no tenemos cantidad y estamos en bitácora, buscar en formato diferente
                                if cantidad == 0 and campo == 'bitacora':
                                    # En bitácora a veces aparece como "CANTIDAD: X" o "X unidades"
                                    cantidad_match = re.search(r'(\d+\.?\d*)\s+(?:unidades|pzas|UNIDADES|PZAS)', linea)
                                    if cantidad_match:
                                        try:
                                            cantidad = float(cantidad_match.group(1))
                                        except ValueError:
                                            pass
                                
                                # En el peor caso, si no encontramos cantidad, asumimos 1
                                if cantidad == 0:
                                    cantidad = 1
                                
                                # Extraer precios
                                precios = re.findall(r'\$\s*([\d,]+\.\d+|\d+,\d+|\d+)', linea)
                                precio_unitario = 0.0
                                precio_total = 0.0
                                
                                if precios:
                                    if len(precios) >= 2:  # Tenemos precio unitario y total
                                        try:
                                            precio_unitario = float(precios[-2].replace(',', ''))
                                            precio_total = float(precios[-1].replace(',', ''))
                                            
                                            # Verificar si el total calculado coincide con el reportado
                                            total_calculado = precio_unitario * cantidad
                                        except ValueError:
                                            pass
                                    elif len(precios) == 1:  # Solo tenemos un precio (asumimos que es el total)
                                        try:
                                            precio_total = float(precios[0].replace(',', ''))
                                            if cantidad > 0:
                                                precio_unitario = precio_total / cantidad
                                        except ValueError:
                                            pass
                                
                                # Si no tenemos precio total pero sí unitario y cantidad
                                if precio_total == 0 and precio_unitario > 0:
                                    precio_total = precio_unitario * cantidad
                                
                                # Extraer la descripción (todo después de "LLANTA")
                                inicio_desc = linea.upper().find("LLANTA")
                                descripcion = linea[inicio_desc:].strip()
                                
                                # Limpiar la descripción (quitar precios)
                                descripcion = re.sub(r'\$\s*[\d,]+\.\d+|\$\s*\d+,\d+|\$\s*\d+', '', descripcion)
                                descripcion = re.sub(r'@.*$', '', descripcion)
                                descripcion = descripcion.strip()
                                
                                # Crear diccionario de la llanta
                                llanta_item = {
                                    'descripcion': descripcion,
                                    'cantidad': cantidad,
                                    'precio_unitario': precio_unitario,
                                    'total': precio_total
                                }
                                
                                # Añadir a la lista de llantas
                                todas_llantas.append(llanta_item)
                                
                                llantas_encontradas = True
                                total_llantas_encontradas += 1
                        
                        # Buscar también en formato de bitácora (fuera de la sección de artículos)
                        elif not in_item_section and "LLANTA" in linea_upper:
                            # Verificar que no contenga palabras de exclusión
                            if not any(keyword in linea_upper for keyword in keywords_no_llanta):
                                # En la bitácora a veces aparece con otro formato
                                import re
                                
                                # Buscar cantidad (puede estar junto al código antes de la descripción)
                                cantidad_match = None
                                cantidad = 1  # Valor por defecto
                                
                                # Primero buscamos patrones como "CÓDIGO      X      DESCRIPCIÓN"
                                if re.search(r'^\S+\s+(\d+\.?\d*)\s+LLANTA', linea_upper):
                                    cantidad_match = re.search(r'^\S+\s+(\d+\.?\d*)\s+LLANTA', linea_upper)
                                    if cantidad_match:
                                        try:
                                            cantidad = float(cantidad_match.group(1))
                                        except ValueError:
                                            cantidad = 1
                                
                                # Extraer precios (en bitácora suelen estar al final)
                                precios = re.findall(r'\$\s*([\d,]+\.\d+|\d+,\d+|\d+)', linea)
                                precio_unitario = 0.0
                                precio_total = 0.0
                                
                                if precios:
                                    if len(precios) >= 2:  # Tenemos precio unitario y total
                                        try:
                                            precio_unitario = float(precios[-2].replace(',', ''))
                                            precio_total = float(precios[-1].replace(',', ''))
                                            
                                            # Verificar si el total calculado coincide con el reportado
                                            total_calculado = precio_unitario * cantidad
                                            if abs(total_calculado - precio_total) > 0.01:
                                                # Si hay discrepancia, recalcular la cantidad
                                                if precio_unitario > 0:
                                                    cantidad_calculada = round(precio_total / precio_unitario)
                                                    cantidad = cantidad_calculada
                                        except ValueError:
                                            pass
                                    elif len(precios) == 1:  # Solo tenemos un precio (asumimos que es el total)
                                        try:
                                            precio_total = float(precios[0].replace(',', ''))
                                        except ValueError:
                                            pass
                                
                                # Extraer la descripción (todo después de "LLANTA")
                                inicio_desc = linea.upper().find("LLANTA")
                                descripcion = linea[inicio_desc:].strip()
                                
                                # Limpiar la descripción (quitar precios)
                                descripcion = re.sub(r'\$\s*[\d,]+\.\d+|\$\s*\d+,\d+|\$\s*\d+', '', descripcion)
                                descripcion = descripcion.strip()
                                
                                # Crear diccionario de la llanta
                                llanta_item = {
                                    'descripcion': descripcion,
                                    'cantidad': cantidad,
                                    'precio_unitario': precio_unitario,
                                    'total': precio_total
                                }
                                
                                # Añadir a la lista de llantas
                                todas_llantas.append(llanta_item)
                                
                                llantas_encontradas = True
                                total_llantas_encontradas += 1
            
            if llantas_encontradas:
                ventas_con_llantas += 1
        
        # Si no se encontraron llantas, retornar None
        if len(todas_llantas) == 0:
            return None
        
        # Agrupar llantas por modelo
        llantas_agrupadas = {}
        for llanta in todas_llantas:
            descripcion = llanta['descripcion']
            
            # Inicializar si es primera vez
            if descripcion not in llantas_agrupadas:
                llantas_agrupadas[descripcion] = {
                    'nombre': descripcion,
                    'cantidad': 0,
                    'total': 0,
                    'precio_promedio': 0
                }
            
            # Sumar cantidad y total
            llantas_agrupadas[descripcion]['cantidad'] += llanta['cantidad']
            llantas_agrupadas[descripcion]['total'] += llanta['total']
        
        # Calcular precios promedio
        for modelo, datos in llantas_agrupadas.items():
            if datos['cantidad'] > 0:
                datos['precio_promedio'] = datos['total'] / datos['cantidad']
        
        return llantas_agrupadas
    
    def mostrar_pagina_actual(self):
        """Muestra los datos de la página actual"""
        if self.top_tires_df is None or len(self.top_tires_df) == 0:
            return
            
        # Calcular índices de inicio y fin para la página actual
        start_idx = self.current_page * self.tires_per_page
        end_idx = min(start_idx + self.tires_per_page, self.total_tires)
        
        # Actualizar etiqueta de información de página
        self.page_info_label.setText(f"Mostrando llantas {start_idx+1}-{end_idx} de {self.total_tires}")
        
        # Obtener datos para la página actual
        page_data = self.top_tires_df.iloc[start_idx:end_idx]
        
        # Actualizar gráfico
        self.actualizar_grafico(page_data)
        
        # Actualizar tabla
        self.actualizar_tabla(page_data)
        
        # Actualizar estado de los botones de navegación
        self.update_navigation_buttons()
    
    def actualizar_grafico(self, data):
        """Actualiza el gráfico con los datos de la página actual"""
        # Limpiar el layout del gráfico
        self.clear_layout(self.chart_layout)
        
        try:
            # Crear figura para el gráfico
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
            
            figure = plt.figure(figsize=(10, 6))
            ax = figure.add_subplot(111)
            
            # Crear gráfico de barras
            x = range(len(data))
            bars = ax.bar(x, data['cantidad'], color='skyblue', alpha=0.7)
            
            # Configurar etiquetas
            ax.set_xlabel('Modelo de Llanta')
            ax.set_ylabel('Cantidad Vendida')
            ax.set_title('Top Llantas Más Vendidas')
            ax.set_xticks(x)
            
            # Rotar y ajustar las etiquetas del eje x para legibilidad
            nombres_cortos = [self.acortar_nombre(name) for name in data['nombre']]
            ax.set_xticklabels(nombres_cortos, rotation=45, ha='right')
            
            # Añadir valor numérico sobre cada barra
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            # Ajustar diseño
            plt.tight_layout()
            
            # Crear widget de canvas para mostrar el gráfico en Qt
            canvas = FigureCanvas(figure)
            self.chart_layout.addWidget(canvas)
            
            # Añadir barra de herramientas de navegación para el gráfico
            toolbar = NavigationToolbar(canvas, self)
            self.chart_layout.addWidget(toolbar)
        except Exception as e:
            from PyQt6.QtWidgets import QLabel
            error_label = QLabel(f"Error al generar gráfico: {str(e)}")
            self.chart_layout.addWidget(error_label)
    
    def actualizar_tabla(self, data):
        """Actualiza la tabla con los datos detallados"""
        try:
            from PyQt6.QtCore import Qt
            
            self.table.setRowCount(len(data))
            
            for i, (_, row) in enumerate(data.iterrows()):
                # Nombre de la llanta
                nombre_item = QTableWidgetItem(row['nombre'])
                self.table.setItem(i, 0, nombre_item)
                
                # Cantidad vendida
                cantidad_item = QTableWidgetItem(str(int(row['cantidad'])))
                cantidad_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 1, cantidad_item)
                
                # Ingresos totales
                ingresos_item = QTableWidgetItem(f"${row['total']:.2f}")
                ingresos_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 2, ingresos_item)
                
                # Precio promedio
                precio_item = QTableWidgetItem(f"${row['precio_promedio']:.2f}")
                precio_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 3, precio_item)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Error al actualizar tabla: {str(e)}")
    
    def acortar_nombre(self, nombre, max_length=20):
        """Acorta el nombre para mejor visualización en el gráfico"""
        if len(nombre) > max_length:
            return nombre[:max_length-3] + "..."
        return nombre
    
    def next_page(self):
        """Avanza a la siguiente página"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.mostrar_pagina_actual()
    
    def previous_page(self):
        """Retrocede a la página anterior"""
        if self.current_page > 0:
            self.current_page -= 1
            self.mostrar_pagina_actual()
    
    def update_navigation_buttons(self):
        """Actualiza el estado de los botones de navegación"""
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.total_pages - 1)
    
    def clear_layout(self, layout):
        """Limpia todos los widgets de un layout"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
    
    def clear_analysis(self):
        """Limpia todos los elementos de análisis"""
        self.clear_layout(self.chart_layout)
        self.table.setRowCount(0)
        self.page_info_label.setText("No hay datos disponibles")
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.top_tires_df = None
        self.total_tires = 0
        self.current_page = 0              


class CategoryAnalysisTab(QWidget):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.categorias = {
            'NITROGENO': ['LLENADO DE NITROGENO'],
            'TUERCAS': ['TUERCA CODIGO K', 'TUERCA K'],
            'CENTRADORES': ['CENTRADOR'],
            'BALATAS': ['BALATAS'],
            'RECTIFICACION': ['RECTIFICACION'],
            'DISCOS': ['DISCO', 'DISCOS'],
            'KIT DE SEGURIDAD': ['KIT TUERCAS DE SEGURIDAD', 'KIT BIRLOS DE SEGURIDAD']
        }
        self.productos_por_categoria = {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Gráfico de ventas por categoría
        self.canvas_categorias = MatplotlibCanvas(width=8, height=4)
        layout.addWidget(QLabel("<h3>Ventas por Categoría</h3>"))
        layout.addWidget(self.canvas_categorias)
        
        # Tabla de resumen de categorías
        layout.addWidget(QLabel("<h3>Resumen por Categoría</h3>"))
        self.tabla_categorias = QTableWidget()
        self.tabla_categorias.setColumnCount(3)
        self.tabla_categorias.setHorizontalHeaderLabels(["Categoría", "Cantidad Vendida", "Total Vendido ($)"])
        self.tabla_categorias.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_categorias)
        
        # Tabla de detalle de productos por categoría
        layout.addWidget(QLabel("<h3>Detalle de Productos por Categoría</h3>"))
        self.tabla_detalle = QTableWidget()
        self.tabla_detalle.setColumnCount(5)
        self.tabla_detalle.setHorizontalHeaderLabels(["Categoría", "Código", "Descripción", "Cantidad", "Total ($)"])
        self.tabla_detalle.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_detalle)
        
        self.setLayout(layout)
        
    def actualizar_analisis(self, df):
        self.df = df
        if len(df) > 0:
            # Extraer productos y categorizarlos
            self.extraer_productos_por_categoria()
            
            # Actualizar visualizaciones
            self.actualizar_grafico_categorias()
            self.actualizar_tabla_categorias()
            self.actualizar_tabla_detalle()
            
            # Asegurarnos de que la pestaña se actualice visualmente
            self.update()
    
    def extraer_productos_por_categoria(self):
        # Inicializar diccionario para almacenar productos por categoría
        self.productos_por_categoria = {categoria: [] for categoria in self.categorias.keys()}
        # Ya no incluimos la categoría OTROS
        
        # Lista para almacenar todos los productos
        todos_productos = []
        
        # Extraer productos de cada venta
        for _, venta in self.df.iterrows():
            if isinstance(venta['bitacora'], str) and venta['bitacora'].strip():
                # Primero intentar extraer los productos de la bitácora
                productos = self.extraer_productos_de_bitacora(venta['bitacora'])
                
                # Si es uno de los folios especiales para NITROGENO, tratarlo diferente
                if venta['Folio'] in ['4432', '3098']:
                    productos_nitrogeno = self.extraer_productos_especiales(venta['bitacora'], venta['Folio'])
                    if productos_nitrogeno:
                        # Solo usamos los productos de NITROGENO para estos folios específicos
                        todos_productos.extend(productos_nitrogeno)
                    else:
                        # Si no se encontraron productos específicos, usamos los normales
                        todos_productos.extend(productos)
                else:
                    # Para los demás folios, procesar normalmente
                    todos_productos.extend(productos)
        
        # Categorizar los productos
        for producto in todos_productos:
            categorizado = False
            descripcion = producto['descripcion'].upper() if 'descripcion' in producto else ''
            
            # Verificar categoría para cada producto
            for categoria, palabras_clave in self.categorias.items():
                for palabra_clave in palabras_clave:
                    # Para NITROGENO, excluimos específicamente "RELLENADO"
                    if categoria == "NITROGENO" and "RELLENADO" in descripcion:
                        continue
                    
                    if palabra_clave.upper() in descripcion:
                        self.productos_por_categoria[categoria].append(producto)
                        categorizado = True
                        break
                if categorizado:
                    break
            
            # No hacemos nada con los productos no categorizados
            # (se omiten en lugar de agregarse a "OTROS")
    
    def extraer_productos_especiales(self, bitacora, folio):
        # Especial para folios 4432 y 3098
        productos = []
        
        # Buscar líneas de productos en la bitácora
        lineas = bitacora.split('\n')
        for linea in lineas:
            # Patrón para extraer: código, cantidad, descripción, precio, total
            patron = r'(\d+)\s+(\d+)\s+(.*?)\s+\$(\d+\.\d+)\s+\$(\d+\.\d+)'
            match = re.search(patron, linea)
            if match:
                codigo = match.group(1)
                cantidad = int(match.group(2))
                descripcion = match.group(3).strip()
                precio = float(match.group(4))
                total = float(match.group(5))
                
                # Solo incluir LLENADO DE NITROGENO para estos folios
                # y excluir RELLENADO
                if "LLENADO DE NITROGENO" in descripcion.upper() and "RELLENADO" not in descripcion.upper():
                    productos.append({
                        'codigo': codigo,
                        'descripcion': descripcion,
                        'cantidad': cantidad,
                        'precio': precio,
                        'total': total,
                        'folio': folio
                    })
        
        return productos
        
    def extraer_productos_de_bitacora(self, bitacora):
        productos = []
        
        # Buscar líneas de productos en la bitácora
        lineas = bitacora.split('\n')
        for linea in lineas:
            # Patrón para extraer: código, cantidad, descripción, precio, total
            patron = r'(\d+)\s+(\d+)\s+(.*?)\s+\$(\d+\.\d+)\s+\$(\d+\.\d+)'
            match = re.search(patron, linea)
            if match:
                codigo = match.group(1)
                cantidad = int(match.group(2))
                descripcion = match.group(3).strip()
                precio = float(match.group(4))
                total = float(match.group(5))
                
                productos.append({
                    'codigo': codigo,
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio': precio,
                    'total': total
                })
        
        return productos
    
    def actualizar_grafico_categorias(self):
        # Calcular cantidades por categoría
        cantidades_categoria = {}
        
        for categoria, productos in self.productos_por_categoria.items():
            if not productos:  # Saltear categorías vacías
                continue
                
            cantidad_categoria = sum(p['cantidad'] for p in productos)
            cantidades_categoria[categoria] = cantidad_categoria
        
        # Ordenar categorías por cantidad vendida (de mayor a menor)
        categorias_ordenadas = sorted(
            cantidades_categoria.keys(), 
            key=lambda x: cantidades_categoria[x], 
            reverse=True
        )
        
        # Preparar datos para el gráfico
        categorias = []
        valores_cantidad = []
        
        for cat in categorias_ordenadas:
            categorias.append(cat)
            valores_cantidad.append(cantidades_categoria[cat])
        
        # Graficar
        ax = self.canvas_categorias.axes
        ax.clear()
        
        # Crear gráfico horizontal de barras
        barras = ax.barh(categorias, valores_cantidad, color='lightgreen')
        
        # Añadir valores en las barras
        for barra in barras:
            width = barra.get_width()
            ax.text(width + 0.3, barra.get_y() + barra.get_height()/2, f'{width:,.0f}', 
                    ha='left', va='center')
        
        # Título y etiquetas
        ax.set_title('Ventas por Categoría')
        ax.set_xlabel('Cantidad Vendida')
        
        self.canvas_categorias.fig.tight_layout()
        self.canvas_categorias.draw()
    
    def actualizar_tabla_categorias(self):
        # Preparar datos para la tabla
        datos_tabla = []
        
        for categoria, productos in self.productos_por_categoria.items():
            if not productos:  # Saltear categorías vacías
                continue
                
            total_categoria = sum(p['total'] for p in productos)
            cantidad_categoria = sum(p['cantidad'] for p in productos)
            
            datos_tabla.append({
                'categoria': categoria,
                'cantidad': cantidad_categoria,
                'total': total_categoria
            })
        
        # Ordenar por cantidad vendida (de mayor a menor)
        datos_tabla.sort(key=lambda x: x['cantidad'], reverse=True)
        
        # Actualizar tabla
        self.tabla_categorias.setRowCount(0)
        
        for i, dato in enumerate(datos_tabla):
            self.tabla_categorias.insertRow(i)
            
            # Categoría
            self.tabla_categorias.setItem(i, 0, QTableWidgetItem(dato['categoria']))
            
            # Cantidad (centrado)
            item_cantidad = QTableWidgetItem(f"{dato['cantidad']:,.0f}")
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_categorias.setItem(i, 1, item_cantidad)
            
            # Total (alineado a la derecha)
            item_total = QTableWidgetItem(f"${dato['total']:,.2f}")
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla_categorias.setItem(i, 2, item_total)
    
    def actualizar_tabla_detalle(self):
        # Preparar datos para la tabla detallada
        datos_detalle = []
        
        # Obtener las categorías con productos
        categorias_con_productos = [cat for cat, prods in self.productos_por_categoria.items() if prods]
        
        # Solo procesamos las categorías que tienen productos
        for categoria in categorias_con_productos:
            productos = self.productos_por_categoria[categoria]
                
            # Agrupar productos por código y descripción dentro de cada categoría
            productos_agrupados = {}
            for producto in productos:
                clave = (producto['codigo'], producto['descripcion'])
                if clave not in productos_agrupados:
                    productos_agrupados[clave] = {
                        'codigo': producto['codigo'],
                        'descripcion': producto['descripcion'],
                        'cantidad': 0,
                        'total': 0,
                        'categoria': categoria
                    }
                
                productos_agrupados[clave]['cantidad'] += producto['cantidad']
                productos_agrupados[clave]['total'] += producto['total']
            
            # Añadir a la lista
            for producto in productos_agrupados.values():
                datos_detalle.append(producto)
        
        # Ordenar primero por categoría (de mayor a menor cantidad total) y luego por cantidad vendida
        # Primero calculamos total por categoría para ordenar
        total_por_categoria = {}
        for cat in categorias_con_productos:
            total_por_categoria[cat] = sum(p['cantidad'] for p in self.productos_por_categoria[cat])
        
        # Ahora ordenamos las categorías por cantidad total
        categorias_ordenadas = sorted(total_por_categoria.keys(), key=lambda x: total_por_categoria[x], reverse=True)
        
        # Crear un orden para las categorías
        orden_categorias = {cat: i for i, cat in enumerate(categorias_ordenadas)}
        
        # Ordenar datos usando el orden de categorías y luego por cantidad
        datos_detalle.sort(key=lambda x: (orden_categorias.get(x['categoria'], 999), -x['cantidad']))
        
        # Actualizar tabla
        self.tabla_detalle.setRowCount(0)
        
        for i, dato in enumerate(datos_detalle):
            self.tabla_detalle.insertRow(i)
            
            # Categoría
            self.tabla_detalle.setItem(i, 0, QTableWidgetItem(dato['categoria']))
            
            # Código
            self.tabla_detalle.setItem(i, 1, QTableWidgetItem(dato['codigo']))
            
            # Descripción
            self.tabla_detalle.setItem(i, 2, QTableWidgetItem(dato['descripcion']))
            
            # Cantidad (centrado)
            item_cantidad = QTableWidgetItem(f"{dato['cantidad']:,.0f}")
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_detalle.setItem(i, 3, item_cantidad)
            
            # Total (alineado a la derecha)
            item_total = QTableWidgetItem(f"${dato['total']:,.2f}")
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla_detalle.setItem(i, 4, item_total)
                                               
class DataAnalysisTab(QWidget):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Gráfico de ventas diarias
        self.canvas_ventas_diarias = MatplotlibCanvas(width=8, height=4)
        layout.addWidget(QLabel("<h3>Ventas Diarias</h3>"))
        layout.addWidget(self.canvas_ventas_diarias)
        
        # Tabla de resumen
        layout.addWidget(QLabel("<h3>Resumen de Ventas</h3>"))
        self.tabla_resumen = QTableWidget()
        self.tabla_resumen.setColumnCount(2)
        self.tabla_resumen.setHorizontalHeaderLabels(["Métrica", "Valor"])
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_resumen)
        
        self.setLayout(layout)
        
    def actualizar_analisis(self, df):
        self.df = df
        self.actualizar_grafico_ventas_diarias()
        self.actualizar_tabla_resumen()
        
    def actualizar_grafico_ventas_diarias(self):
        # Agrupar por fecha y contar ventas
        ventas_por_dia = self.df.groupby('fecha').size()
        
        # Graficar
        ax = self.canvas_ventas_diarias.axes
        ax.clear()
        ventas_por_dia.plot(kind='bar', ax=ax, color='skyblue')
        ax.set_title('Número de Ventas por Día')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Número de Ventas')
        ax.tick_params(axis='x', rotation=45)
        self.canvas_ventas_diarias.fig.tight_layout()
        self.canvas_ventas_diarias.draw()
        
    def actualizar_tabla_resumen(self):
        # Calcular métricas
        total_ventas = len(self.df)
        total_ingresos = self.df['total'].sum()
        promedio_venta = self.df['total'].mean() if total_ventas > 0 else 0
        ventas_efectivo = self.df[self.df['comoPago'].str.contains('EFECTIVO', case=False, na=False)]['total'].sum()
        ventas_tarjeta = self.df[self.df['comoPago'].str.contains('TARJETA', case=False, na=False)]['total'].sum()
        
        # Actualizar tabla
        self.tabla_resumen.setRowCount(0)
        metricas = [
            ("Total de Ventas", f"{total_ventas}"),
            ("Total de Ingresos", f"${total_ingresos:,.2f}"),
            ("Promedio por Venta", f"${promedio_venta:,.2f}"),
            ("Ventas en Efectivo", f"${ventas_efectivo:,.2f}"),
            ("Ventas con Tarjeta", f"${ventas_tarjeta:,.2f}")
        ]
        
        for i, (metrica, valor) in enumerate(metricas):
            self.tabla_resumen.insertRow(i)
            self.tabla_resumen.setItem(i, 0, QTableWidgetItem(metrica))
            item_valor = QTableWidgetItem(valor)
            item_valor.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla_resumen.setItem(i, 1, item_valor)

class ProductAnalysisTab(QWidget):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.productos_df = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Gráfico de productos más vendidos
        self.canvas_productos = MatplotlibCanvas(width=8, height=4)
        layout.addWidget(QLabel("<h3>Productos Más Vendidos</h3>"))
        layout.addWidget(self.canvas_productos)
        
        # Tabla de productos
        layout.addWidget(QLabel("<h3>Detalle de Productos</h3>"))
        self.tabla_productos = QTableWidget()
        self.tabla_productos.setColumnCount(4)
        self.tabla_productos.setHorizontalHeaderLabels(["Código", "Descripción", "Cantidad Vendida", "Total Vendido ($)"])
        self.tabla_productos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_productos)
        
        self.setLayout(layout)
        
    def actualizar_analisis(self, df):
        self.df = df
        self.extraer_datos_productos()
        self.actualizar_grafico_productos()
        self.actualizar_tabla_productos()
        
    def extraer_datos_productos(self):
        # Lista para almacenar los datos de productos
        productos_data = []
        
        # Iterar sobre cada venta y extraer productos de la bitácora
        for _, venta in self.df.iterrows():
            if isinstance(venta['bitacora'], str) and venta['bitacora'].strip():
                productos = self.extraer_productos_de_bitacora(venta['bitacora'])
                for producto in productos:
                    productos_data.append(producto)
        
        # Crear DataFrame con los productos extraídos
        if productos_data:
            self.productos_df = pd.DataFrame(productos_data)
            # Agrupar por código y descripción
            self.productos_agrupados = self.productos_df.groupby(['codigo', 'descripcion']).agg({
                'cantidad': 'sum',
                'total': 'sum'
            }).reset_index()
            self.productos_agrupados = self.productos_agrupados.sort_values('cantidad', ascending=False)
        else:
            self.productos_df = pd.DataFrame(columns=['codigo', 'descripcion', 'cantidad', 'precio', 'total'])
            self.productos_agrupados = self.productos_df
    
    def extraer_productos_de_bitacora(self, bitacora):
        productos = []
        
        # Buscar líneas de productos en la bitácora
        lineas = bitacora.split('\n')
        for linea in lineas:
            # Patrón para extraer: código, cantidad, descripción, precio, total
            patron = r'(\d+)\s+(\d+)\s+(.*?)\s+\$(\d+\.\d+)\s+\$(\d+\.\d+)'
            match = re.search(patron, linea)
            if match:
                codigo = match.group(1)
                cantidad = int(match.group(2))
                descripcion = match.group(3).strip()
                precio = float(match.group(4))
                total = float(match.group(5))
                
                productos.append({
                    'codigo': codigo,
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio': precio,
                    'total': total
                })
        
        return productos
    
    def actualizar_grafico_productos(self):
        if self.productos_agrupados is None or len(self.productos_agrupados) == 0:
            return
            
        # Tomar los 10 productos más vendidos
        top_productos = self.productos_agrupados.head(10)
        
        # Graficar
        ax = self.canvas_productos.axes
        ax.clear()
        
        # Crear etiquetas que combinen código y descripción acortada
        etiquetas = [f"{codigo} - {desc[:15]}..." if len(desc) > 15 else f"{codigo} - {desc}" 
                     for codigo, desc in zip(top_productos['codigo'], top_productos['descripcion'])]
        
        # Crear gráfico horizontal
        bars = ax.barh(etiquetas, top_productos['cantidad'], color='lightgreen')
        
        # Añadir valores en las barras
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.3, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                    ha='left', va='center')
        
        ax.set_title('Top 10 Productos Más Vendidos')
        ax.set_xlabel('Cantidad Vendida')
        self.canvas_productos.fig.tight_layout()
        self.canvas_productos.draw()
    
    def actualizar_tabla_productos(self):
        if self.productos_agrupados is None:
            return
            
        self.tabla_productos.setRowCount(0)
        
        for i, (_, producto) in enumerate(self.productos_agrupados.iterrows()):
            self.tabla_productos.insertRow(i)
            self.tabla_productos.setItem(i, 0, QTableWidgetItem(producto['codigo']))
            self.tabla_productos.setItem(i, 1, QTableWidgetItem(producto['descripcion']))
            
            # Cantidad con alineación centrada
            item_cantidad = QTableWidgetItem(f"{producto['cantidad']:,.0f}")
            item_cantidad.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_productos.setItem(i, 2, item_cantidad)
            
            # Total con formato de moneda y alineación derecha
            item_total = QTableWidgetItem(f"${producto['total']:,.2f}")
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla_productos.setItem(i, 3, item_total)

class SeasonalAnalysisTab(QWidget):
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Gráfico de ventas por mes
        self.canvas_estacional = MatplotlibCanvas(width=8, height=5)
        layout.addWidget(QLabel("<h3>Análisis Estacional de Ventas</h3>"))
        layout.addWidget(self.canvas_estacional)
        
        # Tabla de ventas por mes
        layout.addWidget(QLabel("<h3>Ventas por Mes</h3>"))
        self.tabla_estacional = QTableWidget()
        self.tabla_estacional.setColumnCount(3)
        self.tabla_estacional.setHorizontalHeaderLabels(["Mes", "Número de Ventas", "Total Vendido"])
        self.tabla_estacional.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabla_estacional)
        
        self.setLayout(layout)
        
    def actualizar_analisis(self, df):
        # Actualizar el dataframe con los datos filtrados
        self.df = df.copy()  # Hacer una copia para evitar problemas de referencia
        
        # Limpiar SIEMPRE las visualizaciones antes de actualizar con nuevos datos
        self.limpiar_visualizaciones()
        
        # Regenerar análisis sólo si hay datos
        if len(df) > 0:
            self.actualizar_grafico_estacional()
            self.actualizar_tabla_estacional()
    
    def limpiar_visualizaciones(self):
        """Limpia las visualizaciones antes de mostrar nuevos datos"""
        # Limpiar gráfico de manera más exhaustiva
        ax = self.canvas_estacional.axes
        ax.clear()
        
        # Asegurarse de que también se limpia el eje secundario si existe
        for axis in self.canvas_estacional.fig.axes:
            axis.clear()
        
        # Si hay más de un eje (el principal), eliminar los adicionales
        if len(self.canvas_estacional.fig.axes) > 1:
            # No podemos asignar directamente a fig.axes, debemos eliminar los ejes adicionales uno por uno
            # Mantener una referencia al eje principal
            main_ax = self.canvas_estacional.axes
            # Eliminar todos los ejes excepto el principal
            for ax in self.canvas_estacional.fig.axes[:]:
                if ax != main_ax:
                    self.canvas_estacional.fig.delaxes(ax)
        
        self.canvas_estacional.draw()
        
        # Limpiar tabla
        self.tabla_estacional.setRowCount(0)
    
    def actualizar_grafico_estacional(self):
        try:
            # Convertir fecha a datetime si no lo es
            self.df['fecha_dt'] = pd.to_datetime(self.df['fecha'])
            
            # Extraer año y mes
            self.df['año_mes'] = self.df['fecha_dt'].dt.to_period('M')
            
            # Agrupar por año-mes y calcular total
            ventas_por_mes = self.df.groupby('año_mes').agg({
                'total': 'sum',
                'Folio': 'count'
            }).reset_index()
            
            # Si no hay datos después de agrupar, mostrar mensaje vacío
            if len(ventas_por_mes) == 0:
                ax = self.canvas_estacional.axes
                ax.clear()
                ax.set_title('No hay datos para mostrar')
                self.canvas_estacional.draw()
                return
            
            ventas_por_mes['año_mes_str'] = ventas_por_mes['año_mes'].astype(str)
            
            # Graficar
            ax = self.canvas_estacional.axes
            ax.clear()
            
            # Crear gráfico de barras apiladas como en la imagen de referencia
            width = 0.75  # Ancho de las barras
            x = range(len(ventas_por_mes))
            
            # Crear figura con dos ejes Y (asegurando que no haya residuos previos)
            # Primero verificamos si ya existe un eje secundario y lo eliminamos
            if len(self.canvas_estacional.fig.axes) > 1:
                for i in range(1, len(self.canvas_estacional.fig.axes)):
                    self.canvas_estacional.fig.delaxes(self.canvas_estacional.fig.axes[i])
                
            # Ahora creamos un nuevo eje secundario
            ax2 = ax.twinx()
            
            # Definir colores
            color_total = 'tab:blue'
            color_ventas = 'tab:orange'  # Este es el color de los puntos que aparecen como "rojos"
            
            # Graficar barras para el total vendido (con escala ajustada)
            total_vendido = ventas_por_mes['total'] / 1000  # Convertir a miles para mejor visualización
            ax.bar(x, total_vendido, width, color=color_total, label='Total Vendido (miles $)')
            
            # Graficar línea para número de ventas
            num_ventas = ventas_por_mes['Folio']
            ax2.plot(x, num_ventas, 'o-', color=color_ventas, linewidth=2, markersize=8, label='Cantidad de Ventas')
            
            # Configurar ejes
            ax.set_xlabel('Mes')
            ax.set_ylabel('Total Vendido (miles $)', color=color_total)
            ax.tick_params(axis='y', labelcolor=color_total)
            
            ax2.set_ylabel('Número de Ventas', color=color_ventas)
            ax2.tick_params(axis='y', labelcolor=color_ventas)
            
            # Configurar etiquetas del eje X
            ax.set_xticks(x)
            ax.set_xticklabels(ventas_por_mes['año_mes_str'], rotation=45)
            
            # Ajustar escala del eje Y para total vendido
            if total_vendido.max() > 0:  # Evitar errores si no hay datos
                max_total = total_vendido.max()
                y_ticks = np.arange(0, max_total + 200, 100)  # De 0 a max+200, de 100 en 100
                ax.set_yticks(y_ticks)
            
            # Añadir valores encima de cada barra
            for i, (total, ventas) in enumerate(zip(total_vendido, num_ventas)):
                # Total vendido en la barra
                ax.text(i, total + (total * 0.03), f'${ventas_por_mes["total"].iloc[i]:,.0f}', 
                        ha='center', va='bottom', fontsize=9, color=color_total, weight='bold')
                
                # Número de ventas en el punto
                ax2.text(i, ventas + (ventas * 0.03), f'{ventas:,.0f}', 
                        ha='center', va='bottom', fontsize=9, color=color_ventas, weight='bold')
            
            # Añadir leyenda combinada
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)
            
            # Título
            ax.set_title('Ventas Mensuales: Total y Cantidad')
            
            # Establecer grid para mejor lectura
            ax.grid(True, linestyle='--', alpha=0.7)
            
            self.canvas_estacional.fig.tight_layout()
            self.canvas_estacional.draw()
        except Exception as e:
            # En caso de error, mostrar un mensaje y registrar la excepción
            print(f"Error al actualizar gráfico estacional: {str(e)}")
            ax = self.canvas_estacional.axes
            ax.clear()
            ax.set_title('Error al generar el gráfico')
            self.canvas_estacional.draw()
    
    def actualizar_tabla_estacional(self):
        try:
            # Limpiar tabla antes de actualizar
            self.tabla_estacional.setRowCount(0)
            
            # Verificar si hay datos
            if len(self.df) == 0:
                return
                
            # Asegurarse de que tenemos la columna año_mes
            if 'año_mes' not in self.df.columns:
                self.df['fecha_dt'] = pd.to_datetime(self.df['fecha'])
                self.df['año_mes'] = self.df['fecha_dt'].dt.to_period('M')
            
            # Agrupar por año-mes
            ventas_por_mes = self.df.groupby('año_mes').agg({
                'total': 'sum',
                'Folio': 'count'
            }).reset_index()
            
            # Verificar si hay datos después de agrupar
            if len(ventas_por_mes) == 0:
                return
            
            # Ordenar por año-mes
            ventas_por_mes = ventas_por_mes.sort_values('año_mes', ascending=False)
            
            # Formatear año-mes para mostrar
            ventas_por_mes['año_mes_str'] = ventas_por_mes['año_mes'].astype(str)
            
            # Actualizar tabla
            for i, row in ventas_por_mes.iterrows():
                row_position = self.tabla_estacional.rowCount()
                self.tabla_estacional.insertRow(row_position)
                
                # Mes
                self.tabla_estacional.setItem(row_position, 0, QTableWidgetItem(row['año_mes_str']))
                
                # Número de ventas (centrado)
                item_num = QTableWidgetItem(f"{row['Folio']:,.0f}")
                item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_estacional.setItem(row_position, 1, item_num)
                
                # Total vendido (alineado a la derecha)
                item_total = QTableWidgetItem(f"${row['total']:,.2f}")
                item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla_estacional.setItem(row_position, 2, item_total)
        except Exception as e:
            print(f"Error al actualizar tabla estacional: {str(e)}")

class DataScience(QWidget):
    def __init__(self):
        super().__init__()
        self.ventas_data = {}
        self.df = None
        self.periodo_actual = "semana_actual"  # Valor predeterminado
        self.modo_filtro = "predefinido"  # Modo de filtro predeterminado: "predefinido" o "personalizado"
        self.init_ui()
        self.cargar_datos()
        
    def init_ui(self):
            # Configurar la ventana principal
            self.setWindowTitle("Análisis de Datos de Ventas")
            screen_size = QApplication.primaryScreen().size()
            self.resize(int(screen_size.width() * 0.8), int(screen_size.height() * 0.8))
            
            # Layout principal
            main_layout = QVBoxLayout()
            
            # Panel superior para filtros
            filter_frame = QFrame()
            filter_frame.setFrameShape(QFrame.Shape.StyledPanel)
            filter_layout = QVBoxLayout(filter_frame)
            
            # Primera fila para selección de modo de filtro
            modo_filtro_layout = QHBoxLayout()
            
            # Checkbox para alternar entre filtro predefinido y personalizado
            self.use_custom_dates_checkbox = QCheckBox("Usar rango de fechas personalizado")
            self.use_custom_dates_checkbox.stateChanged.connect(self.toggle_filter_mode)
            modo_filtro_layout.addWidget(self.use_custom_dates_checkbox)
            modo_filtro_layout.addStretch()
            
            filter_layout.addLayout(modo_filtro_layout)
            
            # Segunda fila para filtros predefinidos
            self.filtro_predefinido_frame = QFrame()
            filtro_predefinido_layout = QHBoxLayout(self.filtro_predefinido_frame)
            
            # Selector de período predefinido
            periodo_label = QLabel("Período:")
            self.periodo_combo = QComboBox()
            self.periodo_combo.addItems([
                "Semana actual",  # Nueva opción para la semana actual
                "Último mes",     # Nueva opción para los últimos 30 días
                "Últimos 6 meses", 
                "Último año", 
                "Últimos 3 años", 
                "Últimos 5 años", 
                "Todo el histórico"
            ])
            self.periodo_combo.currentIndexChanged.connect(self.cambiar_periodo)
            
            # Añadir widgets al layout de filtros predefinidos
            filtro_predefinido_layout.addWidget(periodo_label)
            filtro_predefinido_layout.addWidget(self.periodo_combo)
            filtro_predefinido_layout.addStretch()
            filter_layout.addWidget(self.filtro_predefinido_frame)
            
            # Tercera fila para filtros personalizados (inicialmente oculta)
            self.filtro_personalizado_frame = QFrame()
            filtro_personalizado_layout = QHBoxLayout(self.filtro_personalizado_frame)
            
            # Selectores de fecha personalizada
            fecha_inicio_label = QLabel("Fecha Inicio:")
            self.fecha_inicio_picker = QDateEdit()
            self.fecha_inicio_picker.setCalendarPopup(True)
            self.fecha_inicio_picker.setDate(QDate.currentDate().addMonths(-6))  # Por defecto 6 meses atrás
            
            fecha_fin_label = QLabel("Fecha Fin:")
            self.fecha_fin_picker = QDateEdit()
            self.fecha_fin_picker.setCalendarPopup(True)
            self.fecha_fin_picker.setDate(QDate.currentDate())  # Fecha actual por defecto
            
            # Botón para aplicar filtro personalizado
            self.aplicar_fechas_btn = QPushButton("Aplicar Fechas")
            self.aplicar_fechas_btn.clicked.connect(self.aplicar_filtro_personalizado)
            
            # Añadir widgets al layout de filtros personalizados
            filtro_personalizado_layout.addWidget(fecha_inicio_label)
            filtro_personalizado_layout.addWidget(self.fecha_inicio_picker)
            filtro_personalizado_layout.addWidget(fecha_fin_label)
            filtro_personalizado_layout.addWidget(self.fecha_fin_picker)
            filtro_personalizado_layout.addWidget(self.aplicar_fechas_btn)
            filtro_personalizado_layout.addStretch()
            
            # Inicialmente ocultar el filtro personalizado
            self.filtro_personalizado_frame.setVisible(False)
            filter_layout.addWidget(self.filtro_personalizado_frame)
            
            # Cuarta fila para botón de actualización general
            botones_layout = QHBoxLayout()
            
            # Botón de actualización
            refresh_button = QPushButton("Actualizar Datos")
            refresh_button.clicked.connect(self.cargar_datos)
            
            botones_layout.addStretch()
            botones_layout.addWidget(refresh_button)
            
            filter_layout.addLayout(botones_layout)
            
            # Pestañas para diferentes análisis
            self.tabs = QTabWidget()
            
            # Agregar las pestañas
            self.tab_general = DataAnalysisTab(pd.DataFrame())
            self.tab_productos = ProductAnalysisTab(pd.DataFrame())
            self.tab_estacional = SeasonalAnalysisTab(pd.DataFrame())
            self.tab_categorias = CategoryAnalysisTab(pd.DataFrame())
            self.tab_llantas = TireAnalysisTab(pd.DataFrame())
            
            self.tabs.addTab(self.tab_general, "Análisis General")
            self.tabs.addTab(self.tab_productos, "Análisis de Productos")
            self.tabs.addTab(self.tab_estacional, "Análisis Estacional")
            self.tabs.addTab(self.tab_categorias, "Análisis por Categoría")
            self.tabs.addTab(self.tab_llantas, "Análisis de Llantas")
            
            # Añadir elementos al layout principal
            main_layout.addWidget(filter_frame)
            main_layout.addWidget(self.tabs)
            
            self.setLayout(main_layout)
    
    def toggle_filter_mode(self):
        if self.use_custom_dates_checkbox.isChecked():
            self.modo_filtro = "personalizado"
            self.filtro_predefinido_frame.setVisible(False)
            self.filtro_personalizado_frame.setVisible(True)
        else:
            self.modo_filtro = "predefinido"
            self.filtro_predefinido_frame.setVisible(True)
            self.filtro_personalizado_frame.setVisible(False)
            # Aplicar el filtro predefinido seleccionado actualmente
            if hasattr(self, 'df_completo'):
                self.aplicar_filtro_periodo()
    
    def cargar_datos(self):
        try:
            # Mostrar mensaje de carga
            QMessageBox.information(self, "Cargando", "Cargando datos de ventas. Esto puede tardar un momento.")
            
            # Cargar datos desde la base de datos
            self.ventas_data = get_ventas_data()
            
            if not self.ventas_data:
                QMessageBox.warning(self, "Error", "No se pudieron cargar los datos de ventas.")
                return
            
            # Convertir a DataFrame
            datos = []
            for folio, venta in self.ventas_data.items():
                venta['Folio'] = folio
                datos.append(venta)
            
            self.df_completo = pd.DataFrame(datos)
            
            # Aplicar filtro según el modo actual
            if self.modo_filtro == "predefinido":
                self.aplicar_filtro_periodo()
            else:
                self.aplicar_filtro_personalizado()
            
            QMessageBox.information(self, "Éxito", f"Datos cargados exitosamente. {len(self.df_completo)} registros encontrados.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar los datos: {str(e)}")
    
    def cambiar_periodo(self):
        # Mapear el índice del combo a un valor interno
        periodos = {
            0: "semana_actual",  # Nueva opción
            1: "ultimo_mes",     # Nueva opción para los últimos 30 días
            2: "6_meses",
            3: "1_año",
            4: "3_años",
            5: "5_años",
            6: "todo"
        }
        self.periodo_actual = periodos[self.periodo_combo.currentIndex()]
        
        # Aplicar el filtro si ya hay datos cargados
        if hasattr(self, 'df_completo'):
            self.aplicar_filtro_periodo()
    
    def aplicar_filtro_periodo(self):
        if self.df_completo is None or len(self.df_completo) == 0:
            return
        
        # Convertir las fechas a datetime
        self.df_completo['fecha'] = pd.to_datetime(self.df_completo['fecha'], errors='coerce')
        
        # Fecha de referencia (hoy)
        fecha_hoy = datetime.now()
        
        # Aplicar filtro según el período seleccionado
        if self.periodo_actual == "semana_actual":
            # Calcular el inicio de la semana actual (lunes)
            # El método weekday() devuelve 0 para lunes, 1 para martes, etc.
            dias_desde_lunes = fecha_hoy.weekday()
            fecha_inicio = fecha_hoy - timedelta(days=dias_desde_lunes)
            # Establecer a las 00:00:00 del lunes
            fecha_inicio = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0, 0, 0)
            
            # Calcular el fin de la semana actual (domingo)
            dias_hasta_domingo = 6 - dias_desde_lunes
            fecha_fin = fecha_hoy + timedelta(days=dias_hasta_domingo)
            # Establecer a las 23:59:59 del domingo
            fecha_fin = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)
            
            # Filtrar dataframe por la semana actual
            self.df = self.df_completo[
                (self.df_completo['fecha'] >= pd.Timestamp(fecha_inicio)) & 
                (self.df_completo['fecha'] <= pd.Timestamp(fecha_fin))
            ].copy()
            
            # Mostrar mensaje informativo con el rango de fechas
            QMessageBox.information(
                self, 
                "Filtro de Semana Actual", 
                f"Mostrando datos desde el lunes {fecha_inicio.strftime('%d/%m/%Y')} "
                f"hasta el domingo {fecha_fin.strftime('%d/%m/%Y')}"
            )
            
        elif self.periodo_actual == "ultimo_mes":
            # Calcular la fecha de inicio (30 días atrás desde hoy)
            fecha_inicio = fecha_hoy - timedelta(days=30)
            # Establecer a las 00:00:00 de esa fecha
            fecha_inicio = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day, 0, 0, 0)
            
            # La fecha fin es hoy a las 23:59:59
            fecha_fin = datetime(fecha_hoy.year, fecha_hoy.month, fecha_hoy.day, 23, 59, 59)
            
            # Filtrar dataframe por los últimos 30 días
            self.df = self.df_completo[
                (self.df_completo['fecha'] >= pd.Timestamp(fecha_inicio)) & 
                (self.df_completo['fecha'] <= pd.Timestamp(fecha_fin))
            ].copy()
            
            # Mostrar mensaje informativo con el rango de fechas
            QMessageBox.information(
                self, 
                "Filtro de Último Mes", 
                f"Mostrando datos de los últimos 30 días, desde {fecha_inicio.strftime('%d/%m/%Y')} "
                f"hasta {fecha_fin.strftime('%d/%m/%Y')}"
            )
            
        elif self.periodo_actual == "6_meses":
            fecha_inicio = fecha_hoy - timedelta(days=180)
            self.df = self.df_completo[self.df_completo['fecha'] >= fecha_inicio].copy()
        elif self.periodo_actual == "1_año":
            fecha_inicio = fecha_hoy - timedelta(days=365)
            self.df = self.df_completo[self.df_completo['fecha'] >= fecha_inicio].copy()
        elif self.periodo_actual == "3_años":
            fecha_inicio = fecha_hoy - timedelta(days=365*3)
            self.df = self.df_completo[self.df_completo['fecha'] >= fecha_inicio].copy()
        elif self.periodo_actual == "5_años":
            fecha_inicio = fecha_hoy - timedelta(days=365*5)
            self.df = self.df_completo[self.df_completo['fecha'] >= fecha_inicio].copy()
        else:  # "todo"
            self.df = self.df_completo.copy()
        
        # Actualizar las pestañas con los nuevos datos
        self.actualizar_pestanas()
        
    def aplicar_filtro_personalizado(self):
        if self.df_completo is None or len(self.df_completo) == 0:
            return
        
        # Convertir las fechas a datetime
        self.df_completo['fecha'] = pd.to_datetime(self.df_completo['fecha'], errors='coerce')
        
        # Obtener fechas seleccionadas
        fecha_inicio = self.fecha_inicio_picker.date().toPyDate()
        fecha_fin = self.fecha_fin_picker.date().toPyDate()
        
        # Ajustar fecha_fin para incluir todo el día
        fecha_fin = datetime.combine(fecha_fin, datetime.max.time())
        
        # Filtrar dataframe
        self.df = self.df_completo[
            (self.df_completo['fecha'] >= pd.Timestamp(fecha_inicio)) & 
            (self.df_completo['fecha'] <= pd.Timestamp(fecha_fin))
        ].copy()
        
        # Actualizar las pestañas con los nuevos datos
        self.actualizar_pestanas()
    
    def actualizar_pestanas(self):
        # Actualizar cada pestaña con los datos filtrados
        self.tab_general.actualizar_analisis(self.df)
        self.tab_productos.actualizar_analisis(self.df)
        self.tab_estacional.actualizar_analisis(self.df)
        self.tab_categorias.actualizar_analisis(self.df)
        self.tab_llantas.actualizar_analisis(self.df)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DataScience()
    window.show()
    sys.exit(app.exec())