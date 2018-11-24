import base64
import json
import logging
import socket
import time
import ssl
import os
from . import exceptions


URL_FORMAT = "ws://{}:{}/api/v2/channels/samsung.remote.control?name={}"
SSL_URL_FORMAT = "wss://{}:{}/api/v2/channels/samsung.remote.control?name={}"


class RemoteWebsocket():
    """Object for remote control connection."""

    def __init__(self, config):
        import websocket


        self.token_file = os.path.dirname(
            os.path.realpath(__file__)) + "/token.txt"
        if not config["port"]:
            config["port"] = 8001

        if config["timeout"] == 0:
            config["timeout"] = None

        if config["port"] == 8002:
            url = SSL_URL_FORMAT.format(config["host"], config["port"],
                self._serialize_string(config["name"]))
            if os.path.isfile(self.token_file):
                with open(self.token_file, "r") as token_file:
                    token = token_file.readline()
                    if token.strip():
                        url += "&token=" + token
                        has_token = True
                    else:
                        has_token = False
            else:
                has_token = False

            timeout = config["timeout"] if has_token else 10.0
            self.connection = websocket.create_connection(url, timeout,
                sslopt={"cert_reqs": ssl.CERT_NONE})

            self.has_token = has_token

        else:
            url = URL_FORMAT.format(config["host"], config["port"],
                self._serialize_string(config["name"]))
            self.connection = websocket.create_connection(url,
                config["timeout"])
        self._read_response()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Close the connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logging.debug("Connection closed.")

    def control(self, key):
        """Send a control command."""
        if not self.connection:
            raise exceptions.ConnectionClosed()

        payload = json.dumps({
            "method": "ms.remote.control",
            "params": {
                "Cmd":          "Click",
                "DataOfCmd":    key,
                "Option":       "false",
                "TypeOfRemote": "SendRemoteKey"
            }
        })

        logging.info("Sending control command: %s", key)
        self.connection.send(payload)
        time.sleep(self._key_interval)

        self._read_response()

    _key_interval = 0.5

    def _read_response(self):
        response = self.connection.recv()
        response = json.loads(response)
        
        print(json.dumps(response, indent=4))

        if 'data' in response and 'token' in response["data"]:
            with open(self.token_file, "w") as token_file:
                self.has_token = True
                token_file.write(response['data']["token"])

        # if response["event"] != "ms.channel.connect":
        #     self.close()
        #     raise exceptions.UnhandledResponse(response)
        # 
        # logging.debug("Access granted.")

    @staticmethod
    def _serialize_string(string):
        if isinstance(string, str):
            string = str.encode(string)

        return base64.b64encode(string).decode("utf-8")
