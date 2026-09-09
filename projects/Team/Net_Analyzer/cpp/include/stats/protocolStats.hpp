#ifndef PROTOCOLSTATS_HPP
#define PROTOCOLSTATS_HPP

#include "../packet/packet.hpp"
#include "ftxui/dom/elements.hpp"
#include <chrono>
#include <filesystem>
#include <map>
#include <queue>
#include <unordered_map>

struct protocolStats {
	uint32_t packets = 0;
	uint32_t bytes = 0;
};

struct trafficStats {
	uint32_t total_packets = 0;
	uint32_t total_bytes = 0;
};

struct IPStats {
	uint32_t bytes_sent = 0;
	uint32_t bytes_received = 0;

	uint32_t packets_sent = 0;
	uint32_t packets_received = 0;
};

struct BandwidthPoint {
	double timestamp;
	double bytes_per_sec;
};

struct StatsSnapshot {
	std::vector<std::vector<std::string>> transport_rows;
	std::vector<std::vector<std::string>> app_rows;
	std::vector<std::vector<std::string>> rows;
	std::vector<std::vector<std::string>> pairs_rows;
	std::vector<std::vector<std::string>> packets_rows;

	uint32_t total_p = 0, total_b = 0;
	// bandwidth
	std::vector<BandwidthPoint> bandwidth_history;
	double bandwidth = 0;
	double max_bandwidth = 0;
};

/**
 * @brief Thread-safe statistics engine.
 *
 * Responsible for:
 *  - Aggregating packet statistics
 *  - Maintaining protocol distributions
 *  - Tracking IP traffic
 *  - Calculating bandwidth
 *  - Providing snapshot for UI rendering
 *
 * All write operations are protected by mutex.
 */
class Stats {
  private:
	std::mutex mtx;

	uint32_t last_b = 0;

	std::chrono::steady_clock::time_point last_tick;

	std::unordered_map<TransportProtocol, protocolStats> transport_map;
	std::unordered_map<ApplicationProtocol, protocolStats> application_map;
	std::unordered_map<std::string, IPStats> ip_map;

	std::map<std::pair<std::string, std::string>, protocolStats> pairs;

	std::deque<Packet> packets;
	int limit_packets = 10;

	StatsSnapshot snapshot;

  public:
	void push(const Packet &p) {
		std::lock_guard<std::mutex> lock(mtx);
		if (packets.size() > static_cast<long unsigned int>(limit_packets)) {
			packets.pop_front();
		}
		packets.push_back(p);
	}

	StatsSnapshot get_snapshot() {
		std::lock_guard<std::mutex> lock(mtx);
		return snapshot;
	}
	void update_bandwidth();
	double smooth_bandwidth = 0.0;

	void set_packets_limit(int limit) { limit_packets = limit; }

	void add_packet(const Packet &packet);

	void update_transport_stats();
	void update_application_stats();
	void update_ip_stats(size_t limit);
	void update_pairs(size_t limit = 10);
	void update_packets();

	void export_csv(const std::string &filename);
	void export_json(const std::string &filename);

	Stats();
};

#endif // PROTOCOLSTATS_HPP
