#!/usr/bin/env python3
"""
Script de acceso directo para generar reportes de jobs
Uso: python scripts/generate_reports.py --format [terminal|markdown|excel|all]
"""

import sys
import os

# Agregar path del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.jobs_report_generator import main

if __name__ == "__main__":
    exit(main())