# LAS Interface Software

The Atellica Solution's LAS-Driver communicates with the LAS using a uRAP-based protocol, which includes messages to support sample transfer between LAS and an Atellica Solution. The LAS communication is for exchanging system event and alert information, assay inventory status, and sample exchange messages.

# About LAS Communication Rules

The following are the general LAS communication rules (Page 82 About Establishing LAS Connection):

NOTE: The Atellica Solution uses a client-server model with the LAS acting as the client and the Atellica Solution acting as the server.

- Connection Made: When handshake messages exchange finishes, the communication connection occurs (Page 82 About Establishing LAS Connection).

- Keep Alive message transmission starts upon making connection.  
- Except for locked carrier knowledge, the Atellica Solution resets all other information when communication is lost.

NOTE: "Locked carrier" refers to an LAS pallet at an LAS buffer Interface Position where the LAS sends a LOAD-UNLOAD COMMAND message and the connected Atellica Solution does not respond with the appropriate message. The LAS does not release the pallet from the Interface Position (pallet is locked in position) because the Atellica Solution sample container robot can move at any time after the Atellica Solution sends LOAD-UNLOAD COMMAND message. Indexing (unlocking) the pallet before the Atellica Solution sends the appropriate message can cause loss of sample and other hazards.

- Until communication occurs, the LAS only sends handshake messages and the Atellica Solution responds. This ensures messages are exchanged in working state. Additionally, this allows either side to reset the connection when there is a connection loss by failing ACK/NACK responses.

- After connection occurs, the connection reset rules apply (Page 107 About LAS Connection Reset).

- The connection initialization step requires a series of message exchanges that the LAS initiates. After connection is initialized, sample routing and sample transfer can begin, and the Atellica Solution begins transmitting status updates unsolicited.

<table><tr><td>Initialization message</td><td>Notes</td></tr><tr><td>Clear Queue</td><td>Clear queue does not affect previously locked carrier.</td></tr><tr><td>Onboard Sample Info Request and Response</td><td>—</td></tr><tr><td>Instrument Health Request and Response</td><td>If the operator receives the Instrument Health Response with a lock the Atellica Solution owns, then unsolicited Load_Unload Command Response is required before connection initialization completes.</td></tr><tr><td>Test Inventory Request and Response</td><td>Solicited response contains full test inventory information.</td></tr><tr><td>Consumable Inventory Request and Response</td><td>Solicited response contains full consumable inventory information.</td></tr><tr><td>Transfer Status Request and Response</td><td>—</td></tr></table>

- While it is permitted for LAS to query the Atellica Solution for information during initialization, the LAS does not poll the Atellica Solution because the Atellica Solution generates unsolicited response message as Atellica Solution status updates occur and solicited response messages may slow sample transfer throughput.

- The Atellica Solution sends unsolicited responses when any changes occur.

NOTE: When LAS communication is initiated, the Atellica Solution does not accept any further initialization solicited requests. These solicited requests are NACKed with a Return Code of Message Type Not Supported (Refer to 0).

- In exception circumstances, if the LAS loses the test or consumable inventory data, the LAS resets connection to reestablish baseline.

- If the connection becomes ambiguous, disconnect and re-establish connection. For example, if a response to a command contains a mismatched barcode, the operator must reset the connection and re-baseline the connection.

- Only 1 interaction message can be active at a given time. Before the Atellica Solution sends the next command for Interface Position, the existing interaction must complete by response message and acknowledgment of response message. Only 1 of the following messages can be active per interface position:

- Load_Unload Command request

- Skip Command request

- The operator can send a message on Acknowledgment timeout, but cannot retry it if the response times out. If a response message times out, then the operator must reset connect.

Sample ID support:

- Maximum Length: 20 characters. LAS protocol messages supports 24 characters sent by LAS but the Atellica Solution does not accept samples with greater than 20 characters.  
Supports Alphanumeric  
- Supports standard 7-bit ASCII symbols (for example, "@#$%^&*(")". Sample ID should not start with & or % because these characters have special usage on an Atellica Solution.  
- Does NOT support non-printable characters or extended ASCII symbols (8-bit)  
Case sensitive

- Unsolicited Messages:

- Messages that are sent unsolicited:

<table><tr><td>Unsolicited messages</td><td>Notes</td></tr><tr><td>Keep Alive message</td><td>[either side]</td></tr><tr><td>Transfer Status message</td><td>[Atellica Solution to LAS]</td></tr><tr><td>Onboard Sample Info</td><td>[Atellica Solution to LAS]</td></tr><tr><td>Instrument Health</td><td>[Atellica Solution to LAS]</td></tr><tr><td>Test Inventory</td><td>[Atellica Solution to LAS]</td></tr><tr><td>Consumable Inventory</td><td>[Atellica Solution to LAS]</td></tr><tr><td>Load Unload Command Request messages</td><td>Load Unload Command Request messages have higher priority than unsolicited messages as they directly affect sample throughput.</td></tr><tr><td>Test Inventory</td><td>—</td></tr><tr><td>Consumable Inventory</td><td>—</td></tr><tr><td>Onboard Sample Info</td><td>—</td></tr><tr><td>Load Unload Command Response messages</td><td>Load Unload Command Response message have lower priority than unsolicited Instrument health messages to ensure that LAS is aware of the Atellica Solution health prior to lock release.</td></tr><tr><td>Keep Alive messages</td><td>(Page 110 About Keep Alive Messages).</td></tr><tr><td>Transfer Status Message</td><td>(Page 120 About Transfer Status Messages).</td></tr><tr><td>Onboard Sample Info</td><td>When the operator removes any LAS sample from the Atellica Solution without unloading it to the track, an unsolicited message displays.
This message displays when the Atellica Solution recognizes a positive sample loss event.</td></tr><tr><td>In case the operator removes a sample from the Atellica Solution and they cannot report the removal to the LAS, the operator is responsible to inform the LAS about the sample removal. The operator cannot report the information in the following conditions:
·If the connection between the Atellica Solution and the LAS is lost.
·If the sample containing the Atellica module is offline or not communicating.</td><td>—</td></tr><tr><td>Instrument Health Update on Status change</td><td>—</td></tr><tr><td>Unsolicited messages generated for following status changes:</td><td>—</td></tr><tr><td>LAS Interface Status</td><td>—</td></tr><tr><td>Instrument Process Status</td><td>—</td></tr><tr><td>Remote Control Status</td><td>—</td></tr><tr><td>LIS Connection Status</td><td>—</td></tr><tr><td>The frequency of these unsolicited response messages is gated to limit traffic.</td><td>—</td></tr><tr><td>A configurable delay between unsolicited Instrument Health Response messages is provided: (Default: 5 seconds; Range: 5–60 seconds).</td><td>—</td></tr><tr><td>Test Inventory Update on Status change.</td><td>—</td></tr><tr><td>During LAS connection initialization, the Atellica Solution transmits full test inventory in a single message.</td><td>—</td></tr><tr><td>The unsolicited message only contains the Test Inventory that has changed since the last response message transmission.</td><td>—</td></tr><tr><td>The Atellica Solution generates unsolicited messages on any reagent status change or reagent level change of the configurable step size:
• Default: 22 count
• Range: 5–100</td><td>A large number of reagents changing to Red or to Green from Red is an exception:
• Change in consumable availability.
• Atellica module becoming active.</td></tr><tr><td>The Atellica Solution gates the frequency of this unsolicited response message to limit traffic.</td><td>A configurable delay between unsolicited Test Inventory response messages:
• Default: 5 seconds
• Range: 5–60 seconds</td></tr><tr><td>Consumable Inventory Update on Status change.</td><td>—</td></tr><tr><td>During LAS connection initialization, the Atellica Solution transmits full consumable inventory in a single message.</td><td>—</td></tr><tr><td>The unsolicited message only contains the Consumable Inventory that has changed since last response message transmission.</td><td>—</td></tr><tr><td>The Atellica Solution generates unsolicited messages for any consumable status change.</td><td>A large number of consumables changing to Red or to Green from Red is an exception:
• Change in consumable availability.
• Atellica Module becoming active.</td></tr></table>

NOTE: If the Atellica Solution receives a request or response message with an invalid value, the message is Nacked.

- The message exchange can be nested, overlapped, or both.  
- The operator cannot issue multiple commands on a sample interface gate pallet.

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/04c1a80080a16341daad4716c700a4da0d535bba0c79aa0de54c2172e41bbe0b.jpg)

# About uRAP Protocol Primitives

All uRAP messages are in a uRAP protocol Header & Footer. Transportation protocol is not part of the uRAP protocol Header & Footer.

# About Field Length

A Field Length byte (1 byte) prefixes a dynamic length byte field (ASCII string field), such as sample ID. When a given field length value is  $0 \times 00$ , the dynamic length byte field is not present. The maximum value of the field length is  $0 \times FF$ .

# Headers

<table><tr><td>Header format</td><td>Size (bytes)</td></tr><tr><td>Start Signature</td><td>1</td></tr><tr><td>Message Length</td><td>2</td></tr><tr><td>Sequence ID</td><td>2</td></tr><tr><td>Return Sequence ID</td><td>2</td></tr><tr><td>Message Type</td><td>2</td></tr><tr><td>Time Stamp</td><td>8</td></tr><tr><td>Instrument ID</td><td>1</td></tr></table>

# About Start Signatures

The Header starts with an <stx> byte. This value, which is the standard starting byte value for most serial communication protocols, is present regardless of the employed transport mechanism.

NOTE: When the Atellica Solution employs serial communication as the transport mechanism, the <stx> byte appears twice in each message. The application layer inserts 1 instance of the byte, and the transport layer inserts the other instance.

# About Message Length

The message length specifies the number of bytes in the entire message, including the header and footer. The message length does not include any header or footer bytes added by the transport layer.

# About Sequence ID

The sequence ID is a unique identifier for ordering and keeping track of the messages. Each sender, such as the Atellica Solution and the LAS, performs their own sequence ID counter.

The sequence ID starts at 1, and the sequence ID of  $0 \times 0000$  is reserved for use in Return Sequence ID. When sequence ID reaches maximum value (0xFFFF), it is rolled over to  $0 \times 0001$ . The Atellica Solution resets the sequence ID value upon successful handshake.

# About Return Sequence ID

The return sequence ID indicates if the message is a response message or an unsolicited message. If the return sequence ID is empty (0x0000), then the message is an unsolicited message. If the return Sequence ID is occupied with a non-zero sequence ID, then the message is a response message. The operator must set the return sequence ID to the sequence ID of the received message when it is a response or ACK/NACK message.

# About Message Types

The message type is a 2-byte binary code to indicate which type of command or response message it is.

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/c164fc9da73c9cec49d46fae2b48b8f5ad8b75ffa0347f033c0174565c3929bc.jpg)  
About Time Stamps

The timestamp shows message origination date and time using local date and time. The bytes are arranged in format of largest gradient of time to smallest for sorting purposes. The custom format arrangement maintains neutrality to any system date and time format of any operating system and programming language. The baseline time is January 1st, 2000. If the operator cannot set the time, they must set the value to the following: Year: 0, Month: 1, Day: 1, Hour: 0, Minute: 0, Second: 0, Millisecond: 0.

# About Instrument ID

The instrument ID is an enumerated number for the device on a communication network (Page 84 About Handshake Messages).

Footers  

<table><tr><td>Parameter</td><td>Size (bytes)</td></tr><tr><td>Checksum</td><td>2</td></tr><tr><td>End Signature</td><td>1</td></tr></table>

# About Checksums

The checksum field is always present, even if the transport layer protocol has its own checksum. This requirement follows from the goal of making the URAP application layer independent of the transport layer.

The Atellica Solution calculates the checksum value from uRAP header and message body (not including the footer section). The algorithm is a binary sum, formatted as the ASCII representation of its hexadecimal value (modulo 256) in 2 digits with leading zeroes, a range of 00-FF.

# About End Signatures

The Footer ends with an <ctx> byte. This value, which is the standard ending byte value for most serial communication protocols, is present regardless of the employed transport mechanism.

NOTE: When the Atellica Solution employs serial communication, the transport mechanism, the byte appears twice in each message. The application layer inserts 1 instance of the byte, and the transport layer inserts the other instance.

# About Establishing LAS Connection

To establish a connection, the client-server model uses the Atellica Solution as the server and the LAS as the client. When the Atellica Solution powers on and initializes its software, it enters into listening mode and monitors the LAS communication port for handshake message.

The LAS as client is responsible for initiating the handshake message exchange. The Atellica Solution responds with an acknowledgment message to the LAS handshake request and replies with a handshake response message. The LAS considers the connection complete when it receives the handshake response message from the Atellica Solution. The Atellica Solution considers the connection complete when it receives acknowledgment for its handshake message from the LAS.

NOTE: The operator can send Initialization Request messages in any order. If the Instrument Health Response reports 1 or more, the Atellica Solution locks the IP and the LAS must wait for respective IP's unsolicited response or responses to complete Connection Initialization. The Atellica Solution waits for acknowledgment for those responses to complete Connection Initialization.

The LAS waits a maximum of 600 seconds for a Load_Unload response message.

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/0ba98833821d35b29a4f5305924c7cad8710282fd047c5be6f74d5eb08a90ce8.jpg)

# Serial Port Settings

LAS communication uses the serial port. The following settings define available configuration values and respective default configuration values:

<table><tr><td>Connection parameter</td><td>Valid values</td><td>Default value</td></tr><tr><td rowspan="4">Com port</td><td>COM1</td><td rowspan="4">Hardware Specific</td></tr><tr><td>COM2</td></tr><tr><td>COM3</td></tr><tr><td>COM4</td></tr><tr><td>Baud rate</td><td>9600, 19200, 38400, 57600, 115200</td><td>57600</td></tr><tr><td>Flow control</td><td>None</td><td>None [uRAP module does not use Flow Control for a serial connection]</td></tr><tr><td>Parity</td><td>None, Odd, Even, Mark, Space</td><td>None</td></tr><tr><td>Data bits</td><td>7, 8</td><td>8</td></tr><tr><td>Stop bits</td><td>1, 2</td><td>1</td></tr></table>

# About Handshake Messages

The handshake message does not follow a typical request or response message pair format. Single message format exists for use by the LAS and Atellica Solution.

<table><tr><td>Header</td><td>Protocol Version (2 Bytes)</td><td>Instrument Type (2 Bytes)</td><td>Capability Version (2 Bytes)</td><td>Software Version (2 Bytes)</td><td>Instrument ID (1 Byte)</td><td>F L</td><td>Instrument Serial # (n Bytes)</td><td>Footer</td></tr><tr><td colspan="4">Handshake message format and values</td><td colspan="5">Notes</td></tr><tr><td colspan="4">Message Direction</td><td colspan="5">Bi-Directional</td></tr><tr><td colspan="4">Message Type</td><td colspan="5">0x0001</td></tr><tr><td colspan="4">Protocol Version</td><td colspan="5">The uRAP protocol version is divided: 
• High Byte: Major Version 
• Low Byte: Minor Version</td></tr><tr><td colspan="4">Instrument Type</td><td colspan="5">The enumeration of the instrument types.</td></tr><tr><td colspan="4">Implemented Capability</td><td colspan="5">The enumeration of the capabilities of the instrument or automation system using this protocol version: 
• High Byte: Capability (for example, Core = 0x01, Enhanced = 0x02, Advanced = 0x03, and so on)</td></tr><tr><td colspan="4">Handshake message format and values</td><td colspan="5">Notes</td></tr><tr><td>Software Version</td><td colspan="8">The software version is filled with 0xFFFF.</td></tr><tr><td>Instrument ID</td><td colspan="8">The Atellica Solution and the LAS utilize FFh to indicate Instrument ID.</td></tr><tr><td>Instrument serial #</td><td colspan="8">The instrument serial # is for verification of the instrument.</td></tr></table>

The following specific implementation adjustments apply to simplify handshaking:

- The Atellica Solution uses Software Version number 1.0.  
- The Atellica Solution uses 0xFFh and Instrument ID is disabled.  
- Instrument Serial # is fixed, and automation does not transmit the expected serial number.

NOTE: Handshake Messages is NACKed if the operator uses invalid parameters.

<table><tr><td>Handshake</td><td>Used by</td><td>Fixed values</td></tr><tr><td>Protocol version</td><td>Both</td><td>0x0330h</td></tr><tr><td>Instrument type</td><td>Both</td><td>Instrument = 0x0001h
LAS = 0x0000h</td></tr><tr><td>Implemented capability version</td><td>Both</td><td>0x0104h</td></tr><tr><td>Software version</td><td>LAS</td><td>0xFFFFFFh</td></tr><tr><td>Software version</td><td>Instrument</td><td>0x0100h</td></tr><tr><td>Instrument ID</td><td>Both</td><td>0xFFh</td></tr><tr><td>Instrument serial #</td><td>Both</td><td>FL set to 8. &quot;ATELLICA&quot;</td></tr></table>

<table><tr><td>Handshake message configuration item</td><td>Default values</td></tr><tr><td>Handshake Retry Period</td><td>30 seconds (range 10–300)</td></tr><tr><td>Handshake Response Timeout</td><td>20 second (range 2–60)</td></tr><tr><td>Wait Period Prior to Initiating Handshake (LAS)</td><td>30 seconds (range 10–600)</td></tr><tr><td>Wait Period Prior to Entering Listening Mode</td><td>15 seconds (range 10–600)</td></tr><tr><td>Wait Period to complete initialization sequence after Handshake (LAS)</td><td>30 seconds (range 10–600)</td></tr></table>

# Acknowledgment Message

The Atellica Solution sends a Message Acknowledgment (ACK/NACK) is sent upon each message it receives. The ACK/NACK message uses 0x0000 as the message type:

<table><tr><td>Header</td><td>Return Code (1 Byte)</td><td>Footer</td></tr></table>

Where Return Code may be 1 of the following values:

<table><tr><td>Acceptance state</td><td>ACK/NACK</td><td>Value (Hex)</td><td>Usage</td></tr><tr><td rowspan="3">Message Understood &amp; Accepted</td><td rowspan="3">ACK</td><td rowspan="3">0x00</td><td>• Properly formed Atelica Interface Specification message.</td></tr><tr><td>• Request messages received during connection initialization.</td></tr><tr><td>• Non request message received after connection initialization.</td></tr><tr><td>Message Not Understood</td><td>NACK</td><td>0x01</td><td>• Message contains unexpected enumeration.
• Illegal composition of message fields such as mismatched field data.
- Example 1: Number of test inventory do not match actual inventory data.
- Example 2: If carrier occupancy do not match with barcode entry.
- Example 3: Message type is known but internal field does not match with known message structure.</td></tr><tr><td>Message Type Not Supported</td><td>NACK</td><td>0x03</td><td>• Any message the Atelica Solution receives prior to handshake.
• Request message after connection initialization.
• Any message that the Atelica Interface Specification does not support.</td></tr></table>

# About Initializing the LAS Connection

After the systems exchange and ACK handshake messages, the LAS sends the following 6 requests to initialize the connection:

- Clear Queue Command Message

- This message explicitly clears any previous queue in the Atellica Solution memory. However, any previously locked carriers are not cleared by this message.  
- Onboard Sample Info Request Message

- Instrument Health Request Message

- In the response message, if the LAS Interface Status is Critical (0x04), the LAS does not move any pallets in the LAS buffer as the Atellica Magline Transport mechanism or mechanisms may be obstructing the pallet or sample container travel path (Page 97 About Automation Interface Status: Critical).

- If the LAS owns the Instrument Health Response with a lock the Atellica Solution owns, then an unsolicited Load_Unload Command Response is required before connection initialization can complete.

- Test Inventory Request Message

- Any solicited Reagent Inventory response message include full reagent inventory information.

- Any unsolicited reagent inventory response messages only include changes from previous response message (Page 73 About LAS Communication Rules).

- Consumable Inventory Request Message

- A solicited Consumable Inventory response message includes full consumable inventory information.

- An unsolicited Consumable Inventory response message only includes changes from the most recent response message (Page 73 About LAS Communication Rules).

- Transfer Status Request Message

- A Transfer Status Request or Response exists for each interface position (IP0 and IP1).

After handshake messages are exchanged and ACK'd, the LAS waits for the following message to make sure the initialization is complete:

- Initialization Sequence Complete Message

- This unsolicited Initialization Sequence Complete message indicates the completion of all message exchanges.

The Atellica Solution does not transmit unsolicited messages until the LAS connection initializes. However, even after initializing the connection, carrier routing does not occur if following conditions are not met:

Loaded carrier routing  

<table><tr><td>Element</td><td>Condition</td></tr><tr><td>Test inventory</td><td>At least 1 assay with usable test count</td></tr><tr><td>Instrument health – automation interface status</td><td>Green (Can transfer sample tubes)</td></tr><tr><td>Instrument health – instrument process status</td><td>Green (Can process sample)</td></tr><tr><td>Instrument health – LIS Connection status</td><td>Connected</td></tr><tr><td>Instrument health – remote control status</td><td>IP0: Exchange Mode</td></tr><tr><td>Instrument health – remote control status (SHC)</td><td>IP0: Loading Only ModeIP1: Unloading Only Mode</td></tr><tr><td colspan="2">Empty carrier routing</td></tr><tr><td>Element</td><td>Condition</td></tr><tr><td>Instrument health – automation interface status</td><td>Green (Can transfer sample tubes)</td></tr><tr><td>Instrument health – remote control status</td><td>IP0: Exchange ModeorIP0: Unloading Only Mode</td></tr><tr><td>Instrument health – remote control status (SHC)</td><td>IP0: Loading Only ModeIP1: Unloading Only ModeorIP0: OfflineIP1: Unloading Only Mode</td></tr></table>

The LAS must wait for all conditions to be met. The Atellica Solution sends unsolicited messages when its status changes.

# Instrument Health Message

The Instrument Health Message informs the LAS about the condition (readiness) of the Atellica Solution and allows the LAS to make routing decisions. The Atellica Solution sends this data to the LAS in the Instrument Health Response message after receiving an Instrument Health Request message from the LAS. The Atellica Solution sends an unsolicited Instrument Health Response if any of the data values change.

NOTE: Atellica module identifiers (module serial numbers) do not include the following characters:  $\wedge |$  ;

<table><tr><td>Header</td><td>Footer</td><td></td><td></td><td></td><td></td></tr><tr><td>Instrument Health
Request message</td><td colspan="5">Notes</td></tr><tr><td>Message direction</td><td colspan="5">LAS to Atellica Solution</td></tr><tr><td>Message type</td><td colspan="5">0x0201</td></tr><tr><td>Header</td><td>Automation Interface
Status (1 Byte)</td><td>Instrument Process
Status (1 Byte)</td><td>LIS Connection Status
(1 Byte)</td><td></td><td></td></tr><tr><td>Interface Positions
(1 Bytes)</td><td>First Remote Control
Status (1 Bytes)</td><td>First Lock Ownership
(1 Bytes)</td><td>---</td><td>Last Remote Control
Status (1 Bytes)</td><td>Last Lock Ownership
(1 Bytes)</td></tr><tr><td>Processing Backlog
(2 Bytes)</td><td>Sample Acquisition
Delay
(2 Bytes)</td><td>On Board Tube Count
(2 Byte)</td><td>Completed Tube Count
(2 Byte)</td><td>Footer</td><td></td></tr></table>

<table><tr><td>Instrument Health Response message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>Atellica Solution to LAS.</td></tr><tr><td>Usage</td><td>The Atellica Solution replies with LAS interface, Atellica Solution, Remote Control Status, and other parameters.</td></tr><tr><td>Message Type</td><td>0x0202.</td></tr></table>

<table><tr><td>Instrument Health Response message</td><td>Notes</td></tr><tr><td>Automation Interface Status (Page 97 About Automation Interface Status: Critical).</td><td>A software component monitors and controls the Transfer Arm and Transfer Vessel state. The Atellica Solution reports the status of the Transfer Arm and the Transfer Vessel to the LAS to indicate if the interface to the LAS is usable. Sample processing is only possible if the Transfer Arm and the Transfer Vessel are in working condition. Interference by the Transfer Arm may block pallet flow through the LAS buffer (Page 97 About Automation Interface Status: Critical).The Atellica Solution reports the Automation Interface Status in the following conditions:0x01 - Green: Transfer mechanism is fully functional and is not interfering with Track.0x03 - Red: Transfer mechanism is not functional and is not interfering with Track.Track Carrier can not move functional and is interfering with Track. Operator or Service intervention required.</td></tr><tr><td>Instrument Process Status</td><td>Message to report the process status of the Atellica Solution. For this status, the following is considered:NOTE: The LAS cannot change the Atellica Solution status using uRAP commands. Events within the Atellica Solution automatically trigger the status changes, such as start up, shutdown, consumption of consumables, or error conditions.0x01 - Green: The Atellica Solution can process samples and has sufficient reagents and consumables.0x02 - Yellow: One or more analyzer modules in the system configuration is not processing samples.0x03 - Red: The Atellica Solution cannot process because of an error state or vital consumable depleted.</td></tr></table>

<table><tr><td>Instrument Health Response message</td><td>Notes</td></tr><tr><td>Affected Modules Count</td><td>When instrument processing status is Yellow or Red, the operator must provide the module and the reason for its unavailability. This field reports the number of modules currently not available. The maximum number of supported analyzers in the deployment is 7 as per the Atellica architecture.</td></tr><tr><td>Module ID</td><td>Affected Analytical Module's Serial Number. The maximum number of characters in the serial number is 15.</td></tr><tr><td>Module Not Available Reason</td><td>The reason that the Atellica Solution is not available. The system reports the following prioritized causes to the LAS: 
0x01 – Operator initiated activity 
0x02 – Consumable not available 
• A consumable or supply is not available. 
0x03 – Empty waste bin 
• The operator must change the waste bin due to a continuous test. 
0x04 – Initiate weekly maintenance 
• The operator must initiate maintenance activities due to an internal system behavior. 
0x05 – Maintenance in progress 
0x06 – Hardware error 
• The Atellica Solution has encountered a hardware error, such as a probe error. 
0x07 – Magline error 
• Overall status is Yellow or Red due to the Atellica Magline status. 
0xFF – Software Error 
• Default message if the error does not map to any of the defined causes.</td></tr><tr><td>LIS Connection Status</td><td>Message to report the current LIS connection status. The LIS connection status indicates the ability the Atellica Solution to download orders from the LIS. When the LIS is disconnected, then automation does not divert sample tubes to the Atellica Solution.
• 0x01 – Connected
• 0x02 – Disconnected</td></tr><tr><td>Interface Positions</td><td>The count of interface positions. 
SHC uses value 2. 
For each interface position, there is Remote Control Status and Lock Ownership.</td></tr><tr><td>Remote Control Status (Active Configuration of Interface Positions)</td><td>Remote control status indicates if each interface position accepts samples from LAS. NOTE: Interface Position Array starts directly behind the divert gate.The Atellica Solution returns the Remote Control Status in a single byte for each interface position in the LAS buffer. The preceding Field Length indicates the number of Interface positions. Interface Position 0 (IP0) is closest to sample entry position of LAS buffer.
·0x01 – Offline or Local Mode:
Operator or system logic has Automation Interface offline and does not accept samples from the LAS.
·0x03 – Online Exchange Mode
·0x04 – Online Loading Only Mode
·0x05 – Online Unloading Only Mode
NOTE: The Atellica Solution does not use all enumeration values per instance of system connection (Page 96 About Remote Control Status).The operator determines the Remote Control Status configuration based on the state of the SHC. The SHC can be 1 of the following states:
·Online
·Offline
·Processing
·Diagnostics</td></tr></table>

<table><tr><td>Instrument Health Response message</td><td>Notes</td><td></td></tr><tr><td rowspan="2">Lock Ownership</td><td colspan="2">This field is for initializing connection. Upon each connection, LAS refreshes Lock Ownership from the Atellica Solution.For example, if the connection drops after the LAS has transmits a Load_Unload Command Request without receiving an ACK response, then it is ambiguous if the lock is currently owned by the Atellica Solution.0x01 - Locked by Instrument如果是01,则不能释放Carrier如果处于Ini,则需要等Load_Unload解锁</td></tr><tr><td colspan="2">0x02 - Not Locked by InstrumentNOTE: During LAS communication initialization, if the Lock Ownership status is 0x01 - Locked by Instrument for any Interface Position, then LAS communication is not initialized until the LAS receives an unsolicited Load_Unload Command Response message for all locked positions.After LAS communication initialization, the LAS does not request Lock Ownership status.</td></tr><tr><td>Processing Backlog</td><td colspan="2">Not Applicable: The field exists in the message, but the values are unusable.The Atellica Solution populates this field with 0xFFFFh.</td></tr><tr><td>Sample Acquisition Delay</td><td colspan="2">Not Applicable: The field exists in the message, but the values is not utilized. The Atellica Solution populates this field with 0xFFFFh.</td></tr><tr><td>On Board Tube Count</td><td colspan="2">Number of tubes onboard from the LAS.</td></tr><tr><td>Completed Tube Count</td><td colspan="2">Number of tube onboard ready to be return to the LAS.</td></tr><tr><td></td><td>Configuration items</td><td>Default values</td></tr><tr><td></td><td>Instrument Health ResponseTimeout</td><td>20 second (range 2-60)</td></tr></table>

# About Remote Control Status

The Remote Control Status field of the Instrument Health Response message describes interface position's current active mode. In the Atellica Solution, the SHC is the 1 interfacing system.

NOTE: The Remote Control Status value usage may differ depending on the capability.

The SHC has 2 Interface Positions: IPO and IP1. The operator typically uses IPO to load pallets from the LAS buffer onto an empty Atellica Magline Transport on the system. The operator typically uses IP1 to unload sample carriers from the Atellica Solution back to the LAS.

<table><tr><td>Supported remote control by mode of implementation</td><td>Usable values</td></tr><tr><td>SHC
(Interface Position 0)</td><td>0x01: Offline or Local
0x04: Online Loading Only Mode</td></tr><tr><td>SHC
(Interface Position 1)</td><td>0x01: Offline or Local
0x05: Online Unloading Only Mode</td></tr></table>

<table><tr><td>DC supported status detail</td><td>Notes</td></tr><tr><td>IPO: Offline</td><td>When the Atellica Solution is configured to not process LAS samples and only process front loaded samples, IPO is set to Offline.</td></tr><tr><td>IPO: Exchange</td><td>When the Atellica Solution accepts LAS samples normally, IPO is set to Exchange.</td></tr><tr><td>IPO: Unloading Only</td><td>The Atellica Solution mode may change to return all LAS samples and not process any additional LAS samples.
In this case, IPO is set to Unloading Only.</td></tr></table>

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/31b7f5b626d884f44eb9a5b0115b94dae1cc79c7d5aad7e5730a9bb6a3f53144.jpg)  
SHC state transitions

<table><tr><td>SHC supported status detail</td><td>Description</td></tr><tr><td>IP0: Offline</td><td rowspan="2">When the Atellica Solution is configured to process front-loaded samples in place of LAS samples, IPO and IP1 are set to Offline.</td></tr><tr><td>IP1: Offline</td></tr><tr><td>IP0: Loading Only</td><td rowspan="2">When the Atellica Solution accepts LAS samples, IPO is set to Loading Only and IP1 is set to Unloading Only.</td></tr><tr><td>IP1: Unloading Only</td></tr><tr><td></td><td>Initially, when the Atellica Solution is loading samples from the LAS and has no samples to unload, &quot;Excess empty puck is cycled out of IP1 by Instrument&quot; is displayed.</td></tr><tr><td>IP0: Offline</td><td rowspan="2">The Atellica Solution mode may change to return all LAS samples and not process any additional LAS samples.</td></tr><tr><td>IP1: Unloading Only</td></tr><tr><td></td><td>In this case, IPO is set to Offline and IP1 is set to Unloading Only.</td></tr></table>

# About Automation Interface Status: Critical

At times, the transport mechanism can fail because of a power outage or a motor jam. This obstructs the LAS pallet travel path. In these cases, it becomes necessary to halt the SHC modules and the LAS buffer and, alert the operator for error recovery to reduce the chance of contamination and loss of sample.

When the Atellica Solution recognizes this condition, it halts all its movement and sends an unsolicited Instrument Health Response.

Automation interface status is set to Critical to report to the operator via its primary UI.

Except during initialization, the LAS does not send Clear Queue Command Request when the Automation interface status is Critical. During initialization, the sending of this message by the LAS is dependent on the automation interface status.

When the transport mechanism becomes usable or it does not obstruct the LAS pallet travel path, the Atellica Solution sends an unsolicited Instrument Health Response with the LAS interface status other than Critical.

The LAS may send the clear queue message for both interfaces and rebuild the logical queue by sending Add Queue commands- (in the order of the carriers that are physically in the queue) after it receives an Automation interface status other than Critical.

In establishing a connection, if the LAS receives a first Instrument Health Response message with:

- Automation Interface Status of Critical, the LAS does not move any pallets and waits for another Instrument Health response message with Automation interface status other than Critical.  
- Lock Ownership status of Locked by Instrument, the LAS does not move any pallets and waits for a Load_Unload Command Response with Load Command Status not 0x02 and Unload Command Status not 0x02.

备注：Load_Unload Command Message :

02=error performing Load command(Lock Carrier in place)

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/260a67fab45209a80f31cce769f33679932f273ece8d1b5e7e1105812158adc5.jpg)

# About Test Inventory Messages

Test Inventory messages inform the LAS about the assay portfolio and test availability (test counts) on the Atellica Solution. During Connection Initialization, the Atellica Solution sends the complete test inventory to the LAS via the Test Inventory Response message after receiving a Test Inventory Request message from automation. Automation can request complete test inventory only during connection initialization. The Atellica Solution periodically sends unsolicited updates that contain only those tests with status that have changed (Page 73 About LAS Communication Rules).

The response message contains only immediately usable test counts.

<table><tr><td>Header</td><td>Footer</td></tr></table>

<table><tr><td>Test inventory request message</td><td>Notes</td></tr><tr><td>Message direction</td><td>LAS to Atellica Solution</td></tr><tr><td>Message type</td><td>0x0203</td></tr></table>

<table><tr><td>Header</td><td colspan="2">Test Inventory Count (2 Bytes)</td><td>F L</td><td colspan="2">First Assay Name (n Bytes)</td><td colspan="2">First Usable Test Count (2 Bytes)</td><td colspan="2">First Assay Status (1 Byte)</td></tr><tr><td></td><td>F L</td><td colspan="3">Last Assay Name (n Bytes)</td><td colspan="2">Last Usable Test Count (2 Bytes)</td><td colspan="2">Last Assay Status (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Reagent inventory response message</td><td>Notes</td></tr><tr><td>Message direction</td><td>Atellica Solution to LAS</td></tr><tr><td>Usage</td><td>The Atellica Solution sends a message upon request or sends it unsolicited to indicate a change in reagent status.
If responding to a Test Inventory Request, the Atellica Solution replies with reagent level for all active assays. Only reagent levels that have changed since the last response are included in unsolicited responses.</td></tr><tr><td>Message type</td><td>0x204.</td></tr><tr><td>Test inventory count</td><td>Number of test inventory counts in the message. This is the total number of tests on the Atellica Solution that are usable. [Maximum Size: 500].</td></tr><tr><td>Assay name</td><td>Assay Name in ASCII string. This matches the test code used in the LIS test order. [Maximum Length: 10]. NOTE: The Atellica Solution only reports assays that are part of the Atellica Solution test map.</td></tr><tr><td>Usable Test Count</td><td>Calculation of usable tests for the assay. To be usable, the Atellica Solution must enable, calibrate, and QC the test and have consumables to perform these tests. The Atellica Solution reports test counts per assay, not per reagent. The test count of an assay is dependent on the reagent with the lowest level. Typically, the Atellica Solution calculates the test count as follows: The available reagent volume and the required reagent volume is equal to the assay test count.</td></tr><tr><td rowspan="4">Assay status</td><td>0x01 – Green: Usable Test Count of Assay ≥ Threshold.</td></tr><tr><td colspan="1">0x02 – Yellow: Usable Test Count of Assay &lt; Threshold.</td></tr><tr><td colspan="1">0x03 – Red: Usable Test Count of Assay = 0.</td></tr><tr><td colspan="1">The Threshold value between Green and Yellow is configurable per assay on the Atellica Solution (Default: 10, Range: 1–999).</td></tr></table>

The LAS can retry the Test Inventory Request if the system does not receive the response after a configurable timeout period. The default value for the Test Inventory Response Timeout is 20 seconds, with a range from 2-60 seconds.

# About Onboard Sample Info Messages

The Onboard Sample Info message synchronizes knowledge of the list of sample tubes that the LAS delivers to the Atellica Solution. The message includes a list of sample IDs that the LAS loads the Atellica Solution and a list of sample IDs the LAS loads and removes from the Atellica Solution, but does not unload to the track.

During connection initialization, the LAS sends an Onboard Sample Info Query to synchronize the onboard sample tube information between the LAS and the Atellica Solution.

If the Atellica Solution loses custody of a delivered tube because the operator removes it or a system malfunction occurs, the Atellica Solution sends an unsolicited Onboard Sample Info Response.

NOTE: If the Atellica Solution loses custody of a delivered tube, the LAS must remove the removed sample tube from its database so that if the operator re-introduces the sample tube to LAS, the Atellica Solution does not declare it as a duplicate sample.

Header

Footer

<table><tr><td colspan="4">Onboard sample info request</td><td colspan="4">Notes</td></tr><tr><td colspan="4">message direction</td><td colspan="4">LAS to Atellica Solution</td></tr><tr><td colspan="4">Message type</td><td colspan="4">0x0207</td></tr><tr><td>Header</td><td>Onboard Sample Count (2 Bytes)</td><td>F L</td><td>First Onboard Sample ID (n Bytes)</td><td>F L</td><td colspan="3">Last Onboard Sample ID (n Bytes)</td></tr><tr><td></td><td colspan="2">Removed Sample Count (2 Bytes)</td><td>F L</td><td>First Removed Sample ID (n Bytes)</td><td>F L</td><td>Last Removed Sample ID (n Bytes)</td><td>Footer</td></tr><tr><td colspan="4">Onboard sample info response message</td><td colspan="4">Notes</td></tr><tr><td colspan="4">Message direction</td><td colspan="4">Atellica Solution to LAS</td></tr><tr><td colspan="4">Usage</td><td colspan="4">Message is sent upon request or is sent unsolicited to indicate a sample removal.</td></tr><tr><td colspan="4">Message type</td><td colspan="4">0x208</td></tr><tr><td colspan="4">Onboard Sample Count</td><td colspan="4">Number of sample tubes that the LAS has loaded on the Atellica Solution. [Maximum Count: 90].</td></tr><tr><td colspan="4">Onboard Sample ID</td><td colspan="4">Zero or more Onboard Sample IDs in ASCII string. [Maximum Length: 24].NOTE: This sample ID is same sample ID the Atellica Solution uses during sample loading. The Atellica Solution accepts sample ID up to length 20.</td></tr><tr><td colspan="4">Removed Sample Count</td><td colspan="4">Number of sample tubes that the LAS has loaded and removed since the last update and are not returned to the track. [Maximum Count: 90].</td></tr><tr><td colspan="4">Onboard sample info response message</td><td colspan="4">Notes</td></tr><tr><td>Removed Sample ID</td><td colspan="7">Zero or more Removed Sample IDs in ASCII string. 
[Maximum Length: 24]. 
NOTE: This sample ID is same sample ID the Atellica Solution uses during sample loading. The Atellica Solution accepts sample ID up to length 20.</td></tr></table>

The LAS can retry the Onboard Sample Request if the LAS does not receive the response from the Atellica Solution after a configurable timeout period. The default value for the Onboard Sample Request is 20 seconds, with a range from 2-60 seconds.

# About Consumable Inventory Messages

The Consumable Inventory provides the operator and the LAS with additional statuses on Atellica Solution readiness to conduct specific assays. When the LAS requests the consumable inventory, the Atellica Solution responds with inventory for all active consumables. When the Atellica Solution sends an unsolicited consumable inventory response message, it only sends only the consumables that have a changed value since last transmission. After resetting communications, the Atellica Solution performs as if it did not send any previous reagent inventory. The system sends a complete inventory after a communications restore. For example, during Connection Initialization, the LAS sends a Consumable Inventory Request message and the Atellica Solution sends a complete Consumable Inventory. The LAS can request complete consumable inventory only during connection initialization. The Atellica Solution periodically sends unsolicited updates that contain only those consumables with a changed status.

The response message contains only immediately usable consumables based on the status.

Consumable Inventory Request Message:

<table><tr><td>Header</td><td>Footer</td></tr></table>

<table><tr><td>Message info</td><td>Notes</td></tr><tr><td>Message direction</td><td>LAS to Atellica Solution</td></tr><tr><td>Message type</td><td>0x020B</td></tr></table>

Consumable Inventory Response Message:  

<table><tr><td>Header</td><td colspan="2">Module Count (1 Byte)</td><td>F L</td><td colspan="2">First Module Identifier (n Bytes)</td><td colspan="2">Number of Consumables Reported (1 Byte)</td><td colspan="2">First Consumable Identifier(1 Byte)</td><td>First Consumable Status (1 Byte)</td></tr><tr><td>...</td><td colspan="2">Last Consumable Identifier (1 Byte)</td><td colspan="2">Last Consumable Status (1 Byte)</td><td>...</td><td>F L</td><td colspan="2">Last Module Identifier (n Bytes)</td><td colspan="2">Number of Consumable Reported (1 Byte)</td></tr><tr><td colspan="2">First Consumable Identifier (1 Byte)</td><td colspan="2">First Consumable Status (1 Byte)</td><td colspan="2">...</td><td colspan="2">Last Consumable Identifier (1 Byte)</td><td colspan="2">Last Consumable Status (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Message Info</td><td>Notes</td></tr><tr><td>Message Direction</td><td>Atellica Solution to LAS.</td></tr><tr><td>Usage</td><td>·The system sends a message upon request.
·Instrument replies with consumable status for all consumables.
·LAS has a view on the overall consumabale data for a particular module using this message. The message facilitates the individual consumable status.</td></tr><tr><td>Message Type</td><td>0x020C</td></tr><tr><td>Module Count</td><td>Number of modules or instruments connected to the Atellica Solution. Maximum number of supported analyzers in the deployment is 7 as per the Atellica architecture.</td></tr><tr><td rowspan="2">Module Identifier</td><td>Analytical module's serial number.</td></tr><tr><td>Maximum number of characters in the serial number is 15.</td></tr><tr><td>Consumable Reported count</td><td>Number of consumables with its name and status. Maximum number of consumables per module is 18.</td></tr><tr><td>Consumable Identifier</td><td>0x01 – CH Cleaner
0x02 - CH Conditioner
0x03 – CH Wash
0x04 – CH Diluent
0x05 – Pretreatment
0x11 – IMT Std B + salt Bridge
0x12 – IMT Standard A
0x13 – IMT Diluent
0x14 – A- LYTE Multisensor
0x21 - IM Acid
0x22 – IM Base
0x23 - IM Cleaner
0x24 - IM Wash
0x25 - Tips
0x26 - Cuvettes
0x27 – Water
0x28 – Cuvette and Tips waste
0x29 – Tip Tray waste</td></tr><tr><td>Consumable Status</td><td>0x01 – Green: Consumables are in an acceptable state.
0x02 – Yellow: Consumable level low or consumable expires soon (for example, within the next hour).
0x03 – Red: Consumable expired or consumable depleted.</td></tr></table>

The LAS can retry the Consumable Inventory Request if the response from the analyzer is not received after a configurable timeout period of 2-6-seconds (default 20).

# About Initialization Sequence Completed Messages

The Initialization Sequence Completed message notifies the LAS that the 6 messages in (Page 87 About Initializing the LAS Connection) are complete. The LAS initiates the sample/carrier routing requests when it receives this message. This is an unsolicited message without any request. After sending Acknowledgement of the analyzer's Handshake message, the LAS starts a timer indicating the start of the Initialization Sequence.

Initialization Completed Message:

<table><tr><td>Header</td><td>Footer</td></tr></table>

<table><tr><td>Message info</td><td>Details</td></tr><tr><td>Message direction</td><td>Atellica Solution to LAS</td></tr><tr><td>Message type</td><td>0x020D</td></tr></table>

The LAS attempts the reset connection procedure if this message is not received from the analyzer after a configurable timeout period:

<table><tr><td>Configuration Items</td><td>Default Values</td></tr><tr><td>InitializationSequenceComplete-WaitTimePeriod</td><td>30 seconds (range: 10–600 seconds)</td></tr></table>

# About LAS Connection Reset

When a communication failure occurs, a connection reset must occur. The following are causes for a communication failure:

- Communication Driver issues  
- Application software issues  
- Hardware disconnect  
Power loss

The LAS protocol contains multiple mechanics to support a connection reset.

When the connection is lost, the Atellica Solution resets Queue knowledge except for locked positions, and the LAS resets Instrument Health, Test Inventory, Consumable Inventory Information, and Transfer Status. While the LAS is disconnected, no pallets move in any queue.

If communication was lost while the Atellica Solution locks the interface position via a Load_Unload Request Command then the LAS does not move any carriers until it receives a Load_Unload Response with the Automation Interface Status of not Critical.

The LAS or the Atellica Solution detects communication failure when timeouts for ACK/NACKs or expected Response Message timeouts are exceeded.

When either side (LAS or Atellica Solution) detects that the connection is not functioning, then each side is responsible for resetting its connection status. After restoring the connection, both sides wait prior to initiating reconnect attempts (Page 82 About Establishing LAS Connection).

<table><tr><td>Wait period timeout configuration items</td><td>Default values</td></tr><tr><td>Instrument Initial Wait Period (Prior to Entering Listening Mode)</td><td>15 second (range 10–600)</td></tr><tr><td>Automation Initial Wait Period (Prior to initiating Handshake)</td><td>30 second (range 10–600)</td></tr></table>

# About ACK/NACK timeouts

All messages the LAS or Atellica Solution send must be acknowledged. If the system does not receive an ACK or NACK within the specified timeout, it must re-send the message. After re-sending the message the maximum number of retries without an ACK or NACK response, the sender should assume that the connection is offline and must be reset.

NOTE: The following configuration items' value match between LAS and the Atellica Solution:

<table><tr><td>ACK/NACK configuration items</td><td>Default values</td></tr><tr><td>ACK/NACK timeout (from LAS)</td><td>1 second (range 1–9)</td></tr><tr><td>ACK/NACK timeout (from the Atellica Solution)</td><td>1 second (range 1–9)</td></tr><tr><td>Maximum Allowed Retries</td><td>5 (range 1–9)</td></tr></table>

# About Response Message timeouts

When the Atellica Solution sends an acknowledged request message or command message, a corresponding response message always occurs. The operator can send a message on Acknowledgment timeout, but the system cannot retrieve it if the response times out. The following is a summary table of the response timeouts:

<table><tr><td>Category</td><td>Item</td><td>Range of values</td><td>Default</td><td>Units (data type)</td></tr><tr><td>Instrument Health</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Test Inventory</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Onboard Sample Info</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Transfer Status</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Add Queue</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Skip Queue</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Clear Queue</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr><tr><td>Load_Unload Command</td><td>Response Timeout</td><td>60–900</td><td>600</td><td>seconds (int)</td></tr><tr><td>Consumable Inventory</td><td>Response Timeout</td><td>2–60</td><td>20</td><td>seconds (int)</td></tr></table>

# About NACK Responses

When the Atellica Solution sends a message, there always must be an acknowledgment of that message. The Atellica Solution generates a NACK acknowledgment message when the checksum does not match or a received message contains invalid values. If the message acknowledgment is a NACK response, the operator must resend the message. If the Atellica Solution receives the maximum NACK acknowledgment messages for a message, then the operator must reset the connection.

<table><tr><td>NACK response configuration items</td><td>Default values</td></tr><tr><td>Maximum NACK limit for a message</td><td>3 (range 1–9)</td></tr></table>

# About Keep Alive Messages

During LAS connection inactivity, Keep Alive messages monitor the connection. Keep Alive messages are not request messages, therefore no corresponding response messages exist. When the Atellica Solution receives a Keep Alive message, the receiver only needs to acknowledge via ACK/NACK response.

Header

Footer

<table><tr><td>Keep alive</td><td>Notes</td></tr><tr><td>Message direction</td><td>LAS to Atellica Solution</td></tr><tr><td>Message type</td><td>0x0005</td></tr><tr><td>Keep alive message</td><td>Default values</td></tr><tr><td>Inactivity timeout before sending</td><td>15 (range 5–300) seconds</td></tr><tr><td>Keep Alive message</td><td></td></tr></table>

# About Carrier Queue Management

A series of queue messages informs the Atellica Solution of carriers diverted to the LAS buffer. The Atellica Solution uses this information to anticipate and prepare sample loading, unloading, or exchange. By preparing for sample transfer, the Atellica Solution ensures a high rate of exchange.

# About Add Queue Command Messages

As the Atellica Solution prepares for a load, unload, or exchange operation, the LAS must send an Add Queue message to the Atellica Solution in the order of divert. The Atellica Solution expects the carrier to be presented for sample transfer in first-in-first-out (FIFO).

For SHC, automation must send Add Queue commands to respective IPs. The Atellica Solution sends an Add Queue command to IPO when a carrier diverts to IPO queue. When the Atellica Solution adds a carrier to IP1 via released from IPO or diverts directly from the main track via an IPO divert gate, the Atellica Solution must send an Add Queue command for IP1.

NOTE: The Atellica Solution accepts a duplicate Sample ID in an Add Queue message. If the Atellica Solution detects a duplicate Sample ID, it returns the sample with a duplicate sample error.

NOTE: The Atellica Solution sets STAT priority when a sample tube contains STAT order or if it introduces a sample tube via Priority Lane.

NOTE: The Atellica Solution will accept Greiner MiniCollect Complete samples only when it is configured with Atellica Solution Immunoassay analyzers because the Greiner MiniCollect Complete sample is required to go for volume check before routing to perform the actual test.

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Carrier Occupancy (1 Byte)</td><td>F L</td><td>Sample ID (n Bytes)</td><td>Sample Priority (1 Byte)</td><td>Tube Height (1 Byte)</td><td>Tube Diameter (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Add queue command request message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>LAS to Atellica Solution.</td></tr><tr><td>Message Type</td><td>0x0401.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Carrier Occupancy</td><td>0x01: Empty Carrier. 
0x02: Uncapped Tube. 
0x03: Capped Tube. 
NOTE: If the carrier occupancy is empty, a sample ID does not exist (Field Length for Sample ID must be set to 0). If carrier occupancy type is Capped Tube or Uncapped Tube, then a sample ID must exist.</td></tr><tr><td>Sample ID</td><td>Sample ID in ASCII string [Maximum Length: 24].</td></tr><tr><td>Sample Priority</td><td>Priority of Sample tube in the carrier. 
0x00 – Undefined. 
0x01 – Routine. 
0x02 – STAT.</td></tr><tr><td>Tube Height</td><td>The Atellica Solution ignores it (Unit: Millimeter).</td></tr><tr><td rowspan="7">Tube Diameter</td><td>Unit: Tenth of a millimeter</td></tr><tr><td colspan="1">0x52 – Inside diameter is 8.2 mm. The tube is in the category of Greiner MiniCollect Complete tubes.</td></tr><tr><td colspan="1">0x82 – the tube is in the category of 13 mm outside diameter tubes</td></tr><tr><td colspan="1">0x96 – the tube is in the category of 15 mm outside diameter tubes</td></tr><tr><td colspan="1">0xA0 – the tube is in the category of 16 mm outside diameter tubes</td></tr><tr><td colspan="1">Value 0x52 identifies Greiner MiniCollect Complete tubes</td></tr><tr><td colspan="1">Tubes with Tube Diameter of 0x52 will be considered as Greiner MiniCollect Complete tubes by Atellica Solution. Any other diameter value from the above list or outside of the list will be processed as a regular (i.e. not Greiner MiniCollect Complete) tube by Atellica Solution.</td></tr></table>

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>F L</td><td>Sample ID (n Bytes)</td><td>Command Status (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Add queue command response message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>Atellica Solution to LAS</td></tr><tr><td rowspan="3">Usage</td><td>The Atellica Solution sends a message upon request.</td></tr><tr><td>LAS cannot initiate a Load unloaded Command until it receives an Add Queue Response.</td></tr><tr><td>The Atellica Solution can send more than 1 Add Queue Command at a time.</td></tr><tr><td>Message Type</td><td>0x0402.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Sample ID</td><td>Sample ID in ASCII string [Maximum Length: 24].</td></tr><tr><td>Command Status</td><td>0x01 – The Atellica Solution performs Add Queue Command successfully. 
NOTE: The system cannot reject the Add Queue command. However, the system is not required to load or process the sample.</td></tr></table>

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/f3730d7ac4c34408a71719d77070bb8e79d176879cab9fcdfcb18a6f338cd170.jpg)

# About Skip Queue Command Messages

When a carrier has been added to the queue, the Atellica Solution can issue the Skip Queue Command at any time before the carrier is locked by a Load_Unload Command request. Upon receipt of Skip Queue Command, the Atellica Solution removes the skipped carrier from its carrier queue database. When there is an ambiguity, such as multiple samples with duplicate sample IDs, the first item the Atellica Solution adds with matching criteria is skipped. Skip Queue Command affects the matching Sample ID & Carrier Occupancy Type in FIFO order.

The LAS must wait for a Skip Response message and acknowledge response message prior to moving the pallet out of IPO/IP1 gate.

NOTE: The Atellica Solution can send a Skip Command to any unlocked queue element while another pallet is locked for transfer.

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Carrier Occupancy (1 Byte)</td><td>F L</td><td>Sample ID (n Bytes)</td><td>In Queue (1 Byte)</td></tr></table>

<table><tr><td>Tube Height
(1 Byte)</td><td>Tube Diameter
(1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Skip queue command request message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>LAS to Atellica Solution.</td></tr><tr><td>Message Type</td><td>0x0403.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Carrier Occupancy</td><td>0x01: Empty Carrier.0x02: Uncapped Tube.0x03: Capped Tube.NOTE: If carrier occupancy is empty, a sample ID does not exist. (Field Length for Sample ID must be set to 0). If carrier occupancy type is Capped Tube or Uncapped Tube, then a sample ID must be present.</td></tr><tr><td>Sample ID</td><td>Sample ID in ASCII string [Maximum Length: 24].</td></tr></table>

<table><tr><td>Skip queue command request message</td><td colspan="4">Notes</td><td></td></tr><tr><td>In Queue</td><td colspan="4">0x00: The Atellica Solution previously added to queue and it is physically on LAS buffer (the typical scenario).0x01: The Atellica Solution previously added to queue, but it is not physically on LAS buffer (a divert error occurred).</td><td></td></tr><tr><td>Tube Height</td><td colspan="4">The Atellica Solution ignores it (Unit: Millimeter).</td><td></td></tr><tr><td>Tube Diameter</td><td colspan="4">The Atellica Solution ignores it (Unit: Millimeter).</td><td></td></tr><tr><td colspan="5"></td><td></td></tr><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>F L</td><td>Sample ID (n Bytes)</td><td>Command Status (1 Byte)</td><td>Footer</td></tr><tr><td colspan="6"></td></tr><tr><td>Skip queue command response message</td><td colspan="5">Notes</td></tr><tr><td>Message Direction</td><td colspan="5">Atellica Solution to LAS.</td></tr><tr><td>Usage</td><td colspan="5">The Atellica Solution sends a message upon request.The Atellica Solution removes the tube from its queue and abort any scheduled processing for this tube if possible.</td></tr><tr><td>Message Type</td><td colspan="5">0x0404.</td></tr><tr><td>Interface Position Index</td><td colspan="5">The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Sample ID</td><td colspan="5">Sample ID in ASCII string. [Maximum Length: 24].</td></tr><tr><td>Command Status</td><td colspan="5">0x01: The Atellica Solution performs Skip Queue Command successfully.</td></tr></table>

Typical message with skip command sequence diagram

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/c6ca81721cee64cb905335cad29051450087db4908010a519841d7cf443ccf42.jpg)

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/35986f4b529825b2690d69005c65844499654b43a6bb1b8345649e25f4e253ac.jpg)

Multi-cycles early skip command sequence diagram

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/3a37983d0aa362bf0941e54deb6c6322b054810fcc817463ff76bac4a819085c.jpg)

# Clear Queue Command Message

This command informs the Atellica Solution to clear all carriers presently in the buffer from its database. While automation can send a Clear Queue Command at any time, it does not affect the carrier already the Load_Unload Command locks.

When the Atellica Solution receives a Clear Queue Command Response, the cleared carriers can move through the Interface Position without requiring the Load_Unload Command message exchanges. If a locked carrier is in the Interface Position, then the clear carrier waits until the locked carrier becomes unlocked.

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Clear queue command request message details</td><td>Notes</td></tr><tr><td>Message Direction</td><td>LAS to Atellica Solution.</td></tr><tr><td>Message Type</td><td>0x0405.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.
For the SHC, the Atellica Solution must send separate Clear Queue commands for IPO and IP1 during communication initialization. However, it is not always necessary to clear both queues as a pair during run time if only 1 queue needs clearing.</td></tr></table>

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Command Status (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Clear queue command response message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>Atellica Solution to LAS.</td></tr><tr><td>Usage</td><td>The Atellica Solution sends a message upon request.The Atellica Solution removes all queued tubes it has previously added but not sampled. The Atellica Solution must send tubes queried and not sampled with null test results and an aborted error flag to the LIS. The Atellica Solution should process any result tube that was successfully sampled normally.</td></tr><tr><td>Message Type</td><td>0x0406.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Command Status</td><td>0x01: The Atellica Solution performs Clear Queue Command successfully.</td></tr></table>

# Instrument Control

# About Transfer Status Messages

The Transfer Status message informs LAS of immediate readiness of the Atellica Solution to Load or unload tubes. The LAS uses this information to initiate Load_Unload Command and empty pallet routing decisions. The LAS does not base sample routing decisions on Transfer Status as the Atellica Solution does not generate necessary consumables if no samples are waiting to load. Instead, LAS uses Analyzer Health and Test Inventory messages to route samples.

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Message info</td><td>Notes</td></tr><tr><td>Message Direction</td><td>LAS to Atellica Solution.</td></tr><tr><td>Message Type</td><td>0x0209.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr></table>

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Ready To Load (1 Byte)</td><td>Return Ready Tube Count (2 Bytes)</td><td>Footer</td></tr></table>

<table><tr><td>Transfer status response message</td><td>Notes</td></tr><tr><td>Message Direction</td><td>Atellica Solution to LAS.</td></tr><tr><td>Message Type</td><td>0x020A.</td></tr><tr><td>Interface Position Index</td><td>The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Ready to Load</td><td>Message that indicates that the Atellica Solution is ready to Load. 
0x00: Not Ready to Load. 
0x01: Ready to Load.</td></tr><tr><td>Return Ready Tube Count</td><td>The number of tubes immediately ready to return to LAS.</td></tr><tr><td>Transfer status message configuration item</td><td>Default values</td></tr><tr><td>Transfer Status Response Timeout</td><td>20 seconds (range 2–60)</td></tr></table>

# About Load_Unload Command Messages

This command supports sample pick-and-place by the Atellica Solution. The Load_Unload Command message indicates to the Atellica Solution that a carrier is locked for the Atellica Solution to perform sample transfer operations. When the Atellica Solution Transfer Arm is clear of the track, the Atellica Solution transmits the Load_Unload Command response to the LAS. At this point, the LAS can release the carrier from its locked position and move the next carrier into the lock position. While the carrier is locked, the Atellica Solution expects to have full access to the locked carrier space. The track cannot unlock the carrier until the Atellica Solution receives the response message. If the LAS releases a sample prematurely, a mechanical jam, damage, or sample spill can occur.

NOTE: The LAS must wait for Load_Unload Command response to unlock the position and release the carrier. If the LAS receives a Health Status message while waiting for a Load_Unload Command response, the LAS ignores Lock Ownership status. The LAS can release the carrier upon receipt of the Load_Unload Command Message response only if neither the Load Command Status nor Unload Command Status are 0x02 - Error performing Load command: Lock Carrier in place or Error performing Unload command: Lock Carrier in place.

If the operator performs a communication reset is performed internally or externally and the Instrument Health Response Message indicates that the lock ownership status is Not Locked by the instrument, the LAS can release the carrier without waiting for a Load_Unload Command Message response.

After mixing a whole blood sample, the LAS sends the sample to the Atellica Solution. The maximum time for whole blood samples to be loaded onto the Atellica Solution from the LAS is 8 minutes. If a sample is in the Load Queue and the maximum time is reached, the LAS skips the sample. The operator can configure this element in the LAS.

<table><tr><td>Configuration items</td><td>Default values</td></tr><tr><td>Analyzer Shaking Timeout</td><td>8 minutes (range: 2–30 minutes</td></tr></table>

NOTE: For the SHC, all solicited Load_Unload Command response message advances queue by 1 in the Atellica Solution's database.

NOTE: The Atellica Solution checks if the maximum needed volume for ordered tests exceeds a certain limit (100 uL). If the needed volume exceeds the limit then the Atellica Solution rejects the orders and returns the sample tube without processing, and sample processing status code 0x22 – Insufficient Sample is utilized.

Greiner MiniCollect Complete tubes are processed similar to capillary tubes. Every time a tube is sent to CH analyzers, it is first sent to IA to check for minimum volume availability. If there are no connected IM analyzers, then Greiner MiniCollect Complete tubes are not processed. Sample processing status code, 0x15 Not Processed Capability Unavailable, is used.

<table><tr><td>Header</td><td>Interface Position Index (1 Byte)</td><td>Carrier Occupancy (1 Byte)</td><td>F L</td><td>Sample ID (n Bytes)</td></tr></table>

<table><tr><td>Tube Height
(1 Byte)</td><td>Tube Diameter
(1 Byte)</td><td>Footer</td></tr></table>

<table><tr><td>Load_Unload Command request message</td><td colspan="6">Notes</td></tr><tr><td>Message Direction</td><td colspan="6">LAS to Atellica Solution.</td></tr><tr><td>Message Type</td><td colspan="6">0x0303.</td></tr><tr><td>Interface Position Index</td><td colspan="6">The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Carrier Occupancy</td><td colspan="6">0x01: Empty Carrier.0x02: Uncapped Tube.0x03: Capped Tube.NOTE: If carrier occupancy is empty, a sample ID does not exist (Field Length for Sample ID must be set to 0). If carrier occupancy type is Capped Tube or Uncapped Tube, then a sample ID must be present.</td></tr><tr><td>Sample ID</td><td colspan="6">Sample ID in ASCII string. [Maximum Length: 24]</td></tr><tr><td>Tube Height</td><td colspan="6">The Atellica Solution ignores it (Unit: Millimeter).Unit: Tenthsof a millimeter0x52 – Inside diameter is 8.2 mm. The tube is in the category of Greiner MiniCollect Complete tubes.0x82 – the tube is in the category of 13 mm outside diameter tubes0x96 – the tube is in the category of 15 mm outside diameter tubes0xA0 – the tube is in the category of 16 mm outside diameter tubesValue 0x52 identifies Greiner MiniCollect Complete tubesTubes with Tube Diameter of 0x52 will be considered as Greiner MiniCollect Complete tubes by Atellica Solution.Any other diameter value from the above list or outside of the list will be processed as a regular (i.e. not Greiner MiniCollect Complete) tube by Atellica Solution.</td></tr><tr><td>Tube Diameter</td><td colspan="6">The Atellica Solution ignores it (Unit: Millimeter).</td></tr><tr><td>Load_Unload Command
request message</td><td colspan="6">Notes</td></tr><tr><td>Elapsed Time</td><td colspan="6">The elapsed time in seconds from the LAS initiating the Load Unload Request to the Atellica Solution accepting the whole blood sample. Elapsed time starts when the system releases the sample from the Shaker Module. The default value for this parameter is 0xFFFFh.</td></tr><tr><td></td><td>Header</td><td>Interface Position
Index (1 Byte)</td><td>F L</td><td>Load Sample ID
(n Bytes)</td><td>Load Command Status
(1 Bytes)</td><td></td></tr><tr><td></td><td></td><td></td><td>F L</td><td>Unload Sample ID
(n Bytes)</td><td>Unload Command
Status (1 Bytes)</td><td>Sample Processing
Status (1 Bytes)</td></tr><tr><td></td><td></td><td></td><td></td><td>On Board Tube Count
(2 Bytes)</td><td>Completed Tube Count
(2 Bytes)</td><td>Ready To Load
(1 Byte)</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td>Return Ready Tube
Count (2 Bytes)</td></tr><tr><td>Load_Unload Command
response message</td><td colspan="6">Notes</td></tr><tr><td>Message Direction</td><td colspan="6">Atellica Solution to LAS.</td></tr><tr><td>Usage</td><td colspan="6">The Atellica Solution sends a message upon request.
The Atellica Solution replies with Sample ID, Command Status, On Board Tube count, and Completed Tube count.</td></tr><tr><td>Message Type</td><td colspan="6">0x0304.</td></tr><tr><td>Interface Position Index</td><td colspan="6">The 0-based index value of Interface Position. Index Position starts closest to sample entry position (divert gate) to the LAS buffer.</td></tr><tr><td>Load Sample ID</td><td colspan="6">Sample ID in ASCII string [Maximum Length: 24].
Field length maximum is 24, but the Atellica Solution does not accept sample IDs greater than 20 characters.
When the Atellica Solution loads a sample from the LAS, the Sample ID returns in ASCII. This does not mean that the Atellica Solution verifies the Sample ID with barcode reader.
The Atellica Solution performs Sample ID verification after sample transfer and before processing the sample.
If a transfer error occurs without disturbing the loaded sample tube, such as an arm jam during lateral move from the Atellica Solution side to the LAS side, then the field matches LAS provided value.</td></tr></table>

# Load_Unload Command response message

# Load Command Status

# Notes

The Load Command Status reports the transfer status of sample

0x01: The Atellica Solution performs Load Command successfully.

- The Atellica Solution successfully loaded the original sample in pallet.

0x02: The Atellica Solution error performing Load command: Lock Carrier in place.

- Transfer Arm failure occurs within the LAS space. Automation Interface Status is Critical (Page 89 Instrument Health Message). The LAS must not release the carrier and informs the operator.  
- The Atellica Solution cannot move the pallet until the Instrument Health Statusfor Automation Interface Status changes to Green or Red.  
- The Atellica Solution successfully accesses pallet content.  
- Pallet is empty when Instrument Health Status for Automation Interface Status changes to Green or Red. Accessed sample tubes are considered manually removed from the LAS and the Atellica Solution.  
- Sample load detection generates an Onboard Sample Info response. Sample loss may vary by physical condition.

0x03: Error performing Load command: OK to Unlock Carrier.

- Transfer Arm failure occurs but is not interfering with the track so the carrier can be released. Automation Interface Status is Red.  
- Pallet is full and it is moveable.  
- The Atellica Solution has not accessed pallet content.  
- Transferring sample tubes are considered manually removed from the LAS and the Atellica Solution.  
- Sample load detection generates an Onboard Sample Info response. Sample loss may vary by physical condition.

<table><tr><td>Load_Unload Command response message</td><td>Notes</td></tr><tr><td></td><td>0x04: Unable to perform command: Queue Mismatch.</td></tr><tr><td></td><td>· When carriers do not match the Atellica Solution queue knowledge, this value is returned.</td></tr><tr><td></td><td>· Pallet is not affected and the LAS can deliver it to another analyzer.</td></tr><tr><td></td><td>NOTE: The Atellica Solution responds with this status when a carrier, which is not in the queue or is out of sequence, is requires transfer.</td></tr><tr><td></td><td>0x05: Unable to perform command: Interface position is offline.</td></tr><tr><td></td><td>· The Atellica Solution is in the offline or local control mode and does not load any further samples until it becomes online mode.</td></tr><tr><td></td><td>· Pallet is not affected and the LAS can deliver it to another Atellica Solution.</td></tr><tr><td></td><td>NOTE: To be consistent, the Atellica Solution assumes the unlocked carrier is released from carrier queue. Optionally, if the LAS needs to hold carrier in position to retry at a later time, then it may clear queue and then rebuild queue via Add Queue commands without flushing the buffer (this is the LAS' prerogative) including the supposedly released carrier in front.</td></tr><tr><td></td><td>0x06: Load Skipped.</td></tr><tr><td></td><td>· The Atellica Solution may return this status when it presents a loaded carrier to an Unload Only position.</td></tr><tr><td></td><td>· The Atellica Solution returns this status if the interface position's Remote Control Mode is Unload Only.</td></tr><tr><td></td><td>· Pallet is not affected and the LAS can deliver it to another analyzer.</td></tr><tr><td></td><td>0x07: Unable to perform command: Instrument Skipped Loading.</td></tr><tr><td></td><td>·The Atelica Solution skips loading sample for an internal issue: 
- Automation Interface Status change. 
- Instrument Process Status change. 
- LIS Connection Status change. 
- Complete Test Inventory loss. 
- The Atelica Solution rejects loading on capped tube. 
- Pallet is not affected and the LAS can deliver it to another analyzer. 
0x08: Unable to perform command:Unsupported Sample ID. 
·Either the Sample ID exceeds supported length or uses unsupported characters [Supported SID Maximum length: 20 characters].</td></tr><tr><td>Unload Sample ID</td><td>·Sample ID in ASCII string [Maximum Length: 24]. 
·If an empty carrier in lock position exists, the Atelica Solution may unload LAS sample to LAS. The operator can lock or generate either empty carrier by loading the LAS sample into the Atelica Solution. If the Atelica Solution did not load a tube, the field is left blank. 
·This is the same Sample ID the LAS provided to the Atelica Solution when it loaded the sample from the LAS to the Atelica Solution.</td></tr><tr><td>Unload Command Status</td><td>0x01: The Atellica Solution Perform Sunload Command successfully.
· Pallet is full and is movable.
0x02: Error performing Unload command: Lock Carrier in place.
· An error occurs such that the Transfer Arm is blocking the track and the carrier cannot be released. The Atellica Solution sets the Automation Interface Status to Critical (Page 89 Instrument Health Message). The LAS informs the operator.
· Pallet is not movable until Instrument Health Status for Automation Interface Status changes to Green or Red.
· The Atellica Solution accesses pallet content.
· Pallet is empty when Instrument Health Status for Automation Interface Status changes to Green or Red.
· Accessed sample tube is considered manually removed from the LAS and the Atellica Solution.
· The Atellica Solution generates an Onboard Sample Info response upon sample loss detection. Sample loss may vary by physical condition.
0x03: Error performing Unload command: OK to Unlock Carrier.
· An error occurs but the Transfer Arm is not interfering with the LAS and the carrier can be released.
Automation Interface Status is Red.
· Pallet is empty and is movable.
· The Atellica Solution has not access pallet content.
· Transferring sample tube is considered manually removed from the LAS and the Atellica Solution.
· Sample loss detection generates an Onboard Sample Info response. Sample loss may vary by physical condition.
0x04: Unable to perform command: Queue Mismatch.</td></tr></table>

# Load_Unload Command response message

# Notes

- When carriers do not match the Atellica Solution queue knowledge, this value is returned.  
- Pallet is not affected and the Atellica Solution can deliver it to another analyzer.  
- NOTE: The Atellica Solution responds with this status when a carrier, which is not in the queue or is out of sequence, requires transfer.

0x05: Unable to perform command: Interface position is offline.

The Atellica Solution is in the offline or local control mode and does not unload samples until it becomes online mode.

Pallet is not affected and the LAS can deliver it to another analyzer.

NOTE: The Atellica Solution assumes the unlocked carrier is released from carrier queue. If the LAS needs to hold carrier in position to retry at a later time, it can clear queue and rebuild queue via Add Queue commands without flushing the buffer, including the supposedly released carrier in front.

0x06: Unload Skipped.

- The Atellica Solution may return this status when it presents an empty carrier to a Load Only position.  
- The Atellica Solution returns this status if the interface position's Remote Control Mode is Load Only.  
- Pallet is not affected and the LAS can deliver it to another analyzer.

0x07: Unable to perform command: Instrument Skipped Unloading.

The Atellica Solution skipped unloading sample for internal issue:

Automation Interface Status changes.

Pallet is not affected and the LAS can deliver it to another Atellica Solution.

<table><tr><td>Load_Unload Command response message</td><td>Notes</td></tr><tr><td>Sample Processing Status</td><td>Sample Processing Status provides 2 types of information: 
• Order Processing Status: 
   - Completed Order processing 
   - Order Processing Attempted 
   - Order processing NOT Attempted 
• Sample Condition: 
   - Sample Usable 
   - Sample Error (Operator Inspection Required) 
0x00: No Tube Unloaded. 
0x01: Sample Processed successfully. 
0x11: Sample not processed: Instrumentation failure. 
• For example, a Sample Tube Identifier Error. 
0x12: Sample not processed: Sample ID mismatch. 
• After sample loading, the Atellica Solution tries to verify the Sample ID and finds a mismatch between the provided barcode and read barcode. 
0x13: Sample not processed: Unreadable Barcode. 
• After sample loading, the Atellica Solution fails to read Sample ID. 
0x14: Sample not processed: No LIS orders. 
• The Atellica Solution finds no orders for the unloaded sample to process. 
0x15: Sample not processed: No consumables/Not Processed Capability Unavailable. 
• The Atellica Solution is out of consumables and needs to process an unloaded sample. 
• The Atellica Solution is not available to perform the volument check. 
0x16: Sample not processed: No reagent. 
• The Atellica Solution is out of reagents and needs to process an unloaded sample. 
0x17: Sample not processed: Duplicate Sample Error.</td></tr><tr><td></td><td>0x18: Sample not processed: Capped Tube.</td></tr><tr><td></td><td>0x22: Error processing sample: Insufficient sample.</td></tr><tr><td></td><td>• The Atellica Solution detects insufficient samples.</td></tr><tr><td></td><td>0x23: Error processing sample: Clogged sample.</td></tr><tr><td></td><td>0x26: Error processing sample: Unknown Container Type.</td></tr><tr><td></td><td>0x27: Error Processing sample: HIL Problem / Specimen Type Issue.</td></tr><tr><td></td><td>• The sample tube's orders contain whole blood samples and the Atellica Solution does not support whole blood or flags the sample with HIL.</td></tr><tr><td></td><td>0x28: Error Processing sample: WholeBloodMixingToSamplingTimeExpired</td></tr><tr><td></td><td>• The sample tube orders contain a whole blood sample with an expiration date occurring prior to aspiration of all the ordered tests.</td></tr><tr><td>On Board Tube Count</td><td>Number of tubes onboard from LAS.</td></tr><tr><td>Completed Tube Count</td><td>Number of tube onboard ready to be return to LAS.</td></tr><tr><td>Ready to Load</td><td>Indicates that the Atellica Solution is ready to Load.</td></tr><tr><td></td><td>0x00: Not Ready to Load.</td></tr><tr><td></td><td>0x01: Ready to Load.</td></tr><tr><td></td><td>(Page 120 About Transfer Status Messages)</td></tr><tr><td>Return Ready Tube Count</td><td>The number of tubes immediately ready to return to LAS. (Page 120 About Transfer Status Messages)</td></tr></table>

Typical SHC sample exchange sequence  
![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/14149a2ddd75ddd3f5fac8557fecb2d270abeefb8f695df471ad38e5644754f7.jpg)  
NOTE: The Atellica Solution independently sends Load unloaded Command requests to each Interface Position.

Load_Unload command requesting sent independently to each interface position

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/6996fe593f760e3f8cc09b19246c4bdccc73424c22a824822eb65bca3bbbe3f5.jpg)  
About SHC IP1 Unlock Delayed

Full carriers diverted to the Atellica Solution enter the IPO queue. When a load operation releases carriers from IPO, they move to the IP1 queue for an unload operation.

These queues can hold only a finite number of carriers. If the Atellica Solution delays releasing carriers from IP1, the IP1 queue can fill up which delays any operations at IPO. This may also cause the IPO queue to fill up which may delay additional carriers being diverted to the Atellica Solution.

The LAS skips carriers in IP1 to generate space in IP1 queue.

# About Out of Reagent Scenario

At times, reagent may be out for samples that the operator loads onto the instrument. These samples return with processing status and a reagent issue flag (Page 100 About Test Inventory Messages) (Page 104 About Consumable Inventory Messages).

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/343b3ee4697a04b3a1cf1af3ed0116d8a74b4aa85036adccca7620e51971520a.jpg)

# About Instrument Status Change Scenario

The Instrument Health Status may change so that sample is no longer loadable. If the Atellica Solution receives a Load_Unload Command request before reporting the Instrument Health Status, the Atellica Solution sends an unsolicited Instrument Health response followed by a Load_Unload Command response indicating that sample was not loaded (Page 87 About Initializing the LAS Connection).

Sample Load/Processing Affecting Status [Any]

<table><tr><td>Status</td><td>Type</td><td>Notes</td></tr><tr><td>Automation Interface Status</td><td>All</td><td>0x03: Red
0x04: Critical</td></tr><tr><td>Remote Control Status</td><td>SHC</td><td>• Offline:
- IP0: 0x01: Offline
- IP1: 0x01: Offline
• Unloading Only:
- IP0: 0x01: Offline
- IP1: 0x05: On-Line Unloading Only Mode</td></tr><tr><td>LIS Connection Status</td><td>All</td><td>0x02: Disconnected</td></tr><tr><td>Instrument Process Status</td><td>All</td><td>0x03: Red</td></tr></table>

Sample Unload Affecting Status [Any]

<table><tr><td>Status</td><td>Type</td><td>Notes</td></tr><tr><td>Automation Interface Status</td><td>All</td><td>0x03: Red
0x04 – Critical</td></tr><tr><td>Remote Control Status</td><td>SHC</td><td>• Offline:
- IPO: 0x01: Offline
- IP1: 0x01: Offline</td></tr></table>

![](https://cdn-mineru.openxlab.org.cn/result/2025-12-23/bc2cd51b-3494-4f71-b5dc-29cf3df2e31e/13559f044920c1c05ff0dc58178fd54f0a3a5d9c11b59d27bbe9420c2f4d752b.jpg)
