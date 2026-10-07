"""Módulo puente de compatibilidad para factos_client hacia el gateway desacoplado."""

from src.services.facturador.client import FacturadorClient, facturador_gateway

# Alias retrocompatible
factos_client = facturador_gateway
FactosClient = FacturadorClient
