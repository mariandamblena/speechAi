"""
Demostración de la diferencia entre Call Setup y Cost per Minute
"""

def demonstrate_cost_calculation():
    """Demuestra cómo funciona el cálculo de costos"""
    
    print("📞 DIFERENCIA: CALL SETUP vs COST PER MINUTE")
    print("=" * 50)
    
    # Configuración de ejemplo
    cost_per_call_setup = 0.05  # 5 centavos fijos
    cost_per_minute = 0.15      # 15 centavos por minuto
    
    print(f"⚙️ Configuración:")
    print(f"   📞 Call Setup: ${cost_per_call_setup:.2f} (FIJO)")
    print(f"   ⏱️ Por Minuto: ${cost_per_minute:.2f} (VARIABLE)")
    print()
    
    # Escenarios de llamadas
    scenarios = [
        {"duration": 0, "description": "📞 No contesta (colgó inmediatamente)"},
        {"duration": 0.5, "description": "📞 Contestó 30 segundos"},
        {"duration": 1, "description": "📞 Llamada corta (1 minuto)"},
        {"duration": 3, "description": "📞 Llamada normal (3 minutos)"},
        {"duration": 5, "description": "📞 Llamada larga (5 minutos)"},
        {"duration": 10, "description": "📞 Llamada muy larga (10 minutos)"}
    ]
    
    print("📊 CÁLCULO DE COSTOS POR ESCENARIO:")
    print("-" * 50)
    
    for scenario in scenarios:
        duration = scenario["duration"]
        description = scenario["description"]
        
        # Calcular costos
        setup_cost = cost_per_call_setup  # Siempre se cobra
        minute_cost = duration * cost_per_minute  # Variable
        total_cost = setup_cost + minute_cost
        
        print(f"\n{description}")
        print(f"   🏁 Setup Cost:  ${setup_cost:.3f}")
        print(f"   ⏱️ Minute Cost: ${minute_cost:.3f} ({duration} min × ${cost_per_minute:.2f})")
        print(f"   💰 TOTAL:      ${total_cost:.3f}")
        
        # Mostrar porcentajes
        if total_cost > 0:
            setup_percent = (setup_cost / total_cost) * 100
            minute_percent = (minute_cost / total_cost) * 100
            print(f"   📊 Distribución: {setup_percent:.1f}% setup, {minute_percent:.1f}% minutos")

def compare_different_configurations():
    """Compara diferentes configuraciones de precios"""
    
    print("\n\n🔄 COMPARACIÓN DE CONFIGURACIONES")
    print("=" * 50)
    
    configurations = [
        {
            "name": "💼 Plan Empresarial",
            "setup": 0.02,
            "minute": 0.10,
            "description": "Bajo setup, precio competitivo por minuto"
        },
        {
            "name": "📞 Plan Call Center",
            "setup": 0.01,
            "minute": 0.08,
            "description": "Muy bajo setup, ideal para alto volumen"
        },
        {
            "name": "👥 Plan Premium",
            "setup": 0.05,
            "minute": 0.15,
            "description": "Setup más alto, pero minutos premium"
        },
        {
            "name": "🎯 Plan Básico",
            "setup": 0.10,
            "minute": 0.05,
            "description": "Alto setup, minutos muy baratos"
        }
    ]
    
    # Duración de prueba: 3 minutos
    test_duration = 3
    
    for config in configurations:
        setup = config["setup"]
        minute = config["minute"]
        name = config["name"]
        description = config["description"]
        
        total_cost = setup + (test_duration * minute)
        
        print(f"\n{name}")
        print(f"   📝 {description}")
        print(f"   📞 Setup: ${setup:.3f}")
        print(f"   ⏱️ Por minuto: ${minute:.3f}")
        print(f"   💰 Costo llamada 3min: ${total_cost:.3f}")

def business_impact_analysis():
    """Analiza el impacto de negocio de cada componente"""
    
    print("\n\n💡 IMPACTO DE NEGOCIO")
    print("=" * 40)
    
    print("\n🏁 CALL SETUP (Costo Fijo):")
    print("✅ Pros:")
    print("   • Garantiza ingresos mínimos por llamada")
    print("   • Cubre costos de infraestructura/setup")
    print("   • Desalienta llamadas frívolas")
    print("❌ Contras:")
    print("   • Puede ser costoso para llamadas muy cortas")
    print("   • Cliente paga aunque no contesten")
    
    print("\n⏱️ COST PER MINUTE (Costo Variable):")
    print("✅ Pros:")
    print("   • Justo: pagas por lo que usas")
    print("   • Escalable con la duración")
    print("   • Incentiva eficiencia en llamadas")
    print("❌ Contras:")
    print("   • Ingresos impredecibles")
    print("   • No cubre costos fijos si llamadas son muy cortas")
    
    print("\n🎯 ESTRATEGIA COMBINADA:")
    print("💡 Setup BAJO + Minuto MODERADO:")
    print("   → Ideal para llamadas de duración media")
    print("💡 Setup ALTO + Minuto BAJO:")
    print("   → Ideal para llamadas largas frecuentes")
    print("💡 Setup MODERADO + Minuto ALTO:")
    print("   → Ideal para llamadas cortas y directas")

if __name__ == "__main__":
    demonstrate_cost_calculation()
    compare_different_configurations()
    business_impact_analysis()