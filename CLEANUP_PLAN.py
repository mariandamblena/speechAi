"""
PLAN DE LIMPIEZA Y ORGANIZACIÓN - SPEECHAI BACKEND
==================================================

Este archivo identifica archivos innecesarios y propone una estructura optimizada
"""

def analyze_files_for_cleanup():
    print("🧹 ANÁLISIS PARA LIMPIEZA DEL PROYECTO")
    print("=" * 60)
    
    # ARCHIVOS A ELIMINAR
    files_to_delete = {
        "🗑️ ARCHIVOS DEMO/TEMPORALES": [
            "app/configure_pricing.py",
            "app/cost_breakdown_demo.py", 
            "app/demo_protecciones_saas.py",
            "app/demo_universal_system.py",
            "app/real_cost_analysis.py",
            "app/test_balance_protection.py",
            "PROJECT_ANALYSIS.py"  # Este mismo archivo
        ],
        "🗑️ ARCHIVOS LEGACY/DUPLICADOS": [
            "app/api.py",  # Reemplazado por universal_api.py
            "app/call_worker.py",  # Reemplazado por universal_call_worker.py
            "app/universal_call_worker_part2.py",  # Fragmento temporal
            "app/universal_call_worker_complete.py"  # Version temporal
        ],
        "🗑️ ARCHIVOS DE DESARROLLO": [
            "app/utils/excel_processor.py",  # Reemplazado por universal
            "app/scripts/init_data.py",  # Solo para setup inicial
        ],
        "🗑️ DOCUMENTOS TEMPORALES": [
            "catalogosDer.png",
            "nucleoOperativoDer.png", 
            "operacionDer.png",
            "sql/catalogos.sql",
            "sql/nucleoOperativo.sql",
            "sql/operacion.sql"
        ]
    }
    
    # ARCHIVOS A MANTENER
    files_to_keep = {
        "🔥 CORE PRODUCTION": [
            "app/universal_api.py",  # API principal
            "app/universal_call_worker.py",  # Worker principal
            "app/run_api.py",  # Servidor
            "app/domain/",  # Capa de dominio completa
            "app/infrastructure/",  # Persistencia
            "app/services/",  # Lógica de negocio
            "app/config/",  # Configuración
            "app/utils/universal_excel_processor.py"  # Procesador universal
        ],
        "📚 DOCUMENTACIÓN ESENCIAL": [
            "README.md",
            "UNIVERSAL_ARCHITECTURE.md",
            "ARCHITECTURE_ROADMAP.md", 
            "STRUCTURE.md"
        ],
        "⚙️ CONFIGURACIÓN": [
            "app/.env.example",
            "app/requirements.txt",
            ".gitignore",
            "Workflow/"  # Workflows de referencia
        ],
        "🧪 TESTS IMPORTANTES": [
            "app/tests/test_structure.py",
            "app/tests/test_excel_batch.py"
        ]
    }
    
    for category, files in files_to_delete.items():
        print(f"\n{category}:")
        for file in files:
            print(f"   ❌ {file}")
    
    print(f"\n{'='*60}")
    
    for category, files in files_to_keep.items():
        print(f"\n{category}:")
        for file in files:
            print(f"   ✅ {file}")

def proposed_final_structure():
    print(f"\n\n📁 ESTRUCTURA FINAL PROPUESTA")
    print("=" * 50)
    
    structure = """
speechAi_backend/
├── 📋 README.md                         # Documentación principal
├── 📋 UNIVERSAL_ARCHITECTURE.md         # Arquitectura universal
├── 📋 ARCHITECTURE_ROADMAP.md           # Roadmap completo
├── 📋 STRUCTURE.md                      # Estructura detallada
├── 🔒 .gitignore                        # Git ignore rules
│
├── 📂 app/                              # 🚀 APLICACIÓN PRINCIPAL
│   ├── ⚙️ .env.example                  # Template de configuración
│   ├── 📋 requirements.txt              # Dependencias Python
│   │
│   ├── 🚀 universal_api.py              # 🔥 API REST principal
│   ├── 🚀 run_api.py                    # Servidor FastAPI
│   ├── 🤖 universal_call_worker.py      # 🔥 Worker principal
│   │
│   ├── 📂 domain/                       # 🏛️ CAPA DE DOMINIO
│   │   ├── 📄 enums.py                  # Enums del sistema
│   │   ├── 📄 models.py                 # Modelos legacy
│   │   ├── 📄 use_case_registry.py      # 🔥 Registry central
│   │   │
│   │   ├── 📂 abstract/                 # Abstracciones base
│   │   │   ├── 📄 base_models.py        # Modelos abstractos
│   │   │   └── 📄 use_case_enums.py     # Enums de casos
│   │   │
│   │   └── 📂 use_cases/                # Casos de uso concretos
│   │       ├── 📄 debt_collection.py    # Cobranza
│   │       └── 📄 user_experience.py    # UX surveys
│   │
│   ├── 📂 services/                     # 🚀 CAPA DE APLICACIÓN
│   │   ├── 📄 account_service.py        # Gestión de cuentas
│   │   ├── 📄 batch_service.py          # Gestión de batches
│   │   ├── 📄 batch_creation_service.py # Creación desde Excel
│   │   └── 📄 job_service_api.py        # Jobs para API
│   │
│   ├── 📂 infrastructure/               # 🏗️ INFRAESTRUCTURA
│   │   ├── 📄 database.py               # Configuración DB
│   │   └── 📄 mongo_client.py           # Cliente MongoDB
│   │
│   ├── 📂 config/                       # ⚙️ CONFIGURACIÓN
│   │   ├── 📄 database.py               # Config DB
│   │   └── 📄 settings.py               # Settings generales
│   │
│   ├── 📂 utils/                        # 🛠️ UTILIDADES
│   │   └── 📄 universal_excel_processor.py # 🔥 Procesador Excel
│   │
│   └── 📂 tests/                        # 🧪 TESTING
│       ├── 📄 test_structure.py         # Tests de estructura
│       └── 📄 test_excel_batch.py       # Tests de batches
│
├── 📂 Workflow/                         # 📋 WORKFLOWS DE REFERENCIA
│   ├── 📄 Adquisicion (5).json         # Workflow original
│   ├── 📄 Adquisicion_v3.json          # Version 3
│   ├── 📄 Llamada_v3.json              # Llamadas v3
│   ├── 📄 llamadaIndividual.json       # Llamada individual
│   ├── 📄 llamadaOrquestada (2).json   # Orquestada
│   └── 📄 Seed (1).json                # Seed data
│
└── 📂 docs/                             # 📚 DOCUMENTACIÓN ADICIONAL
    └── 📂 guides/                       # Guías específicas
        └── 📄 WEBHOOK_README.md         # Documentación webhooks
"""
    
    print(structure)

def cleanup_benefits():
    print(f"\n💎 BENEFICIOS DE LA LIMPIEZA")
    print("=" * 40)
    
    benefits = [
        "✅ Código más limpio y mantenible",
        "✅ Estructura clara y profesional", 
        "✅ Eliminación de archivos obsoletos",
        "✅ Foco en componentes de producción",
        "✅ Documentación organizada",
        "✅ Fácil onboarding para nuevos devs",
        "✅ Deploy más eficiente (menos archivos)",
        "✅ Menos confusión entre versiones"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")

def cleanup_commands():
    print(f"\n🔧 COMANDOS DE LIMPIEZA")
    print("=" * 40)
    
    commands = [
        "# 1. BACKUP (Por seguridad)",
        "git add .; git commit -m 'Backup antes de limpieza'",
        "",
        "# 2. ELIMINAR ARCHIVOS DEMO",
        "del app\\configure_pricing.py",
        "del app\\cost_breakdown_demo.py", 
        "del app\\demo_protecciones_saas.py",
        "del app\\demo_universal_system.py",
        "del app\\real_cost_analysis.py",
        "del app\\test_balance_protection.py",
        "",
        "# 3. ELIMINAR ARCHIVOS LEGACY",
        "del app\\api.py",
        "del app\\call_worker.py", 
        "del app\\universal_call_worker_part2.py",
        "del app\\universal_call_worker_complete.py",
        "",
        "# 4. ELIMINAR ARCHIVOS TEMPORALES",
        "del catalogosDer.png",
        "del nucleoOperativoDer.png",
        "del operacionDer.png",
        "rmdir /s sql",
        "",
        "# 5. COMMIT FINAL",
        "git add .; git commit -m 'Limpieza y organización del proyecto'"
    ]
    
    for command in commands:
        if command.startswith("#"):
            print(f"\n{command}")
        elif command == "":
            continue
        else:
            print(f"   {command}")

if __name__ == "__main__":
    analyze_files_for_cleanup()
    proposed_final_structure()
    cleanup_benefits()
    cleanup_commands()