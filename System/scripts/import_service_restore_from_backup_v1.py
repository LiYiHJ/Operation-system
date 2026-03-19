from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src' / 'ecom_v51' / 'services' / 'import_service.py'
BACKUP = ROOT / 'scripts' / 'mapping_accuracy_safe_patch_v3.import_service.backup.py'

if not BACKUP.exists():
    raise SystemExit(f'未找到备份文件: {BACKUP}')

text = BACKUP.read_text(encoding='utf-8')
SRC.write_text(text, encoding='utf-8', newline='\n')
print('已恢复 import_service.py 为上传备份版本')
