#include "../../include/packet/packet.hpp"
#include <cstring>

ApplicationProtocol Packet::get_application_protocol() {
	if (payload_ptr != nullptr && payload_len >= 4) {
		if (transport_protocol == TransportProtocol::TCP) {
			if (memcmp(payload_ptr, "GET ", 4) == 0 || memcmp(payload_ptr, "POST", 4) == 0 ||
				memcmp(payload_ptr, "HEAD", 4) == 0 || memcmp(payload_ptr, "PUT ", 4) == 0 ||
				memcmp(payload_ptr, "HTTP", 4) == 0) {
				return ApplicationProtocol::HTTP;
			}
		}

		if ((src_port == 53 || dst_port == 53) && payload_len >= 12) {
			return ApplicationProtocol::DNS;
		}

		if (transport_protocol == TransportProtocol::TCP) {
			if (payload_ptr[0] == 0x16 && payload_ptr[1] == 0x03) {
				return ApplicationProtocol::HTTPS;
			}
		}
	}

	const uint16_t port = (src_port < dst_port) ? src_port : dst_port;

	if (transport_protocol == TransportProtocol::TCP) {
		switch (port) {
		case 21:
			return ApplicationProtocol::FTP;
		case 22:
			return ApplicationProtocol::SSH;
		case 25:
			return ApplicationProtocol::SMTP;
		case 53:
			return ApplicationProtocol::DNS;
		case 80:
			return ApplicationProtocol::HTTP;
		case 443:
			return ApplicationProtocol::HTTPS;
		default:
			return ApplicationProtocol::UNKNOWN;
		}
	}

	if (transport_protocol == TransportProtocol::UDP) {
		switch (port) {
		case 53:
			return ApplicationProtocol::DNS;
		case 443:
			return ApplicationProtocol::QUIC;
		case 123:
			return ApplicationProtocol::NTP;
		default:
			return ApplicationProtocol::UNKNOWN;
		}
	}

	return ApplicationProtocol::UNKNOWN;
}
