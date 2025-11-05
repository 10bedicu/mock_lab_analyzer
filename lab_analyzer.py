import hl7
import os
import sys
import asyncio
from datetime import datetime
import random
import logging 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# MLLP Protocol constants
MLLP_START = b'\x0b'  # Start of block
MLLP_END = b'\x1c\x0d'  # End of block (FS + CR)

class DummyLabAnalyzer:
    """A dummy HL7 lab analyzer that receives orders and sends results to an MLLP server."""
    
    def __init__(self, listen_host='0.0.0.0', listen_port=2575, mllp_host='127.0.0.1', mllp_port=2577):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.mllp_host = mllp_host
        self.mllp_port = int(mllp_port)

    def generate_dummy_results(self, order_message):
        """Generate dummy lab results based on the order."""
        try:
            parsed = hl7.parse(order_message.decode('utf-8', errors='ignore'))
            
            # Extract relevant information from the order
            msh = None
            pid = None
            pv1 = None
            orc = None
            obr = None
            
            try:
                msh = parsed.segment('MSH')
            except KeyError:
                pass
            
            try:
                pid = parsed.segment('PID')
                logger.info(f"DEBUG: PID segment found: {pid}")
                logger.info(f"DEBUG: PID[3] = {repr(pid[3])} (type: {type(pid[3])})")
                logger.info(f"DEBUG: str(PID[3]) = {repr(str(pid[3]))}")
                logger.info(f"DEBUG: PID[5] = {repr(pid[5])}")
                logger.info(f"DEBUG: str(PID[5]) = {repr(str(pid[5]))}")
            except KeyError:
                logger.info("DEBUG: PID segment not found!")
                pass
            
            try:
                pv1 = parsed.segment('PV1')
            except KeyError:
                pass
            
            try:
                orc = parsed.segment('ORC')
            except KeyError:
                pass
            
            try:
                obr = parsed.segment('OBR')
            except KeyError:
                pass
            
            # Get message header info
            sending_application = str(msh[3]) if msh and len(msh) > 3 else "ORDER_SYSTEM"
            sending_facility = str(msh[4]) if msh and len(msh) > 4 else "HOSPITAL"
            message_control_id = str(msh[10]) if msh and len(msh) > 10 else f"MSG{random.randint(10000, 99999)}"
            
            # Get patient info - handle HL7 field components properly
            patient_id = str(pid[3]) if pid and len(pid) > 3 and str(pid[3]) else "UNKNOWN"
            patient_name = str(pid[5]) if pid and len(pid) > 5 and str(pid[5]) else "DOE^JOHN"
            patient_dob = str(pid[7]) if pid and len(pid) > 7 and str(pid[7]) else ""
            patient_sex = str(pid[8]) if pid and len(pid) > 8 and str(pid[8]) else "U"
            patient_address = str(pid[11]) if pid and len(pid) > 11 and str(pid[11]) else ""
            patient_phone = str(pid[13]) if pid and len(pid) > 13 and str(pid[13]) else ""
            
            logger.info(f"DEBUG: Patient ID extracted: {patient_id}")
            logger.info(f"DEBUG: Patient Name extracted: {patient_name}")
            logger.info(f"DEBUG: Patient DOB: {patient_dob}, Sex: {patient_sex}")
            # Get visit info
            encounter_id = str(pv1[19]) if pv1 and len(pv1) > 19 and str(pv1[19]) else ""
            
            # Get order info - handle both ORC and OBR sources with proper field extraction
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
            
            logger.info(f"DEBUG: Placer Order: {placer_order}")
            logger.info(f"DEBUG: Filler Order: {filler_order}")
            
            # Get ordering provider info
            ordering_provider = ""
            if orc and len(orc) > 12 and str(orc[12]):
                ordering_provider = str(orc[12])
            elif obr and len(obr) > 16 and str(obr[16]):
                ordering_provider = str(obr[16])
            
            # Get test info
            if not obr or len(obr) <= 4 or not obr[4]:
                raise ValueError("OBR segment missing or does not contain test information in field 4")
            
            # Access components safely - obr[4] is a Field, need to access its components
            # First, convert to string and split by ^ to handle the field properly
            obr_field_4 = str(obr[4])
            field_components = obr_field_4.split('^')
            
            logger.info(f"DEBUG: OBR[4] raw: {repr(obr[4])}")
            logger.info(f"DEBUG: OBR[4] as string: {obr_field_4}")
            logger.info(f"DEBUG: Field components: {field_components}")
            
            test_id = field_components[0] if len(field_components) > 0 and field_components[0] else None
            test_name = field_components[1] if len(field_components) > 1 else ""
            test_system = field_components[2] if len(field_components) > 2 else ""
            
            if not test_id:
                raise ValueError("Test ID (OBR-4.1) is required but not found in the order message")
            
            logger.info(f"DEBUG: Test ID: {test_id}")
            logger.info(f"DEBUG: Test Name: {test_name}")
            logger.info(f"DEBUG: Test System: {test_system}")

            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Create ORU message (Observation Result)
            result_message = self.create_oru_message(
                sending_application=sending_application,
                sending_facility=sending_facility,
                message_control_id=message_control_id,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_dob=patient_dob,
                patient_sex=patient_sex,
                patient_address=patient_address,
                patient_phone=patient_phone,
                encounter_id=encounter_id,
                placer_order=placer_order,
                filler_order=filler_order,
                ordering_provider=ordering_provider,
                test_id=test_id,
                test_name=test_name,
                test_system=test_system,
                timestamp=timestamp,
            )
            
            return result_message
            
        except Exception as e:
            logger.info(f"Error parsing order message: {e}")
            return None
    
    def create_oru_message(self, sending_application, sending_facility, message_control_id,
                          patient_id, patient_name, patient_dob, patient_sex, 
                          patient_address, patient_phone, encounter_id,
                          placer_order, filler_order, ordering_provider,
                          test_id, test_name, test_system, timestamp, components=None):
        """Create an ORU^R01 message with dummy results."""
        
        logger.info(f"DEBUG create_oru_message: test_id={test_id}, test_name={test_name}, test_system={test_system}")
        
        test_results = {
                'CBC': [
                    ('6690-2', 'White Blood Count', 'http://loinc.org', random.uniform(4.0, 11.0), '10^3/uL', '4.0-11.0'),
                    ('789-8', 'Red Blood Count', 'http://loinc.org', random.uniform(4.2, 5.9), '10^6/uL', '4.2-5.9'),
                    ('718-7', 'Hemoglobin', 'http://loinc.org', random.uniform(12.0, 17.0), 'g/dL', '12.0-17.0'),
                    ('4544-3', 'Hematocrit', 'http://loinc.org', random.uniform(36.0, 50.0), '%', '36.0-50.0'),
                ],
                'BMP': [
                    ('2345-7', 'Glucose', 'http://loinc.org', random.uniform(70, 100), 'mg/dL', '70-100'),
                    ('3094-0', 'Blood Urea Nitrogen', 'http://loinc.org', random.uniform(7, 20), 'mg/dL', '7-20'),
                    ('2160-0', 'Creatinine', 'http://loinc.org', random.uniform(0.6, 1.2), 'mg/dL', '0.6-1.2'),
                    ('2951-2', 'Sodium', 'http://loinc.org', random.uniform(136, 145), 'mmol/L', '136-145'),
                    ('2823-3', 'Potassium', 'http://loinc.org', random.uniform(3.5, 5.0), 'mmol/L', '3.5-5.0'),
                ],
                'GLUCOSE': [
                    ('1554-5', 'Glucose', 'http://loinc.org', random.uniform(70, 100), 'mg/dL', '70-105'),
                ],
                '1554-5': [
                    ('1554-5', 'Glucose', 'http://loinc.org', random.uniform(70, 100), 'mg/dL', '70-105'),
                ],
                # SNOMED code for Complete blood count
                '26604007': [
                    ('LP32067-8', 'Hemoglobin', 'http://loinc.org', random.uniform(10.0, 17.0), 'g/dL', '12.0-17.0'),
                    ('LP15101-6', 'Hematocrit', 'http://loinc.org', random.uniform(36.0, 50.0), '%', '36.0-50.0'),
                    ('LA12896-9', 'Erythrocytes', 'http://loinc.org', random.uniform(4.2, 5.9), '10*6/uL', '4.2-5.9'),
                    ('LP7631-7', 'Platelets', 'http://loinc.org', random.uniform(150, 400), '10*3/uL', '150-400'),
                ],
            }

        # Use CBC as default if test not found
        # Clean up test_id to remove any whitespace or special characters
        test_id_clean = test_id.strip()
        logger.info(f"DEBUG: Looking up test_id '{test_id_clean}' (repr: {repr(test_id_clean)})")
        logger.info(f"DEBUG: Available test IDs: {list(test_results.keys())}")
        
        # Check if test_id is supported, raise error if not found
        if test_id_clean not in test_results:
            raise ValueError(f"Unsupported test ID '{test_id_clean}'. Supported test IDs are: {', '.join(test_results.keys())}")
        
        results = test_results[test_id_clean]
        logger.info(f"DEBUG: Selected results for test_id '{test_id_clean}': {len(results)} components")
        
        # Build HL7 message segments
        segments = []
        
        # MSH segment - Use values from incoming message
        msh = f"MSH|^~\\&|LAB_ANALYZER|DUMMY_LAB|{sending_application}|{sending_facility}|{timestamp}||ORU^R01|{message_control_id}_RESULT|P|2.5"
        segments.append(msh)
        
        # PID segment - Use actual patient information from incoming message
        pid = f"PID|1||{patient_id}||{patient_name}||{patient_dob}|{patient_sex}|||{patient_address}||{patient_phone}|||||||"
        segments.append(pid)
        
        # PV1 segment - Use encounter ID from incoming message
        if encounter_id:
            pv1 = f"PV1|1|||||||||||||||||{encounter_id}|||||||||||||||||||||||||||||||||"
            segments.append(pv1)
        
        # ORC segment - Use ordering provider from incoming message
        orc = f"ORC|RE|{placer_order}|{filler_order}||CM||||{timestamp}|||{ordering_provider}"
        segments.append(orc)
        
        # OBR segment - Use ordering provider, include test system if provided
        if test_system:
            obr = f"OBR|1|{placer_order}|{filler_order}|{test_id}^{test_name}^{test_system}|||{timestamp}|||||||{timestamp}|||{ordering_provider}||||||||F"
        else:
            obr = f"OBR|1|{placer_order}|{filler_order}|{test_id}^{test_name}|||{timestamp}|||||||{timestamp}|||{ordering_provider}||||||||F"
        segments.append(obr)
        
        # OBX segments (observations/results)
        for idx, (result_id, result_name, result_system, value, units, reference) in enumerate(results, 1):
            # Use code^display^system format if system is provided, otherwise just code^display
            if result_system:
                obx = f"OBX|{idx}|NM|{result_id}^{result_name}^{result_system}||{value:.2f}|{units}|{reference}|N|||F|||{timestamp}"
            else:
                obx = f"OBX|{idx}|NM|{result_id}^{result_name}||{value:.2f}|{units}|{reference}|N|||F|||{timestamp}"
            segments.append(obx)
        
        # Join segments with carriage return
        message = '\r'.join(segments)
        return message
    
    def wrap_mllp(self, message):
        """Wrap message with MLLP framing."""
        if isinstance(message, str):
            message = message.encode('utf-8')
        return MLLP_START + message + MLLP_END
    
    def unwrap_mllp(self, data):
        """Remove MLLP framing from message."""
        if data.startswith(MLLP_START) and data.endswith(MLLP_END):
            return data[1:-2]  # Remove start and end bytes
        return data
    
    async def send_to_mllp_server(self, message):
        """Send results to the MLLP server."""
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
            logger.info("Timeout waiting for ACK from MLLP server")
            return False
        except Exception as e:
            logger.info(f"Error sending to MLLP server: {e}")
            return False
    
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
                # Extract base message type (e.g., O01 from ORM^O01 or O21 from OML^O21)
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
            
            # Generate dummy results
            logger.info("Generating dummy results...")
            result_message = self.generate_dummy_results(message)
            
            if result_message:
                logger.info("Generated HL7 Result Message:")
                logger.info("-" * 60)
                for line in result_message.split('\r'):
                    if line:
                        logger.info(line)
                logger.info("-" * 60)
                
                # Send results to MLLP server
                await self.send_to_mllp_server(result_message)
            else:
                logger.info("Failed to generate results")
            
        except Exception as e:
            logger.info(f"Error handling client: {e}")
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
        logger.info(f"MLLP Server: {self.mllp_host}:{self.mllp_port}")
        logger.info(f"{'='*60}")
        logger.info("Waiting for lab orders...")
        
        async with server:
            await server.serve_forever()


async def main():
    """Main entry point."""
    # Get configuration from environment variables

    listen_host = os.getenv('LISTEN_HOST', '0.0.0.0')
    listen_port = int(os.getenv('LISTEN_PORT', '2575'))
    mllp_server_address = os.getenv('MLLP_SERVER_ADDRESS', 'localhost:2577')
    mllp_host, mllp_port = mllp_server_address.split(':')

    analyzer = DummyLabAnalyzer(listen_host, listen_port, mllp_host, int(mllp_port))


    try:
        await analyzer.start_server()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.info(f"Error: {e}")


if __name__ == '__main__':
    logger.info("Starting Dummy HL7 Lab Analyzer...")
    asyncio.run(main())