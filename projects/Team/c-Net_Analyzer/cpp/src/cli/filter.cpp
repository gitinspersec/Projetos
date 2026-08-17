#include "../../include/cli/filter.hpp"
#include <map>
#include <stdexcept>

filter parse(const std::string &str) {
	const auto pos = str.find(':');
	if (pos == std::string::npos) {
		throw std::invalid_argument("Invalid filter format: '" + str + "' (expected key:value)");
	}

	const std::string type = str.substr(0, pos);
	const std::string value = str.substr(pos + 1);

	if (type == "protocol") {
		return {.type = PROTOCOL, .val = value};
	}
	if (type == "port") {
		return {.type = PORT, .val = value};
	}
	if (type == "dest") {
		return {.type = IP_DEST, .val = value};
	}
	if (type == "src") {
		return {.type = IP_SRC, .val = value};
	}
	if (type == "ip") {
		return {.type = IP_TYPE, .val = value};
	}
	return {.type = NONE, .val = value};
}

std::string get_bpf_filter(const std::vector<filter> &f) {
	std::map<filter_type, std::vector<std::string>> groups;

	for (const auto &x : f) {
		switch (x.type) {
		case PROTOCOL:
			if (x.val == "dns") {
				groups[PROTOCOL].emplace_back("port 53");
			} else if (x.val == "http") {
				groups[PROTOCOL].emplace_back("port 80");
			} else if (x.val == "https") {
				groups[PROTOCOL].emplace_back("port 443");
			} else if (x.val == "ssh") {
				groups[PROTOCOL].emplace_back("port 22");
			} else if (x.val == "ftp") {
				groups[PROTOCOL].emplace_back("port 21");
			} else if (x.val == "smtp") {
				groups[PROTOCOL].emplace_back("port 25");
			} else {
				groups[PROTOCOL].push_back(x.val);
			}
			break;

		case IP_DEST:
			groups[IP_DEST].push_back("dst host " + x.val);
			break;

		case IP_SRC:
			groups[IP_SRC].push_back("src host " + x.val);
			break;

		case PORT:
			groups[PORT].push_back("port " + x.val);
			break;
		case IP_TYPE: {
			if (x.val == "v4" || x.val == "4" || x.val == "ipv4") {
				groups[IP_TYPE].emplace_back("ip");
			} else if (x.val == "v6" || x.val == "6" || x.val == "ipv6") {
				groups[IP_TYPE].emplace_back("ip6");
			} else {
				throw std::invalid_argument("Unknown IP type: '" + x.val + "'");
			}
			break;
		}

		default:
			break;
		}
	}

	std::string result;
	bool first_group = true;

	for (auto &[type, parts] : groups) {
		if (!first_group) {
			result += " and ";
		}
		first_group = false;

		if (parts.size() > 1) {
			result += "(";
		}

		for (size_t i = 0; i < parts.size(); ++i) {
			result += parts[i];
			if (i + 1 < parts.size()) {
				result += " or ";
			}
		}

		if (parts.size() > 1) {
			result += ")";
		}
	}

	return result;
}
