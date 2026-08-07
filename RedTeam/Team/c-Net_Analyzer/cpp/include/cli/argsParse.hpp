#ifndef ARGSPARSE_HPP
#define ARGSPARSE_HPP
#include <boost/program_options.hpp>

namespace po = boost::program_options;
struct argsParser {
	po::options_description desc;
	po::variables_map vm;
	void print_help() const;

	argsParser(int argc, char **argv);
};

#endif // ARGSPARSE_HPP
