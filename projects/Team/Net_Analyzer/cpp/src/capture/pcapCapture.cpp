#include "../../include/capture/pcapCapture.hpp"
#include "../../include/stats/protocolStats.hpp"

/* get a list of all available network interfaces */
void PcapCapture::initialize() {
	/*	find all devs available in network, save them to pcap_if_t struct (interfaces) */
	if (pcap_findalldevs(&interfaces, errbuf) == -1) {
		throw std::runtime_error("Error: pcap_findalldevs has been failed");
		/*fprintf(stderr, "Error: pcap_findalldevs has been failed - %s\n", errbuf);*/
	}
}

void PcapCapture::datalink_type(int type) {
	switch (type) {

	case DLT_EN10MB: {
		offset = 14;
		get_ether_type = [](const u_char *p) {
			const auto *eth = reinterpret_cast<const ether_header *>(p);
			return ntohs(eth->ether_type);
		};
		break;
	}

	case DLT_LINUX_SLL: {
		offset = 16;
		get_ether_type = [](const u_char *p) { return ntohs(*reinterpret_cast<const uint16_t *>(p + 14)); };
		break;
	}

	case DLT_LINUX_SLL2: {
		offset = 20;
		get_ether_type = [](const u_char *p) { return ntohs(*reinterpret_cast<const uint16_t *>(p + 18)); };
		break;
	}
	default:
		throw std::runtime_error("Unsupported datalink type");
	}
}

/**
 * Start live packet capture.
 *
 * Steps:
 *  1. Resolve network mask
 *  2. Open device in promiscuous mode
 *  3. Compile and apply BPF filter (if provided)
 *  4. Start pcap_loop in a separate thread
 */
void PcapCapture::start() {
	// getting the netmask of the interface
	if (pcap_lookupnet(interface.c_str(), &net, &mask, errbuf) == -1) {
		fprintf(stderr, "Couldn't get netmask for device %s: %s\n", interface.c_str(), errbuf);
		net = 0;
		mask = 0;
	}

	/* open capture device */
	handle.reset(pcap_open_live(interface.c_str(), SNAP_LEN, 1, 1000, errbuf));
	if (handle == nullptr) {
		throw std::runtime_error("Couldn't open device " + interface + ": " + errbuf);
	}

	datalink_type(pcap_datalink(handle.get()));

	if (!filter_exp.empty()) {
		/* compile the filter expression */
		if (pcap_compile(handle.get(), &fp, filter_exp.c_str(), 0, net) == -1) {
			throw std::runtime_error("Couldn't parse filter " + filter_exp + ": " + pcap_geterr(handle.get()));
		}

		/* apply the compiled filter */
		if (pcap_setfilter(handle.get(), &fp) == -1) {
			throw std::runtime_error("Couldn't install filter " + filter_exp + ": " + pcap_geterr(handle.get()));
		}
	}

	/* start a separate thread */
	running = true;
	thread = std::thread([this]() {
		if (pcap_loop(handle.get(), num_packets, &PcapCapture::callback, reinterpret_cast<u_char *>(this)) < 0) {
			// fprintf(stderr, "Error in pcap_loop: %s\n", pcap_geterr(handle));
			// pcap_close(handle);
			// throw std::runtime_error("Couldn't start capture");
		}
		running = false;
	});
}
PcapCapture::~PcapCapture() { stop(); }
void PcapCapture::stop() {
	pcap_freecode(&fp);
	if (!handle) {
		return;
	}

	running = false;

	pcap_breakloop(handle.get());

	if (thread.joinable()) {
		thread.join();
	}

	handle.reset();

	if (interfaces != nullptr) {
		pcap_freealldevs(interfaces);
		interfaces = nullptr;
	}
}

/* print all available interfaces */
void PcapCapture::print_interfaces() {
	int i = 0;
	for (const pcap_if_t *dev = interfaces; dev != nullptr; dev = dev->next) {
		printf("%d. %s  ", ++i, dev->name);
		if (dev->description != nullptr) {
			printf("(%s)\n", dev->description);
		} else {
			printf("\n");
		}
	}
}
/**
 * @brief Static wrapper required by libpcap C API.
 *
 * Since libpcap expects a C-style function pointer,
 * we forward the call to the current class instance.
 *
 * @param user   Pointer to PcapCapture instance
 * @param header Packet metadata
 * @param packet Raw packet bytes
 */
void PcapCapture::callback(u_char *user, const struct pcap_pkthdr *header, const u_char *packet) {
	auto *const self = reinterpret_cast<PcapCapture *>(user);
	if (!self->isRunning()) {
		return;
	}
	self->got_packet(header, packet);
}

/**
 * @brief Parses a single captured packet.
 *
 * Responsibilities:
 *  - Parse Ethernet header
 *  - Detect IP version (IPv4 / IPv6)
 *  - Extract transport & application protocols
 *  - Construct Packet abstraction
 *  - Forward packet to Stats engine
 *
 * Only IPv4 and IPv6 are currently processed.
 * Other Ethernet types are ignored.
 */
void PcapCapture::got_packet(const struct pcap_pkthdr *header, const u_char *packet) {
	if (!running) {
		return;
	}

	// --- Ethernet header ---
	const uint16_t ether_type = get_ether_type(packet);

	/* if we have a ipv4 type */
	if (ether_type == ETHERTYPE_IP) {
		IPv4 ip(packet + offset);
		const TransportProtocol prot = ip.get_protocol();

		Packet packetView(v4, prot, ip.get_source(), ip.get_dest(), ip.get_src_port(), ip.get_dest_port(), header->len,
						  ip.get_payload_len(), ip.get_payload_ptr());
		stats->add_packet(packetView);
		stats->push(packetView);
	}
	/* ipv6 type */
	else if (ether_type == ETHERTYPE_IPV6) {
		IPv6 ip(packet + offset);
		const TransportProtocol prot = ip.get_protocol();
		Packet packetView(v6, prot, ip.get_source(), ip.get_dest(), ip.get_src_port(), ip.get_dest_port(), header->len,
						  ip.get_payload_len(), ip.get_payload_ptr());
		stats->add_packet(packetView);
		stats->push(packetView);
	}
}

void PcapCapture::set_capabilities(const std::string &interface, int num_packets, const std::string &filter_exp,
								   const int packets_limit, Stats *stats) {
	this->interface = interface;
	this->num_packets = num_packets;
	this->filter_exp = filter_exp;
	this->stats = stats;
	this->stats->set_packets_limit(packets_limit);
}
/**
 * @brief Processes packets from an offline .pcap file.
 *
 * Differences from live mode:
 *  - Runs synchronously
 *  - No additional thread is created
 *  - Blocks until entire file is processed
 *
 * Used for post-capture analysis and exporting results.
 */
void PcapCapture::start_offline(const std::string &fpath) {
	handle.reset(pcap_open_offline(fpath.c_str(), errbuf));
	if (handle == nullptr) {
		fprintf(stderr, "Error opening offline file: %s\n", errbuf);
		return;
	}
	datalink_type(pcap_datalink(handle.get()));

	running = true;

	pcap_loop(handle.get(), num_packets, &PcapCapture::callback, reinterpret_cast<u_char *>(this));

	running = false;
}
