# Configuration

##### General

* `HOST` (`str`) - The listening address of the server (eg: `127.0.0.1` or `0.0.0.0`)
* `PORT` (`int`) - The port the server will listen at (eg: `8080`)
* `SSL` (`bool`) - If the server is going to use SSL/TLS (Secure Sockets Layer)

##### SSL

* `CER_FILE` (`str`) - The path to the certificate file to be used for SSL (PEM format)
* `KEY_FILE` (`str`) - The path to the private key file to be used for SSL (PEM format)
* `CA_FILE` (`str`) - The path to the CA (certificate authority) file to be used for SSL (PEM format)
* `SSL_VERIFY` (`bool`) - If the standard SSL verification process (CA) should be performed for the connection,
if the current instance is a client the host verification will also be performed for the server side host
* `SSL_HOST` (`str`) - The hostname that is going to be used in for domain verification, this value is only
user in server to be able to verify client certificates  against an expected host
