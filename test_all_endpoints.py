"""
🚀 TEST AUTOMATIZADO COMPLETO - SPEECHAI BACKEND
Tests exhaustivos de todos los endpoints y funcionalidades
"""

import pytest
import asyncio
import httpx
import json
import os
from typing import Dict, Any
import pandas as pd
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_ACCOUNT_ID = "test_automation_2025"
EXCEL_FILE_PATH = "docs/chile_usuarios.xlsx"

class SpeechAITester:
    """Tester automatizado para SpeechAI Backend"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = {}
        self.created_batch_ids = []
    
    async def setup(self):
        """Configuración inicial de tests"""
        print("🔧 Configurando tests...")
        
        # Verificar que el archivo Excel existe
        if not os.path.exists(EXCEL_FILE_PATH):
            raise FileNotFoundError(f"Archivo Excel no encontrado: {EXCEL_FILE_PATH}")
        
        # Verificar conexión con API
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                raise ConnectionError("API no disponible")
            print("✅ API conectada correctamente")
        except Exception as e:
            raise ConnectionError(f"No se puede conectar a la API: {e}")
    
    async def test_health_endpoint(self):
        """Test del endpoint de salud"""
        print("\n📊 Testing /health endpoint...")
        
        response = await self.client.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        
        self.test_results["health"] = {"status": "✅ PASSED", "response": data}
        print("✅ Health endpoint funcionando")
    
    async def test_account_creation(self):
        """Test de creación de cuenta"""
        print("\n👤 Testing account creation...")
        
        account_data = {
            "account_id": TEST_ACCOUNT_ID,
            "name": "Test Automation Account",
            "email": "test@automation.com",
            "phone": "+56987654321",
            "is_active": True
        }
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/accounts",
            json=account_data
        )
        
        # Puede que ya exista, eso está bien
        assert response.status_code in [200, 201, 409]
        
        if response.status_code == 409:
            print("⚠️ Cuenta ya existe (OK)")
        else:
            print("✅ Cuenta creada/actualizada")
        
        self.test_results["account_creation"] = {
            "status": "✅ PASSED", 
            "response": response.json()
        }
    
    async def test_batch_preview_excel(self):
        """Test de preview de batch desde Excel"""
        print("\n📄 Testing batch preview from Excel...")
        
        # Leer archivo Excel
        with open(EXCEL_FILE_PATH, "rb") as f:
            files = {"file": ("chile_usuarios.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/batches/excel/preview",
                files=files,
                params={"account_id": TEST_ACCOUNT_ID}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "preview" in data
        assert "valid_debtors" in data["preview"]
        assert "total_debtors" in data["preview"]
        
        self.test_results["batch_preview"] = {
            "status": "✅ PASSED",
            "valid_debtors": data["preview"]["valid_debtors"],
            "total_debtors": data["preview"]["total_debtors"]
        }
        
        print(f"✅ Preview generado: {data['preview']['valid_debtors']} deudores válidos")
    
    async def test_batch_creation_basic(self):
        """Test de creación básica de batch desde Excel"""
        print("\n📦 Testing basic batch creation...")
        
        with open(EXCEL_FILE_PATH, "rb") as f:
            files = {"file": ("chile_usuarios.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/batches/excel/create",
                files=files,
                params={
                    "account_id": TEST_ACCOUNT_ID,
                    "processing_type": "basic"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "batch_id" in data
        assert "total_debtors" in data
        assert "total_jobs" in data
        
        # Guardar batch_id para cleanup
        if data["batch_id"]:
            self.created_batch_ids.append(data["batch_id"])
        
        self.test_results["batch_creation_basic"] = {
            "status": "✅ PASSED",
            "batch_id": data.get("batch_id"),
            "total_debtors": data.get("total_debtors"),
            "total_jobs": data.get("total_jobs")
        }
        
        print(f"✅ Batch básico creado: {data.get('batch_id')} con {data.get('total_jobs')} jobs")
    
    async def test_batch_creation_acquisition(self):
        """Test de creación de batch con lógica de adquisición"""
        print("\n🎯 Testing acquisition batch creation...")
        
        with open(EXCEL_FILE_PATH, "rb") as f:
            files = {"file": ("chile_usuarios.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/batches/excel/create",
                files=files,
                params={
                    "account_id": TEST_ACCOUNT_ID,
                    "processing_type": "acquisition"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "batch_id" in data
        assert "debtors_created" in data
        assert "jobs_created" in data
        
        # Guardar batch_id para cleanup
        if data["batch_id"]:
            self.created_batch_ids.append(data["batch_id"])
        
        self.test_results["batch_creation_acquisition"] = {
            "status": "✅ PASSED",
            "batch_id": data.get("batch_id"),
            "debtors_created": data.get("debtors_created"),
            "jobs_created": data.get("jobs_created")
        }
        
        print(f"✅ Batch adquisición creado: {data.get('batch_id')} con {data.get('jobs_created')} jobs")
    
    async def test_batch_listing(self):
        """Test de listado de batches"""
        print("\n📋 Testing batch listing...")
        
        response = await self.client.get(
            f"{BASE_URL}/api/v1/batches",
            params={"account_id": TEST_ACCOUNT_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batches" in data
        assert isinstance(data["batches"], list)
        
        self.test_results["batch_listing"] = {
            "status": "✅ PASSED",
            "total_batches": len(data["batches"])
        }
        
        print(f"✅ Listado de batches: {len(data['batches'])} encontrados")
    
    async def test_batch_details(self):
        """Test de detalles de batch"""
        if not self.created_batch_ids:
            print("⚠️ Skipping batch details test - no batch created")
            return
        
        print("\n🔍 Testing batch details...")
        
        batch_id = self.created_batch_ids[0]
        response = await self.client.get(f"{BASE_URL}/api/v1/batches/{batch_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batch_id" in data
        assert "name" in data
        assert "account_id" in data
        
        self.test_results["batch_details"] = {
            "status": "✅ PASSED",
            "batch_data": data
        }
        
        print(f"✅ Detalles de batch obtenidos: {batch_id}")
    
    async def test_jobs_listing(self):
        """Test de listado de jobs"""
        print("\n👷 Testing jobs listing...")
        
        response = await self.client.get(
            f"{BASE_URL}/api/v1/jobs",
            params={"account_id": TEST_ACCOUNT_ID, "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        
        self.test_results["jobs_listing"] = {
            "status": "✅ PASSED",
            "total_jobs": len(data["jobs"])
        }
        
        print(f"✅ Listado de jobs: {len(data['jobs'])} encontrados")
    
    async def test_account_stats(self):
        """Test de estadísticas de cuenta"""
        print("\n📊 Testing account stats...")
        
        response = await self.client.get(f"{BASE_URL}/api/v1/accounts/{TEST_ACCOUNT_ID}/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar que tiene las estadísticas básicas
        expected_keys = ["total_batches", "total_jobs", "pending_jobs", "completed_jobs"]
        for key in expected_keys:
            assert key in data
        
        self.test_results["account_stats"] = {
            "status": "✅ PASSED",
            "stats": data
        }
        
        print(f"✅ Stats obtenidas: {data.get('total_jobs')} jobs totales")
    
    async def test_google_sheets_preview(self):
        """Test de preview desde Google Sheets (simulado)"""
        print("\n🔗 Testing Google Sheets preview...")
        
        # Simular datos de Google Sheets
        mock_sheets_data = {
            "spreadsheet_id": "test_spreadsheet_123",
            "range": "A1:Z1000",
            "account_id": TEST_ACCOUNT_ID
        }
        
        # Este endpoint puede fallar si no hay configuración real de Google Sheets
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/batches/googlesheets/preview",
                json=mock_sheets_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_results["google_sheets_preview"] = {
                    "status": "✅ PASSED",
                    "response": data
                }
                print("✅ Google Sheets preview funcionando")
            else:
                self.test_results["google_sheets_preview"] = {
                    "status": "⚠️ SKIPPED",
                    "reason": f"No configurado (status: {response.status_code})"
                }
                print("⚠️ Google Sheets no configurado (OK)")
        
        except Exception as e:
            self.test_results["google_sheets_preview"] = {
                "status": "⚠️ SKIPPED",
                "reason": str(e)
            }
            print("⚠️ Google Sheets endpoint no disponible (OK)")
    
    async def cleanup(self):
        """Limpieza post-tests"""
        print("\n🧹 Cleaning up test data...")
        
        # Aquí podríamos eliminar los batches de test creados
        # Por ahora solo los reportamos
        if self.created_batch_ids:
            print(f"📋 Batches creados durante tests: {self.created_batch_ids}")
            print("💡 Pueden ser eliminados manualmente si es necesario")
    
    async def run_all_tests(self):
        """Ejecuta todos los tests"""
        print("🚀 INICIANDO TESTS AUTOMATIZADOS DE SPEECHAI BACKEND")
        print("=" * 60)
        
        try:
            await self.setup()
            
            # Tests básicos
            await self.test_health_endpoint()
            await self.test_account_creation()
            
            # Tests de funcionalidad Excel
            await self.test_batch_preview_excel()
            await self.test_batch_creation_basic()
            await self.test_batch_creation_acquisition()
            
            # Tests de consulta
            await self.test_batch_listing()
            await self.test_batch_details()
            await self.test_jobs_listing()
            await self.test_account_stats()
            
            # Tests opcionales
            await self.test_google_sheets_preview()
            
            await self.cleanup()
            
        except Exception as e:
            print(f"❌ Error durante tests: {e}")
            self.test_results["error"] = str(e)
        
        finally:
            await self.client.aclose()
            
        self.print_results()
    
    def print_results(self):
        """Imprime resultados de tests"""
        print("\n" + "=" * 60)
        print("📊 RESULTADOS DE TESTS AUTOMATIZADOS")
        print("=" * 60)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                status = result.get("status", "❌ ERROR")
            else:
                status = "❌ ERROR"
            print(f"{status} {test_name}")
            
            if "✅" in status:
                passed += 1
            elif "⚠️" in status:
                skipped += 1
            else:
                failed += 1
        
        print("\n📈 RESUMEN:")
        print(f"✅ Pasados: {passed}")
        print(f"❌ Fallidos: {failed}")
        print(f"⚠️ Omitidos: {skipped}")
        print(f"🎯 Total: {passed + failed + skipped}")
        
        if failed == 0:
            print("\n🎉 ¡TODOS LOS TESTS CRÍTICOS PASARON!")
        else:
            print(f"\n⚠️ {failed} tests fallaron - revisar logs")

# Script principal
async def main():
    tester = SpeechAITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())