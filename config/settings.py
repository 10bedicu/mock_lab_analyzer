"""Configuration settings for the application."""
import os


class Config:
    """Application configuration."""
    
    # Lab Analyzer settings
    LISTEN_HOST = os.getenv('LISTEN_HOST', '0.0.0.0')
    LISTEN_PORT = int(os.getenv('LISTEN_PORT', '2575'))
    MLLP_SERVER_ADDRESS = os.getenv('MLLP_SERVER_ADDRESS', 'localhost:2577')
    
    # Flask settings
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '8050'))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Basic Auth settings
    BASIC_AUTH_USERNAME = os.getenv('BASIC_AUTH_USERNAME', 'admin')
    BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD', 'pithon')
    
    @classmethod
    def get_mllp_host_port(cls):
        """Parse MLLP server address into host and port."""
        host, port = cls.MLLP_SERVER_ADDRESS.split(':')
        return host, int(port)
