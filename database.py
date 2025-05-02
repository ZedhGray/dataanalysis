import logging
import pyodbc
from datetime import datetime, date, time
from config import (
    SQL_SERVER_GARCIA, 
    DATABASE, USERNAME, PASSWORD
)

def get_db_connection(server, database, username, password):
    """Establish a database connection."""
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password}'
        )
        return pyodbc.connect(conn_str)
    except pyodbc.Error as e:
        logging.error(f"Database connection error: {e}")
        return None


def get_ventas_data():
    conn = get_db_connection(SQL_SERVER_GARCIA, DATABASE, USERNAME, PASSWORD)
    if not conn:
        logging.error("No se pudo establecer conexión con la base de datos")
        return {}
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                Folio,
                ISNULL(Estado, '') as Estado,
                ISNULL(CveCte, '') as CveCte,
                ISNULL(Cliente, '') as Cliente,
                ISNULL(Fecha, '') as Fecha,
                ISNULL(Hora, '') as Hora,
                ISNULL(Total, 0) as Total,
                ISNULL(Restante, 0) as Restante,
                ISNULL(FechaPago, '') as FechaPago,
                ISNULL(Paga, 0) as Paga,
                ISNULL(Cambio, '') as Cambio,
                ISNULL(Ticket, '') as Ticket,
                ISNULL(Condiciones, '') as Condiciones,
                ISNULL(FechaProg, '') as FechaProg,
                ISNULL(Corte, 0) as Corte,
                ISNULL(Vendedor, '') as Vendedor,
                ISNULL(ComoPago, '') as ComoPago,
                ISNULL(DiasCred, 0) as DiasCred,
                ISNULL(IntCred, '') as IntCred,
                ISNULL(Articulos, '') as Articulos,
                ISNULL(BarCuenta, '') as BarCuenta,
                ISNULL(BarMesero, '') as BarMesero,
                ISNULL(NotasAdicionales, '') as NotasAdicionales,
                ISNULL(IdBarCuenta, '') as IdBarCuenta,
                ISNULL(Bitacora, '') as Bitacora,
                ISNULL(Anticipo, 0) as Anticipo,
                ISNULL(FolioPago, '') as FolioPago,
                ISNULL(SaldoCliente, 0) as SaldoCliente,
                ISNULL(Caja, 0) as Caja
            FROM Ventas
            WHERE Estado != 'CANCELADA'
            AND Estado IS NOT NULL
        """
        
        logging.info(f"Ejecutando consulta SQL para Ventas: {query}")
        cursor.execute(query)
        results = cursor.fetchall()
        
        logging.info(f"Registros de Ventas encontrados: {len(results)}")
        
        def format_date(date_value):
            if date_value:
                if isinstance(date_value, (datetime, date)):
                    return date_value.strftime('%Y-%m-%d')
                try:
                    return datetime.strptime(str(date_value), '%Y-%m-%d').strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    logging.warning(f"Valor de fecha no válido: {date_value}")
                    return ""
            return ""

        def format_time(time_value):
            if time_value:
                if isinstance(time_value, time):
                    return time_value.strftime('%H:%M:%S')
                try:
                    if isinstance(time_value, str):
                        return time_value
                    return datetime.strptime(str(time_value), '%H:%M:%S').strftime('%H:%M:%S')
                except (ValueError, TypeError):
                    logging.warning(f"Valor de hora no válido: {time_value}")
                    return ""
            return ""
        
        ventas_data = {
            str(row.Folio): {
                "estado": row.Estado.strip() if row.Estado else "",
                "cveCte": row.CveCte.strip() if row.CveCte else "",
                "cliente": row.Cliente.strip() if row.Cliente else "",
                "fecha": format_date(row.Fecha),
                "hora": format_time(row.Hora),
                "total": float(row.Total) if row.Total else 0.0,
                "restante": float(row.Restante) if row.Restante else 0.0,
                "fechaPago": format_date(row.FechaPago),
                "paga": float(row.Paga) if row.Paga else 0.0,
                "cambio": row.Cambio.strip() if row.Cambio else "",
                "ticket": row.Ticket.strip() if row.Ticket else "",
                "condiciones": row.Condiciones.strip() if row.Condiciones else "",
                "fechaProg": format_date(row.FechaProg),
                "corte": int(row.Corte) if row.Corte else 0,
                "vendedor": row.Vendedor.strip() if row.Vendedor else "",
                "comoPago": row.ComoPago.strip() if row.ComoPago else "",
                "diasCorte": int(row.DiasCred) if row.DiasCred else 0,
                "intCred": row.IntCred.strip() if row.IntCred else "",
                "articulos": row.Articulos.strip() if row.Articulos else "",
                "barCuenta": row.BarCuenta.strip() if row.BarCuenta else "",
                "barMesero": row.BarMesero.strip() if row.BarMesero else "",
                "notasAdicionales": row.NotasAdicionales.strip() if row.NotasAdicionales else "",
                "idBarCuenta": row.IdBarCuenta.strip() if row.IdBarCuenta else "",
                "bitacora": row.Bitacora.strip() if row.Bitacora else "",
                "anticipo": float(row.Anticipo) if row.Anticipo else 0.0,
                "folioPago": row.FolioPago.strip() if row.FolioPago else "",
                "saldoCliente": float(row.SaldoCliente) if row.SaldoCliente else 0.0,
                "caja": int(row.Caja) if row.Caja else 0
            } for row in results
        }
        
        logging.info(f"Datos de Ventas procesados exitosamente. Total de registros: {len(ventas_data)}")
        return ventas_data
        
    except pyodbc.Error as e:
        logging.error(f"Error al obtener datos de Ventas: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error inesperado al procesar datos de Ventas: {e}")
        return {}
    finally:
        logging.info("Cerrando conexión a la base de datos")
        conn.close()
