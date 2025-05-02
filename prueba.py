import logging
import json
from database import get_ventas_data

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    # Obtener los datos de ventas
    logging.info("Obteniendo datos de ventas...")
    ventas_data = get_ventas_data()
    
    # Verificar si se obtuvieron datos
    if not ventas_data:
        logging.error("No se obtuvieron datos de ventas")
        return
    
    # Mostrar la cantidad total de registros
    total_ventas = len(ventas_data)
    logging.info(f"Total de registros de ventas: {total_ventas}")
    
    # Obtener los primeros 5 registros
    primeras_ventas = dict(list(ventas_data.items())[:20])
    
    # Mostrar los datos en crudo de las primeras 5 ventas
    logging.info("PRIMERAS 5 VENTAS (DATOS EN CRUDO):")
    for folio, datos in primeras_ventas.items():
        print(f"\n{'=' * 50}")
        print(f"FOLIO: {folio}")
        print(f"{'=' * 50}")
        for campo, valor in datos.items():
            print(f"{campo}: {valor}")
    
    # También mostrar en formato JSON para una visualización alternativa
    print(f"\n{'=' * 50}")
    print("FORMATO JSON:")
    print(f"{'=' * 50}")
    print(json.dumps(primeras_ventas, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()