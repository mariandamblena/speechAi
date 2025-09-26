"""
Desglose REAL de costos - Retell AI + Twilio + Tu SaaS
Análisis de la cadena de costos en llamadas con IA
"""

def explain_real_cost_breakdown():
    """Explica el desglose real de costos en la cadena de servicios"""
    
    print("💰 DESGLOSE REAL DE COSTOS - CADENA DE SERVICIOS")
    print("=" * 60)
    
    print("\n🔗 CADENA DE SERVICIOS:")
    print("   📱 Cliente → 🤖 Tu SaaS → 🎯 Retell AI → 📞 Twilio → 📱 Deudor")
    
    print("\n💸 COSTOS REALES POR SERVICIO:")
    
    # Costos reales aproximados (pueden variar)
    twilio_setup = 0.0085  # ~0.85 centavos por llamada
    twilio_per_minute = 0.013  # ~1.3 centavos por minuto
    
    retell_setup = 0.005  # ~0.5 centavos por setup
    retell_per_minute = 0.08  # ~8 centavos por minuto
    
    # Tu margen
    your_setup = 0.02  # 2 centavos
    your_per_minute = 0.15  # 15 centavos
    
    print(f"\n📞 TWILIO (Telefonía):")
    print(f"   🏁 Setup: ${twilio_setup:.4f} (~0.85¢)")
    print(f"   ⏱️ Por minuto: ${twilio_per_minute:.3f} (~1.3¢)")
    print(f"   📝 Cubre: Conexión telefónica, ruteo de llamada")
    
    print(f"\n🤖 RETELL AI (IA Conversacional):")
    print(f"   🏁 Setup: ${retell_setup:.4f} (~0.5¢)")
    print(f"   ⏱️ Por minuto: ${retell_per_minute:.3f} (~8¢)")
    print(f"   📝 Cubre: GPT, Voice AI, NLP, conversación")
    
    print(f"\n🏢 TU SAAS (Plataforma):")
    print(f"   🏁 Setup: ${your_setup:.3f} (2¢)")
    print(f"   ⏱️ Por minuto: ${your_per_minute:.3f} (15¢)")
    print(f"   📝 Cubre: Tu plataforma, profit, features")
    
    print(f"\n📊 CÁLCULO PARA LLAMADA DE 3 MINUTOS:")
    
    # Llamada de 3 minutos
    minutes = 3
    
    twilio_cost = twilio_setup + (minutes * twilio_per_minute)
    retell_cost = retell_setup + (minutes * retell_per_minute)
    your_cost = your_setup + (minutes * your_per_minute)
    
    total_real_cost = twilio_cost + retell_cost
    total_charged = your_cost
    profit = total_charged - total_real_cost
    margin_percent = (profit / total_charged) * 100
    
    print(f"   📞 Costo Twilio: ${twilio_cost:.3f}")
    print(f"   🤖 Costo Retell: ${retell_cost:.3f}")
    print(f"   💰 COSTO REAL: ${total_real_cost:.3f}")
    print(f"   🏢 Cobras al cliente: ${total_charged:.3f}")
    print(f"   💸 Tu ganancia: ${profit:.3f} ({margin_percent:.1f}%)")

def show_margin_analysis():
    """Muestra análisis de márgenes por duración"""
    
    print(f"\n\n📈 ANÁLISIS DE MÁRGENES POR DURACIÓN")
    print("=" * 50)
    
    # Costos fijos por provider
    costs = {
        'twilio': {'setup': 0.0085, 'per_minute': 0.013},
        'retell': {'setup': 0.005, 'per_minute': 0.08},
        'your_saas': {'setup': 0.02, 'per_minute': 0.15}
    }
    
    durations = [0.5, 1, 2, 3, 5, 10]
    
    print(f"{'Duración':<10} {'Twilio':<8} {'Retell':<8} {'Total Real':<12} {'Cobras':<8} {'Ganancia':<10} {'Margen':<8}")
    print("-" * 75)
    
    for duration in durations:
        twilio_total = costs['twilio']['setup'] + (duration * costs['twilio']['per_minute'])
        retell_total = costs['retell']['setup'] + (duration * costs['retell']['per_minute'])
        real_cost = twilio_total + retell_total
        
        charged = costs['your_saas']['setup'] + (duration * costs['your_saas']['per_minute'])
        profit = charged - real_cost
        margin = (profit / charged) * 100 if charged > 0 else 0
        
        print(f"{duration:<10.1f} ${twilio_total:<7.3f} ${retell_total:<7.3f} ${real_cost:<11.3f} ${charged:<7.3f} ${profit:<9.3f} {margin:<7.1f}%")

def competitive_analysis():
    """Análisis competitivo de precios"""
    
    print(f"\n\n🏆 ANÁLISIS COMPETITIVO")
    print("=" * 40)
    
    competitors = [
        {
            "name": "💼 Tu SaaS (Actual)",
            "setup": 0.02,
            "per_minute": 0.15,
            "description": "Con protecciones y features"
        },
        {
            "name": "🔴 Competidor Agresivo", 
            "setup": 0.015,
            "per_minute": 0.12,
            "description": "Precios más bajos, menos features"
        },
        {
            "name": "🟢 Competidor Premium",
            "setup": 0.05, 
            "per_minute": 0.25,
            "description": "Precios altos, muchas features"
        },
        {
            "name": "🟡 Solo Costos Reales",
            "setup": 0.0135,  # Twilio + Retell setup
            "per_minute": 0.093,  # Twilio + Retell per minute
            "description": "Sin margen (imposible sostener)"
        }
    ]
    
    print(f"Llamada de 3 minutos:")
    print(f"{'Proveedor':<25} {'Costo':<8} {'Descripción':<35}")
    print("-" * 70)
    
    for comp in competitors:
        cost_3min = comp["setup"] + (3 * comp["per_minute"])
        print(f"{comp['name']:<25} ${cost_3min:<7.3f} {comp['description']:<35}")

def protection_value_with_real_costs():
    """Muestra el valor de las protecciones con costos reales"""
    
    print(f"\n\n🛡️ VALOR DE LAS PROTECCIONES (Costos Reales)")
    print("=" * 50)
    
    # Escenario: 500 llamadas bloqueadas por falta de saldo
    blocked_calls = 500
    avg_duration = 3  # minutos
    
    # Costo real que evitas pagar
    real_cost_per_call = 0.0135 + (avg_duration * 0.093)  # Twilio + Retell
    total_real_cost_avoided = blocked_calls * real_cost_per_call
    
    # Lo que habrías cobrado (pero no recibes pago)
    would_charge_per_call = 0.02 + (avg_duration * 0.15)
    total_lost_revenue = blocked_calls * would_charge_per_call
    
    print(f"📊 Escenario: {blocked_calls} llamadas bloqueadas por saldo insuficiente")
    print(f"⏱️ Duración promedio: {avg_duration} minutos")
    print()
    print(f"🔴 SIN PROTECCIÓN:")
    print(f"   💸 Pagarías a providers: ${total_real_cost_avoided:.2f}")
    print(f"   📉 No recibes de cliente: ${total_lost_revenue:.2f}")
    print(f"   💔 PÉRDIDA NETA: ${total_real_cost_avoided:.2f}")
    print()
    print(f"🟢 CON PROTECCIÓN:")
    print(f"   💰 Costo evitado: ${total_real_cost_avoided:.2f}")
    print(f"   ✅ Pérdida real: $0.00")
    print(f"   🎯 AHORRO NETO: ${total_real_cost_avoided:.2f}")

if __name__ == "__main__":
    explain_real_cost_breakdown()
    show_margin_analysis()
    competitive_analysis()
    protection_value_with_real_costs()