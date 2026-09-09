#include "../../include/cli/argsParse.hpp"
#include <iostream>

argsParser::argsParser(int argc, char **argv) {
	desc.add_options()("help,h", "Display this help message and exit")("interfaces, interfaces",
																	   "Display all possible interfaces")(
		"interface,i", po::value<std::string>()->default_value("wlan0"),
		"Network interface to capture packets from (e.g. eth0, wlan0, any)")

		("count,c", po::value<int>()->default_value(0), "Number of packets to capture (0 = unlimited)")(
			"time, t", po::value<int>()->default_value(INT_MAX), "Working time (in seconds)")

			("offline,r", po::value<std::string>(), "Read packets from an offline pcap file")

				("filter,f", po::value<std::vector<std::string>>()->composing(),
				 "Traffic filter (can be used multiple times)\n"
				 "  proto:<name>   tcp | udp | icmp | dns\n"
				 "  src:<ip>       Source IP address\n"
				 "  dst:<ip>       Destination IP address\n"
				 "  port:<number>  Source or destination port")

					("sort,s", po::value<std::string>()->default_value("bytes"), "Sort field: bytes | packets | ip")

						("order,o", po::value<std::string>()->default_value("desc"), "Sort order: asc | desc")

							("limit,n", po::value<int>()->default_value(43), "Limit number of displayed entries")

								("csv", po::value<std::string>(), "Export analysis results to CSV file")

									("json", po::value<std::string>(), "Export analysis results to JSON file");

	po::store(po::parse_command_line(argc, argv, desc), vm);
	po::notify(vm);
}

void argsParser::print_help() const {
	std::cout << "Network Traffic Analyzer\n"
				 "========================\n\n"
				 "Usage:\n"
				 "  ./network-traffic-analyzer [options]\n\n"
				 "Description:\n"
				 "  Captures and analyzes network traffic from live interfaces or\n"
				 "  offline pcap files. Provides protocol statistics, top talkers,\n"
				 "  and bandwidth usage information.\n\n";

	std::cout << desc << "\n";

	std::cout << "Examples:\n"
				 "  ./network-traffic-analyzer -i wlan0 --count 100 --time 10\n"
				 "  ./network-traffic-analyzer -i any --filter port:54\n"
				 "  ./network-traffic-analyzer --offline traffic.pcap --json result.json\n\n";

	std::cout << "To end the program, press 'q' or Esc to exit.\n";
}