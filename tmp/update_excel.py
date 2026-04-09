import os

file_path = r'c:\Users\shyam\Downloads\FOOTBALL APP\backend\services\excel_exporter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replacement for _add_filters_sheet
old_filters = '''    def _add_filters_sheet(self, wb, filters: Dict):
        """Creates a summary sheet for the filters applied to this export."""
        ws = wb.create_sheet("Applied Filters", index=0)
        
        # \xe2\x94\x80\xe2\x94\x80 Styling helpers \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80
        header_font = Font(name="Arial", bold=True, size=14, color="FFFFFF")
        header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid") # accent-green
        
        # Header Row
        ws.merge_cells("A1:C1")
        cell = ws["A1"]
        cell.value = "APPLIED EXPORT FILTERS"
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        # Data Rows
        labels = {
            "market": "Target Market",
            "min_prob": "Minimum Probability (%)",
            "date": "Export Date/Time",
            "count": "Matches Included"
        }
        
        # Convert values to display format
        data = {
            "market": str(filters.get("market", "any")).replace("_", " ").title(),
            "min_prob": f"{filters.get('min_prob', 0) * 100:.0f}%",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": filters.get("count", 0)
        }

        row = 3
        for key, label in labels.items():
            ws.cell(row=row, column=2).value = label
            ws.cell(row=row, column=2).font = Font(bold=True)
            ws.cell(row=row, column=3).value = data.get(key)
            row += 1
            
        _autofit(ws)'''

# I'll use regex or simpler string matching for the parts that are hard to match exactly.
# Let's try a safer approach: find the method start and end.

new_filters = '''    def _add_filters_sheet(self, wb, filters: Dict):
        """Creates a summary sheet for the filters applied to this export."""
        ws = wb.create_sheet("Applied Filters", index=0)
        
        # Header Row (Matching style)
        ws.merge_cells("A1:C1")
        cell = ws["A1"]
        cell.value = "APPLIED EXPORT FILTERS"
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
        ws.row_dimensions[1].height = 25

        # Also add border to the other merged cells in the header row
        for col in range(1, 4):
            ws.cell(row=1, column=col).border = THIN_BORDER

        # Data Rows
        labels = {
            "market": "Target Market",
            "min_prob": "Minimum Probability (%)",
            "date": "Export Date/Time",
            "count": "Matches Included"
        }
        
        # Convert values to display format
        data = {
            "market": str(filters.get("market", "any")).replace("_", " ").title(),
            "min_prob": f"{filters.get('min_prob', 0) * 100:.0f}%",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count": filters.get("count", 0)
        }

        row = 3
        for key, label in labels.items():
            lc = ws.cell(row=row, column=2, value=label)
            lc.font = Font(bold=True)
            lc.border = THIN_BORDER
            lc.fill = ALT_FILL if row % 2 == 0 else PatternFill(fill_type=None)
            
            vc = ws.cell(row=row, column=3, value=data.get(key))
            vc.border = THIN_BORDER
            vc.fill = ALT_FILL if row % 2 == 0 else PatternFill(fill_type=None)
            vc.alignment = Alignment(horizontal="right")
            
            row += 1
            
        _autofit(ws)
        ws.column_dimensions["B"].width = 25
        ws.column_dimensions["C"].width = 25'''

new_batch_overview = '''    def _add_batch_overview_sheet(self, wb, predictions: List[Dict]):
        """Creates a high-level summary sheet for the entire batch results."""
        ws = wb.create_sheet("Batch Overview", index=1 if "Applied Filters" in wb.sheetnames else 0)
        
        # Header Row (Matching style)
        ws.merge_cells("A1:C1")
        cell = ws["A1"]
        cell.value = "BATCH RESULTS OVERVIEW"
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
        ws.row_dimensions[1].height = 25

        # Also add border to the other merged cells in the header row
        for col in range(1, 4):
            ws.cell(row=1, column=col).border = THIN_BORDER

        # Calculate Metrics
        total = len(predictions)
        valid = [p for p in predictions if p.get("success", True)]
        failed = total - len(valid)
        
        home_wins = 0
        draws = 0
        away_wins = 0
        total_conf = 0
        
        for p_entry in valid:
            p = p_entry.get("result", p_entry)
            mr = p.get("match_result", {})
            total_conf += p_entry.get("model_confidence", 0)
            
            # Use favored logic
            max_v = max(mr.get("home", 0), mr.get("draw", 0), mr.get("away", 0))
            if max_v == mr.get("home"): home_wins += 1
            elif max_v == mr.get("draw"): draws += 1
            else: away_wins += 1

        avg_conf = (total_conf / len(valid)) if valid else 0
        
        # Data Rows
        labels = {
            "total": "Total Matches Processed",
            "successful": "Successful Predictions",
            "failed": "Failed/Error Matches",
            "home": "Home Wins Predicted",
            "draw": "Draws Predicted",
            "away": "Away Wins Predicted",
            "conf": "Average Model Confidence"
        }
        
        data = {
            "total": total,
            "successful": len(valid),
            "failed": failed,
            "home": f"{home_wins} ({home_wins/len(valid):.1%})" if valid else "0",
            "draw": f"{draws} ({draws/len(valid):.1%})" if valid else "0",
            "away": f"{away_wins} ({away_wins/len(valid):.1%})" if valid else "0",
            "conf": f"{avg_conf:.1%}"
        }

        row = 3
        for key, label in labels.items():
            lc = ws.cell(row=row, column=2, value=label)
            lc.font = Font(bold=True)
            lc.border = THIN_BORDER
            lc.fill = ALT_FILL if row % 2 == 0 else PatternFill(fill_type=None)
            
            vc = ws.cell(row=row, column=3, value=data.get(key))
            vc.border = THIN_BORDER
            vc.fill = ALT_FILL if row % 2 == 0 else PatternFill(fill_type=None)
            vc.alignment = Alignment(horizontal="right")
            
            if key == "failed" and failed > 0:
                vc.font = Font(color="FF0000", bold=True)
            row += 1
            
        _autofit(ws)
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 25'''

# Using a simpler way to find the blocks:
import re

content = re.sub(r'    def _add_filters_sheet\(self, wb, filters: Dict\):.*?_autofit\(ws\)', new_filters, content, flags=re.DOTALL)
content = re.sub(r'    def _add_batch_overview_sheet\(self, wb, predictions: List\[Dict\]\):.*?row \+= 1', new_batch_overview, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated excel_exporter.py")
