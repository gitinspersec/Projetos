#ifndef PACKET_HPP
#define PACKET_HPP
#include <cstdint>
#include <string>
#include <utility>
enum IPVersion {
	v4,
	v6,
};

enum class TransportProtocol {
	TCP = 1,
	UDP = 2,
	ICMP = 3,
	ICMP6 = 4,
	IGMP = 5,
	UNKNOWN = -1,
};

enum class ApplicationProtocol {
	HTTP,
	HTTPS,
	DNS,
	FTP,
	SSH,
	SMTP,
	QUIC,
	NTP,
	UNKNOWN,
};

struct Packet {
	IPVersion ip_version;
	TransportProtocol transport_protocol;
	ApplicationProtocol application_protocol;
	// src address
	std::string src;
	// dest address
	std::string dst;
	uint16_t src_port;
	uint16_t dst_port;

	uint32_t total_len;
	uint16_t payload_len;

	const uint8_t *payload_ptr;

	Packet(IPVersion version, TransportProtocol protocol, std::string src, std::string dst, uint16_t src_port,
		   uint16_t dst_port, uint32_t total_len, uint16_t payload, const uint8_t *payload_ptr)
		: ip_version(version), transport_protocol(protocol), src(std::move(src)), dst(std::move(dst)),
		  src_port(src_port), dst_port(dst_port), total_len(total_len), payload_len(payload), payload_ptr(payload_ptr) {
		application_protocol = get_application_protocol();
		this->payload_ptr = nullptr;
	}

  private:
	ApplicationProtocol get_application_protocol();
};
#endif // PACKET_HPP
