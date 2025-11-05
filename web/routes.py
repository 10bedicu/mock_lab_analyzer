"""Flask routes for the web interface."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from shared.state import message_queue
from lab_analyzer.analyzer import LabAnalyzerService
from config.settings import Config
import asyncio
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)
auth = HTTPBasicAuth()

# Create a lab analyzer service instance for processing messages
lab_service = LabAnalyzerService()

# Store credentials (in production, use a proper user database)
users = {
    Config.BASIC_AUTH_USERNAME: generate_password_hash(Config.BASIC_AUTH_PASSWORD)
}


@auth.verify_password
def verify_password(username, password):
    """Verify username and password."""
    if username in users and check_password_hash(users.get(username), password):
        return username
    return None


@bp.route('/')
@auth.login_required
def index():
    """Display the message queue."""
    messages = message_queue.get_all_messages()
    # Sort by received time, newest first
    sorted_messages = sorted(messages.values(), 
                            key=lambda x: x['received_at'], 
                            reverse=True)
    return render_template('index.html', messages=sorted_messages)


@bp.route('/message/<message_id>/discard', methods=['POST'])
@auth.login_required
def discard_message(message_id):
    """Discard a message."""
    if message_queue.update_status(message_id, 'discarded'):
        flash('Message discarded successfully', 'success')
    else:
        flash('Message not found', 'error')
    return redirect(url_for('main.index'))


@bp.route('/message/<message_id>/process', methods=['GET'])
@auth.login_required
def process_message_form(message_id):
    """Show the form to process a message."""
    message = message_queue.get_message(message_id)
    if not message:
        flash('Message not found', 'error')
        return redirect(url_for('main.index'))
    
    if message['status'] != 'pending':
        flash('Message has already been processed or discarded', 'warning')
        return redirect(url_for('main.index'))
    
    # Get the test type from parsed data
    parsed_data = message['parsed_data']
    test_id = parsed_data.get('test_id', '')
    
    # Get observation fields for this test type
    obs_fields = lab_service.get_observation_fields(test_id)
    
    return render_template('process.html', 
                         message=message, 
                         obs_fields=obs_fields,
                         test_id=test_id)


@bp.route('/message/<message_id>/process', methods=['POST'])
@auth.login_required
def process_message_submit(message_id):
    """Process a message and send results."""
    message = message_queue.get_message(message_id)
    if not message:
        flash('Message not found', 'error')
        return redirect(url_for('main.index'))
    
    if message['status'] != 'pending':
        flash('Message has already been processed or discarded', 'warning')
        return redirect(url_for('main.index'))
    
    # Get form data for observation values
    parsed_data = message['parsed_data']
    test_id = parsed_data.get('test_id', '')
    obs_fields = lab_service.get_observation_fields(test_id)
    
    # Collect user-provided values
    observation_values = {}
    for field in obs_fields:
        value = request.form.get(f"obs_{field['id']}")
        if value:
            try:
                observation_values[field['id']] = float(value)
            except ValueError:
                flash(f"Invalid value for {field['name']}", 'error')
                return redirect(url_for('main.process_message_form', message_id=message_id))
    
    # Generate ORU message with user-provided values
    try:
        result_message = lab_service.create_result_message(parsed_data, observation_values)
        
        # Send to MLLP server asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(lab_service.send_result(result_message))
        loop.close()
        
        if success:
            message_queue.update_status(message_id, 'processed')
            flash('Message processed and sent successfully!', 'success')
        else:
            flash('Failed to send message to MLLP server', 'error')
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        flash(f'Error processing message: {str(e)}', 'error')
        return redirect(url_for('main.process_message_form', message_id=message_id))
    
    return redirect(url_for('main.index'))


@bp.route('/clear-processed', methods=['POST'])
@auth.login_required
def clear_processed():
    """Clear all processed and discarded messages."""
    count = message_queue.clear_processed()
    flash(f'Cleared {count} processed/discarded messages', 'success')
    return redirect(url_for('main.index'))
