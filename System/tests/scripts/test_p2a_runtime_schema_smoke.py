from ecom_v51.api.app import create_app
from ecom_v51.services.batch_service import BatchService
from ecom_v51.config.settings import settings


def test_batch_service_import_smoke():
    service = BatchService(settings.BASE_DIR)
    assert service is not None


def test_create_app_import_smoke():
    app = create_app('development')
    assert app is not None
    assert 'import_bp' not in app.config
