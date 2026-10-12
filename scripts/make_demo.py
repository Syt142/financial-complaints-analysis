"""Create a small, clearly synthetic, multiline CSV for reproducibility."""
import csv
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from complaints_analyzer.core import COLUMNS

root=Path(__file__).resolve().parents[1]
path=root/'data'/'synthetic_complaints.csv'
path.parent.mkdir(exist_ok=True)
with path.open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=COLUMNS);writer.writeheader()
    for i in range(1,13):
        row={c:'' for c in COLUMNS}
        row.update({'Date received':f'2024-{(i-1)%3+1:02d}-15T10:00:00Z',
            'Product':['Mortgage','Checking or savings account','Debt collection'][i%3],
            'Issue':'Synthetic demonstration issue','Company':f'SYNTHETIC COMPANY {i%2}',
            'State':'CA' if i%2 else 'NY','Submitted via':'Web','Complaint ID':str(i),
            'Timely response?':'No' if i%4==0 else 'Yes',
            'Company response to consumer':'Closed with monetary relief' if i%4==0 else 'Closed with explanation',
            'Date sent to company':f'2024-{(i-1)%3+1:02d}-15T11:00:00Z',
            'Consumer complaint narrative':'SYNTHETIC example, not a real consumer.\nSecond line.' if i%2 else ''})
        writer.writerow(row)
print(path)
