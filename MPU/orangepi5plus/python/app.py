"""
This is a simple example script showing how to

    * Connect to a SPIKE™ Prime hub over BLE
    * Subscribe to device notifications
    * Transfer and start a new program

The script is heavily simplified and not suitable for production use.

----------------------------------------------------------------------

After prompting for confirmation to continue, the script will simply connect to
the first device it finds advertising the SPIKE™ Prime service UUID, and proceed
with the following steps:

    1. Request information about the device (e.g. max chunk size for file transfers)
    2. Subscribe to device notifications (e.g. state of IMU, display, sensors, motors, etc.)
    3. Clear the program in a specific slot
    4. Request transfer of a new program file to the slot
    5. Transfer the program in chunks
    6. Start the program

If the script detects an unexpected response, it will print an error message and exit.
Otherwise it will continue to run until the connection is lost or stopped by the user.
(You can stop the script by pressing Ctrl+C in the terminal.)

While the script is running, it will print information about the messages it sends and receives.
"""

import sys
from typing import cast, TypeVar

TMessage = TypeVar("TMessage", bound="BaseMessage")

import cobs
from messages import *
from crc import crc

import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from pynput.keyboard import Key, Listener
import socket
import time
import logging

SERVER_ADDRESS = ("192.168.199.178", 80)

SCAN_TIMEOUT = 10.0
"""How long to scan for devices before giving up (in seconds)"""

SERVICE = "0000fd02-0000-1000-8000-00805f9b34fb"
"""The SPIKE™ Prime BLE service UUID"""

RX_CHAR = "0000fd02-0001-1000-8000-00805f9b34fb"
"""The UUID the hub will receive data on"""

TX_CHAR = "0000fd02-0002-1000-8000-00805f9b34fb"
"""The UUID the hub will transmit data on"""

DEVICE_NOTIFICATION_INTERVAL_MS = 5000
"""The interval in milliseconds between device notifications"""

EXAMPLE_SLOT = 0
"""The slot to upload the example program to"""


EXAMPLE_PROGRAM_PREFIX = """import runloop
from hub import light_matrix, port, sound
import motor
print("Console message from hub.")
def foo():
    return False
async def main():
    await runloop.until(foo)# light_matrix.write("Proc...")
"""
EXAMPLE_PROGRAM_SUBFIX = """runloop.run(main())"""

EXAMPLE_PROGRAM_CORE_UP = """
sound.beep()
motor.run(port.D, 100) # front wheel
motor.run(port.C, 100) # back wheel
"""

EXAMPLE_PROGRAM_CORE_STOP = """
    await runloop.until(foo)# light_matrix.write("Proc...")
sound.beep()
motor.stop(port.D) # front wheel
motor.stop(port.C) # back wheel
"""

# answer = input(
#     f"This example will override the program in slot {EXAMPLE_SLOT} of the first hub found. Do you want to continue? [Y/n] "
# )
# if answer.strip().lower().startswith("n"):
#     print("Aborted by user.")
#     sys.exit(0)

stop_event = asyncio.Event()

def send_http_request(server_address):
    refresh_requested:bool=False
    EXAMPLE_PROGRAM = """""".encode("utf8")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(server_address)

        request = f"GET / HTTP/1.1\r\nHost: {server_address[0]}\r\n\r\n"
        logging.debug("Sending request: %s", request)
        sock.sendall(request.encode())

        while True:
            data = sock.recv(1024)
            if not data:
                break
            logging.debug("Received data: %s", data.decode())

            
            code = data.decode()
            print(f'code == {code}')
            if "move" in code: # be care, "move" != code, maybe it's 'move\n'

                refresh_requested = True
                # EXAMPLE_PROGRAM = (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_UP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')
                sock.close()
                print(refresh_requested)
                print((EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_UP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8'))
                return refresh_requested, (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_UP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')
            elif "stop" in code:
                refresh_requested = True
                # EXAMPLE_PROGRAM = (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_STOP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')
                sock.close()
                return refresh_requested, (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_STOP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')

        sock.close()
    except socket.error as e:
        logging.error("Socket error: %s", e)
    return False, """""".encode('utf8')
    

async def main():
    refresh_requested = False
    EXAMPLE_PROGRAM = """import runloop
from hub import light_matrix
print("Console message from hub.")
async def main():
    await light_matrix.write("Hi!")
runloop.run(main())""".encode("utf8")
    def match_service_uuid(device: BLEDevice, adv: AdvertisementData) -> bool:
        return SERVICE.lower() in adv.service_uuids

    print(f"\nScanning for {SCAN_TIMEOUT} seconds, please wait...")
    device = await BleakScanner.find_device_by_filter(
        filterfunc=match_service_uuid, timeout=SCAN_TIMEOUT
    )

    if device is None:
        print(
            "No hubs detected. Ensure that a hub is within range, turned on, and awaiting connection."
        )
        sys.exit(1)

    device = cast(BLEDevice, device)
    print(f"Hub detected! {device}")

    def on_disconnect(client: BleakClient) -> None:
        print("Connection lost.")
        stop_event.set()

    print("Connecting...")
    async with BleakClient(device, disconnected_callback=on_disconnect) as client:
        print("Connected!\n")

        service = client.services.get_service(SERVICE)
        rx_char = service.get_characteristic(RX_CHAR)
        tx_char = service.get_characteristic(TX_CHAR)

        # simple response tracking
        pending_response: tuple[int, asyncio.Future] = (-1, asyncio.Future())

        # callback for when data is received from the hub
        def on_data(_: BleakGATTCharacteristic, data: bytearray) -> None:
            if data[-1] != 0x02:
                # packet is not a complete message
                # for simplicity, this example does not implement buffering
                # and is therefore unable to handle fragmented messages
                un_xor = bytes(map(lambda x: x ^ 3, data))  # un-XOR for debugging
                print(f"Received incomplete message:\n {un_xor}")
                return

            data = cobs.unpack(data)
            try:
                message = deserialize(data)
                print(f"Received: {message}")
                if message.ID == pending_response[0]:
                    pending_response[1].set_result(message)
                if isinstance(message, DeviceNotification):
                    # sort and print the messages in the notification
                    updates = list(message.messages)
                    updates.sort(key=lambda x: x[1])
                    lines = [f" - {x[0]:<10}: {x[1]}" for x in updates]
                    print("\n".join(lines))

            except ValueError as e:
                print(f"Error: {e}")

        # enable notifications on the hub's TX characteristic
        await client.start_notify(tx_char, on_data)

        # to be initialized
        info_response: InfoResponse = None

        # serialize and pack a message, then send it to the hub
        async def send_message(message: BaseMessage) -> None:
            print(f"Sending: {message}")
            payload = message.serialize()
            frame = cobs.pack(payload)

            # use the max_packet_size from the info response if available
            # otherwise, assume the frame is small enough to send in one packet
            packet_size = info_response.max_packet_size if info_response else len(frame)

            # send the frame in packets of packet_size
            for i in range(0, len(frame), packet_size):
                packet = frame[i : i + packet_size]
                await client.write_gatt_char(rx_char, packet, response=False)

        # send a message and wait for a response of a specific type
        async def send_request(
            message: BaseMessage, response_type: type[TMessage]
        ) -> TMessage:
            nonlocal pending_response
            pending_response = (response_type.ID, asyncio.Future())
            await send_message(message)
            return await pending_response[1]

        # first message should always be an info request
        # as the response contains important information about the hub
        # and how to communicate with it
        info_response = await send_request(InfoRequest(), InfoResponse)

        # enable device notifications
        notification_response = await send_request(
            DeviceNotificationRequest(DEVICE_NOTIFICATION_INTERVAL_MS),
            DeviceNotificationResponse,
        )
        if not notification_response.success:
            print("Error: failed to enable notifications")
            sys.exit(1)

        # clear the program in the example slot
        clear_response = await send_request(
            ClearSlotRequest(EXAMPLE_SLOT), ClearSlotResponse
        )
        if not clear_response.success:
            print(
                "ClearSlotRequest was not acknowledged. This could mean the slot was already empty, proceeding..."
            )

        # start a new file upload
        program_crc = crc(EXAMPLE_PROGRAM)
        start_upload_response = await send_request(
            StartFileUploadRequest("program.py", EXAMPLE_SLOT, program_crc),
            StartFileUploadResponse,
        )
        if not start_upload_response.success:
            print("Error: start file upload was not acknowledged")
            sys.exit(1)

        # transfer the program in chunks
        running_crc = 0
        for i in range(0, len(EXAMPLE_PROGRAM), info_response.max_chunk_size):
            chunk = EXAMPLE_PROGRAM[i : i + info_response.max_chunk_size]
            running_crc = crc(chunk, running_crc)
            chunk_response = await send_request(
                TransferChunkRequest(running_crc, chunk), TransferChunkResponse
            )
            if not chunk_response.success:
                print(f"Error: failed to transfer chunk {i}")
                sys.exit(1)

        # start the program
        start_program_response = await send_request(
            ProgramFlowRequest(stop=False, slot=EXAMPLE_SLOT), ProgramFlowResponse
        )
        if not start_program_response.success:
            print("Error: failed to start program")
            sys.exit(1)

        # wait for the user to stop the script or disconnect the hub
        # await stop_event.wait()

        async def handle_refresh():
            print("processing ... ")

            # start a new file upload
            program_crc = crc(EXAMPLE_PROGRAM)
            start_upload_response = await send_request(
                StartFileUploadRequest("program.py", EXAMPLE_SLOT, program_crc),
                StartFileUploadResponse,
            )
            if not start_upload_response.success:
                print("Error: start file upload was not acknowledged")
                sys.exit(1)

            # transfer the program in chunks
            running_crc = 0
            for i in range(0, len(EXAMPLE_PROGRAM), info_response.max_chunk_size):
                chunk = EXAMPLE_PROGRAM[i : i + info_response.max_chunk_size]
                running_crc = crc(chunk, running_crc)
                chunk_response = await send_request(
                    TransferChunkRequest(running_crc, chunk), TransferChunkResponse
                )
                if not chunk_response.success:
                    print(f"Error: failed to transfer chunk {i}")
                    sys.exit(1)

            # start the program
            start_program_response = await send_request(
                ProgramFlowRequest(stop=False, slot=EXAMPLE_SLOT), ProgramFlowResponse
            )
            if not start_program_response.success:
                print("Error: failed to start program")
                sys.exit(1)

        async def background_task():
            nonlocal refresh_requested
            nonlocal EXAMPLE_PROGRAM
            while True:
                refresh_requested, EXAMPLE_PROGRAM = send_http_request(SERVER_ADDRESS)

                print(refresh_requested,EXAMPLE_PROGRAM)
                if refresh_requested:
                    await handle_refresh()
                    refresh_requested = False  # Reset flag after refresh
                time.sleep(0.1)
                # await asyncio.sleep(1)  # Check for refresh request every second, keyboard mode

        # task = asyncio.create_task(background_task())

        # # Start listening for keyboard events (outside the loop)
        # def on_press(key):
        #     print(f"Key pressed: {key}")
        #     nonlocal refresh_requested
        #     nonlocal EXAMPLE_PROGRAM

        #     if key == Key.up:
        #         refresh_requested = True
        #         EXAMPLE_PROGRAM = (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_UP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')
        #     elif key.char == 's':
        #         refresh_requested = True
        #         EXAMPLE_PROGRAM = (EXAMPLE_PROGRAM_PREFIX  + EXAMPLE_PROGRAM_CORE_STOP + EXAMPLE_PROGRAM_SUBFIX).encode('utf8')

        # with Listener(on_press=on_press) as listener:
        #     await task  # Wait for background task to finish

        # await background_task()

        while True:
            refresh_requested, EXAMPLE_PROGRAM = send_http_request(SERVER_ADDRESS)

            print(f'{refresh_requested},{EXAMPLE_PROGRAM}')
            if refresh_requested:
                await handle_refresh()
                refresh_requested = False  # Reset flag after refresh
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")
        stop_event.set()
