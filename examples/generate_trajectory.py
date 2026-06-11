import csv
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / 'src'))
from trajectory import generate_trajectory

out = Path('trajectory.csv')
points = generate_trajectory((0, 0), (320, 4))
with out.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y', 't_ms'])
    for p in points:
        writer.writerow([round(p.x, 3), round(p.y, 3), round(p.t, 3)])
print(f'wrote {out.resolve()}')
