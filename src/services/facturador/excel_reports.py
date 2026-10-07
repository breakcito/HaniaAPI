"""Generador de Reportes en Excel de Alto Valor Ejecutivo y Fiscal para SUNAT / Contabilidad.

Genera archivos Excel (.xlsx) estructurados con formato oficial del Registro de Ventas e Ingresos,
control logístico de Guías de Remisión y análisis financiero de cobranzas.
"""

from io import BytesIO
from decimal import Decimal
from typing import List, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Paleta corporativa sobria y elegante
HEADER_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid") # Navy / Slate 900
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="0F172A")
SUBTITLE_FONT = Font(name="Calibri", size=10, bold=False, color="475569")
TOTAL_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
TOTAL_FONT = Font(name="Calibri", size=11, bold=True, color="0F172A")

THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)
DOUBLE_BOTTOM_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="double", color="0F172A"),
)

def generate_sales_report_excel(company_name: str, company_ruc: str, documents: List[Any]) -> bytes:
    """Genera el reporte de Registro de Ventas e Ingresos (Formato oficial contable)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Registro de Ventas"
    ws.views.sheetView[0].showGridLines = True

    # 1. Cabecera Corporativa
    ws.merge_cells("A1:N1")
    ws["A1"] = f"{company_name.upper()}"
    ws["A1"].font = TITLE_FONT
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("A2:N2")
    ws["A2"] = f"RUC: {company_ruc}  |  REGISTRO OFICIAL DE VENTAS E INGRESOS  |  SISTEMA HANIASYSTEM"
    ws["A2"].font = SUBTITLE_FONT
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")

    headers = [
        "Item",
        "Fecha Emisión",
        "Fecha Vcto.",
        "Tipo",
        "Serie",
        "Correlativo",
        "Doc. Cliente",
        "RUC / DNI",
        "Razón Social / Cliente",
        "Moneda",
        "Op. Gravada",
        "I.G.V. (18%)",
        "Total Venta",
        "Forma Pago",
        "Detracción BN",
        "Estado SUNAT",
    ]

    header_row = 4
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[header_row].height = 26

    # 2. Filas de Datos
    current_row = 5
    tot_taxable = Decimal("0.00")
    tot_igv = Decimal("0.00")
    tot_sales = Decimal("0.00")
    tot_detraction = Decimal("0.00")

    doc_type_names = {
        "01": "Factura",
        "03": "Boleta",
        "07": "Nota Crédito",
        "08": "Nota Débito",
    }

    for idx, doc in enumerate(documents, 1):
        is_voided = doc.status == "voided"
        multiplier = Decimal("-1.00") if doc.type_code == "07" else Decimal("1.00")
        if is_voided:
            multiplier = Decimal("0.00")

        taxable = Decimal(str(doc.total_taxable or 0)) * multiplier
        igv = Decimal(str(doc.total_igv or 0)) * multiplier
        total = Decimal(str(doc.total or 0)) * multiplier
        
        detr_amount = Decimal("0.00")
        if doc.detraction and isinstance(doc.detraction, dict):
            detr_amount = Decimal(str(doc.detraction.get("amount", 0))) * multiplier

        tot_taxable += taxable
        tot_igv += igv
        tot_sales += total
        tot_detraction += detr_amount

        status_text = "ACEPTADO"
        if doc.status == "voided":
            status_text = "ANULADO"
        elif doc.status == "rejected":
            status_text = "RECHAZADO"
        elif doc.status == "pending":
            status_text = "PENDIENTE"
        if getattr(doc, "is_test_mode", False):
            status_text += " (PRUEBA)"

        row_values = [
            idx,
            str(doc.issue_date),
            str(doc.due_date) if doc.due_date else "-",
            doc_type_names.get(doc.type_code, doc.type_code),
            doc.series,
            str(doc.correlative).zfill(8),
            "RUC" if doc.client_doc_type == "6" else "DNI",
            doc.client_doc_number,
            doc.client_name,
            doc.currency,
            float(taxable),
            float(igv),
            float(total),
            (doc.payment_method or "contado").upper(),
            float(detr_amount),
            status_text,
        ]

        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            cell.border = THIN_BORDER

            # Formatos numéricos y alineaciones
            if col_idx in (11, 12, 13, 15):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif col_idx in (1, 2, 3, 4, 5, 6, 7, 8, 10, 14, 16):
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(horizontal="left")

        current_row += 1

    # 3. Fila de Totales
    total_row = current_row
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=10)
    total_label_cell = ws.cell(row=total_row, column=1, value="TOTALES GENERALES:")
    total_label_cell.font = TOTAL_FONT
    total_label_cell.alignment = Alignment(horizontal="right", vertical="center")
    total_label_cell.fill = TOTAL_FILL

    for c in range(1, 11):
        ws.cell(row=total_row, column=c).fill = TOTAL_FILL
        ws.cell(row=total_row, column=c).border = DOUBLE_BOTTOM_BORDER

    # Op Gravada
    cell_tot_tax = ws.cell(row=total_row, column=11, value=float(tot_taxable))
    cell_tot_tax.font = TOTAL_FONT
    cell_tot_tax.number_format = '#,##0.00'
    cell_tot_tax.fill = TOTAL_FILL
    cell_tot_tax.border = DOUBLE_BOTTOM_BORDER

    # IGV
    cell_tot_igv = ws.cell(row=total_row, column=12, value=float(tot_igv))
    cell_tot_igv.font = TOTAL_FONT
    cell_tot_igv.number_format = '#,##0.00'
    cell_tot_igv.fill = TOTAL_FILL
    cell_tot_igv.border = DOUBLE_BOTTOM_BORDER

    # Total Ventas
    cell_tot_sales = ws.cell(row=total_row, column=13, value=float(tot_sales))
    cell_tot_sales.font = TOTAL_FONT
    cell_tot_sales.number_format = '#,##0.00'
    cell_tot_sales.fill = TOTAL_FILL
    cell_tot_sales.border = DOUBLE_BOTTOM_BORDER

    # Espacio y Detracción
    ws.cell(row=total_row, column=14).fill = TOTAL_FILL
    ws.cell(row=total_row, column=14).border = DOUBLE_BOTTOM_BORDER

    cell_tot_detr = ws.cell(row=total_row, column=15, value=float(tot_detraction))
    cell_tot_detr.font = TOTAL_FONT
    cell_tot_detr.number_format = '#,##0.00'
    cell_tot_detr.fill = TOTAL_FILL
    cell_tot_detr.border = DOUBLE_BOTTOM_BORDER

    ws.cell(row=total_row, column=16).fill = TOTAL_FILL
    ws.cell(row=total_row, column=16).border = DOUBLE_BOTTOM_BORDER

    ws.row_dimensions[total_row].height = 22

    # Ajuste automático del ancho de columnas
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len and cell.row > 2:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def generate_despatches_report_excel(company_name: str, company_ruc: str, despatches: List[Any]) -> bytes:
    """Genera el reporte logístico de Guías de Remisión Electrónica (GRE)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Guías de Remisión"
    ws.views.sheetView[0].showGridLines = True

    ws.merge_cells("A1:L1")
    ws["A1"] = f"{company_name.upper()}"
    ws["A1"].font = TITLE_FONT

    ws.merge_cells("A2:L2")
    ws["A2"] = f"RUC: {company_ruc}  |  REPORTE LOGÍSTICO DE GUÍAS DE REMISIÓN ELECTRÓNICA (GRE)"
    ws["A2"].font = SUBTITLE_FONT

    headers = [
        "Item",
        "Guía N°",
        "Tipo",
        "Fecha Emisión",
        "Fecha Traslado",
        "Destinatario RUC/DNI",
        "Razón Social Destinatario",
        "Punto Partida",
        "Punto Llegada",
        "Peso Total",
        "Modalidad",
        "Estado SUNAT",
    ]

    header_row = 4
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
    ws.row_dimensions[header_row].height = 26

    current_row = 5
    for idx, gre in enumerate(despatches, 1):
        recipient = gre.recipient or {}
        origin = gre.origin or {}
        destination = gre.destination or {}

        status_text = "ACEPTADO"
        if gre.status == "voided":
            status_text = "ANULADO"
        elif gre.status == "rejected":
            status_text = "RECHAZADO"
        elif gre.status == "pending":
            status_text = "PENDIENTE"

        row_values = [
            idx,
            f"{gre.series}-{str(gre.correlative).zfill(8)}",
            "Remitente (09)" if gre.type_code == "09" else "Transportista (31)",
            str(gre.issue_date),
            str(gre.transfer_date),
            recipient.get("doc_number", "-"),
            recipient.get("name", "-"),
            origin.get("address", "-"),
            destination.get("address", "-"),
            f"{float(gre.total_weight or 0):.2f} {gre.weight_unit or 'TNE'}",
            "Público" if gre.transport_mode == "01" else "Privado",
            status_text,
        ]

        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            cell.border = THIN_BORDER
            if col_idx in (1, 2, 3, 4, 5, 6, 10, 11, 12):
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(horizontal="left")

        current_row += 1

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len and cell.row > 2:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()
