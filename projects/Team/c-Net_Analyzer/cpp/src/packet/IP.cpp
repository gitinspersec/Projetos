#include "../../include/packet/IP.hpp"

#include <arpa/inet.h>
#include <array>
#include <cstdio>
#include <netinet/icmp6.h>
#include <netinet/ip_icmp.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <stdexcept>
uint16_t IP_class::get_payload_len() const { return payload_len; }

TransportProtocol IP_class::get_protocol() const { return protocol; }
const std::string &IP_class::get_source() const { return src; }
const std::string &IP_class::get_dest() const { return dst; }

/*** Ipv4 ***/
IPv4::IPv4(const u_char *data)
	: ip_hdr(reinterpret_cast<const ip *>(data)), ip_hdr_len(static_cast<int>(ip_hdr->ip_hl) * 4) {
	std::array<char, INET_ADDRSTRLEN> src_buf{};
	inet_ntop(AF_INET, &ip_hdr->ip_src, src_buf.data(), sizeof(src_buf));
	src = src_buf.data();

	std::array<char, INET_ADDRSTRLEN> dst_buf{};
	inet_ntop(AF_INET, &ip_hdr->ip_dst, dst_buf.data(), sizeof(dst_buf));
	dst = dst_buf.data();
	if (ip_hdr_len < 20) {
		throw std::runtime_error("Failed to initial IPv4 ");
	}
	switch (ip_hdr->ip_p) {
	case IPPROTO_TCP:
		IPv4::handle_tcp();
		break;
	case IPPROTO_UDP:
		IPv4::handle_udp();
		break;

	case IPPROTO_ICMP:
		IPv4::handle_icmp();
		break;

	case IPPROTO_ICMPV6:
		IPv4::handle_icmpv6();
		break;
	case IPPROTO_IGMP:
		IPv4::handle_igmp();
		break;
	default:
		protocol = TransportProtocol::UNKNOWN;
		break;
	}
}

void IPv4::handle_tcp() {
	const auto *tcp = reinterpret_cast<const tcphdr *>(reinterpret_cast<const u_char *>(ip_hdr) + ip_hdr_len);

	src_port = ntohs(tcp->source);
	dest_port = ntohs(tcp->dest);

	const auto tcp_hdr_len = static_cast<std::size_t>(tcp->doff) * 4U;
	payload_ptr = reinterpret_cast<const u_char *>(tcp) + tcp_hdr_len;
	payload_len = static_cast<uint16_t>(ntohs(ip_hdr->ip_len) - ip_hdr_len - static_cast<int>(tcp_hdr_len));

	protocol = TransportProtocol::TCP;
}
void IPv4::handle_udp() {
	const auto *udp = reinterpret_cast<const udphdr *>(reinterpret_cast<const u_char *>(ip_hdr) + ip_hdr_len);
	dest_port = ntohs(udp->dest);
	src_port = ntohs(udp->source);

	payload_ptr = reinterpret_cast<const u_char *>(udp) + sizeof(udphdr);
	payload_len = ntohs(udp->len) - sizeof(udphdr);

	protocol = TransportProtocol::UDP;
}
void IPv4::handle_icmp() { protocol = TransportProtocol::ICMP; }
void IPv4::handle_icmpv6() { protocol = TransportProtocol::ICMP6; }
void IPv4::handle_igmp() { protocol = TransportProtocol::IGMP; }

uint16_t IPv4::get_src_port() { return src_port; }
uint16_t IPv4::get_dest_port() { return dest_port; }

/*** Ipv6 ***/

IPv6::IPv6(const u_char *data)
	: ip_hdr(reinterpret_cast<const ip6_hdr *>(data)), ptr(reinterpret_cast<const uint8_t *>(ip_hdr + 1)) {
	uint8_t hdr = ip_hdr->ip6_nxt;
	std::array<char, INET6_ADDRSTRLEN> src{};
	inet_ntop(AF_INET6, &ip_hdr->ip6_src, src.data(), sizeof(src));
	this->src = src.data();

	std::array<char, INET6_ADDRSTRLEN> dst{};
	inet_ntop(AF_INET6, &ip_hdr->ip6_dst, dst.data(), sizeof(dst));
	this->dst = dst.data();
	while (true) {
		switch (hdr) {
		case IPPROTO_TCP:
			IPv6::handle_tcp();
			return;
		case IPPROTO_UDP:
			IPv6::handle_udp();
			return;
		case IPPROTO_ICMP:
			IPv6::handle_icmp();
			return;
		case IPPROTO_ICMPV6:
			IPv6::handle_icmpv6();
			return;

		case IPPROTO_IGMP:
			IPv6::handle_igmp();
			return;
			/* if we have an extension headers, dont leave from loop,
			 * keep find a protocol type
			 */
		case IPPROTO_HOPOPTS:
		case IPPROTO_ROUTING:
		case IPPROTO_DSTOPTS: {
			const auto *ext = reinterpret_cast<const ip6_ext *>(ptr);
			hdr = ext->ip6e_nxt;
			ptr += (static_cast<std::size_t>(ext->ip6e_len) + 1U) * 8U;
			break;
		}
		case IPPROTO_FRAGMENT: {

			const auto *frag = reinterpret_cast<const ip6_frag *>(ptr);
			hdr = frag->ip6f_nxt;
			ptr += sizeof(ip6_frag);
			break;
		}
		default:
			protocol = TransportProtocol::UNKNOWN;
			return;
		}
	}
	ptr = nullptr;
}

void IPv6::handle_tcp() {
	const auto *const tcp = reinterpret_cast<const tcphdr *>(ptr);
	dest_port = ntohs(tcp->dest);
	src_port = ntohs(tcp->source);

	const auto tcp_hdr_len = static_cast<std::size_t>(tcp->doff) * 4U;
	payload_ptr = reinterpret_cast<const uint8_t *>(tcp) + tcp_hdr_len;
	payload_len = static_cast<uint16_t>(ntohs(ip_hdr->ip6_plen) - static_cast<uint16_t>(tcp_hdr_len));

	protocol = TransportProtocol::TCP;
	ptr = nullptr;
}
void IPv6::handle_udp() {
	const auto *const udp = reinterpret_cast<const udphdr *>(ptr);
	dest_port = ntohs(udp->dest);
	src_port = ntohs(udp->source);

	payload_ptr = reinterpret_cast<const uint8_t *>(udp) + sizeof(udphdr);
	payload_len = ntohs(udp->len) - sizeof(udphdr);

	protocol = TransportProtocol::UDP;
	ptr = nullptr;
}
void IPv6::handle_icmp() {
	protocol = TransportProtocol::ICMP;
	ptr = nullptr;
}
void IPv6::handle_icmpv6() {
	protocol = TransportProtocol::ICMP6;
	payload_len = ntohs(ip_hdr->ip6_plen) - sizeof(icmp6_hdr);
	ptr = nullptr;
}
void IPv6::handle_igmp() {
	protocol = TransportProtocol::IGMP;
	ptr = nullptr;
}

uint16_t IPv6::get_src_port() { return src_port; }

uint16_t IPv6::get_dest_port() { return dest_port; }
