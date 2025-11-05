import asyncio

import hl7
from hl7.mllp import open_hl7_connection


async def main():
    # Standard HL7 OML^O21 message structure:
    # - OBR segment represents the panel (CBC panel)
    # - OBX segments represent the component tests within the panel
    # - OBX observation status "O" indicates this is an order (not a result)
    # message = """
    #     MSH|^~\&|CARE|CAREHOSP|MOCKDEV|ANALYZER|20251006165007||OML^O21|5287b2d8-b2ce-4a0b-8495-f0b76cc37f9a|P|2.5.1
    #     PID|1||9c5db015-95bd-4aca-a163-13e17260eaa6^^^CARE^MR||Moe^John||19950101|M
    #     ORC|NW|5287b2d8-b2ce-4a0b-8495-f0b76cc37f9a|3b073bb3-dc9e-496c-9408-cab566c3f660
    #     OBR|1|5287b2d8-b2ce-4a0b-8495-f0b76cc37f9a|3b073bb3-dc9e-496c-9408-cab566c3f660|58410-2^CBC panel - Blood by Automated count^LN
    #     OBX|1|NM|718-7^Hemoglobin [Mass/volume] in Blood^LN||||||||||O
    #     OBX|2|NM|4544-3^Hematocrit [Volume Fraction] of Blood^LN||||||||||O
    #     OBX|3|NM|6690-2^Leukocytes [#/volume] in Blood by Automated count^LN||||||||||O
    #     OBX|4|NM|777-3^Platelets [#/volume] in Blood by Automated count^LN||||||||||O
    #     SPM|1|5a39772b-09da-42fe-856d-f385ee243c81|||20251006151045
    # """
    message = """MSH|^~\&|edbc790a-9eb9-4953-a698-a1082177fa43|FACILITY WITH PATIENTS|LAB_ANALYZER|LAB|20251030144251||OML^O21^OML_O21|b9559079-961b-4018-a3e9-044b11f628ad|P|2.5.1||||NE|AL
    PID|1||2b278730-ec9d-457c-bbf2-f1bb1f98b60b||Nanda^Damini||19650601000000|M
    ORC|NW|b9559079-961b-4018-a3e9-044b11f628ad|b9559079-961b-4018-a3e9-044b11f628ad|||||20251030130639
    OBR|1|b9559079-961b-4018-a3e9-044b11f628ad||26604007^Complete blood count^http://snomed.info/sct||20251030130639|"""
    # Format the message to remove unnecessary whitespaces and replace newlines with \r
    message = '\r'.join(line.strip() for line in message.strip().split('\n'))

    # Open the connection to the HL7 receiver.
    # Using wait_for is optional, but recommended so
    # a dead receiver won't block you for long
    hl7_reader, hl7_writer = await asyncio.wait_for(
        open_hl7_connection("127.0.0.1", 2575),
        timeout=10,
    )

    hl7_message = hl7.parse(message)

    # Write the HL7 message, and then wait for the writer
    # to drain to actually send the message
    hl7_writer.writemessage(hl7_message)
    await hl7_writer.drain()
    print(f'Sent message\n {hl7_message}'.replace('\r', '\n'))

    # Now wait for the ACK message from the receiever
    hl7_ack = await asyncio.wait_for(
      hl7_reader.readmessage(),
      timeout=10
    )
    print(f'Received ACK\n {hl7_ack}'.replace('\r', '\n'))
    
    # Close the connection
    hl7_writer.close()
    await hl7_writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())