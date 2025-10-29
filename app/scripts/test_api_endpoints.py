#!/usr/bin/env python3
"""
Script para testear todos los endpoints de la API y verificar que devuelvan 
los datos esperados con la nueva estructura (sin duplicados)
"""
import os
import sys
import requests
import json
from typing import Dict, Any, List, Optional
from colorama import init, Fore, Style

# Inicializar colorama para colores en Windows
init()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuración
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_ACCOUNT_ID = None
TEST_BATCH_ID = None
TEST_JOB_ID = None

# Contadores de resultados
tests_passed = 0
tests_failed = 0
tests_skipped = 0

def print_header(text: str):
    """Imprime un encabezado decorado"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    print("=" * 80)

def print_test(test_name: str):
    """Imprime el nombre del test"""
    print(f"\n{Fore.YELLOW}🧪 Test: {test_name}{Style.RESET_ALL}")

def print_success(message: str):
    """Imprime mensaje de éxito"""
    global tests_passed
    tests_passed += 1
    print(f"{Fore.GREEN}✅ PASS: {message}{Style.RESET_ALL}")

def print_failure(message: str):
    """Imprime mensaje de fallo"""
    global tests_failed
    tests_failed += 1
    print(f"{Fore.RED}❌ FAIL: {message}{Style.RESET_ALL}")

def print_skip(message: str):
    """Imprime mensaje de skip"""
    global tests_skipped
    tests_skipped += 1
    print(f"{Fore.YELLOW}⏭️  SKIP: {message}{Style.RESET_ALL}")

def print_info(message: str):
    """Imprime información"""
    print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")

def print_warning(message: str):
    """Imprime advertencia"""
    print(f"{Fore.MAGENTA}⚠️  WARNING: {message}{Style.RESET_ALL}")

def check_field_exists(data: Dict, field_path: str, field_name: str) -> bool:
    """
    Verifica que un campo exista en la respuesta.
    field_path puede ser 'root.field' o 'root.nested.field'
    """
    parts = field_path.split('.')
    current = data
    
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                print_failure(f"Campo '{field_path}' no encontrado en respuesta")
                return False
            current = current[part]
        else:
            print_failure(f"No se puede navegar a '{field_path}', tipo incorrecto")
            return False
    
    return True

def check_no_field_exists(data: Dict, field_path: str) -> bool:
    """
    Verifica que un campo NO exista (para confirmar eliminación de duplicados)
    """
    parts = field_path.split('.')
    current = data
    
    for i, part in enumerate(parts):
        if isinstance(current, dict):
            if part not in current:
                return True  # No existe, eso es bueno
            current = current[part]
            if i == len(parts) - 1:
                print_warning(f"Campo '{field_path}' todavía existe (debería estar eliminado)")
                return False
        else:
            return True
    
    return False

def test_health():
    """Test: Health check endpoint"""
    print_test("GET /health")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in ["ok", "healthy"]:
                print_success(f"Health check OK (status: {status})")
                return True
            else:
                print_failure(f"Status inesperado: {status}")
                return False
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_failure("No se pudo conectar a la API. ¿Está corriendo?")
        print_info(f"Intentando conectar a: {API_BASE_URL}")
        print_info("Ejecuta: python app/run_api.py")
        return False
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_accounts():
    """Test: Listar todas las cuentas"""
    print_test("GET /api/v1/accounts")
    global TEST_ACCOUNT_ID
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/accounts")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print_success(f"Se encontraron {len(data)} cuentas")
                TEST_ACCOUNT_ID = str(data[0].get("_id"))
                print_info(f"Usando account_id: {TEST_ACCOUNT_ID}")
                return True
            else:
                print_warning("No hay cuentas en el sistema")
                return True
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_batches():
    """Test: Listar todos los batches"""
    print_test("GET /api/v1/batches")
    global TEST_BATCH_ID
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/batches")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print_success(f"Se encontraron {len(data)} batches")
                TEST_BATCH_ID = str(data[0].get("_id"))
                print_info(f"Usando batch_id: {TEST_BATCH_ID}")
                return True
            else:
                print_warning("No hay batches en el sistema")
                return True
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_jobs():
    """Test: Listar todos los jobs"""
    print_test("GET /api/v1/jobs")
    global TEST_JOB_ID
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/jobs?limit=10")
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print_success(f"Se encontraron {len(data)} jobs")
                
                # Verificar estructura del primer job
                first_job = data[0]
                TEST_JOB_ID = str(first_job.get("_id"))
                print_info(f"Usando job_id: {TEST_JOB_ID}")
                
                # Verificar campos esperados
                expected_fields = [
                    "_id", "status", "batch_id", "account_id", 
                    "contact", "payload", "to_number"
                ]
                
                all_present = True
                for field in expected_fields:
                    if field not in first_job:
                        print_warning(f"Campo esperado '{field}' no encontrado")
                        all_present = False
                
                if all_present:
                    print_success("Todos los campos esperados presentes")
                
                # Verificar estructura anidada
                if "contact" in first_job and isinstance(first_job["contact"], dict):
                    contact = first_job["contact"]
                    if "name" in contact or "dni" in contact or "phones" in contact:
                        print_success("Estructura 'contact' correcta")
                    else:
                        print_warning("Estructura 'contact' vacía o incompleta")
                
                if "payload" in first_job and isinstance(first_job["payload"], dict):
                    payload = first_job["payload"]
                    if "debt_amount" in payload or "company_name" in payload:
                        print_success("Estructura 'payload' correcta")
                    else:
                        print_warning("Estructura 'payload' vacía o incompleta")
                
                # Verificar que NO existan campos duplicados en root
                # Estos campos NO deberían estar en el root level
                duplicate_fields_to_check = ["nombre", "rut", "monto_total", "deuda", "fecha_limite", "origen_empresa"]
                duplicates_found = []
                
                for field in duplicate_fields_to_check:
                    if field in first_job:
                        duplicates_found.append(field)
                
                if duplicates_found:
                    print_warning(f"⚠️  DUPLICADOS ENCONTRADOS en root: {duplicates_found}")
                    print_info("Estos campos deberían estar SOLO en contact/payload, no en root")
                else:
                    print_success("✅ NO hay duplicados en root level (correcto)")
                
                return True
            else:
                print_warning("No hay jobs en el sistema")
                return True
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_job_by_id():
    """Test: Obtener un job específico por ID"""
    if not TEST_JOB_ID:
        print_skip("No hay job_id disponible para testear")
        return True
    
    print_test(f"GET /api/v1/jobs/{TEST_JOB_ID}")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/jobs/{TEST_JOB_ID}")
        
        if response.status_code == 200:
            job = response.json()
            
            print_success("Job obtenido correctamente")
            
            # Verificar campos críticos
            critical_fields = {
                "_id": "ID del job",
                "status": "Estado del job",
                "contact": "Información de contacto",
                "payload": "Información de payload",
                "to_number": "Teléfono de destino"
            }
            
            all_present = True
            for field, description in critical_fields.items():
                if field in job:
                    print_success(f"Campo '{field}' presente ({description})")
                else:
                    print_failure(f"Campo '{field}' faltante ({description})")
                    all_present = False
            
            # Verificar campos en contact
            if "contact" in job and isinstance(job["contact"], dict):
                contact = job["contact"]
                contact_fields = ["name", "dni", "phones"]
                for field in contact_fields:
                    if field in contact:
                        print_success(f"  contact.{field} presente")
                    else:
                        print_warning(f"  contact.{field} faltante")
            
            # Verificar campos en payload
            if "payload" in job and isinstance(job["payload"], dict):
                payload = job["payload"]
                payload_fields = ["debt_amount", "company_name", "use_case"]
                for field in payload_fields:
                    if field in payload:
                        print_success(f"  payload.{field} presente")
                    else:
                        print_warning(f"  payload.{field} faltante")
            
            # Verificar campos que NO deberían existir (duplicados)
            should_not_exist = ["nombre", "rut", "monto_total", "deuda", "origen_empresa"]
            duplicates = [f for f in should_not_exist if f in job]
            
            if duplicates:
                print_warning(f"⚠️  Campos duplicados encontrados: {duplicates}")
            else:
                print_success("✅ Sin campos duplicados en root")
            
            # Verificar campos agregados recientemente
            if "fecha_pago_cliente" in job:
                print_success("Campo 'fecha_pago_cliente' presente")
            else:
                print_info("Campo 'fecha_pago_cliente' no presente (OK si no hay pago)")
            
            if "monto_pago_cliente" in job:
                print_success("Campo 'monto_pago_cliente' presente")
            else:
                print_info("Campo 'monto_pago_cliente' no presente (OK si no hay pago)")
            
            return all_present
        elif response.status_code == 404:
            print_failure(f"Job {TEST_JOB_ID} no encontrado")
            return False
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_batch_jobs():
    """Test: Obtener jobs de un batch específico"""
    if not TEST_BATCH_ID:
        print_skip("No hay batch_id disponible para testear")
        return True
    
    print_test(f"GET /api/v1/batches/{TEST_BATCH_ID}/jobs")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}/jobs")
        
        if response.status_code == 200:
            data = response.json()
            
            if "jobs" in data and isinstance(data["jobs"], list):
                jobs = data["jobs"]
                print_success(f"Batch tiene {len(jobs)} jobs")
                
                if len(jobs) > 0:
                    # Verificar estructura del primer job
                    first_job = jobs[0]
                    
                    # Verificar campos esperados
                    has_contact = "contact" in first_job
                    has_payload = "payload" in first_job
                    has_to_number = "to_number" in first_job
                    
                    if has_contact and has_payload and has_to_number:
                        print_success("Estructura de jobs correcta (contact, payload, to_number)")
                    else:
                        print_warning("Estructura de jobs incompleta")
                    
                    # Verificar duplicados
                    duplicates = [f for f in ["nombre", "rut", "monto_total"] if f in first_job]
                    if duplicates:
                        print_warning(f"Duplicados encontrados: {duplicates}")
                    else:
                        print_success("Sin duplicados en jobs del batch")
                
                return True
            else:
                print_failure("Formato de respuesta incorrecto")
                return False
        elif response.status_code == 404:
            print_failure(f"Batch {TEST_BATCH_ID} no encontrado")
            return False
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_dashboard_stats():
    """Test: Estadísticas del dashboard"""
    print_test("GET /api/v1/dashboard/stats")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/dashboard/stats")
        
        if response.status_code == 200:
            data = response.json()
            
            expected_fields = ["total_jobs", "jobs_by_status", "total_accounts", "total_batches"]
            
            all_present = True
            for field in expected_fields:
                if field in data:
                    print_success(f"Campo '{field}' presente")
                else:
                    print_warning(f"Campo '{field}' faltante")
                    all_present = False
            
            return all_present
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_calls_history():
    """Test: Historial de llamadas"""
    print_test("GET /api/v1/calls/history")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/calls/history?limit=10")
        
        if response.status_code == 200:
            data = response.json()
            
            if "calls" in data and isinstance(data["calls"], list):
                calls = data["calls"]
                print_success(f"Se encontraron {len(calls)} llamadas")
                
                if len(calls) > 0:
                    first_call = calls[0]
                    # Verificar campos esperados
                    expected = ["job_id", "call_id", "status", "duration_ms"]
                    for field in expected:
                        if field in first_call:
                            print_success(f"  {field} presente")
                        else:
                            print_warning(f"  {field} faltante")
                
                return True
            else:
                print_warning("No hay historial de llamadas")
                return True
        else:
            print_failure(f"Status code {response.status_code}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def run_all_tests():
    """Ejecuta todos los tests"""
    print_header("🧪 TESTING API ENDPOINTS - Verificación de Estructura Sin Duplicados")
    print_info(f"API Base URL: {API_BASE_URL}")
    
    # Tests de conectividad
    if not test_health():
        print_failure("La API no está disponible. Abortando tests.")
        return
    
    # Tests de endpoints básicos
    test_get_accounts()
    test_get_batches()
    
    # Tests de jobs (CRÍTICO para verificar duplicados)
    test_get_jobs()
    test_get_job_by_id()
    test_get_batch_jobs()
    
    # Tests de endpoints de información
    test_dashboard_stats()
    test_calls_history()
    
    # Resumen final
    print_header("📊 RESUMEN DE TESTS")
    total = tests_passed + tests_failed + tests_skipped
    print(f"\n{Fore.CYAN}Total de tests: {total}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Pasados: {tests_passed}{Style.RESET_ALL}")
    print(f"{Fore.RED}❌ Fallidos: {tests_failed}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⏭️  Omitidos: {tests_skipped}{Style.RESET_ALL}")
    
    if tests_failed == 0:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 TODOS LOS TESTS PASARON!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}⚠️  HAY {tests_failed} TESTS FALLIDOS{Style.RESET_ALL}")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    run_all_tests()
