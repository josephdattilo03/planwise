import json
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

# Import the lambda handlers
import sys
sys.path.insert(0, 'functions\events')

from functions.events import create_event, delete_event, get_event, update_event, get_events_by_time_range


@pytest.fixture()
def mock_table():
    """Mock DynamoDB table"""
    with patch('functions.events.create_event.get_table') as mock_get_table, \
         patch('functions.events.delete_event.get_table') as mock_delete_table, \
         patch('functions.events.get_event.get_table') as mock_get_table_get, \
         patch('functions.events.update_event.get_table') as mock_update_table, \
         patch('functions.events.get_events_by_time_range.get_table') as mock_range_table:
        
        table = MagicMock()
        mock_get_table.return_value = table
        mock_delete_table.return_value = table
        mock_get_table_get.return_value = table
        mock_update_table.return_value = table
        mock_range_table.return_value = table
        yield table


@pytest.fixture()
def sample_event_data():
    """Sample event data for testing"""
    return {
        "id": "123",
        "calendar_id": 1,
        "start_time": "2025-01-01",
        "end_time": "2025-01-02",
        "event_color": "#FF0000",
        "is_all_day": True,
        "description": "Test Event",
        "location": "Test Location",
        "timezone": "America/New_York",
        "recurrence": None
    }

# Create event tests
class TestCreateEvent:
    def test_create_event_success(self, mock_table, sample_event_data):
        """Test successful event creation"""
        mock_table.put_item.return_value = {}
        
        event = {
            'body': json.dumps(sample_event_data)
        }
        
        response = create_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Event created successfully'
        assert 'event_id' in body
        mock_table.put_item.assert_called_once()
    
    def test_create_event_validation_error(self, mock_table):
        """Test event creation with invalid data"""
        event = {
            'body': json.dumps({"id": "123"})  # Missing required fields
        }
        
        response = create_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

# Delete event tests
class TestDeleteEvent:
    def test_delete_event_success(self, mock_table):
        """Test successful event deletion"""
        mock_table.get_item.return_value = {'Item': {'id': '123'}}
        mock_table.delete_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '123'}
        }
        
        response = delete_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Event deleted successfully'
        assert body['event_id'] == '123'
        mock_table.delete_item.assert_called_once_with(Key={'id': '123'})
    
    def test_delete_event_not_found(self, mock_table):
        """Test deleting non-existent event"""
        mock_table.get_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '999'}
        }
        
        response = delete_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
        assert body['error'] == 'Event not found'
    
    def test_delete_event_missing_id(self, mock_table):
        """Test deleting event without ID"""
        event = {
            'pathParameters': {}
        }
        
        response = delete_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

# Get event tests
class TestGetEvent:
    def test_get_event_success(self, mock_table, sample_event_data):
        """Test successful event retrieval"""
        mock_table.get_item.return_value = {'Item': sample_event_data}
        
        event = {
            'pathParameters': {'id': '123'}
        }
        
        response = get_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['id'] == '123'
        mock_table.get_item.assert_called_once_with(Key={'id': '123'})
    
    def test_get_event_not_found(self, mock_table):
        """Test retrieving non-existent event"""
        mock_table.get_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '999'}
        }
        
        response = get_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Event not found'
    
    def test_get_event_missing_id(self, mock_table):
        """Test retrieving event without ID"""
        event = {
            'pathParameters': {}
        }
        
        response = get_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

# Update event tests
class TestUpdateEvent:
    def test_update_event_success(self, mock_table, sample_event_data):
        """Test successful event update"""
        mock_table.get_item.return_value = {'Item': sample_event_data}
        updated_data = sample_event_data.copy()
        updated_data['description'] = 'Updated Description'
        mock_table.update_item.return_value = {'Attributes': updated_data}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'description': 'Updated Description'})
        }
        
        response = update_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Event updated successfully'
        assert 'event' in body
        mock_table.update_item.assert_called_once()
    
    def test_update_event_multiple_fields(self, mock_table, sample_event_data):
        """Test updating multiple fields"""
        mock_table.get_item.return_value = {'Item': sample_event_data}
        mock_table.update_item.return_value = {'Attributes': sample_event_data}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({
                'description': 'New Description',
                'location': 'New Location',
                'event_color': '#00FF00'
            })
        }
        
        response = update_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        mock_table.update_item.assert_called_once()
    
    def test_update_event_not_found(self, mock_table):
        """Test updating non-existent event"""
        mock_table.get_item.return_value = {}
        
        event = {
            'pathParameters': {'id': '999'},
            'body': json.dumps({'description': 'Updated'})
        }
        
        response = update_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Event not found'
    
    def test_update_event_no_fields(self, mock_table, sample_event_data):
        """Test updating with no valid fields"""
        mock_table.get_item.return_value = {'Item': sample_event_data}
        
        event = {
            'pathParameters': {'id': '123'},
            'body': json.dumps({'invalid_field': 'value'})
        }
        
        response = update_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'No valid fields to update'
    
    def test_update_event_invalid_json(self, mock_table):
        """Test updating with invalid JSON"""
        event = {
            'pathParameters': {'id': '123'},
            'body': 'invalid json'
        }
        
        response = update_event.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


class TestGetEventsByTimeRange:
    def test_get_events_by_time_range_success(self, mock_table, sample_event_data):
        """Test successful retrieval of events by time range"""
        mock_table.scan.return_value = {
            'Items': [sample_event_data],
            'Count': 1
        }
        
        event = {
            'queryStringParameters': {
                'start_time': '2025-01-01',
                'end_time': '2025-01-31'
            }
        }
        
        response = get_events_by_time_range.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'events' in body
        assert body['count'] == 1
        assert len(body['events']) == 1
    
    def test_get_events_by_time_range_with_pagination(self, mock_table, sample_event_data):
        """Test retrieval with pagination"""
        # First call returns items with LastEvaluatedKey
        mock_table.scan.side_effect = [
            {
                'Items': [sample_event_data],
                'LastEvaluatedKey': {'id': '123'}
            },
            {
                'Items': [sample_event_data],
                'Count': 1
            }
        ]
        
        event = {
            'queryStringParameters': {
                'start_time': '2025-01-01',
                'end_time': '2025-01-31'
            }
        }
        
        response = get_events_by_time_range.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 2  # Should have both batches
        assert mock_table.scan.call_count == 2
    
    def test_get_events_by_time_range_missing_params(self, mock_table):
        """Test retrieval without required parameters"""
        event = {
            'queryStringParameters': {'start_time': '2025-01-01'}
        }
        
        response = get_events_by_time_range.lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_get_events_by_time_range_no_results(self, mock_table):
        """Test retrieval with no matching events"""
        mock_table.scan.return_value = {
            'Items': [],
            'Count': 0
        }
        
        event = {
            'queryStringParameters': {
                'start_time': '2025-01-01',
                'end_time': '2025-01-31'
            }
        }
        
        response = get_events_by_time_range.lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 0
        assert body['events'] == []
    
    def test_get_events_by_time_range_client_error(self, mock_table):
        """Test handling of DynamoDB client error"""
        mock_table.scan.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'Scan'
        )
        
        event = {
            'queryStringParameters': {
                'start_time': '2025-01-01',
                'end_time': '2025-01-31'
            }
        }
        
        response = get_events_by_time_range.lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert 'error' in body
