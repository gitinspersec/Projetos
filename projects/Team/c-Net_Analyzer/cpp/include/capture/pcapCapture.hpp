#ifndef PCAPCAPTURE_HPP
#define PCAPCAPTURE_HPP

#include <deque>
#include <memory>
#include <pcap/pcap.h>
#include <queue>
#include <thread>

#include <netinet/if_ether.h>
#include <netinet/igmp.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#define SNAP_LEN 1518

#include "../../include/stats/protocolStats.hpp"
#include "../packet/IP.hpp"
#include "../packet/packet.hpp"

/**
 * Packet capture engine based on libpcap
 *
 * Supports:
 *  - Live capture from network interface
 *  - Offline capture from .pcap file
 *  - BPF filtering
 *  - Separate capture thread (for live mode)
 *
 * Workflow:
 *  initialize()      -> load interfaces
 *  set_capabilities()-> configure capture parameters
 *  start()           -> start live capture (threaded)
 *  start_offline()   -> process file synchronously
 *  stop()            -> stop capture and cleanup
 */

class PcapCapture {
  private:
	/* libpcap error buffer */
	char errbuf[PCAP_ERRBUF_SIZE] = {};

	/* filter expression (compiled before capture) */
	std::string filter_exp;
	/* compiled filter program (expression) */
	struct bpf_program fp = {};
	/* Active pcap handle */
	std::unique_ptr<pcap_t, decltype(&pcap_close)> handle{nullptr, &pcap_close};
	void datalink_type(int type);
	uint16_t offset = 0;
	std::function<uint16_t(const u_char *)> get_ether_type;

	/* Network mask and IP */
	bpf_u_int32 mask = 0;
	bpf_u_int32 net = 0;

	/* Number of packets to capture */
	int num_packets = 0;

	/* Linked list of available interfaces */
	pcap_if_t *interfaces = nullptr;

	/* Selected network interface */
	std::string interface;
	/**
	 * Static wrapper required by C-style libpcap callback.
	 *
	 * Since libpcap expects a C function pointer,
	 * we use a static function and forward the call
	 * to the class instance.
	 */
	static void callback(u_char *user, const struct pcap_pkthdr *header, const u_char *packet);
	// packet processing logic
	void got_packet(const struct pcap_pkthdr *header, const u_char *packet);

	/* Separate thread used for live capture */
	std::thread thread;
	std::atomic<bool> running{false};
	void stop();
	Stats *stats = nullptr;

  public:
	PcapCapture() = default;
	~PcapCapture();

	PcapCapture(const PcapCapture &) = delete;
	PcapCapture &operator=(const PcapCapture &) = delete;
	PcapCapture(PcapCapture &&) = delete;
	PcapCapture &operator=(PcapCapture &&) = delete;
	void print_interfaces();

	bool isRunning() { return running; }
	void setRunning(bool running) { this->running = running; }
	/* Pointer to statistics engine */

	void set_capabilities(const std::string &interface, int num_packets, const std::string &filter_exp,
						  int packets_limit, Stats *stats);
	void initialize();

	void start();
	void start_offline(const std::string &fpath);
};

#endif // PCAPCAPTURE_HPP
