from pathlib import Path
import re

ROOT = Path(r"C:/Operation-system/System")
if not ROOT.exists():
    ROOT = Path('.')

profit_py = ROOT / 'src' / 'ecom_v51' / 'api' / 'routes' / 'profit.py'
services_init = ROOT / 'src' / 'ecom_v51' / 'services' / '__init__.py'
registry_service = ROOT / 'src' / 'ecom_v51' / 'services' / 'profit_registry_service.py'

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'{label} 未命中')
    return text.replace(old, new, 1)

text = profit_py.read_text(encoding='utf-8')
text = replace_once(
    text,
    'from ecom_v51.services import ProfitRegistryService, ProfitService',
    'from ecom_v51.services import ProfitService',
    'profit.py import'
)
text = text.replace('\nprofit_registry_service = ProfitRegistryService()', '')

block = '''\n\n@profit_bp.route('/registry/cost-components', methods=['GET'])\ndef get_cost_component_registry():\n    data = profit_registry_service.get_cost_component_registry()\n    return jsonify({\n        'success': True,\n        'data': data,\n    })\n\n\n@profit_bp.route('/registry/metrics', methods=['GET'])\ndef get_profit_metric_registry():\n    data = profit_registry_service.get_profit_metric_registry()\n    return jsonify({\n        'success': True,\n        'data': data,\n    })\n\n\n@profit_bp.route('/registry/summary', methods=['GET'])\ndef get_profit_registry_summary():\n    data = profit_registry_service.get_registry_summary()\n    return jsonify({\n        'success': True,\n        'data': data,\n    })\n'''
if block in text:
    text = text.replace(block, '\n')
else:
    # be tolerant to trailing spaces/newlines
    text = re.sub(r"\n@profit_bp\.route\('/registry/cost-components'.*?\n\s*\})\n", '\n', text, flags=re.S)

profit_py.write_text(text, encoding='utf-8', newline='\n')

text = services_init.read_text(encoding='utf-8')
text = text.replace("\nfrom .profit_registry_service import ProfitRegistryService", '')
services_init.write_text(text, encoding='utf-8', newline='\n')

if registry_service.exists():
    backup = registry_service.with_suffix('.py.disabled')
    if backup.exists():
        backup.unlink()
    registry_service.rename(backup)
    print(f'已停用: {registry_service} -> {backup.name}')
else:
    print('profit_registry_service.py 不存在，跳过')

print('已恢复利润模块到 P0 结构预埋状态：保留 config JSON，不加载 runtime bridge')
