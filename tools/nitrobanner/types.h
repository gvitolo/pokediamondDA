#pragma once

#include <cstdint>

#if defined(_MSC_VER)
#include <filesystem>
namespace filesystem = std::filesystem;
#elif __has_include(<filesystem>)
#include <filesystem>
namespace filesystem = std::filesystem;
#elif __has_include(<experimental/filesystem>)
#include <experimental/filesystem>
namespace filesystem = std::experimental::filesystem;
#else
#error "No filesystem implementation available"
#endif

using u8 = uint8_t;
using u16 = uint16_t;
using u32 = uint32_t;
