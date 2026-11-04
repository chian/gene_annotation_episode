// Packet-only harness of the unmodified official hictk 2.2.0 writer API.
#include <hictk/hic.hpp>
#include <hictk/hic/file_writer.hpp>
#include <hictk/balancing/weights.hpp>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv) {
  if (argc != 4) return 64;
  try {
    const std::string variant{argv[3]};
    std::vector<double> values{1.0, 2.0, 1.0, 2.0};
    if (variant == "nan") values[1] = std::numeric_limits<double>::quiet_NaN();
    else if (variant == "zero") values[1] = 0.0;
    else if (variant == "negative") values[1] = -2.0;
    else if (variant == "inf") values[1] = std::numeric_limits<double>::infinity();
    else if (variant == "short") values.pop_back();
    else if (variant == "long") values.push_back(5.0);
    else if (variant != "valid") throw std::invalid_argument("unknown explicitly selected variant");
    std::filesystem::copy_file(argv[1], argv[2]);
    hictk::hic::internal::HiCFileWriter writer{argv[2], 2};
    const hictk::balancing::Weights weights{values, hictk::balancing::Weights::Type::DIVISIVE};
    writer.add_norm_vector("SYNTHETIC_DIVISIVE", writer.chromosomes().at("chrA"), "BP", 10, weights);
    writer.write_norm_vectors_and_norm_expected_values();
    std::cout << "official add_norm_vector completed: " << variant << '\n';
    return 0;
  } catch (const std::exception& exception) {
    std::cerr << exception.what() << '\n';
    return 2;
  }
}
