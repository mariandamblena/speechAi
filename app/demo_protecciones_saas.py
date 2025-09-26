"""
Demo visual de las protecciones SaaS por tipo de plan
Muestra cómo cada plan valida el balance antes de llamar
"""

def demo_protecciones():
    print("🔒 DEMO: PROTECCIONES SAAS POR TIPO DE PLAN")
    print("=" * 60)
    
    # Escenarios de cuentas
    cuentas = [
        {
            "name": "CobranzasABC",
            "plan_type": "minutes_based",
            "minutes_remaining": 0,
            "minutes_purchased": 100,
            "jobs_pendientes": 250
        },
        {
            "name": "TiendaXYZ", 
            "plan_type": "credit_based",
            "credit_balance": 5.50,
            "credit_reserved": 0.50,
            "cost_per_call": 2.00,
            "jobs_pendientes": 10
        },
        {
            "name": "EmpresaPremium",
            "plan_type": "unlimited",
            "jobs_pendientes": 1000
        }
    ]
    
    for cuenta in cuentas:
        print(f"\n👤 CUENTA: {cuenta['name']}")
        print(f"📋 Plan: {cuenta['plan_type']}")
        print(f"📞 Jobs pendientes: {cuenta['jobs_pendientes']}")
        
        # Simular validación
        if cuenta['plan_type'] == 'minutes_based':
            minutes = cuenta['minutes_remaining']
            if minutes > 0:
                print(f"✅ PERMITIDO - Minutos disponibles: {minutes}")
                costo_estimado = cuenta['jobs_pendientes'] * 1.50
                print(f"💰 Costo estimado: ${costo_estimado:.2f}")
            else:
                print(f"🚫 BLOQUEADO - Sin minutos (restantes: {minutes})")
                print(f"💸 Costo evitado: ${cuenta['jobs_pendientes'] * 1.50:.2f}")
                print(f"🔔 Acción: Cliente debe comprar más minutos")
                
        elif cuenta['plan_type'] == 'credit_based':
            available = cuenta['credit_balance'] - cuenta['credit_reserved']
            cost_per_call = cuenta['cost_per_call']
            max_calls = int(available // cost_per_call)
            
            print(f"💳 Créditos disponibles: ${available:.2f}")
            print(f"💵 Costo por llamada: ${cost_per_call:.2f}")
            
            if max_calls >= cuenta['jobs_pendientes']:
                print(f"✅ PERMITIDO - Puede hacer {max_calls} llamadas")
                total_cost = cuenta['jobs_pendientes'] * cost_per_call
                print(f"💰 Costo total: ${total_cost:.2f}")
            else:
                blocked_calls = cuenta['jobs_pendientes'] - max_calls
                print(f"🚫 PARCIALMENTE BLOQUEADO")
                print(f"   ✅ Permitidas: {max_calls} llamadas")
                print(f"   ❌ Bloqueadas: {blocked_calls} llamadas")
                blocked_cost = blocked_calls * 1.50  # Costo real de Retell
                print(f"💸 Costo evitado: ${blocked_cost:.2f}")
                
        elif cuenta['plan_type'] == 'unlimited':
            print(f"✅ PERMITIDO - Plan ilimitado")
            print(f"🎉 Sin restricciones de balance")
            costo_estimado = cuenta['jobs_pendientes'] * 1.50
            print(f"💰 Costo estimado: ${costo_estimado:.2f}")
    
    print(f"\n📊 RESUMEN DE PROTECCIONES:")
    print(f"🔒 minutes_based: Valida minutos > 0")  
    print(f"🔒 credit_based: Valida créditos >= costo_llamada")
    print(f"🔓 unlimited: Sin validación de balance")
    print(f"\n💡 BENEFICIO: Evitas pagar por llamadas de cuentas sin saldo")

if __name__ == "__main__":
    demo_protecciones()