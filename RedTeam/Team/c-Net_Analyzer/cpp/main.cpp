#include "include/capture/pcapCapture.hpp"
#include "include/cli/filter.hpp"
#include <boost/program_options.hpp>
#include <ftxui/component/component.hpp>
#include <ftxui/component/component_options.hpp>
#include <ftxui/component/screen_interactive.hpp>
#include <iostream>
#include <pcap/pcap.h>

#include "include/TUI/view.hpp"
#include "include/cli/argsParse.hpp"

int main(int argc, char **argv) {
	/* initialize stats */
	Stats stats;
	/* initialize capture */
	PcapCapture capture;
	capture.initialize();

	/* initializing the command line parser */
	argsParser parser(argc, argv);

	/* check helper flags */
	if (parser.vm.contains("help")) {
		parser.print_help();
		return 0;
	}
	if (parser.vm.contains("interfaces")) {
		capture.print_interfaces();
		return 0;
	}
	/* take the arguments of the flags into variables */
	std::string interface = parser.vm["interface"].as<std::string>();
	int count = parser.vm["count"].as<int>();
	int limit = parser.vm["limit"].as<int>();
	int time = parser.vm["time"].as<int>();
	std::string filterString = "";

	/* get a filter, use vector for multiple  */
	std::vector<filter> filters;
	if (parser.vm.contains("filter")) {
		const auto &f = parser.vm["filter"].as<std::vector<std::string>>();
		for (const auto &x : f) {
			filters.push_back(parse(x));
			filterString += x + " ";
		}
	}
	/* converting the filter to a pcap readable string */
	std::string expression = get_bpf_filter(filters);

	bool isOffline = parser.vm.contains("offline");

	/* set the flags to capture engine */
	capture.set_capabilities(interface, count, expression, limit, &stats);

	std::atomic<bool> capture_finished = false;
	std::atomic<bool> ui_running = true;
	/* if we capture packets offline, we read the file in full, then print the result */
	if (isOffline) {

		capture.start_offline(parser.vm["offline"].as<std::string>());

		/* full recalculation of statistics after file processing */
		stats.update_packets();
		stats.update_application_stats();
		stats.update_transport_stats();
		stats.update_ip_stats(10);
		stats.update_pairs();
		stats.update_bandwidth();
	}
	/* otherwise start live capture */
	else {
		capture.start();
	}

	/* UI */
	// Timer
	std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
	std::atomic<std::chrono::seconds> timer;
	auto screen = ftxui::ScreenInteractive::Fullscreen();

	/* our class for UI */
	View view;
	std::mutex render_mtx;
	ftxui::Element current_render = isOffline
										? view.render(stats.get_snapshot(), interface, filterString, true, timer.load())
										: ftxui::text("Starting capture...");

	auto component = ftxui::Renderer([&] {
		std::lock_guard<std::mutex> lock(render_mtx);
		return current_render;
	});

	component |= ftxui::CatchEvent([&](ftxui::Event e) {
		if (e == ftxui::Event::Character('q') || e == ftxui::Event::Escape) {
			ui_running = false;
			screen.Exit();
			return true;
		}
		return true;
	});
	std::thread application_thread;
	if (!isOffline) {
		application_thread = std::thread([&] {
			while (!capture_finished && ui_running) {

				auto now = std::chrono::steady_clock::now();
				timer.store(std::chrono::duration_cast<std::chrono::seconds>(now - begin));

				if (timer.load() >= std::chrono::seconds(time) || !capture.isRunning()) {
					capture_finished = true;
				}

				stats.update_packets();
				stats.update_application_stats();
				stats.update_transport_stats();
				stats.update_ip_stats(10);
				stats.update_pairs();
				stats.update_bandwidth();

				ftxui::Element new_frame =
					view.render(stats.get_snapshot(), interface, filterString, capture_finished, timer.load());
				{
					std::lock_guard<std::mutex> lock(render_mtx);
					current_render = new_frame;
				}
				if (ui_running) {
					screen.PostEvent(ftxui::Event::Custom);
				}

				// std::this_thread::sleep_for(std::chrono::milliseconds(500));
			}
		});
	}

	screen.Loop(component);

	ui_running = false;
	capture_finished = true;

	if (application_thread.joinable())
		application_thread.join();

	// Export stats if needed
	if (parser.vm.contains("csv"))
		stats.export_csv(parser.vm["csv"].as<std::string>());
	if (parser.vm.contains("json"))
		stats.export_json(parser.vm["json"].as<std::string>());

	return 0;
}
