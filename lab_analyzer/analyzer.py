"""Lab analyzer service for processing HL7 messages."""
import hl7
import asyncio
from datetime import datetime
import random
import logging
from typing import Dict, List, Any, Optional

from shared.state import message_queue
from config.settings import Config

logger = logging.getLogger(__name__)

# MLLP Protocol constants
MLLP_START = b'\x0b'  # Start of block
MLLP_END = b'\x1c\x0d'  # End of block (FS + CR)


class LabAnalyzerService:
    """Service for handling lab analyzer operations."""
    
    def __init__(self):
        self.mllp_host, self.mllp_port = Config.get_mllp_host_port()
    
    def get_observation_fields(self, test_id: str) -> List[Dict[str, str]]:
        """Get the observation fields required for a test type with pre-filled values and interpretations."""
        test_fields = {
            'LP99237-7': [
                {'id': '717-9', 'name': 'Hemoglobin [Presence] in Blood', 'unit': 'g/dL', 'reference': '12.0-16.0 (F) / 13.0-17.0 (M)', 'value': '13.2', 'interpretation': 'Normal'},
                {'id': 'LP15101-6', 'name': 'Hematocrit', 'unit': '%', 'reference': '36-46 (F) / 40-52 (M)', 'value': '39.5', 'interpretation': 'Normal'},
                {'id': 'LP393833-1', 'name': 'Leukocyte phosphatase | White blood cells | Hematology and Cell counts', 'unit': '10*9/L', 'reference': '4.0-10.0', 'value': '11.8', 'interpretation': 'Abnormal'},
                {'id': 'LP7536-8', 'name': 'RBC', 'unit': '10*12/L', 'reference': '4.2-5.4', 'value': '4.8', 'interpretation': 'Normal'},
            ],
            'BMP': [
                {'id': '2345-7', 'name': 'Glucose', 'unit': 'mg/dL', 'reference': '70-100', 'value': '92', 'interpretation': 'Normal'},
                {'id': '3094-0', 'name': 'Blood Urea Nitrogen', 'unit': 'mg/dL', 'reference': '7-20', 'value': '15', 'interpretation': 'Normal'},
                {'id': '2160-0', 'name': 'Creatinine', 'unit': 'mg/dL', 'reference': '0.6-1.2', 'value': '0.9', 'interpretation': 'Normal'},
                {'id': '2951-2', 'name': 'Sodium', 'unit': 'mmol/L', 'reference': '136-145', 'value': '140', 'interpretation': 'Normal'},
                {'id': '2823-3', 'name': 'Potassium', 'unit': 'mmol/L', 'reference': '3.5-5.0', 'value': '4.2', 'interpretation': 'Normal'},
            ],
            'GLUCOSE': [
                {'id': '1554-5', 'name': 'Glucose', 'unit': 'mg/dL', 'reference': '70-105', 'value': '88', 'interpretation': 'Normal'},
            ],
            '1554-5': [
                {'id': '1554-5', 'name': 'Glucose', 'unit': 'mg/dL', 'reference': '70-105', 'value': '88', 'interpretation': 'Normal'},
            ],
            '26604007': [
                {'id': 'LP32067-8', 'name': 'Hemoglobin', 'unit': 'g/dL', 'reference': '12.0-17.0', 'value': '13.2', 'interpretation': 'Normal'},
                {'id': 'LP15101-6', 'name': 'Hematocrit', 'unit': '%', 'reference': '36.0-50.0', 'value': '39.5', 'interpretation': 'Normal'},
                {'id': 'LA12896-9', 'name': 'Erythrocytes', 'unit': '10*6/uL', 'reference': '4.0-10.0', 'value': '11.8', 'interpretation': 'Abnormal'},
                {'id': 'LP7631-7', 'name': 'Platelets', 'unit': '10*3/uL', 'reference': '150-400', 'value': '250', 'interpretation': 'Normal'},
            ],
        }
        
        test_id_clean = test_id.strip()
        return test_fields.get(test_id_clean, [])
    
    def create_result_message(self, parsed_data: Dict[str, Any], observation_values: Dict[str, float], observation_interpretations: Dict[str, str] = None) -> str:
        """Create an ORU^R01 message with user-provided observation values and interpretations."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        if observation_interpretations is None:
            observation_interpretations = {}
        
        # Build HL7 message segments
        segments = []
        
        # MSH segment
        msh = f"MSH|^~\\&|LAB_ANALYZER|DUMMY_LAB|{parsed_data['sending_application']}|{parsed_data['sending_facility']}|{timestamp}||ORU^R01|{parsed_data['message_control_id']}_RESULT|P|2.5"
        segments.append(msh)
        
        # PID segment
        pid = f"PID|1||{parsed_data['patient_id']}||{parsed_data['patient_name']}||{parsed_data['patient_dob']}|{parsed_data['patient_sex']}|||{parsed_data['patient_address']}||{parsed_data['patient_phone']}|||||||"
        segments.append(pid)
        
        # PV1 segment (if encounter ID exists)
        if parsed_data.get('encounter_id'):
            pv1 = f"PV1|1|||||||||||||||||{parsed_data['encounter_id']}|||||||||||||||||||||||||||||||||"
            segments.append(pv1)
        
        # ORC segment
        orc = f"ORC|RE|{parsed_data['placer_order']}|{parsed_data['filler_order']}||CM||||{timestamp}|||{parsed_data['ordering_provider']}"
        segments.append(orc)
        
        # OBR segment
        test_system = parsed_data.get('test_system', '')
        if test_system:
            obr = f"OBR|1|{parsed_data['placer_order']}|{parsed_data['filler_order']}|{parsed_data['test_id']}^{parsed_data['test_name']}^{test_system}|||{timestamp}|||||||{timestamp}|||{parsed_data['ordering_provider']}||||||||F"
        else:
            obr = f"OBR|1|{parsed_data['placer_order']}|{parsed_data['filler_order']}|{parsed_data['test_id']}^{parsed_data['test_name']}|||{timestamp}|||||||{timestamp}|||{parsed_data['ordering_provider']}||||||||F"
        segments.append(obr)
        
        # OBX segments with user-provided values and interpretations
        obs_fields = self.get_observation_fields(parsed_data['test_id'])
        for idx, field in enumerate(obs_fields, 1):
            value = observation_values.get(field['id'], 0.0)
            interpretation = observation_interpretations.get(field['id'], 'Normal')
            
            # Map interpretation to HL7 abnormal flags
            abnormal_flag = 'N'  # Normal
            _interpretation = interpretation.lower()
            if _interpretation in ['normal', 'n']:
                abnormal_flag = 'N'
            elif _interpretation in ['abnormal', 'a']:
                abnormal_flag = 'A'
            elif _interpretation in ['high', 'h']:
                abnormal_flag = 'H'
            elif _interpretation in ['low', 'l']:
                abnormal_flag = 'L'
            elif _interpretation in ['critical', 'critical high', 'hh']:
                abnormal_flag = 'HH'
            elif _interpretation in ['critical low', 'll']:
                abnormal_flag = 'LL'

            obx = f"OBX|{idx}|NM|{field['id']}^{field['name']}^http://loinc.org||{value:.2f}|{field['unit']}|{field['reference']}|{abnormal_flag}|||F|||{timestamp}||||||"
            segments.append(obx)
        
        # Join segments with carriage return
        message = '\r'.join(segments)
        return message
    
    def wrap_mllp(self, message: str) -> bytes:
        """Wrap message with MLLP framing."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return MLLP_START + message + MLLP_END
    
    async def send_result(self, message: str) -> bool:
        """Send result message to MLLP server."""
        try:
            logger.info(f"Connecting to MLLP server at {self.mllp_host}:{self.mllp_port}...")
            
            reader, writer = await asyncio.open_connection(self.mllp_host, self.mllp_port)
            
            # Wrap message with MLLP framing
            mllp_message = self.wrap_mllp(message)
            
            logger.info(f"Sending result message ({len(mllp_message)} bytes)...")
            writer.write(mllp_message)
            await writer.drain()
            
            # Wait for ACK
            ack = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            logger.info(f"Received ACK: {ack}")
            
            writer.close()
            await writer.wait_closed()
            logger.info("Successfully sent results to MLLP server")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for ACK from MLLP server")
            return False
        except Exception as e:
            logger.error(f"Error sending to MLLP server: {e}")
            return False


class DummyLabAnalyzer:
    """A dummy HL7 lab analyzer that receives orders and stores them in queue."""
    
    def __init__(self, listen_host='0.0.0.0', listen_port=2575):
        self.listen_host = listen_host
        self.listen_port = listen_port
    
    def unwrap_mllp(self, data: bytes) -> bytes:
        """Remove MLLP framing from message."""
        if data.startswith(MLLP_START) and data.endswith(MLLP_END):
            return data[1:-2]  # Remove start and end bytes
        return data
    
    def wrap_mllp(self, message: str) -> bytes:
        """Wrap message with MLLP framing."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return MLLP_START + message + MLLP_END
    
    def parse_order_message(self, message: bytes) -> Optional[Dict[str, Any]]:
        """Parse HL7 order message and extract relevant data."""
        try:
            parsed = hl7.parse(message.decode('utf-8', errors='ignore'))
            
            # Extract segments
            msh = parsed.segment('MSH') if 'MSH' in [seg[0][0] for seg in parsed] else None
            pid = parsed.segment('PID') if 'PID' in [seg[0][0] for seg in parsed] else None
            pv1 = parsed.segment('PV1') if 'PV1' in [seg[0][0] for seg in parsed] else None
            orc = parsed.segment('ORC') if 'ORC' in [seg[0][0] for seg in parsed] else None
            obr = parsed.segment('OBR') if 'OBR' in [seg[0][0] for seg in parsed] else None
            
            # Extract message header info
            sending_application = str(msh[3]) if msh and len(msh) > 3 else "ORDER_SYSTEM"
            sending_facility = str(msh[4]) if msh and len(msh) > 4 else "HOSPITAL"
            message_control_id = str(msh[10]) if msh and len(msh) > 10 else f"MSG{random.randint(10000, 99999)}"
            
            # Extract patient info
            patient_id = str(pid[3]) if pid and len(pid) > 3 and str(pid[3]) else "UNKNOWN"
            patient_name = str(pid[5]) if pid and len(pid) > 5 and str(pid[5]) else "DOE^JOHN"
            patient_dob = str(pid[7]) if pid and len(pid) > 7 and str(pid[7]) else ""
            patient_sex = str(pid[8]) if pid and len(pid) > 8 and str(pid[8]) else "U"
            patient_address = str(pid[11]) if pid and len(pid) > 11 and str(pid[11]) else ""
            patient_phone = str(pid[13]) if pid and len(pid) > 13 and str(pid[13]) else ""
            
            # Extract visit info
            encounter_id = str(pv1[19]) if pv1 and len(pv1) > 19 and str(pv1[19]) else ""
            
            # Extract order info
            if orc and len(orc) > 2 and str(orc[2]):
                placer_order = str(orc[2])
            elif obr and len(obr) > 2 and str(obr[2]):
                placer_order = str(obr[2])
            else:
                placer_order = "ORDER123"
            
            if orc and len(orc) > 3 and str(orc[3]):
                filler_order = str(orc[3])
            elif obr and len(obr) > 3 and str(obr[3]):
                filler_order = str(obr[3])
            else:
                filler_order = f"FILLER{random.randint(1000, 9999)}"
            
            # Extract ordering provider
            ordering_provider = ""
            if orc and len(orc) > 12 and str(orc[12]):
                ordering_provider = str(orc[12])
            elif obr and len(obr) > 16 and str(obr[16]):
                ordering_provider = str(obr[16])
            
            # Extract test info
            if not obr or len(obr) <= 4 or not obr[4]:
                raise ValueError("OBR segment missing or does not contain test information in field 4")
            
            obr_field_4 = str(obr[4])
            field_components = obr_field_4.split('^')
            
            test_id = field_components[0] if len(field_components) > 0 and field_components[0] else None
            test_name = field_components[1] if len(field_components) > 1 else ""
            test_system = field_components[2] if len(field_components) > 2 else ""
            
            if not test_id:
                raise ValueError("Test ID (OBR-4.1) is required but not found in the order message")
            
            return {
                'sending_application': sending_application,
                'sending_facility': sending_facility,
                'message_control_id': message_control_id,
                'patient_id': patient_id,
                'patient_name': patient_name,
                'patient_dob': patient_dob,
                'patient_sex': patient_sex,
                'patient_address': patient_address,
                'patient_phone': patient_phone,
                'encounter_id': encounter_id,
                'placer_order': placer_order,
                'filler_order': filler_order,
                'ordering_provider': ordering_provider,
                'test_id': test_id,
                'test_name': test_name,
                'test_system': test_system,
            }
            
        except Exception as e:
            logger.error(f"Error parsing order message: {e}")
            return None
    
    async def handle_client(self, reader, writer):
        """Handle incoming client connection."""
        addr = writer.get_extra_info('peername')
        logger.info(f"{'='*60}")
        logger.info(f"New connection from {addr}")
        logger.info(f"{'='*60}")
        
        try:
            # Read data from client
            data = await reader.read(4096)
            
            if not data:
                logger.info("No data received")
                return
            
            logger.info(f"Received {len(data)} bytes")
            
            # Unwrap MLLP framing
            message = self.unwrap_mllp(data)
            
            # Display received message
            logger.info("Received HL7 Order Message:")
            logger.info("-" * 60)
            try:
                decoded = message.decode('utf-8', errors='ignore')
                for line in decoded.split('\r'):
                    if line:
                        logger.info(line)
            except Exception:
                logger.info(message)
            logger.info("-" * 60)
            
            # Parse message to get message type for ACK
            try:
                parsed = hl7.parse(message.decode('utf-8', errors='ignore'))
                msh = parsed.segment('MSH')
                msg_type = str(msh[9]) if msh and len(msh) > 9 else "ACK"
                if '^' in msg_type:
                    base_type = msg_type.split('^')[1] if len(msg_type.split('^')) > 1 else msg_type.split('^')[0]
                else:
                    base_type = "O01"
                msg_control_id = str(msh[10]) if msh and len(msh) > 10 else str(random.randint(10000, 99999))
            except Exception:
                base_type = "O01"
                msg_control_id = str(random.randint(10000, 99999))
            
            # Send ACK back to client
            ack_message = f"MSH|^~\\&|LAB_ANALYZER|DUMMY_LAB|ORDER_SYSTEM|HOSPITAL|{datetime.now().strftime('%Y%m%d%H%M%S')}||ACK^{base_type}|ACK{random.randint(10000, 99999)}|P|2.5\rMSA|AA|{msg_control_id}"
            writer.write(self.wrap_mllp(ack_message))
            await writer.drain()
            logger.info("Sent ACK to client")
            
            # Parse and store message in queue
            parsed_data = self.parse_order_message(message)
            if parsed_data:
                message_id = message_queue.add_message(decoded, parsed_data)
                logger.info(f"Message stored in queue with ID: {message_id}")
            else:
                logger.error("Failed to parse order message")
            
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Connection closed from {addr}")
    
    async def start_server(self):
        """Start the TCP server."""
        server = await asyncio.start_server(
            self.handle_client, 
            self.listen_host, 
            self.listen_port
        )
        
        addr = server.sockets[0].getsockname()
        logger.info(f"{'='*60}")
        logger.info("Dummy HL7 Lab Analyzer Started")
        logger.info(f"{'='*60}")
        logger.info(f"Listening on: {addr[0]}:{addr[1]}")
        logger.info(f"{'='*60}")
        logger.info("Waiting for lab orders...")
        
        async with server:
            await server.serve_forever()
