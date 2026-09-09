#ifndef IP_HPP
#define IP_HPP
#include "packet.hpp"
#include <netinet/igmp.h>
#include <netinet/ip.h>
#include <netinet/ip6.h>
#include <string>

/* virtual class for our IPv4, IPv6 classes */
class IP_class {
  protected:
	virtual void handle_tcp() = 0;
	virtual void handle_udp() = 0;
	virtual void handle_icmp() = 0;
	virtual void handle_icmpv6() = 0;
	virtual void handle_igmp() = 0;

	uint16_t payload_len = 0;
	TransportProtocol protocol = TransportProtocol::UNKNOWN;
	std::string src;
	std::string dst;

  public:
	const std::string &get_source() const;
	const std::string &get_dest() const;
	// getters
	/*virtual std::string get_source() = 0;
	virtual std::string get_dest() = 0;*/
	virtual uint16_t get_src_port() = 0;
	virtual uint16_t get_dest_port() = 0;

	TransportProtocol get_protocol() const;
	uint16_t get_payload_len() const;

	const uint8_t *payload_ptr = nullptr;
	const uint8_t *get_payload_ptr() const { return payload_ptr; }

	virtual ~IP_class() = default;
};
/*** ip4 ***/
class IPv4 : public IP_class {
  private:
	const ip *ip_hdr = nullptr;
	int ip_hdr_len = 0;
	uint16_t src_port = 0;
	uint16_t dest_port = 0;

  protected:
	void handle_tcp() override;
	void handle_udp() override;
	void handle_icmp() override;
	void handle_icmpv6() override;
	void handle_igmp() override;

  public:
	uint16_t get_src_port() override;
	uint16_t get_dest_port() override;

	explicit IPv4(const u_char *data);
};

/*** ipv6 ***/
class IPv6 : public IP_class {
  protected:
	void handle_tcp() override;
	void handle_udp() override;
	void handle_icmp() override;
	void handle_icmpv6() override;
	void handle_igmp() override;

  private:
	const ip6_hdr *ip_hdr = nullptr;
	int ip_hdr_len = 40;

	in6_addr ip_source = {};
	in6_addr ip_dest = {};

	uint16_t src_port = 0;
	uint16_t dest_port = 0;

	const uint8_t *ptr = nullptr;

  public:
	explicit IPv6(const u_char *data);

	uint16_t get_src_port() override;
	uint16_t get_dest_port() override;
};

#endif // IP_HPP
