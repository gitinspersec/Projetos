#include "../../include/stats/protocolStats.hpp"
#include "ftxui/dom/table.hpp"
#include <fstream>

Stats::Stats() : last_tick(std::chrono::steady_clock::now()) {}
/**
 * @brief Aggregates a newly captured packet.
 *
 * Updates:
 *  - Total packet/byte counters
 *  - Transport protocol stats
 *  - Application protocol stats
 *  - IP-level statistics
 *  - Communication pairs
 *
 * Must be called only from capture thread.
 * Protected by mutex.
 */
void Stats::add_packet(const Packet &packet) {
	std::lock_guard<std::mutex> lock(mtx);

	++snapshot.total_p;
	snapshot.total_b += packet.total_len;

	auto &t = transport_map[packet.transport_protocol];
	t.packets++;
	t.bytes += packet.total_len;

	auto &a = application_map[packet.application_protocol];
	a.packets++;
	a.bytes += packet.payload_len;

	ip_map[packet.src].packets_sent++;
	ip_map[packet.src].bytes_sent += packet.total_len;

	ip_map[packet.dst].packets_received++;
	ip_map[packet.dst].bytes_received += packet.total_len;

	auto key = std::make_pair(packet.src, packet.dst);
	pairs[key].packets++;
	pairs[key].bytes += packet.total_len;
}

const char *transport_to_str(TransportProtocol p) {
	switch (p) {
	case TransportProtocol::TCP:
		return "TCP";
	case TransportProtocol::UDP:
		return "UDP";
	case TransportProtocol::ICMP:
		return "ICMP";
	case TransportProtocol::ICMP6:
		return "ICMP6";
	case TransportProtocol::IGMP:
		return "IGMP";
	default:
		return "UNKNOWN";
	}
}

const char *app_to_str(ApplicationProtocol p) {
	switch (p) {
	case ApplicationProtocol::HTTP:
		return "HTTP";
	case ApplicationProtocol::HTTPS:
		return "HTTPS";
	case ApplicationProtocol::DNS:
		return "DNS";
	case ApplicationProtocol::FTP:
		return "FTP";
	case ApplicationProtocol::SSH:
		return "SSH";
	case ApplicationProtocol::SMTP:
		return "SMTP";
	case ApplicationProtocol::QUIC:
		return "QUIC";
	case ApplicationProtocol::NTP:
		return "NTP";
	default:
		return "UNKNOWN";
	}
}

/**
 * @brief Rebuilds transport protocol snapshot table.
 *
 * Sorts protocols by packet count (descending).
 * Calculates percentage relative to total traffic.
 *
 * Called periodically by UI update thread.
 */

void Stats::update_transport_stats() {
	std::lock_guard<std::mutex> lock(mtx);
	snapshot.transport_rows.clear();
	snapshot.transport_rows.push_back({"Proto", "Packets", "Bytes", "%"});

	std::vector<std::pair<TransportProtocol, protocolStats>> tps(transport_map.begin(), transport_map.end());
	std::sort(tps.begin(), tps.end(), [](const auto &a, const auto &b) { return a.second.packets > b.second.packets; });

	for (const auto &[proto, stats] : tps) {
		double percent = snapshot.total_b ? stats.bytes * 100.0 / snapshot.total_b : 0.0;
		snapshot.transport_rows.push_back({transport_to_str(proto), std::to_string(stats.packets),
										   std::format("{:.2f}", stats.bytes / (1024.0 * 1024.0)),
										   std::format("{:.2f}", percent)});
	}
}

/**
 * @brief Rebuilds application protocol snapshot.
 *
 * Sorted by packet count.
 * Percent calculated relative to total bytes.
 */
void Stats::update_application_stats() {
	std::lock_guard<std::mutex> lock(mtx);
	std::vector<std::pair<ApplicationProtocol, protocolStats>> apps(application_map.begin(), application_map.end());

	std::sort(apps.begin(), apps.end(),
			  [](const auto &a, const auto &b) { return a.second.packets > b.second.packets; });

	snapshot.app_rows.clear();
	snapshot.app_rows.push_back({"Proto", "Packets", "Bytes (MB)", "%"});

	for (const auto &[proto, s] : apps) {
		double percent = snapshot.total_b ? s.bytes * 100.0 / snapshot.total_b : 0.0;

		snapshot.app_rows.push_back({app_to_str(proto), std::to_string(s.packets),
									 std::format("{:.2f}", s.bytes / (1024.0 * 1024.0)),
									 std::format("{:.2f}", percent)});
	}
}

/**
 * @brief Generates snapshot for top IP addresses.
 *
 * @param limit Maximum number of IPs to display.
 *
 * Sorted by transmitted packets (descending).
 */
void Stats::update_ip_stats(size_t limit) {
	std::lock_guard<std::mutex> lock(mtx);
	snapshot.rows.clear();

	snapshot.rows.push_back({"IP Address", "Packets TX", "Packets RX"});
	std::vector<std::pair<std::string, IPStats>> ips(ip_map.begin(), ip_map.end());

	std::sort(ips.begin(), ips.end(),
			  [](const auto &a, const auto &b) { return a.second.packets_sent > b.second.packets_sent; });

	size_t count = 0;
	for (const auto &[ip, s] : ips) {
		if (count++ >= limit)
			break;
		snapshot.rows.push_back(
			{ip, "TX: " + std::to_string(s.packets_sent), "RX: " + std::to_string(s.packets_received)});
	}
}

/**
 * @brief Builds snapshot of top communication pairs.
 *
 * @param limit Maximum number of pairs to include.
 *
 * Sorted by total bytes transferred.
 */

void Stats::update_pairs(size_t limit) {
	std::lock_guard<std::mutex> lock(mtx);
	std::vector<std::pair<std::pair<std::string, std::string>, protocolStats>> vec(pairs.begin(), pairs.end());
	std::sort(vec.begin(), vec.end(), [](const auto &a, const auto &b) { return a.second.bytes > b.second.bytes; });

	snapshot.pairs_rows.clear();
	snapshot.pairs_rows.push_back({"Source", "Destination", "bytes received", "%"});
	size_t count = 0;
	for (const auto &[pair, s] : vec) {

		if (count++ >= limit)
			break;
		double percent = snapshot.total_b ? (s.bytes * 100.0 / snapshot.total_b) : 0.0;
		snapshot.pairs_rows.push_back({
			pair.first,
			pair.second,
			std::format("{:.0f}", s.bytes * 1.0),
			std::format("{:.2f}", percent),

		});
	}
}

void Stats::update_packets() {
	std::lock_guard lock(mtx);
	snapshot.packets_rows.clear();
	snapshot.packets_rows.push_back({"IPVersion", "Transport protocol", "Source", "Destination", "App protocol"});

	for (auto &packet : packets) {
		snapshot.packets_rows.push_back({
			packet.ip_version == IPVersion::v4 ? "IPv4" : "IPv6",
			transport_to_str(packet.transport_protocol),
			packet.src,
			packet.dst,
			app_to_str(packet.application_protocol),

		});
	}
}

/**
 * @brief Calculates current bandwidth (bytes/sec).
 *
 * Uses:
 *   - Delta bytes since last tick
 *   - Time elapsed
 *   - Exponential smoothing to reduce noise
 *
 * Stores history for graph rendering.
 */
void Stats::update_bandwidth() {
	std::lock_guard<std::mutex> lock(mtx);
	using namespace std::chrono;

	auto now = steady_clock::now();
	double ts = duration_cast<duration<double>>(now.time_since_epoch()).count();
	double elapsed = duration_cast<duration<double>>(now - last_tick).count();

	if (elapsed >= 1.0) {

		uint32_t delta_bytes = snapshot.total_b - last_b;

		snapshot.bandwidth = delta_bytes / elapsed; // bytes per second

		last_b = snapshot.total_b;
		last_tick = now;
		const double alpha = 0.2;
		smooth_bandwidth = alpha * snapshot.bandwidth + (1.0 - alpha) * smooth_bandwidth;

		snapshot.bandwidth_history.push_back({ts, smooth_bandwidth});
	}
	snapshot.max_bandwidth = std::max(snapshot.max_bandwidth, snapshot.bandwidth);
}

/**
 * @brief Exports current statistics to CSV file.
 *
 * Includes:
 *  - Summary
 *  - Transport protocols
 *  - Application protocols
 *  - IP statistics
 *  - Bandwidth history
 */

void Stats::export_csv(const std::string &filename) {
	std::lock_guard<std::mutex> lock(mtx);
	std::ofstream file(filename);
	if (!file.is_open())
		return;

	file << "summary\n";
	file << "total_packets,total_bytes,bandwidth\n";
	file << snapshot.total_p << "," << snapshot.total_b << "," << snapshot.bandwidth << "\n\n";

	// ===== Transport protocols =====
	file << "transport_protocols\n";
	file << "protocol,packets,bytes,percent\n";

	for (const auto &[proto, s] : transport_map) {
		double percent = snapshot.total_b ? (s.bytes * 100.0 / snapshot.total_b) : 0.0;
		file << transport_to_str(proto) << "," << s.packets << "," << s.bytes << "," << percent << "\n";
	}
	file << "\n";

	// ===== Application protocols =====
	file << "application_protocols\n";
	file << "protocol,packets,payload_bytes\n";

	for (const auto &[proto, s] : application_map) {
		file << static_cast<int>(proto) << "," << s.packets << "," << s.bytes << "\n";
	}
	file << "\n";

	// ===== IP stats =====
	file << "ip_stats\n";
	file << "ip,packets_sent,packets_received,bytes_sent,bytes_received\n";

	for (const auto &[ip, s] : ip_map) {
		file << ip << "," << s.packets_sent << "," << s.packets_received << "," << s.bytes_sent << ","
			 << s.bytes_received << "\n";
	}

	// bandwidth
	file << "time,bandwidth\n";

	for (const auto &p : snapshot.bandwidth_history) {
		file << p.timestamp << "," << p.bytes_per_sec << "\n";
	}

	file.close();
}
/**
 * @brief Exports statistics to JSON format.
 *
 * Designed for:
 *  - External processing
 *  - Visualization tools
 *  - Data pipelines
 */
void Stats::export_json(const std::string &filename) {
	std::lock_guard<std::mutex> lock(mtx);
	std::ofstream file(filename);
	if (!file.is_open())
		return;

	file << "{\n";

	// ===== Summary =====
	file << "  \"summary\": {\n";
	file << "    \"total_packets\": " << snapshot.total_p << ",\n";
	file << "    \"total_bytes\": " << snapshot.total_b << ",\n";
	file << "    \"bandwidth\": " << snapshot.bandwidth << "\n";
	file << "  },\n";

	// ===== Transport =====
	file << "  \"transport\": [\n";
	bool first = true;
	for (const auto &[proto, s] : transport_map) {
		if (!first)
			file << ",\n";
		first = false;

		double percent = snapshot.total_b ? (s.bytes * 100.0 / snapshot.total_b) : 0.0;

		file << "    {\n";
		file << "      \"protocol\": \"" << transport_to_str(proto) << "\",\n";
		file << "      \"packets\": " << s.packets << ",\n";
		file << "      \"bytes\": " << s.bytes << ",\n";
		file << "      \"percent\": " << percent << "\n";
		file << "    }";
	}
	file << "\n  ],\n";

	// ===== IP stats =====
	file << "  \"top_ips\": [\n";
	first = true;
	for (const auto &[ip, s] : ip_map) {
		if (!first)
			file << ",\n";
		first = false;

		file << "    {\n";
		file << "      \"ip\": \"" << ip << "\",\n";
		file << "      \"packets_sent\": " << s.packets_sent << ",\n";
		file << "      \"packets_received\": " << s.packets_received << ",\n";
		file << "      \"bytes_sent\": " << s.bytes_sent << ",\n";
		file << "      \"bytes_received\": " << s.bytes_received << "\n";
		file << "    }";
	}
	file << "\n  ]\n";

	file << ",\n  \"communication_pairs\": [\n";
	first = true;

	for (const auto &[pair, s] : pairs) {
		if (!first)
			file << ",\n";
		first = false;

		file << "    {\n";
		file << "      \"src\": \"" << pair.first << "\",\n";
		file << "      \"dst\": \"" << pair.second << "\",\n";
		file << "      \"packets\": " << s.packets << ",\n";
		file << "      \"bytes\": " << s.bytes << "\n";
		file << "    }";
	}

	file << "\n  ]";

	file << "}\n";
	file.close();
}
