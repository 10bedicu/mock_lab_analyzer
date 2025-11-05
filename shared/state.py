"""Shared state management for messages between lab analyzer and web app."""
import threading
from datetime import datetime
from typing import Dict, Optional, Any
import uuid


class MessageQueue:
    """Thread-safe message queue using a hashmap with UUID keys."""
    
    def __init__(self):
        self._messages: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def add_message(self, message_data: str, parsed_data: Dict[str, Any]) -> str:
        """
        Add a new message to the queue.
        
        Args:
            message_data: Raw HL7 message string
            parsed_data: Parsed message data dictionary
            
        Returns:
            UUID string of the added message
        """
        message_id = str(uuid.uuid4())
        
        with self._lock:
            self._messages[message_id] = {
                'id': message_id,
                'raw_message': message_data,
                'parsed_data': parsed_data,
                'status': 'pending',  # pending, processed, discarded
                'received_at': datetime.now().isoformat(),
                'processed_at': None,
                'result_message': None,  # Store generated HL7 result
            }
        
        return message_id
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a message by its ID."""
        with self._lock:
            return self._messages.get(message_id)
    
    def get_all_messages(self) -> Dict[str, Dict[str, Any]]:
        """Get all messages in the queue."""
        with self._lock:
            return dict(self._messages)
    
    def get_pending_messages(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending messages."""
        with self._lock:
            return {k: v for k, v in self._messages.items() if v['status'] == 'pending'}
    
    def update_status(self, message_id: str, status: str, result_message: Optional[str] = None) -> bool:
        """
        Update the status of a message.
        
        Args:
            message_id: UUID of the message
            status: New status (pending, processed, discarded)
            result_message: Optional HL7 result message
            
        Returns:
            True if updated successfully, False if message not found
        """
        with self._lock:
            if message_id in self._messages:
                self._messages[message_id]['status'] = status
                if status in ['processed', 'discarded']:
                    self._messages[message_id]['processed_at'] = datetime.now().isoformat()
                if result_message:
                    self._messages[message_id]['result_message'] = result_message
                return True
            return False
    
    def remove_message(self, message_id: str) -> bool:
        """Remove a message from the queue."""
        with self._lock:
            if message_id in self._messages:
                del self._messages[message_id]
                return True
            return False
    
    def clear_processed(self) -> int:
        """Clear all processed and discarded messages. Returns count of removed messages."""
        with self._lock:
            to_remove = [k for k, v in self._messages.items() 
                        if v['status'] in ['processed', 'discarded']]
            for key in to_remove:
                del self._messages[key]
            return len(to_remove)


# Global instance to be shared between lab analyzer and web app
message_queue = MessageQueue()
