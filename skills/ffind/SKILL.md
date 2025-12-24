---
name: ffind
description: Advanced file finder with type detection and filesystem extraction for analyzing firmware and extracting embedded filesystems. Use when you need to analyze firmware files, identify file types, or extract ext2/3/4 or F2FS filesystems.
---

# Ffind - Advanced File Finder with Extraction

You are helping the user find and analyze files with advanced type detection and optional filesystem extraction capabilities using the ffind tool.

## Tool Overview

Ffind analyzes files and directories, identifies file types, and can extract filesystems (ext2/3/4, F2FS) for deeper analysis. It's designed for firmware and IoT device analysis.

## Instructions

When the user asks to analyze files, find specific file types, or extract filesystems:

1. **Understand the target**:
   - Ask what path(s) they want to analyze
   - Determine if they want to extract filesystems or just analyze
   - Ask if they want all file types or just artifact types

2. **Execute the analysis**:
   - Use the ffind command from the iothackbot bin directory
   - Basic usage: `ffind <path> [<path2> ...]`
   - To extract filesystems: `ffind <path> -e`
   - Custom extraction directory: `ffind <path> -e -d /path/to/output`
   - Show all file types: `ffind <path> -a`
   - Verbose output: `ffind <path> -v`

3. **Output formats**:
   - `--format text` (default): Human-readable colored output with type summaries
   - `--format json`: Machine-readable JSON
   - `--format quiet`: Minimal output

4. **Extraction capabilities**:
   - Supports ext2/ext3/ext4 filesystems (requires e2fsprogs)
   - Supports F2FS filesystems (requires f2fs-tools)
   - Requires sudo privileges for extraction
   - Default extraction location: `/tmp/ffind_<timestamp>`

## Examples

Analyze a firmware file to see file types:
```bash
ffind /path/to/firmware.bin
```

Extract all filesystems from a firmware image:
```bash
sudo ffind /path/to/firmware.bin -e
```

Analyze multiple files and show all types:
```bash
ffind /path/to/file1.bin /path/to/file2.bin -a
```

Extract to a custom directory:
```bash
sudo ffind /path/to/firmware.bin -e -d /tmp/my-extraction
```

## Important Notes

- Extraction requires root/sudo privileges
- Requires external tools: e2fsprogs, f2fs-tools, util-linux
- Identifies "artifact" file types relevant to security analysis by default
- Use `-a` flag to see all file types including common formats
