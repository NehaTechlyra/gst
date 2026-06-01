# import time
# import serial
# import requests
# from sms_config.models import SMSConfiguration
# from serial.tools import list_ports


# # -------------------------------
# # MAIN ENTRY POINT
# # -------------------------------
# def send_sms(phone_number, message):
#     sms_config = SMSConfiguration.objects.filter(status=True).first()
#     if not sms_config:
#         return False, "No SMS configuration found"

#     mode = sms_config.mode.lower()

#     if mode == "gsm":
#         return send_sms_via_gsm(phone_number, sms_config, message)

#     elif mode == "mobile":
#         return send_sms_via_mobile(phone_number, sms_config, message)

#     elif mode == "api":
#         return send_sms_via_api(phone_number, sms_config, message)

#     return False, f"Invalid mode '{mode}' in DB"


# # -------------------------------
# # 1️⃣ GSM MODE — Multiple Ports
# # -------------------------------
# def send_sms_via_gsm(phone_number, sms_config, message):
#     gsm_ports = sms_config.gsm_configs.all()
#     if not gsm_ports:
#         return False, "No GSM modems configured"

#     available_ports = [p.device for p in list_ports.comports()]
#     last_error = ""

#     for cfg in gsm_ports:
#         port = cfg.gsm_port
#         baud = cfg.gsm_baudrate or 115200
#         timeout = cfg.gsm_timeout or 5

#         if port not in available_ports:
#             last_error = f"Port {port} not available"
#             continue

#         ok, info = _send_sms_serial(
#             phone_number,
#             message,
#             port=port,
#             baudrate=baud,
#             timeout=timeout,
#             modem_type="GSM"
#         )

#         if ok:
#             return True, f"Sent using GSM port {port}"

#         last_error = info
#         time.sleep(0.5)

#     return False, f"All GSM modems failed. Last error: {last_error}"


# # -------------------------------
# # 2️⃣ MOBILE MODE — Multiple Ports
# # -------------------------------
# def send_sms_via_mobile(phone_number, sms_config, message):
#     mobile_ports = sms_config.mobile_configs.all()
#     if not mobile_ports:
#         return False, "No Mobile modem configured"

#     available_ports = [p.device for p in list_ports.comports()]
#     last_error = ""

#     for cfg in mobile_ports:
#         port = cfg.mobile_port
#         baud = cfg.mobile_baudrate or 115200
#         timeout = cfg.mobile_timeout or 5

#         if port not in available_ports:
#             last_error = f"Port {port} not available"
#             continue

#         ok, info = _send_sms_serial(
#             phone_number,
#             message,
#             port=port,
#             baudrate=baud,
#             timeout=timeout,
#             modem_type="Mobile"
#         )

#         if ok:
#             return True, f"Sent using Mobile port {port}"

#         last_error = info
#         time.sleep(0.5)

#     return False, f"All Mobile modems failed. Last error: {last_error}"


# # -------------------------------
# # SERIAL SENDING (COMMON FUNCTION)
# # -------------------------------
# def _send_sms_serial(phone_number, message, port, baudrate=None, timeout=None, modem_type="GSM"):
#     try:
#         message = message.replace("\n", " ").strip()
#         if len(message) > 160:
#             message = message[:160]

#         ser = serial.Serial(
#             port=port,
#             baudrate=baudrate or 115200,
#             timeout=timeout or 5
#         )

#         time.sleep(2)

#         def cmd(txt, wait=0.5):
#             ser.write((txt + "\r").encode())
#             time.sleep(wait)
#             return ser.read_all().decode(errors="ignore")

#         cmd("AT")
#         cmd("AT+CMGF=1")
#         cmd('AT+CSCS="GSM"')

#         # Send CMGS command
#         clean = phone_number.strip()
#         ser.write(f'AT+CMGS="{clean}"\r'.encode())

#         prompt = ""
#         t0 = time.time()
#         while time.time() - t0 < 5:
#             prompt += ser.read_all().decode(errors="ignore")
#             if ">" in prompt:
#                 break
#             time.sleep(0.2)

#         if ">" not in prompt:
#             ser.close()
#             return False, f"No CMGS prompt. Raw: {prompt}"

#         # Send message + CTRL+Z
#         ser.write(message.encode())
#         time.sleep(0.3)
#         ser.write(bytes([26]))
#         time.sleep(5)

#         response = ser.read_all().decode(errors="ignore")
#         ser.close()

#         if "+CMGS:" in response and "OK" in response:
#             return True, response.strip()

#         return False, f"Modem returned error: {response.strip()}"

#     except Exception as e:
#         return False, f"{modem_type} modem error: {str(e)}"


# # -------------------------------
# # 3️⃣ API MODE — Multiple API Accounts
# # -------------------------------
# def send_sms_via_api(phone_number, sms_config, message):
#     api_list = sms_config.api_configs.all()
#     if not api_list:
#         return False, "No API configurations available"

#     last_error = ""

#     for api in api_list:
#         payload = {
#             "sender": api.api_sender,
#             "to": [phone_number],
#             "message": message
#         }

#         headers = {
#             "accept": "application/json",
#             "authkey": api.api_key,
#             "content-type": "application/json"
#         }

#         try:
#             r = requests.post(api.api_url, json=payload, headers=headers, timeout=10)

#             if r.status_code == 200:
#                 return True, f"API sent successfully ({api.api_url})"

#             last_error = f"{r.status_code} {r.text}"

#         except Exception as e:
#             last_error = str(e)

#     return False, f"All API accounts failed. Last error: {last_error}"



import time
import serial
import requests
from sms_config.models import SMSConfiguration
from serial.tools import list_ports


# -------------------------------
# MAIN ENTRY POINT
# -------------------------------
def send_sms(phone_number, message, sms_config=None):
    """
    Send SMS using the provided configuration or fetch default
    
    Args:
        phone_number: Recipient phone number
        message: SMS message content
        sms_config: SMSConfiguration object (optional, will fetch default if None)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # If no config passed, try to fetch default/first active one
    if not sms_config:
        sms_config = SMSConfiguration.objects.filter(status=True).first()
    
    if not sms_config:
        return False, "No SMS configuration found"

    mode = sms_config.mode.lower()

    if mode == "gsm":
        return send_sms_via_gsm(phone_number, sms_config, message)

    elif mode == "mobile":
        return send_sms_via_mobile(phone_number, sms_config, message)

    elif mode == "api":
        return send_sms_via_api(phone_number, sms_config, message)

    return False, f"Invalid mode '{mode}' in configuration"


# -------------------------------
# 1️⃣ GSM MODE — Multiple Ports
# -------------------------------
def send_sms_via_gsm(phone_number, sms_config, message):
    """
    Send SMS via GSM modem(s)
    Tries all configured GSM ports until one succeeds
    """
    gsm_ports = sms_config.gsm_configs.all()
    if not gsm_ports:
        return False, "No GSM modems configured"

    available_ports = [p.device for p in list_ports.comports()]
    last_error = ""

    for cfg in gsm_ports:
        port = cfg.gsm_port
        baud = cfg.gsm_baudrate or 115200
        timeout = cfg.gsm_timeout or 5

        if port not in available_ports:
            last_error = f"Port {port} not available"
            continue

        ok, info = _send_sms_serial(
            phone_number,
            message,
            port=port,
            baudrate=baud,
            timeout=timeout,
            modem_type="GSM"
        )

        if ok:
            return True, f"Sent using GSM port {port}"

        last_error = info
        time.sleep(0.5)

    return False, f"All GSM modems failed. Last error: {last_error}"


# -------------------------------
# 2️⃣ MOBILE MODE — Multiple Ports
# -------------------------------
def send_sms_via_mobile(phone_number, sms_config, message):
    """
    Send SMS via Mobile as modem
    Tries all configured mobile ports until one succeeds
    """
    mobile_ports = sms_config.mobile_configs.all()
    if not mobile_ports:
        return False, "No Mobile modem configured"

    available_ports = [p.device for p in list_ports.comports()]
    last_error = ""

    for cfg in mobile_ports:
        port = cfg.mobile_port
        baud = cfg.mobile_baudrate or 115200
        timeout = cfg.mobile_timeout or 5

        if port not in available_ports:
            last_error = f"Port {port} not available"
            continue

        ok, info = _send_sms_serial(
            phone_number,
            message,
            port=port,
            baudrate=baud,
            timeout=timeout,
            modem_type="Mobile"
        )

        if ok:
            return True, f"Sent using Mobile port {port}"

        last_error = info
        time.sleep(0.5)

    return False, f"All Mobile modems failed. Last error: {last_error}"


# -------------------------------
# SERIAL SENDING (COMMON FUNCTION)
# -------------------------------
def _send_sms_serial(phone_number, message, port, baudrate=None, timeout=None, modem_type="GSM"):
    """
    Internal function to send SMS via serial port
    Works for both GSM and Mobile modems
    """
    try:
        # Clean and truncate message
        message = message.replace("\n", " ").strip()
        if len(message) > 160:
            message = message[:160]

        ser = serial.Serial(
            port=port,
            baudrate=baudrate or 115200,
            timeout=timeout or 5
        )

        time.sleep(2)

        def cmd(txt, wait=0.5):
            ser.write((txt + "\r").encode())
            time.sleep(wait)
            return ser.read_all().decode(errors="ignore")

        # Initialize modem
        cmd("AT")
        cmd("AT+CMGF=1")  # Text mode
        cmd('AT+CSCS="GSM"')  # Character set

        # Send CMGS command
        clean = phone_number.strip()
        ser.write(f'AT+CMGS="{clean}"\r'.encode())

        # Wait for ">" prompt
        prompt = ""
        t0 = time.time()
        while time.time() - t0 < 5:
            prompt += ser.read_all().decode(errors="ignore")
            if ">" in prompt:
                break
            time.sleep(0.2)

        if ">" not in prompt:
            ser.close()
            return False, f"No CMGS prompt. Raw: {prompt}"

        # Send message + CTRL+Z
        ser.write(message.encode())
        time.sleep(0.3)
        ser.write(bytes([26]))  # CTRL+Z
        time.sleep(5)

        response = ser.read_all().decode(errors="ignore")
        ser.close()

        if "+CMGS:" in response and "OK" in response:
            return True, response.strip()

        return False, f"Modem returned error: {response.strip()}"

    except Exception as e:
        return False, f"{modem_type} modem error: {str(e)}"


# -------------------------------
# 3️⃣ API MODE — Multiple API Accounts
# -------------------------------
def send_sms_via_api(phone_number, sms_config, message):
    """
    Send SMS via Cloud API
    Tries all configured API accounts until one succeeds
    """
    api_list = sms_config.api_configs.all()
    if not api_list:
        return False, "No API configurations available"

    last_error = ""

    for api in api_list:
        payload = {
            "sender": api.api_sender,
            "to": [phone_number],
            "message": message
        }

        headers = {
            "accept": "application/json",
            "authkey": api.api_key,
            "content-type": "application/json"
        }

        try:
            r = requests.post(api.api_url, json=payload, headers=headers, timeout=10)

            if r.status_code == 200:
                return True, f"API sent successfully ({api.api_url})"

            last_error = f"{r.status_code} {r.text}"

        except Exception as e:
            last_error = str(e)

    return False, f"All API accounts failed. Last error: {last_error}"