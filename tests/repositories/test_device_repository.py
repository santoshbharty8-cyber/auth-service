import uuid
from datetime import datetime, UTC
from unittest.mock import Mock, patch
import pytest

from app.repositories.device_repository import DeviceRepository
from app.models.user_device import UserDevice


@pytest.fixture
def mock_db():
    """Create a mock SQLAlchemy session"""
    return Mock()


@pytest.fixture
def device_repository(mock_db):
    """Create DeviceRepository instance with mock db"""
    return DeviceRepository(mock_db)


def test_find_device_exists(device_repository, mock_db):
    """Test finding a device that exists"""
    user_id = uuid.uuid4()
    fingerprint = "fingerprint123"
    
    # Create a mock device
    mock_device = Mock(spec=UserDevice)
    mock_device.user_id = user_id
    mock_device.fingerprint = fingerprint
    mock_device.user_agent = "Mozilla/5.0"
    mock_device.ip_address = "127.0.0.1"
    
    # Setup mock db.query().filter().first()
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = mock_device
    mock_db.query.return_value = mock_query
    
    # Execute
    result = device_repository.find_device(user_id, fingerprint)
    
    # Assertions
    assert result == mock_device
    mock_db.query.assert_called_once_with(UserDevice)
    mock_query.filter.assert_called_once()


def test_find_device_not_exists(device_repository, mock_db):
    """Test finding a device that doesn't exist"""
    user_id = uuid.uuid4()
    fingerprint = "unknown_fingerprint"
    
    # Setup mock db.query().filter().first() to return None
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None
    mock_db.query.return_value = mock_query
    
    # Execute
    result = device_repository.find_device(user_id, fingerprint)
    
    # Assertions
    assert result is None
    mock_db.query.assert_called_once_with(UserDevice)
    mock_query.filter.assert_called_once()


def test_create_device_success(device_repository, mock_db):
    """Test creating a new device and verifying db operations"""
    user_id = uuid.uuid4()
    fingerprint = "fingerprint456"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    ip_address = "192.168.1.1"
    
    # Setup mock device that will be returned after refresh
    mock_device = Mock(spec=UserDevice)
    mock_device.id = uuid.uuid4()
    mock_device.user_id = user_id
    mock_device.fingerprint = fingerprint
    mock_device.user_agent = user_agent
    mock_device.ip_address = ip_address
    mock_device.created_at = datetime.now(UTC)
    
    # Setup db mock methods
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    
    # Patch UserDevice class to return our mock
    with patch('app.repositories.device_repository.UserDevice') as mock_userdevice_class:
        mock_userdevice_class.return_value = mock_device
        
        # Execute
        result = device_repository.create_device(
            user_id, fingerprint, user_agent, ip_address
        )
        
        # Assertions
        assert result == mock_device
        mock_userdevice_class.assert_called_once_with(
            user_id=user_id,
            fingerprint=fingerprint,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    # Verify db operations were called in correct order
    assert mock_db.add.called, "db.add() should be called"
    assert mock_db.commit.called, "db.commit() should be called"
    assert mock_db.refresh.called, "db.refresh() should be called"


def test_create_device_db_operations_order(device_repository, mock_db):
    """Test that create_device calls db operations in correct order"""
    user_id = uuid.uuid4()
    fingerprint = "test_fingerprint"
    user_agent = "Test Agent"
    ip_address = "10.0.0.1"
    
    # Setup mock device
    mock_device = Mock(spec=UserDevice)
    mock_device.id = uuid.uuid4()
    
    # Track call order
    call_order = []
    
    def track_add(obj):
        call_order.append('add')
    
    def track_commit():
        call_order.append('commit')
    
    def track_refresh(obj):
        call_order.append('refresh')
    
    mock_db.add = Mock(side_effect=track_add)
    mock_db.commit = Mock(side_effect=track_commit)
    mock_db.refresh = Mock(side_effect=track_refresh)
    
    # Patch UserDevice class
    with patch('app.repositories.device_repository.UserDevice') as mock_userdevice_class:
        mock_userdevice_class.return_value = mock_device
        
        # Execute
        result = device_repository.create_device(
            user_id, fingerprint, user_agent, ip_address
        )
        
        # Assertions - verify correct order
        assert call_order == ['add', 'commit', 'refresh'], \
            f"Expected ['add', 'commit', 'refresh'], got {call_order}"
        assert result == mock_device
