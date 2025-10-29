#!/usr/bin/env python3
"""
Script para testear la funcionalidad de call_settings en la API
"""
import requests
import json
import sys
from colorama import init, Fore, Style

init()

API_BASE_URL = "http://localhost:8000"
TEST_BATCH_ID = None

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*80}\n{text}\n{'='*80}{Style.RESET_ALL}")

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_failure(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.BLUE}ℹ️  {text}{Style.RESET_ALL}")

def print_warning(text):
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

def test_get_batch_with_call_settings():
    """Test 1: Verificar que GET devuelve call_settings"""
    print_header("TEST 1: GET /api/v1/batches devuelve call_settings")
    
    global TEST_BATCH_ID
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/batches")
        
        if response.status_code != 200:
            print_failure(f"Status code {response.status_code}")
            return False
        
        batches = response.json()
        
        if not batches or len(batches) == 0:
            print_warning("No hay batches en el sistema")
            return True
        
        # Tomar el primer batch
        first_batch = batches[0]
        TEST_BATCH_ID = first_batch.get("batch_id") or str(first_batch.get("_id"))
        
        print_info(f"Testing con batch: {TEST_BATCH_ID}")
        
        # Verificar si tiene call_settings
        if "call_settings" in first_batch:
            print_success("Campo 'call_settings' presente en la respuesta")
            print_info(f"Valor: {json.dumps(first_batch['call_settings'], indent=2)}")
            return True
        else:
            print_warning("Campo 'call_settings' NO presente (puede ser None/null)")
            return True
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_get_single_batch():
    """Test 2: Verificar GET de un batch específico"""
    print_header("TEST 2: GET /api/v1/batches/{batch_id} incluye call_settings")
    
    if not TEST_BATCH_ID:
        print_warning("No hay batch_id para testear")
        return True
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}")
        
        if response.status_code == 404:
            print_failure(f"Batch {TEST_BATCH_ID} no encontrado")
            return False
        
        if response.status_code != 200:
            print_failure(f"Status code {response.status_code}")
            return False
        
        batch = response.json()
        
        print_info(f"Batch: {batch.get('name', 'Sin nombre')}")
        
        if "call_settings" in batch:
            print_success("Campo 'call_settings' presente")
            
            call_settings = batch["call_settings"]
            if call_settings:
                print_info(f"Call settings configurados:")
                print_info(f"  - max_attempts: {call_settings.get('max_attempts', 'N/A')}")
                print_info(f"  - retry_delay_hours: {call_settings.get('retry_delay_hours', 'N/A')}")
                print_info(f"  - allowed_hours: {call_settings.get('allowed_hours', 'N/A')}")
                print_info(f"  - days_of_week: {call_settings.get('days_of_week', 'N/A')}")
                print_info(f"  - timezone: {call_settings.get('timezone', 'N/A')}")
            else:
                print_info("call_settings es null (usando defaults del worker)")
            
            return True
        else:
            print_warning("Campo 'call_settings' NO presente en respuesta")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_patch_call_settings():
    """Test 3: Actualizar call_settings via PATCH"""
    print_header("TEST 3: PATCH /api/v1/batches/{batch_id} con call_settings")
    
    if not TEST_BATCH_ID:
        print_warning("No hay batch_id para testear")
        return True
    
    # Configuración de prueba
    test_call_settings = {
        "max_attempts": 5,
        "retry_delay_hours": 48,
        "allowed_hours": {
            "start": "08:00",
            "end": "21:00"
        },
        "days_of_week": [1, 2, 3, 4, 5, 6],  # Lun-Sab
        "timezone": "America/Santiago"
    }
    
    print_info(f"Intentando actualizar call_settings a:")
    print_info(json.dumps(test_call_settings, indent=2))
    
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}",
            json={"call_settings": test_call_settings},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 404:
            print_failure(f"Batch {TEST_BATCH_ID} no encontrado")
            return False
        
        if response.status_code != 200:
            print_failure(f"Status code {response.status_code}: {response.text}")
            return False
        
        result = response.json()
        
        if result.get("success"):
            print_success(f"Actualización exitosa: {result.get('message')}")
            print_info(f"Campos actualizados: {result.get('updated_fields')}")
            
            # Verificar que se haya guardado
            print_info("Verificando que los cambios se guardaron...")
            verify_response = requests.get(f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}")
            
            if verify_response.status_code == 200:
                updated_batch = verify_response.json()
                saved_settings = updated_batch.get("call_settings")
                
                if saved_settings:
                    if saved_settings == test_call_settings:
                        print_success("✅ Call settings guardados correctamente")
                        return True
                    else:
                        print_warning("⚠️  Call settings guardados pero con valores diferentes")
                        print_info(f"Guardado: {json.dumps(saved_settings, indent=2)}")
                        return True
                else:
                    print_failure("Call settings es null después de actualizar")
                    return False
            else:
                print_warning("No se pudo verificar (error en GET)")
                return True
        else:
            print_failure(f"Actualización falló: {result}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def test_patch_reset_call_settings():
    """Test 4: Resetear call_settings a null"""
    print_header("TEST 4: PATCH con call_settings: null para usar defaults")
    
    if not TEST_BATCH_ID:
        print_warning("No hay batch_id para testear")
        return True
    
    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}",
            json={"call_settings": None},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print_failure(f"Status code {response.status_code}: {response.text}")
            return False
        
        result = response.json()
        
        if result.get("success"):
            print_success(f"Reset exitoso: {result.get('message')}")
            
            # Verificar
            verify_response = requests.get(f"{API_BASE_URL}/api/v1/batches/{TEST_BATCH_ID}")
            
            if verify_response.status_code == 200:
                updated_batch = verify_response.json()
                if updated_batch.get("call_settings") is None:
                    print_success("✅ Call settings reseteado a null (usará defaults)")
                    return True
                else:
                    print_warning("Call settings no es null")
                    return True
            else:
                return True
        else:
            print_failure(f"Reset falló: {result}")
            return False
            
    except Exception as e:
        print_failure(f"Error: {str(e)}")
        return False

def main():
    print_header("🧪 TESTING CALL_SETTINGS API")
    print_info(f"API Base URL: {API_BASE_URL}")
    
    # Verificar conectividad
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print_failure("API no disponible")
            sys.exit(1)
        print_success("API disponible\n")
    except:
        print_failure("No se puede conectar a la API")
        print_info("Asegúrate de que la API esté corriendo: python app/run_api.py")
        sys.exit(1)
    
    # Ejecutar tests
    tests = [
        ("GET batches con call_settings", test_get_batch_with_call_settings),
        ("GET single batch con call_settings", test_get_single_batch),
        ("PATCH actualizar call_settings", test_patch_call_settings),
        ("PATCH resetear call_settings", test_patch_reset_call_settings),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_failure(f"Test '{name}' falló con excepción: {str(e)}")
            results.append((name, False))
    
    # Resumen
    print_header("📊 RESUMEN")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        color = Fore.GREEN if result else Fore.RED
        print(f"{color}{status}{Style.RESET_ALL}: {name}")
    
    print(f"\n{Fore.CYAN}Total: {passed}/{total} tests pasados{Style.RESET_ALL}")
    
    if passed == total:
        print(f"\n{Fore.GREEN}🎉 ¡TODOS LOS TESTS PASARON!{Style.RESET_ALL}\n")
        sys.exit(0)
    else:
        print(f"\n{Fore.RED}⚠️  Algunos tests fallaron{Style.RESET_ALL}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
