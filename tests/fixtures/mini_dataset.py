"""Dataset sintetico de 12 empresas para las pruebas de resolucion de identidad.

Trae, a proposito, un nombre acentuado, una fecha en formato DD/MM/YYYY,
un clon de empresa, un deal huerfano, un par con dominio compartido que
debe vetarse, un nombre truncado y una cuenta con solo dos meses de uso
para forzar `insufficient_history`, tal como fija la seccion 7 del
diseno. El PR 2 lo consume en `tests/test_identity_resolution.py`; el
PR 3a agrego dos empresas mas que quedan `unresolved` en `mart_mrr`.
"""

from __future__ import annotations

import pandas as pd

# 11 empresas reales (HS-200001 a HS-200011) mas un clon (HS-900010) de
# HS-200001, mas dos empresas del PR 3a que quedan `unresolved`.
_COMPANIES_ROWS = [
    {"hubspot_id": "HS-200001", "name": "Sanchez y Asociados SA de CV", "domain": "sanchez201.com.mx", "segment": "SMB", "industry": "Retail", "mrr": 5000.0, "currency": "MXN", "signup_date": "2022-05-10", "csm_owner": "Ana Ruiz", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    {"hubspot_id": "HS-200002", "name": "Gaitán Comercial", "domain": "gaitán202.com.mx", "segment": "SMB", "industry": "Retail", "mrr": 3200.0, "currency": "MXN", "signup_date": "10/05/2022", "csm_owner": "Ana Ruiz", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    {"hubspot_id": "HS-200003", "name": "Torres y Compania", "domain": "torres203.com.mx", "segment": "Mid-Market", "industry": "Salud", "mrr": 8000.0, "currency": "USD", "signup_date": "2021-11-02", "csm_owner": "Diego Ortega", "plan": "Pro", "state": "Sonora", "churn_date": None},
    {"hubspot_id": "HS-200004", "name": "Club Uno", "domain": "club300.com.mx", "segment": "SMB", "industry": "Educacion", "mrr": 1000.0, "currency": "MXN", "signup_date": "2021-01-15", "csm_owner": "Luis Pena", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    {"hubspot_id": "HS-200005", "name": "Ferreteria Dos", "domain": "club300.com.mx", "segment": "SMB", "industry": "Construccion", "mrr": 2000.0, "currency": "MXN", "signup_date": "2023-06-01", "csm_owner": "Carla Nunez", "plan": "Basico", "state": "Nuevo Leon", "churn_date": None},
    {"hubspot_id": "HS-200006", "name": "Rios y Hermanos SC", "domain": "rios206.com.mx", "segment": "Mid-Market", "industry": "Manufactura", "mrr": 6400.0, "currency": "MXN", "signup_date": "2022-09-20", "csm_owner": "Ana Ruiz", "plan": "Pro", "state": "Chihuahua", "churn_date": None},
    {"hubspot_id": "HS-200007", "name": "Nunez Automotriz", "domain": "nunez207.com.mx", "segment": "Enterprise", "industry": "Automotriz", "mrr": 15000.0, "currency": "MXN", "signup_date": "2020-03-12", "csm_owner": "Diego Ortega", "plan": "Premium", "state": "Jalisco", "churn_date": "2023-08-01"},
    {"hubspot_id": "HS-200008", "name": "Prado Consultores AC", "domain": "prado208.com.mx", "segment": "SMB", "industry": "Servicios", "mrr": 2600.0, "currency": "MXN", "signup_date": "2022-02-02", "csm_owner": "Luis Pena", "plan": "Basico", "state": "Sonora", "churn_date": None},
    {"hubspot_id": "HS-200009", "name": "Vega Logistica", "domain": "vega209.com.mx", "segment": "Mid-Market", "industry": "Logistica", "mrr": 7100.0, "currency": "MXN", "signup_date": "2021-07-19", "csm_owner": "Ana Ruiz", "plan": "Pro", "state": "Yucatan", "churn_date": None},
    {"hubspot_id": "HS-200010", "name": "Camacho e Hijos", "domain": "camacho210.com.mx", "segment": "SMB", "industry": "Alimentos", "mrr": 1900.0, "currency": "MXN", "signup_date": "2023-01-04", "csm_owner": "Carla Nunez", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    {"hubspot_id": "HS-200011", "name": "Solis Financiera SA", "domain": "solis211.com.mx", "segment": "Enterprise", "industry": "Finanzas", "mrr": 21000.0, "currency": "USD", "signup_date": "2020-10-30", "csm_owner": "Diego Ortega", "plan": "Premium", "state": "Queretaro", "churn_date": None},
    {"hubspot_id": "HS-900010", "name": "SANCHEZ Y ASOCIADOS, S.A. DE C.V.", "domain": "sanchez201.com.mx", "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-05-10", "csm_owner": "Ana Ruiz", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    # Sin MRR y con dos deals de monto distinto (no multiplo de 12): queda `unresolved`.
    {"hubspot_id": "HS-200012", "name": "Rivas Ambiguo SA de CV", "domain": "rivas212.com.mx", "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-08-15", "csm_owner": "Ana Ruiz", "plan": "Basico", "state": "Jalisco", "churn_date": None},
    # Sin MRR y sin ningun deal: tambien queda `unresolved`.
    {"hubspot_id": "HS-200013", "name": "Salas Sin Deals SA de CV", "domain": "salas213.com.mx", "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-09-20", "csm_owner": "Ana Ruiz", "plan": "Basico", "state": "Jalisco", "churn_date": None},
]

_ACCOUNTS_ROWS = [
    {"account_id": "ACC-9001", "hubspot_id": "HS-200001", "account_name": "Sanchez y Asoc", "created_at": "2022-05-10"},
    {"account_id": "ACC-9002", "hubspot_id": None, "account_name": "Torres y Compa", "created_at": "2021-11-02"},
    {"account_id": "ACC-9003", "hubspot_id": "HS-200007", "account_name": "Nunez Automotriz", "created_at": "2020-03-12"},
]

_PRODUCT_USAGE_ROWS = [
    {"account_id": "ACC-9001", "month": "2024-06", "active_users": 12, "logins": 40, "payroll_runs_completed": 2, "features_used": 5, "api_calls": 900},
    {"account_id": "ACC-9001", "month": "2024-07", "active_users": 13, "logins": 44, "payroll_runs_completed": 2, "features_used": 5, "api_calls": 950},
    {"account_id": "ACC-9001", "month": "2024-08", "active_users": 14, "logins": 46, "payroll_runs_completed": 2, "features_used": 5, "api_calls": 980},
    {"account_id": "ACC-9002", "month": "2024-07", "active_users": 4, "logins": 10, "payroll_runs_completed": 1, "features_used": 2, "api_calls": 120},
    {"account_id": "ACC-9002", "month": "2024-08", "active_users": 5, "logins": 12, "payroll_runs_completed": 1, "features_used": 2, "api_calls": 140},
]

_CUSTOMERS_ROWS = [
    {"vitally_id": "cus_9001", "domain": "sanchez201.com.mx", "company_name": "Sanchez y Asociados", "csm_email": "ana.ruiz@worky.mx"},
    {"vitally_id": "cus_9002", "domain": "torres203.com.mx", "company_name": "Torres y Compania", "csm_email": "diego.ortega@worky.mx"},
]

_TICKETS_ROWS = [
    {"ticket_id": "T-9001", "vitally_id": "cus_9001", "created_date": "2024-06-15", "priority": "Medium", "status": "closed", "category": "billing", "resolution_hours": 4, "csat_score": 5},
    {"ticket_id": "T-9002", "vitally_id": "cus_9002", "created_date": "2024-07-02", "priority": "Urgent", "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 3},
]

_DEALS_ROWS = [
    {"deal_id": "D-9001", "hubspot_id": "HS-200001", "stage": "closedwon", "amount": 5000.0, "created_date": "2022-05-01", "close_date": "2022-05-10", "owner": "Ana Ruiz", "pipeline": "New Business", "lead_source": "Referral"},
    {"deal_id": "D-9002", "hubspot_id": "HS-999999", "stage": "closedwon", "amount": 3000.0, "created_date": "2023-02-01", "close_date": "2023-02-14", "owner": "Luis Pena", "pipeline": "New Business", "lead_source": "Web"},
    {"deal_id": "D-9003", "hubspot_id": "HS-200012", "stage": "qualifiedtobuy", "amount": 1500.0, "created_date": "2022-08-20", "close_date": None, "owner": "Ana Ruiz", "pipeline": "New Business", "lead_source": "Referral"},
    {"deal_id": "D-9004", "hubspot_id": "HS-200012", "stage": "appointmentscheduled", "amount": 2200.0, "created_date": "2022-09-01", "close_date": None, "owner": "Ana Ruiz", "pipeline": "New Business", "lead_source": "Referral"},
]

_MARKETING_TOUCHES_ROWS = [
    {"touch_id": "MT-9001", "hubspot_id": "HS-200001", "channel": "paid_search", "touch_date": "2022-04-20", "campaign": "spring"},
    {"touch_id": "MT-9002", "hubspot_id": "HS-200002", "channel": "organic", "touch_date": "2022-04-01", "campaign": "brand"},
]


def build_mini_dataset() -> dict[str, pd.DataFrame]:
    """Construye el dataset sintetico de 12 empresas, con las claves `raw_*`."""
    return {
        "raw_companies": pd.DataFrame(_COMPANIES_ROWS),
        "raw_deals": pd.DataFrame(_DEALS_ROWS),
        "raw_marketing_touches": pd.DataFrame(_MARKETING_TOUCHES_ROWS),
        "raw_accounts": pd.DataFrame(_ACCOUNTS_ROWS),
        "raw_product_usage": pd.DataFrame(_PRODUCT_USAGE_ROWS),
        "raw_customers": pd.DataFrame(_CUSTOMERS_ROWS),
        "raw_tickets": pd.DataFrame(_TICKETS_ROWS),
    }
