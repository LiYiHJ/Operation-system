from pathlib import Path
import shutil

root = Path(r"C:\Operation-system\System")

def backup(rel: str) -> Path:
    p = root / rel
    if not p.exists():
        print(f"skip missing -> {p}")
        return p
    bak = p.with_suffix(p.suffix + ".manual_fix_v1")
    shutil.copy2(p, bak)
    print(f"backup -> {bak}")
    return p

# ---------- 1) frontend/src/types/index.ts ----------
types_index = backup(r"frontend/src/types/index.ts")
types_index.write_text(
"""export * from './common'
export * from './dashboard'
export * from './import'
export * from './analysis'
export * from './strategy'
export * from './profit'
export * from './ads'
export * from './dataset'
export * from './batch'
""",
    encoding="utf-8",
)
print(f"updated -> {types_index}")

# ---------- 2) frontend/src/services/api.ts ----------
api_path = backup(r"frontend/src/services/api.ts")
api = api_path.read_text(encoding="utf-8")

if "DatasetRegistryItem" not in api or "DatasetKind" not in api:
    api = api.replace(
        "  AdCampaign\n} from '../types'",
        "  AdCampaign,\n  DatasetRegistryItem,\n  DatasetKind\n} from '../types'",
    )

old_upload_sig = """  uploadFile: (
    file: File,
    shopId: number,
    onProgress?: (progress: number) => void
  ): Promise<ImportResult> => {"""
new_upload_sig = """  uploadFile: (
    file: File,
    shopId: number,
    onProgress?: (progress: number) => void,
    options?: { datasetKind?: DatasetKind | string; importProfile?: string }
  ): Promise<ImportResult> => {"""
api = api.replace(old_upload_sig, new_upload_sig)

old_shop_append = "    formData.append('shop_id', shopId.toString())"
new_shop_append = """    formData.append('shop_id', shopId.toString())
    if (options?.datasetKind) formData.append('dataset_kind', String(options.datasetKind))
    if (options?.importProfile) formData.append('import_profile', String(options.importProfile))"""
api = api.replace(old_shop_append, new_shop_append)

old_confirm_sig = "  confirmImport: (data: ConfirmImportRequest): Promise<ConfirmImportResponse> => {"
new_confirm_sig = "  confirmImport: (data: ConfirmImportRequest & { datasetKind?: DatasetKind | string; importProfile?: string }): Promise<ConfirmImportResponse> => {"
api = api.replace(old_confirm_sig, new_confirm_sig)

field_registry_block = """  getFieldRegistry: (): Promise<FieldRegistryResponse> => {
    return apiClient.get('/import/field-registry')
  },"""
dataset_registry_block = """  getFieldRegistry: (): Promise<FieldRegistryResponse> => {
    return apiClient.get('/import/field-registry')
  },

  getDatasetRegistry: (): Promise<{ contractVersion?: string; datasets?: DatasetRegistryItem[] }> => {
    return apiClient.get('/import/dataset-registry')
  },"""
if "getDatasetRegistry" not in api:
    api = api.replace(field_registry_block, dataset_registry_block)

api_path.write_text(api, encoding="utf-8")
print(f"updated -> {api_path}")

# ---------- 3) src/ecom_v51/services/import_service.py ----------
import_service = backup(r"src/ecom_v51/services/import_service.py")
imp = import_service.read_text(encoding="utf-8")
imp = imp.replace(
    "from .registry.dataset_registry import DatasetRegistryService",
    "from ecom_v51.registry.dataset_registry import DatasetRegistryService",
)
imp = imp.replace(
    "from .ingest.orchestrator import IngestionOrchestrator",
    "from ecom_v51.ingest.orchestrator import IngestionOrchestrator",
)
import_service.write_text(imp, encoding="utf-8")
print(f"updated -> {import_service}")

# ---------- 4) src/ecom_v51/api/routes/reminder.py ----------
reminder = backup(r"src/ecom_v51/api/routes/reminder.py")
rem = reminder.read_text(encoding="utf-8")

if "from datetime import datetime, timezone" not in rem and "from datetime import datetime" in rem:
    rem = rem.replace("from datetime import datetime", "from datetime import datetime, timezone", 1)

anchor = "reminder_bp = Blueprint('reminder', __name__)"
helper = """

def _to_aware_utc(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_unread(item_time, read_at):
    item_dt = _to_aware_utc(item_time)
    read_dt = _to_aware_utc(read_at)
    if item_dt is None:
        return False
    if read_dt is None:
        return True
    return item_dt > read_dt
"""
if "def _to_aware_utc(" not in rem and anchor in rem:
    rem = rem.replace(anchor, anchor + helper, 1)

old_unread = "unread_count = len([x for x in items if not read_at or (x.get('time') and datetime.fromisoformat(x['time']) > read_at)])"
new_unread = "unread_count = len([x for x in items if _is_unread(x.get('time'), read_at)])"
rem = rem.replace(old_unread, new_unread)
rem = rem.replace("now = datetime.utcnow()", "now = datetime.now(timezone.utc)")
reminder.write_text(rem, encoding="utf-8")
print(f"updated -> {reminder}")

# ---------- 5) src/ecom_v51/services/integration_service.py ----------
integration = backup(r"src/ecom_v51/services/integration_service.py")
integ = integration.read_text(encoding="utf-8")

if "from sqlalchemy.exc import OperationalError" not in integ and "from sqlalchemy import inspect" in integ:
    integ = integ.replace(
        "from sqlalchemy import inspect",
        "from sqlalchemy import inspect\nfrom sqlalchemy.exc import OperationalError",
        1,
    )

if "import threading" not in integ and "import json" in integ:
    integ = integ.replace("import json", "import json\nimport threading", 1)

if "_TABLES_READY = False" not in integ and "class IntegrationService:" in integ:
    integ = integ.replace(
        "]\n\n\nclass IntegrationService:",
        "]\n\n_TABLES_READY = False\n_TABLES_LOCK = threading.Lock()\n\n\nclass IntegrationService:",
        1,
    )

old_block = """@staticmethod
    def _ensure_tables() -> None:
        engine = get_engine()
        existing = set(inspect(engine).get_table_names())
        to_create = []
        for m in [ExternalDataSourceConfig, SyncRunLog, PushDeliveryLog, FactSkuExtDaily]:
            if m.__table__.name not in existing:
                to_create.append(m.__table__)
        if to_create:
            ExternalDataSourceConfig.metadata.create_all(bind=engine, tables=to_create)
"""
new_block = """@staticmethod
    def _ensure_tables() -> None:
        global _TABLES_READY

        if _TABLES_READY:
            return

        with _TABLES_LOCK:
            if _TABLES_READY:
                return

            engine = get_engine()
            models = [
                ExternalDataSourceConfig,
                SyncRunLog,
                PushDeliveryLog,
                FactSkuExtDaily,
            ]

            for model in models:
                try:
                    model.__table__.create(bind=engine, checkfirst=True)
                except OperationalError as exc:
                    if "already exists" not in str(exc).lower():
                        raise

            _TABLES_READY = True
"""
integ = integ.replace(old_block, new_block)
integration.write_text(integ, encoding="utf-8")
print(f"updated -> {integration}")

print("\\nDONE")