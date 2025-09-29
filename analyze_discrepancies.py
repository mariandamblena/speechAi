#!/usr/bin/env python3
"""
Script para analizar discrepancias entre deudores procesados y jobs creados.
Ayuda a identificar exactamente qué registros fueron descartados y por qué razón.
"""

import json
import logging
from typing import Dict, List, Any

def analyze_batch_discrepancies(debtors_file: str, jobs_file: str):
    """
    Analiza las discrepancias entre deudores procesados y jobs creados
    """
    
    print("🔍 Analizando discrepancias entre deudores y jobs...")
    
    # Cargar datos
    try:
        with open(debtors_file, 'r', encoding='utf-8') as f:
            debtors_data = json.load(f)
        
        with open(jobs_file, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
    except Exception as e:
        print(f"❌ Error cargando archivos: {e}")
        return
    
    print(f"📊 Datos cargados:")
    print(f"   - Deudores: {len(debtors_data)}")
    print(f"   - Jobs: {len(jobs_data)}")
    print(f"   - Discrepancia: {len(debtors_data) - len(jobs_data)} registros")
    print()
    
    # Crear mapas por RUT
    debtors_by_rut = {d.get('rut', 'N/A'): d for d in debtors_data}
    
    # Extraer RUTs de jobs (desde deduplication_key)
    job_ruts = set()
    for job in jobs_data:
        dedup_key = job.get('deduplication_key', '')
        if '::' in dedup_key:
            parts = dedup_key.split('::')
            if len(parts) >= 2:
                rut = parts[1]  # account_id::RUT::batch_id
                job_ruts.add(rut)
    
    print(f"📋 RUTs únicos:")
    print(f"   - En deudores: {len(set(debtors_by_rut.keys()))}")
    print(f"   - En jobs: {len(job_ruts)}")
    print()
    
    # Encontrar deudores sin job
    deudores_without_jobs = []
    for rut, debtor in debtors_by_rut.items():
        if rut not in job_ruts and rut != 'N/A':
            deudores_without_jobs.append({
                'rut': rut,
                'nombre': debtor.get('nombre', 'N/A'),
                'to_number': debtor.get('to_number', debtor.get('phones', {}).get('best_e164', 'N/A')),
                'monto_total': debtor.get('monto_total', 0),
                'possible_issues': []
            })
    
    # Analizar posibles problemas
    print("🚨 Deudores SIN job creado:")
    print(f"   Total: {len(deudores_without_jobs)}")
    print()
    
    issues_count = {
        'sin_telefono': 0,
        'telefono_invalido': 0,
        'sin_rut': 0,
        'sin_nombre': 0,
        'otros': 0
    }
    
    for i, debtor_info in enumerate(deudores_without_jobs[:10]):  # Solo primeros 10
        print(f"{i+1:2d}. RUT: {debtor_info['rut']}")
        print(f"    Nombre: {debtor_info['nombre']}")
        print(f"    Teléfono: {debtor_info['to_number']}")
        print(f"    Monto: ${debtor_info['monto_total']:,.2f}")
        
        # Detectar problemas
        issues = []
        if not debtor_info['to_number'] or debtor_info['to_number'] in ['N/A', '', None]:
            issues.append('Sin teléfono válido')
            issues_count['sin_telefono'] += 1
        elif not debtor_info['to_number'].startswith('+56'):
            issues.append('Teléfono no normalizado a formato chileno')
            issues_count['telefono_invalido'] += 1
            
        if not debtor_info['rut'] or debtor_info['rut'] == 'N/A':
            issues.append('Sin RUT')
            issues_count['sin_rut'] += 1
            
        if not debtor_info['nombre'] or debtor_info['nombre'] == 'N/A':
            issues.append('Sin nombre')
            issues_count['sin_nombre'] += 1
            
        if not issues:
            issues.append('Razón desconocida')
            issues_count['otros'] += 1
            
        print(f"    🔍 Posibles problemas: {', '.join(issues)}")
        print()
    
    # Resumen de problemas
    print("📈 Resumen de problemas detectados:")
    for issue_type, count in issues_count.items():
        if count > 0:
            print(f"   - {issue_type.replace('_', ' ').title()}: {count}")
    print()
    
    # Verificar jobs sin payload válido
    jobs_without_payload = [j for j in jobs_data if not j.get('payload') or j.get('payload') == {}]
    if jobs_without_payload:
        print(f"⚠️  ALERTA: {len(jobs_without_payload)} jobs creados SIN payload!")
        print("   Esto indica un problema en la creación de DebtCollectionPayload")
        print()
    
    # Análisis de teléfonos
    print("📞 Análisis de teléfonos en deudores:")
    phones_analysis = {
        'total': len(debtors_data),
        'with_phone': 0,
        'with_cl_phone': 0,
        'without_phone': 0
    }
    
    for debtor in debtors_data:
        phone = debtor.get('to_number') or debtor.get('phones', {}).get('best_e164')
        if phone:
            phones_analysis['with_phone'] += 1
            if phone.startswith('+56'):
                phones_analysis['with_cl_phone'] += 1
        else:
            phones_analysis['without_phone'] += 1
    
    for key, value in phones_analysis.items():
        percentage = (value / phones_analysis['total']) * 100
        print(f"   - {key.replace('_', ' ').title()}: {value} ({percentage:.1f}%)")

if __name__ == "__main__":
    # Ejecutar análisis
    debtors_file = r"c:\Users\maria\Downloads\Debtors.Debtors.json"  # Ajustar path
    jobs_file = r"c:\Users\maria\Downloads\Debtors.jobs.json"        # Ajustar path
    
    analyze_batch_discrepancies(debtors_file, jobs_file)